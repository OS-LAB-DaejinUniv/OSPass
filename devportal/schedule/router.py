"""
Schedule API Router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from zoneinfo import ZoneInfo
from devportal_schemes import ScheduleCreate, ScheduleResponse, ShareSchedule
from common.database.async_postgre import get_async_db
from common.models.models import Calendar
from schedule.schedule_service import create_schedule, fetch_schedule, update_schedule, delete_schedule
from schedule.share import shareSchedule
from auth.currentUser import current_user_info
from custom_log import LoggerSetup

schedule_router = APIRouter(prefix="/api", tags=["Devportal Schedule Service"])

logger_setup = LoggerSetup()
logger = logger_setup.logger

@schedule_router.post("/v1/calendars")
async def createSchedule(schedule:ScheduleCreate,
                         db:AsyncSession=Depends(get_async_db),
                         current_user:dict=Depends(current_user_info)):
    """
    공통 달력에 스케줄을 등록 API
    """
    return await create_schedule(schedule, db, current_user)

@schedule_router.get("/v1/calendars", response_model=list[ScheduleResponse])
async def getAllSchedule(db:AsyncSession=Depends(get_async_db)):
    """
    공통 달력에 작성된 일정 조회 API
    로그인한 모든 사용자가 조회 가능
    """
    try:
        return await fetch_schedule(db)
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)

@schedule_router.get("/v1/calendars/{schedule_id}", response_model=ScheduleResponse)
async def getSingleSchedule(schedule_id:int,
                            db:AsyncSession=Depends(get_async_db)):
    """
    개별 스케줄 조회 API
    """
    query = select(Calendar).options(selectinload(Calendar.user)).where(
        Calendar.idx== schedule_id)
    result = await db.execute(query)
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ScheduleResponse(
        idx=schedule.idx,
        title=schedule.title,
        content=schedule.content,
        start_time=schedule.start_time.astimezone(ZoneInfo("Asia/Seoul")),
        end_time=schedule.end_time.astimezone(ZoneInfo("Asia/Seoul")),
        time_zone="Asia/Seoul",
        creator=schedule.user.user_name if schedule.user else "Unknown"
    )
    
@schedule_router.put("/v1/calendars/{schedule_id}")
async def updateSchedule(schedule_id:int,
                         data:ScheduleCreate,
                         db:AsyncSession=Depends(get_async_db),
                         current_user:dict=Depends(current_user_info)):
    """
    공통 달력에 작성자가 작성한 일정 수정 API
    작성자만 수정 허용
    """
    return await update_schedule(schedule_id, data, db, current_user)

@schedule_router.delete("/v1/calendars/{schedule_id}")
async def deleteSchedule(schedule_id:int,
                         db:AsyncSession=Depends(get_async_db),
                         current_user:dict=Depends(current_user_info)):
    """
    공통 달력에 작성된 일정 삭제 API
    작성자만 삭제 허용
    """
    return await delete_schedule(schedule_id, db, current_user)

@schedule_router.post("/v1/calendars/share/{schedule_id}")
async def shareScheduleToRMQ(schedule_id:int,
                       db:AsyncSession=Depends(get_async_db),
                       current_user:dict=Depends(current_user_info)):
    """
    공통 달력에 작성된 일정 Broker에게 발행하는 API 
    """
    return await shareSchedule(schedule_id, db, current_user)