from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import Users
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger

def process_register_uuid(user_uuid:str, current_user:str, db:Session):
    '''
    OStools에서 사용자 카드에 담겨있는 UUID를 Users 테이블에 저장
    '''
    try:
        
        current_user = current_user
        
        users_record = db.query(Users).filter(Users.user_id == current_user).first()
        
        if not users_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid User")
        
        # if users_record.user_uuid:
        #     raise HTTPException(status_code=status.HTTP_409_CONFLICT,
        #                         detail="Alreay Existing UUID in Users Table")
        
        users_record.user_uuid = user_uuid
        db.commit()
        logger.info(f"Success Add Your UUID")
        
        return {
            "status" : status.HTTP_200_OK,
            "message" : "UUID registered successfully!"
        }
    except HTTPException as he:
        logger.error(f"HTTP Exception occurred: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error registering {current_user}'s UUID: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while registering UUID"
        )