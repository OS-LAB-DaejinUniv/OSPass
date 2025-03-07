from fastapi import HTTPException, status
import random
import const
from custom_log import LoggerSetup
from database import redis_config

rd = redis_config()

logger_setup = LoggerSetup()
logger = logger_setup.logger

def gen_challenge(client_id : str):
    """
    challenge 생성
    생성된 challenge와 카드에 담겨져 있는 response랑 비교
    :param
    - client_id : ospass를 등록한 서비스의 고유 client_id(서비스 식별 아이디)
    """
    if rd is None:
        logger.error("redis connection fail")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Redis Connection Failed")
    
    # 128 bit challenge generate : value
    challenge = random.getrandbits(128)
    hex_challenge = hex(challenge)[2:].zfill(32)
    
    rd.setex(client_id, const.EXPIRE_KEY, hex_challenge)
    
    return {
        "key" : client_id,
        "value" : hex_challenge
    }



      