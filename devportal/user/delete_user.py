from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models import Users
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger

# 사용자 탈퇴(DB 삭제)
def process_delete_user(db:Session, current_user:dict):
    '''
    - 사용자 탈퇴
    - 해당 사용자 정보 삭제
    - Users Table에서 삭제 및 참조하는 API_Key Table에서도 삭제(on delete cascade)
    '''
    try:
        # 현재 사용자 정보 가져오기
        current_user = current_user.get("user_id")
        
        # 사용자 정보가 없는 경우
        if not current_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User Not Found")
                    
        user_info = db.query(Users).filter(Users.user_id == current_user).first()
        
        # 사용자 정보 삭제
        db.delete(user_info)
        db.commit()
        
        logger.info(f"User {current_user} deleted successfully")
        
        return {"status" : status.HTTP_200_OK,
                "message" : "User deleted successfully"}
      
    except Exception as e:
        db.rollback()
        logger.error(f'Error: {e}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error")