from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from common.models.models import API_Key, Users
from custom_log import LoggerSetup
logger_setup = LoggerSetup()
logger = logger_setup.logger

def show_service(db:Session, current_user_uid:str):
    '''
    사용자가 등록한 Service에 대한 정보를 보여주는 함수
    :return service_list (service name, client_id, apikey)
    '''
    _uid = current_user_uid['uid']
    user = db.query(Users).filter(Users.uid == _uid).first() # User Table Row 추출 -> user_id 추출하고 싶음
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User Not Found for user:{_uid}")
    # API_Key Table Row 추출
    row_api_key = db.query(API_Key).filter(API_Key.uid == _uid).first()
    if not row_api_key:
        # 등록된 서비스가 없는 경우 빈 배열 반환
        return {"services": []}
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