# Devportal에서 OSPASS 사용 서비스 Redirect URI 등록

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import API_Key
from custom_log import LoggerSetup
from .devportal_schemes import RegisterRedirectUri

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
    
    # API_Key Table 특정 Record
    api_key_record = db.query(API_Key).filter(API_Key.user_id == user_id).first()
    
    if not api_key_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User Not Found")
    
    # 현재 registered_service 데이터 가져오기
    registered_service = api_key_record.registered_service or {}
    print(type(registered_service))
    # client_id(key) 존재 여부 판단
    if data.client_id not in registered_service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Client ID not registered")
    
    # 기존 redirect_uri 가져오기
    existing_uris = set(registered_service[data.client_id].get("redirect_uri", []))
    new_uris = set(str(uri) for uri in data.redirect_uri)
    print(f'기존 redirect uri:{existing_uris}')
    
    # 중복 방지
    if new_uris.issubset(existing_uris):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="No new redirect URIs to add")
    
    # 업데이트된 redirect_uri 저장
    registered_service[data.client_id]["redirect_uri"] = list(existing_uris | new_uris)
    print(f'변경 전:{api_key_record.registered_service}')
    api_key_record.registered_service = registered_service
    print(f'변경 후:{api_key_record.registered_service}')
    
    db.commit()
    print("DB commit 완료")
    db.refresh(api_key_record)
    print("Db refresh 완료")
    print(f'Db commit 완료 후:{api_key_record.registered_service}')
    
    return {
        "message" : "Redirect URIs updated successfully!",
        "redirect_uris" : registered_service[data.client_id]["redirect_uri"]
    }