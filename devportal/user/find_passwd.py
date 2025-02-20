from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from models import Users
from custom_log import LoggerSetup
from passlib.context import CryptContext
import httpx
import string
import random
import os

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger_setup = LoggerSetup()
logger = logger_setup.logger

# SMS 전송 기능
def send_sms(phone : str, content : str) -> bool:
    '''
    비밀번호 찾기 API 사용될 SMS 전송 기능 Function  
    - phone : 해당 아이디 유저의 전화번호
    - content : 전송할 메시지 내용
    '''
    # 전화번호 유효성 검증(숫자로만 구성, 문자 X)
    if not phone or not phone.isdigit():
        raise ValueError("Invalid phone number")
    
    # SmartLab SMS API Endpoint
    endpoint = "https://smartlab.os-lab.dev/sms/send"
    # SmartLab SMS API Header (password)
    headers = {
        "Authorization" : str(os.getenv("SMARTLAB_SMS_API_PASSWD"))
    }
    # SmartLab SMS API Params
    params ={
        "phone" : phone,
        "content" : content
    }
    logger.info(f"Sending SMS to {phone}")
    try:
        with httpx.Client() as client:
            response = client.post(endpoint, json=params, 
                                  headers=headers, timeout=10.0)
            response.raise_for_status()
        
        if response.status_code == 200:
            logger.info(f"SMS sent to {phone} successfully")
            return True
        else:
            logger.error(f"SMS sending to {phone} failed: {response.text}")
            return False
    except httpx.HTTPError as e: # HTTP Error
        logger.error(f'HTTP Error: {e}')
        return False
    except httpx.RequestError as e: # Network Error
        logger.error(f'Network Error: {e}')
        return False
    except Exception as e: # Unexpected Error
        logger.error(f'Unexpected Error: {e}')
        return False

# 비밀번호 재생성 및 전송
def process_reset_user_password(user_id:str, db:Session):
    '''
    STEP 1. 사용자 ID 입력
    STEP 2. 사용자 ID로 사용자 정보 조회(전화번호)
    STEP 3. 전화번호로 생성된 랜덤한 비밀번호 전송
    STEP 4. DB 상에 비밀번호 변경
    '''
    user = db.query(Users).filter(Users.user_id == user_id).first()
    # 사용자 ID 입력
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid User ID")
        
    # 사용자 ID로 사용자 정보 조회(전화번호 SELECT)
    user_phone_number = db.query(Users.phone_num).filter(Users.user_id == user_id).first()
    if not user_phone_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Phone number not found")
    user_phone_number = user_phone_number[0]
    logger.info(f"Phone number found: {user_phone_number}")
    
    gen_random_passwd = string.ascii_letters + string.digits
    choice_random_passwd = "".join(random.choices(gen_random_passwd, k=8)).lower()
    
    # Transaction 처리
    try:
        hashed_new_passwd = pwd_context.hash(choice_random_passwd)
        # Users DB password update
        db.query(Users).filter(Users.user_id == user_id).update({"user_password" : hashed_new_passwd})
        db.commit()
        db.refresh(user)
        
        # SMS 전송
        content = f"비밀번호를 잊어버리셨다구요? 여기 새로운 비밀번호에요: {choice_random_passwd}"
        send_sms(user_phone_number, content)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error while updating password: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error: {e}")
    
    return {"message" : f"New Password sent to {user_id} phone number"}
    