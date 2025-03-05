from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from ..user.login import current_user_info
from models import API_Key
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger

def process_remove_service(client_id:str, db:Session, current_user=Depends(current_user_info)):
    '''
    - Devportal에 등록된 Service Application 삭제
    :Args
    - client_id : 삭제할 서비스의 client_id(JSON key)
    '''
    try:
        _user = current_user["user_id"]
        api_key_record = db.query(API_Key).filter(API_Key.user_id == _user).first()
        
        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registered services found")
        
        registered_service = api_key_record.registered_service
        
        # client_id가 존재하는지 확인
        if client_id not in registered_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found")
        
        # 서비스 정보 삭제
        # JSON Type: Key값 삭제
        service_name = registered_service[client_id]["service_name"]
        del registered_service[client_id]
        
        api_key_record.registered_service = registered_service
        db.commit()
        
        return {
            "message" : "Service removed Successfully",
            "removed_service" : {
                "client_id" : client_id,
                "service_name" : service_name
            }
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error Occured:{str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing service: {str(e)}"
        )
    
    
    