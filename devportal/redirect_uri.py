# Devportal에서 OSPASS 사용 서비스 Redirect URI 등록

from fastapi import HTTPException, status, Response, Depends
from sqlalchemy.orm import Session

from login import current_user_info
from models import API_Key
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger

# redirect_uri 작성 및 저장
# JSON Format
# key : client_id, 
# value : Service name, redirec_uri(여러개 가능), apikey 
def process_register_redirect_uri(client_id:str, service_name:str, redirect_uris:list[str], apikey:str, 
                                  response:Response, db:Session, current_user:dict=Depends(current_user_info)):
    '''
    - Redirect URI Register or Update
    - 현재 사용자 user_id를 register_service(JSONB)에 매핑
    '''
    # 현재 사용자 user_id 가져오기
    # current_user_info return value => user_id
    user_id = current_user["user_id"]
    
    # JSON KEY filtering(키가 존재한다는 것 -> 등록 X, 업데이트 O) 
    # 해당 user_id(current user)의 데이터만 확인
    existing_service = db.query(API_Key).filter(API_Key.registerd_service in client_id, 
                                                API_Key.user_id == user_id).first()
    
    if not existing_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'API KEY not found for Current User({user_id})'
        )
    # cliet: client_id, redirect_uri, apikey ...     
    client_data = existing_service.registerd_service[client_id]
    
    if existing_service:
        # 기존 데이터가 있으면 업데이트    
        # service_name or api_key 업데이트
        if client_data["service_name"] != service_name:
            client_data["service_name"] = service_name
            
        if client_data["apikey"] != apikey:
            client_data["apikey"] = apikey
        
        # redirect_uri 추가(중복 확인)
        for uri in redirect_uris:
            if uri not in client_data["redirect_URI"]:
                client_data["redirect_URI"].append(uri)
        logger.info(f"Client({client_id}) : Updated redirect_uri({redirect_uris})")
        
    else:
        new_register_service = API_Key(
            register_service={
                client_id : {
                    "service_name" : service_name,
                    "redirect_URI" : redirect_uris, # List Type: 여러 개의 redirect uri 등록 
                    "apikey" : apikey
                }
            }
        )
        new_service = API_Key(register_service=new_register_service)
        db.add(new_service)
        existing_service = new_service # Return 값 통일
        logger.info(f"Client({client_id}) Created redirect_uri({redirect_uris})")
    
    db.commit()
    db.refresh(existing_service)
    
    return {"service" : existing_service, "status" : response.status_code}