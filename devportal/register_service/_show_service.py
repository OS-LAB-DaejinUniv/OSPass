from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from models import API_Key
import json

from ..user.login import current_user_info

from custom_log import LoggerSetup
logger_setup = LoggerSetup()
logger = logger_setup.logger

def show_service(db:Session, current_user=Depends(current_user_info)):
    '''
    사용자가 등록한 Service에 대한 정보를 보여주는 함수
    :return service_list (service name, client_id, apikey)
    '''
    
    user_id = current_user["user_id"]
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid User")
    # API_Key Table Row 추출
    row_api_key = db.query(API_Key).filter(API_Key.user_id == user_id).first()
    if not row_api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Result Not Found for user:{user_id} ")
    # registered_service 컬럼(JSONB 데이터) 파싱
    try:
        service_data = row_api_key.registered_service # JSONB 타입 필드 접근
        print(f'service_data type: {type(service_data)}')
        if not service_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="registered_service is not found")
            
        # 각 서비스 정보 추출(Service Name, Api key, Client ID)
        service_list = []
        for client_id, service_info in service_data.items():
            service_list.append({
                "client_id" : client_id,
                "apikey" : service_info.get("apikey"),
                "service_name" : service_info.get("service_name")
            })
        
        return {"services" : service_list}
    
    except Exception as e:
        logger.error(f"Select Service List Error{e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Failed for Selecting Serivce List")