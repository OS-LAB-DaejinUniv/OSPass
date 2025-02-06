"""
Devportal에서 User가 Service Name 등록  
"""
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from .login import current_user_info # 현재 user info 확인
from models import API_Key
from custom_log import LoggerSetup
import string
import random

logger_setup = LoggerSetup()
logger = logger_setup.logger

def gen_client_id():
    '''
    - client_id 생성
    - random string + number  
    '''
    client_id = string.ascii_letters + string.digits
    return f'ospass-{"".join(random.choices(client_id, k=23)).lower()}'

def gen_api_key():
    '''
    - API KEY 생성 : string type
    '''
    apikey = hex(random.getrandbits(128))[2:]
    return apikey

def process_register_service(register_service_name:str, db:Session, 
                                  current_user=Depends(current_user_info)):
    '''
    - 사용자 Service 등록
    - 현재 사용자 검증
    - service name 등록
    '''
    # 현재 사용자 user_id
    user_id = current_user["user_id"]
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid User")
    # client_id 생성 함수 호출
    client_id = gen_client_id()
    
    # API KEY 생성 함수 호출
    api_key = gen_api_key()
    
    # 기존 API_Key 테이블 데이터 존재 여부
    existing_api_key = db.query(API_Key).filter(API_Key.user_id == user_id).first()
    
    if existing_api_key:
        # 기존 데이터 업데이트
        registered_services = existing_api_key.registered_service or {}
        registered_services[client_id] = {
            "service_name":register_service_name,
            "apikey":api_key,
            "redirect_uri" : [] # 초기 Empty List -> redirect_uri 등록
        }
        existing_api_key.registered_service = registered_services
        
    else:
        # 새 데이터 생성
        new_service = API_Key(
            user_id=user_id,
            apikey=api_key,
            register_service={
                client_id:{
                    "service_name":register_service_name,
                    "apikey": api_key,
                    "redirect_uri":[]
                }
            }
        )
        db.add(new_service)
        logger.info(f"Created New Service {register_service_name} from client_id {client_id}")
        
    db.commit()
    
    return {"client_id":{client_id}, "api_key":{api_key}}

