# Devportal에서 OSPASS 사용 서비스 Redirect URI 등록

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from models import API_Key
from custom_log import LoggerSetup
from ..devportal_schemes import RegisterRedirectUri

logger_setup = LoggerSetup()
logger = logger_setup.logger

# redirect_uri 작성 및 저장
# JSON Format
# key : client_id, 
# value : Service name, redirec_uri(여러개 가능), apikey 
def process_register_redirect_uri(data : RegisterRedirectUri, 
                                        db:Session, 
                                        current_user:dict):
    '''
    - Redirect URI Register or Update
    - 현재 사용자 user_id를 register_service(JSONB)에 매핑
    '''
    # 현재 사용자 user_id 가져오기
    # current_user_info return value => user_id
    user_id = current_user["user_id"]
    logger.debug(f'Current User ID: {user_id}')
    
    # API_Key Table 특정 Record
    api_key_record = db.query(API_Key).filter(API_Key.user_id == user_id).first()
    
    if not api_key_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User Not Found")
    
    # 현재 registered_service 데이터 가져오기
    if api_key_record.registered_service is None:
        api_key_record.registered_service = {}

    # client_id(key) 존재 여부 판단
    if data.client_id not in api_key_record.registered_service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Client ID not registered")
    
    # 새로운 URI 목록에서 중복 제거
    # set() : 중복 방지
    new_uris = list(set(str(uri) for uri in data.redirect_uri))
    logger.debug(f'New Redirect URI: {new_uris}')
    
    # URI가 비어있는 경우 처리
    if not new_uris:
        api_key_record.registered_service[data.client_id]["redirect_uri"] = []
    else:
        # URI 목록 내 중복 검사 및 유효성 검사
        seen_uris = set()
        valid_uris = []
        for uri in new_uris:
            uri = uri.strip()  # 앞뒤 공백 제거
            if uri and uri not in seen_uris:  # 빈 문자열이 아니고 중복되지 않은 경우
                seen_uris.add(uri)
                valid_uris.append(uri)
        
        logger.debug(f'Valid URIs after deduplication: {valid_uris}')
        api_key_record.registered_service[data.client_id]["redirect_uri"] = valid_uris

    flag_modified(api_key_record, "registered_service")
    logger.debug(f'After update: {api_key_record.registered_service}')
    
    try:
        db.commit()
        print("DB commit 완료")
        db.refresh(api_key_record)
        print(f"Db refresh 완료 후 :{api_key_record.registered_service}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Database Commit Failed:{e}")
    
    return {
        "message" : "Redirect URIs updated successfully!",
        "redirect_uris" : api_key_record.registered_service[data.client_id]["redirect_uri"]
    }

# 작성한 redirect uri 가져오기
def get_service_redirect_uri(service_name:str, db:Session, current_user : dict):
    '''
    - Redirect URI Select
    - Service Name과과 매핑된 redirect_uri를 보여줌
    '''
    user_id = current_user["user_id"]
    # apikey table user_id 기준 row
    api_key_record = db.query(API_Key).filter(API_Key.user_id == user_id).first()
    
    if not api_key_record:
        logger.error(f'Is Not {user_id}')
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User Not Found")
    
    # 등록된 서비스 JSON 불러오기
    registered_services = api_key_record.registered_service
    
    # service_name에 해당하는 client_id 찾기
    # cid : client_id, service_info : registered_service value
    client_id = None
    for cid, service_info in registered_services.items():
        if service_info.get("service_name") == service_name:
            client_id = cid
            break
    
    if not client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Service {service_name} not found")
    
    redirect_uris = registered_services[client_id].get("redirect_uri", [])
    
    return {
        "service_name" : service_name,
        "client_id" : client_id,
        "redirect_uris" : redirect_uris
    }
    
    