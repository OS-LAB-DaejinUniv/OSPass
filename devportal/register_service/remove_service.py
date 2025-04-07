from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from auth.currentUser import current_user_info
from common.models.models import API_Key
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
        _uid = current_user["uid"]
        api_key_record = db.query(API_Key).filter(API_Key.uid == _uid).all()
        
        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registered services found")
        
        service_removed = False
        removed_service_info = {}
        # 2. 모든 API Key 순회
        for api_key in api_key_record:
            registered_services = api_key.registered_service or {}
            
            if client_id in registered_services:
                # 3. 서비스 정보 추출 후 삭제
                service_info = registered_services[client_id]
                del registered_services[client_id]
                
                # 4. 변경 사항 저장
                api_key.registered_service = registered_services
                db.commit()
                
                removed_service_info = {
                    "client_id": client_id,
                    "service_name": service_info.get("service_name"),
                    "idx": api_key.idx
                }
                print(f"Service removed: {removed_service_info}")
                service_removed = True
                break  # 첫 번째 발견된 서비스 삭제 후 종료

        if not service_removed:
                raise HTTPException(404, f"Service {client_id} not found in any API keys")
            
        return {
                "message": "Service removed successfully",
                "removed_service": removed_service_info
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
    
    
    