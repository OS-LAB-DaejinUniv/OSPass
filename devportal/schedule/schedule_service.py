from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from zoneinfo import ZoneInfo
from common.models.models import Calendar, Users
from devportal_schemes import ScheduleCreate, ScheduleResponse
from schedule.verify_creator import verify_creator
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger

async def create_schedule(data:ScheduleCreate,
                          db:Session,
                          current_user: dict)->ScheduleResponse:
    """
    Calendar 일정 작성 (개인 별 작성)
    Args:
        - calendar : 달력에 작성할 내용(제목, 내용, 일정 시작, 일정 종료, timezone)
        - current_user : 현재 로그인한 사용자의 uid 정보
    return:
        - DB insert Result 
    """
    try:
        # 시간대 유효성 검사
        if not data.start_time.tzinfo or not data.end_time.tzinfo:
            raise HTTPException(
                status_code=400,
                detail="시간대 정보가 포함된 datetime을 전송해야 합니다."
            )

        # 클라이언트 시간대를 서버 UTC로 변환
        start_time_utc = data.start_time.astimezone(ZoneInfo("UTC"))
        end_time_utc = data.end_time.astimezone(ZoneInfo("UTC"))

        # DB 모델 생성
        new_schedule = Calendar(
            title=data.title,
            content=data.content,
            start_time=start_time_utc,
            end_time=end_time_utc,
            time_zone=data.time_zone,
            user_id=current_user['uid']
        )

        # 비동기 DB 작업
        db.add(new_schedule)
        await db.commit()
        await db.refresh(new_schedule)

        # 응답 모델로 변환
        return ScheduleResponse(
            idx=new_schedule.idx,
            title=new_schedule.title,
            content=new_schedule.content,
            start_time=new_schedule.start_time.astimezone(ZoneInfo(data.time_zone)),
            end_time=new_schedule.end_time.astimezone(ZoneInfo(data.time_zone)),
            time_zone=data.time_zone,
            creator=current_user.get('user_name', 'Unknown')
        )

    except HTTPException as he:
        await db.rollback()
        logger.error(f"HTTP Error: {he.detail}")
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="일정 생성 중 오류가 발생했습니다."
        )

async def fetch_schedule(db: AsyncSession) -> list[ScheduleResponse]:
    """일정 조회 서비스 로직"""
    try:
        result = await db.execute(
            select(Calendar)
            .options(selectinload(Calendar.user))  # 사용자 데이터 즉시 로딩
        )
        calendars = result.scalars().all()

        return [
            ScheduleResponse(
                idx=calendar.idx,
                title=calendar.title,
                content=calendar.content,
                start_time=calendar.start_time.astimezone(ZoneInfo("Asia/Seoul")),
                end_time=calendar.end_time.astimezone(ZoneInfo("Asia/Seoul")),
                time_zone="Asia/Seoul",
                creator=calendar.user.user_name if calendar.user else "Unknown" # 관계 확인
            ) for calendar in calendars
        ]
        
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query failed"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

async def update_schedule(schedule_id:int,
                          data:ScheduleCreate,
                          db:AsyncSession,
                          current_user:dict)-> ScheduleResponse:
    """
    Calender 내용 변경 (작성자만 변경 가능)
    verify_creator func로 작성자 여부 판단
    Args:
        - schedule_id: 등록된 일정 id(idx)
        - data: 생성했던 일정 data schema
        - current_user: 현재 로그인한 사용자
    """
    try:
        uid = current_user['uid']
        schedule = await verify_creator(db, schedule_id, uid)
        # 시간대 변환 UTC -> Asia/Seoul
        seoul_timezone = ZoneInfo("Asia/Seoul")
        utc_timezone = ZoneInfo("UTC")
        print(f"Local Time:{seoul_timezone}")
        if data.start_time.tzinfo is None or data.end_time.tzinfo is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="시간대 정보가 포함된 datetime을 전달해야합니다."
            )
        # 일정 시작 & 종료 Time 
        start_time_utc = data.start_time.replace(tzinfo=seoul_timezone).astimezone(utc_timezone)
        end_time_utc = data.end_time.replace(tzinfo=seoul_timezone).astimezone(utc_timezone)
        
        schedule.title = data.title
        schedule.content = data.content
        schedule.start_time = start_time_utc
        schedule.end_time = end_time_utc
        
        await db.commit()
        await db.refresh(schedule)
        return ScheduleResponse(
            idx=schedule.idx,
            title=schedule.title,
            content=schedule.content,
            start_time=schedule.start_time.astimezone(ZoneInfo(data.time_zone)),
            end_time=schedule.end_time.astimezone(ZoneInfo(data.time_zone)),
            time_zone=data.time_zone,
            creator=current_user['user_name']
        )
    except HTTPException as he:
        await db.rollback()
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Error Occured while Updating Schedule: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Update Schedule Error")
        
async def delete_schedule(schedule_id:int,
                          db:AsyncSession,
                          current_user:dict):
    """
    Calendar 내용 삭제 (작성자만 삭제 가능)
    verify_creator func로 작성자 여부 판단
    Args:
        - schedule_id: 등록된 일정 id(idx)
        - current_user: 현재 로그인한 사용자
    return:
        - Delete Complete Message
    """
    try:
        uid = current_user['uid']
        schedule = await verify_creator(db, schedule_id, uid)
        
        await db.delete(schedule)
        await db.commit()
        
        return {"status" : status.HTTP_200_OK,
                "message" : "Schedule deleted successfully"}
    except HTTPException as he:
        await db.rollback()
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Error Occured whiel Delte Schedule:{str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Delete Schedule Error")