from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from messaging.rabbitmq import RabbitMQ
from devportal_schemes import ShareSchedule
from common.models.models import Calendar
from custom_log import LoggerSetup
import json

logger_setup = LoggerSetup()
logger = logger_setup.logger

async def shareSchedule(schedule_id:int,
                        db:AsyncSession,
                        current_user:dict):
    """
    Schedule 공유 - RabbitMQ 활용하여 Push Server로 메시지 생성
    Args:
        - schedule_id: 해당 일정 id
        - db: 비동기 DB 세션
        - current_usr: 현재 로그인한 사용자
    return:
        - producing status
    """
    try:
        # STEP 1. 일정 조회 및 권한 확인
        result = await db.execute(
            select(Calendar)
            .options(selectinload(Calendar.user))
            .where(Calendar.idx == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                detail="일정을 찾을 수 없음")
        if schedule.user_id != current_user['uid']:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="공유 권한 없음")
        message = {
            "[일정 공유]": ShareSchedule(
                idx=schedule.idx,
                title=schedule.title,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                creator=current_user['user_name']
            ).model_dump(mode='json')
        }
        
        with RabbitMQ() as rmq:
            rmq.declare_queue(queue_name="schedule")
            rmq.publish(
            queue_name="schedule",
            message=json.dumps(message)
        )
        return {"status":"success",
                "message":"공유 요청 큐에 추가됨"}    
    except HTTPException as he:
        logger.error(f"공유 실패 - 사용자 오류: {str(he)}")
        raise he
    except Exception as e:
        logger.exception("Occured Unexpected Error!")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error")