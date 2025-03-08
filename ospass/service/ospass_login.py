from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
import httpx
import json
import os
from dotenv import load_dotenv
from ..schemes import InitLoginRequest
from .auth import get_or_issue_challenge
from models import Users, API_Key
from custom_log import LoggerSetup
# from schemes import Init_Login

load_dotenv()

logger_setup = LoggerSetup()
logger = logger_setup.logger

# push server 통신
def push_server_communication(client_id:str, 
                              sliced_phone_num:str,
                              challenge:str, 
                              user_id:str):
    '''
    Push Server 통신 함수
    '''
    # url = str(os.getenv("PUSH_SERVER_URL")) # Push Server URL
    url = "http://api.oslab:7999/post"
    headers = {
        "Content-Type": "application/json",
        "Accept" : "application/json"
    }
    data = {
        "message": "OSPASS Login Success",
        "phone_num" : str(sliced_phone_num),
        "user_id" : str(user_id),
        "client_id" : str(client_id),
        "challenge" : str(challenge),
        "status" : int(status.HTTP_200_OK)
    }
    try:
        response = httpx.post(url, headers=headers, json=data, timeout=5.0)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Push Server returned status code: {response.status_code}")
            return{
                "status" : "push_server_error",
                "message" : f"Server returned status code: {response.status_code}",
                "response_text" : response.text
            }
    
    except httpx.TimeoutException:
        logger.error("Push server timeout")
        return {
            "status": "push_server_error",
            "message": "Server timeout - The server is not responding"
        }
        
    except httpx.ConnectError:
        logger.error("Push server connection failed")
        return {
            "status": "push_server_error",
            "message": "Connection failed - The server might be down or unreachable"
        }
        
    except httpx.RequestError as e:
        logger.error(f"Push server request error: {str(e)}")
        return {
            "status": "push_server_error",
            "message": f"Request error: {str(e)}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in push server communication: {str(e)}")
        return {
            "status": "push_server_error",
            "message": f"Unexpected error: {str(e)}"
        }
# 1차 인증 수단
def process_ospass_login(request : InitLoginRequest, client_id:str, db:Session):
    '''
    OSPASS Login 처리 함수
    :param 
    - db: DB 세션
    - sliced_phone_num : User's Phone Number (010 제외)
    - client_id : Devportal에서 등록한 서비스의 고유 식별 id(client_id)
    :return
    - push server 통신 결과
    '''
    try:
        # 생략된 010 추가
        full_phone_num = f"010{request.sliced_phone_num}"
        print(f'Full Phone Number : {full_phone_num}')
        
        # 입력된 sliced_phone_num을 가진 row의 user_id 찾기 위한 객체 생성
        user = db.query(Users).filter(Users.phone_num == full_phone_num).first()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid Phone Number")
        
        # API_Key Table registered_service Row 추출
        # has_key -> deleted from python3 
        # but.. sqlalchemy uses it to check if there is a json key in JSONB case
        api_key_record = db.query(API_Key).filter(API_Key.registered_service.has_key(client_id)).first() 
        
        if not api_key_record:
            logger.error(f"Client ID not found in DB : {client_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Not Found Your Registered Client_ID")
        
        client_data = api_key_record.registered_service.get(client_id)
        if client_data:
            print(f"Service Name: {client_data['service_name']}")
            print(f"API KEY: {client_data['apikey']}")
            
        challenge = get_or_issue_challenge(client_id)
        print(f"생성된 Challenge: {challenge}")
        
        # Push Server Communication Result
        push_result = push_server_communication(client_data, 
                                                full_phone_num, 
                                                challenge, 
                                                user.user_id)
        
        if push_result.get("status") == "push_server_error":
            logger.error(f"Push Server Occured: {push_result.get('message')}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "Push Server Communication Failed",
                    "message": push_result.get("message")
                })
        
        return {
            "status" : status.HTTP_200_OK,
            "message" : "Successfully delivered data to Push Server"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in process_ospass_login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e))