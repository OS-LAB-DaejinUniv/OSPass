# client_id 생성
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from fastapi import 
from sqlalchemy.orm import Session
from models import API_Key
import string
import random
from const import LENGTH
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger 

def gen_client_id(client_id:str, db:Session):
    # client_id number + string generator
    string_num = string.ascii_letters + string.digits

    # Random Number+String 
    gen_client_id = ""

    for i in range(LENGTH):
        gen_client_id += random.choice(string_num)
    
    # client_id Format
    client_id = f'ospass-{gen_client_id.lower()}'
    
    key = db.query(API_Key).filter(API_Key.registerd_service["client_id"]).first()
    
    if key:
        if key.registerd_service is None:
            # 처음 데이터를 넣을 경우
            key.registerd_service = {client_id:{}}
        else:
            # 기존 데이터가 있는 경우
            current_services = dict(key.registerd_service)
            current_services[client_id] = {} 
            key.registerd_service = current_services
        
        db.commit()
    logger.debug(f'Generated Client_ID:{client_id}')
    print(f'Generated Client_ID:{client_id}')
    return client_id