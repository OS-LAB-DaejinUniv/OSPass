from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
import httpx
import os
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConsumerCancelled
import json
from dotenv import load_dotenv
from schemes import InitLoginRequest
from service.auth import get_or_issue_challenge
from common.models.models import Users, API_Key
from custom_log import LoggerSetup

load_dotenv()

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
        api_key_record = db.query(API_Key).filter(
            func.jsonb_exists(API_Key.registered_service, client_id)
        ).first()
        
        if not api_key_record:
            logger.error(f"Client ID not found in DB : {client_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Not Found Your Registered Client_ID")
        
        client_data = api_key_record.registered_service.get(client_id)
        if client_data:
            print(f"Client ID: {client_id}")
            print(f"Service Name: {client_data['service_name']}")
            print(f"API KEY: {client_data['apikey']}")
            
        challenge = get_or_issue_challenge(client_id)
        print(f"생성된 Challenge: {challenge}")
        
        msg = {
            "client_id" : client_id, 
            "full_phone_num" : full_phone_num, 
            "challenge" : challenge, 
            "uid" : user.uid
        }
        print(f"RMQ에 보낼 데이터 타입 및 내용: {type(msg)} & {msg}")
        
        pro_data = data_producer(msg)
        print(f"보내기 성공: {pro_data}")
        # # Push Server Communication Result
        # push_result = push_server_communication(client_id, 
        #                                         full_phone_num, 
        #                                         challenge, 
        #                                         user.uid)
        
        # if push_result.get("status") == "push_server_error":
        #     logger.error(f"Push Server Occured: {push_result.get('message')}")
        #     raise HTTPException(
        #         status_code=status.HTTP_502_BAD_GATEWAY,
        #         detail={
        #             "error": "Push Server Communication Failed",
        #             "message": push_result.get("message")
        #         })
        
        return {
            "status" : status.HTTP_200_OK,
            "message" : "Successfully delivered data to Push Server",
            "pub_data" : pro_data
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