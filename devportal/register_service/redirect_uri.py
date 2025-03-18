# Devportal에서 OSPASS 사용 서비스 Redirect URI 등록

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional
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
    _uid = current_user["uid"]

    # API_Key Table 특정 Record
    api_key_record = db.query(API_Key).filter(API_Key.uid == _uid).first()
    
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

def get_service_redirect_uri(idx: int, 
                             client_id: Optional[str], 
                             db: Session, 
                             current_user: dict):
    '''
    - Redirect URI Show(조회)
    - 현재 사용자 uid를 register_service(JSONB)에 매핑
    '''
    _uid = current_user["uid"]
    
    # API Key 레코드 조회 (UID + Index)
    api_key_record = db.query(API_Key).filter(
        API_Key.uid == _uid,
        API_Key.idx == idx
    ).first()
    
    if not api_key_record:
        raise HTTPException(404, "API Key not found")
    
    registered_services = api_key_record.registered_service or {}
    
    # Client ID 필터링
    if client_id:
        service_info = registered_services.get(client_id)
        if not service_info:
            raise HTTPException(404, "Client ID not found")
        
        return {
            "idx": idx,
            "client_id": client_id,
            "service_name": service_info.get("service_name"),
            "redirect_uris": service_info.get("redirect_uri", [])
        }
    
    # 전체 서비스 반환
    return {
        "idx": idx,
        "services": {
            cid: {
                "service_name": info.get("service_name"),
                "redirect_uris": info.get("redirect_uri", [])
            } for cid, info in registered_services.items()
        }
    }
    