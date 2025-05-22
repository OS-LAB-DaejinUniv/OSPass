from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
import httpx
import os
import uuid
import random
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConsumerCancelled
import json
from dotenv import load_dotenv
from schemes import InitLoginRequest
from service.auth import get_or_issue_challenge
from router.redisConst import REDIS_AUTH_ATTEMPT_PREFIX
from utils.findApikey import find_service_info_by_service_id_key, find_service_apikey_by_service_id_key
from common.models.models import Users, API_Key
from common.database.database import redis_config
from custom_log import LoggerSetup

load_dotenv()

rd = redis_config()

logger_setup = LoggerSetup()
logger = logger_setup.logger

# RabbitMQ 통신 및 데이터 생성자
def data_producer(msg:dict):
    """
    RabbitMQ 통신 및 메시지 생성
    push_msg: Queue 생성, durable: RabbitMQ가 종료됐다 시작돼도 Queue 유지
    Args:
        msg(dict): ospass login 시 생성되는 데이터
    return:
        {Successfully Message}
    """
    url = os.getenv("RabbitMQ_SERVER")
    params = pika.URLParameters(url)
    connection = None # connection 초기화
    channel = None # channel 초기화
    try:
        # RabbitMQ Connection
        connection = pika.BlockingConnection(params)
        print(f"Connection Successfully:{connection}")
        # Create Channel
        channel = connection.channel()
        print(f"RMQ Channel : {channel}")
        # Create Queue(queue name: push_msg)
        channel.queue_declare(queue='push_msg', durable=True) 
        
        print(f"Produce Data for Push Server:{type(msg)} & {json.dumps(msg)}")
        channel.basic_publish(exchange='', routing_key='push_msg', body=json.dumps(msg))
        
        return {"Message" : "Send Message to RabbitMQ Successfully"}
    
    except AMQPConnectionError as e:
        logger.error(f"RabbitMQ Connection Error: {str(e)}")
        return {
            "status": "AMQP Connection Error",
            "message": f"Failed to connect to RabbitMQ: {str(e)}"
        }
    except AMQPChannelError as pe:
        logger.error(f"AMQP Channel Error: {pe}")
        return {
            "status": "AMQP Channel Error",
            "message": f"RabbitMQ AMQP Channel Error: {str(pe)}"
        }
    except ConsumerCancelled as ce:
        logger.error(f"Consumer Cancelled Error: {ce}")
        return {
            "status": "Consumer Cancelled",
            "message": f"RabbitMQ Consumer Cancelled Error: {str(ce)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error in RMQ communication: {str(e)}", exc_info=True)
        return {
            "status": "Error Occured",
            "message": f"Unexpected error during RabbitMQ operation: {str(e)}"
        }
    finally:
        if channel and channel.is_open:
            try:
                channel.close()
                print("RMQ Channel Closed")
            except Exception as e:
                logger.error(f"Error Closing RMQ Channel: {str(e)}")
        if connection and connection.is_open:
            try:
                connection.close()
                print("RMQ Connection closed")
            except Exception as e:
                logger.error(f"Error closing RMQ Connection: {str(e)}")
        
# 1차 인증 수단
def process_ospass_login(request : InitLoginRequest, 
                         client_id:str,
                         redirect_uri:str,
                         state:str, 
                         db:Session):
    '''
    - OSPASS Login 처리 함수
    - Attempt ID 발급 및 시도 상태 저장
    :params
    - db: DB 세션
    - sliced_phone_num : User's Phone Number (010 제외)
    - client_id : Devportal에서 등록한 Service ID(client_id)
    - redirect_uri: 인증 완료 후 /v1/authorization이 Redirect할 서비스 URI
    - state: OAuth 2.0 state 파라미터 (CSRF 방지 및 상태 유지)
    :return
    - push server 통신 결과
    '''
    logger.debug(f"Entering ospass init login data: {request.sliced_phone_num}, client_id:{client_id}")
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
        api_key_record = db.query(API_Key).filter(
            func.jsonb_exists(API_Key.registered_service, client_id)
        ).first()
        
        if not api_key_record:
            logger.error(f"Client ID not found in DB : {client_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Not Found Your Registered Client_ID")
        service_apikey_value = find_service_apikey_by_service_id_key(api_key_record.registered_service, client_id)
        if not service_apikey_value:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                detail="Internal service configuration error: missing apikey value")
        
        client_data = find_service_info_by_service_id_key(api_key_record.registered_service, client_id)
        if not client_data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Internal service configuration error")
        attempt_id = str(uuid.uuid4())
        logger.debug(f"Generated Attempt ID:{attempt_id}")
        
        new_attempt_challenge = hex(random.getrandbits(128))[2:].zfill(32)
        logger.debug(f"[/v1/ospass-login] Generated Challenge: {new_attempt_challenge}, type:{type(new_attempt_challenge)}")
        
        # challenge = get_or_issue_challenge(client_id)
        # logger.debug(f"Get or Issued Challenge: {challenge}")
        
        attempt_state = {
            "status": "pending",
            "api_key": service_apikey_value,
            "internal_service_id" : client_id,
            "redirect_uri" : redirect_uri,
            "state" : state,
            "s_id" : None,
            "challenge" : new_attempt_challenge
        }
        attempt_ttl_seconds = 300
        redis_key = f"{REDIS_AUTH_ATTEMPT_PREFIX}{attempt_id}"
        rd.setex(redis_key, attempt_ttl_seconds, json.dumps(attempt_state))
        
        msg = {
            "attempt_id" : attempt_id,
            "client_id" : client_id, 
            "full_phone_num" : full_phone_num, 
            "challenge" : new_attempt_challenge, 
            "uid" : user.uid
        }
        print(f"RMQ에 보낼 데이터 타입 및 내용: {msg}")
        
        pro_data = data_producer(msg)
        print(f"보내기 성공: {pro_data}")
        
        return {
            "status" : status.HTTP_200_OK,
            "message" : "Successfully delivered data to Push Server",
            "pub_data" : attempt_id
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in process_ospass_login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e))
        
"""---------------------------------------------------------------------------"""
# push server 통신
def push_server_communication(client_id:str, 
                              sliced_phone_num:str,
                              challenge:str, 
                              uid:str):
    '''
    Push Server 통신 함수
    '''
    url = str(os.getenv("PUSH_SERVER_URL")) # Push Server URL
    print(f"Push Server URL: {url}")
    headers = {
        "Content-Type": "application/json",
        "Accept" : "application/json"
    }
    # Push Server에서 2차 가공 필요
    data = {
        "message": "OSPASS Login Success",
        "phone_num" : str(sliced_phone_num),
        "uid" : str(uid),
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