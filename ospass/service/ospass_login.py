from fastapi import HTTPException, status, Form
from sqlalchemy.orm import Session
import httpx
import json
import os
from dotenv import load_dotenv

from models import Users
# from schemes import Init_Login

load_dotenv()

# push server 통신
def push_server_communication(sliced_phone_num:str, user_id:str):
    '''
    Push Server 통신 함수
    '''
    url = str(os.getenv("PUSH_SERVER_URL")) # Push Server URL
    
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "message": "OSPASS Login Success",
        "phone_num" : sliced_phone_num,
        "user_id" : user_id,
        "status" : status.HTTP_200_OK
    }
    response = httpx.post(url, headers=headers, data=json.dumps(data))
    
    return response.json()

# 1차 인증 수단
def process_ospass_login(sliced_phone_num : str, db:Session):
    '''
    OSPASS Login 처리 함수
    :param db: DB 세션
    :param sliced_phone_num : User's Phone Number (010 제외)
    :return : push server 통신 결과
    '''
    # 생략된 010 추가
    full_phone_num = f"010{sliced_phone_num}"
    print(f'Full Phone Number : {full_phone_num}')
    
    # 입력된 sliced_phone_num을 가진 row의 user_id 찾기 위한 객체 생성
    user = db.query(Users).filter(Users.phone_num == full_phone_num).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid Phone Number")
    
    push_server_communication(full_phone_num, user.user_id)
    
    return {"status" : status.HTTP_200_OK}
