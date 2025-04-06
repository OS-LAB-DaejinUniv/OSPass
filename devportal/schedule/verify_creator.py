from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from common.models.models import Calendar

async def verify_creator(db:AsyncSession,
                         schedule_id:int,
                         user_id:str):
    """일정 수정/삭제 시 작성자 여부 판단"""
    
    query = select(Calendar).where(
        (Calendar.idx==schedule_id) & (Calendar.user_id==user_id)
        )
    result = await db.execute(query)
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="작성자만 수정/삭제 가능합니다.")
    return schedule
