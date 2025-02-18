# Devportal에서 OSPASS 사용 서비스 Redirect URI 등록

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

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
    
    # 기존 redirect_uri 가져오기
    existing_uris = set(api_key_record.registered_service[data.client_id].get("redirect_uri", []))
    new_uris = set(str(uri) for uri in data.redirect_uri)
    logger.debug(f'기존 redirect uri:{existing_uris}')
    
    # 중복 방지
    if new_uris.issubset(existing_uris):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="No new redirect URIs to add")
    
    logger.debug(f'Before update:{api_key_record.registered_service}')
    # 업데이트된 redirect_uri 저장
    api_key_record.registered_service[data.client_id]["redirect_uri"] = list(existing_uris | new_uris)
    
    ## flag_modified : JSONB 컬럼 변경 사항 명시적 알림 ## 
    # sqlalchemy -> JSONB, ARRAY, HSTORE 같은 '복합 데이터 타입'을 다룰 때
    # 변경 사항 자동 감지 못 하는 경우 있음
    flag_modified(api_key_record, "registered_service")
    logger.debug(f'After update:{api_key_record.registered_service}')
    
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