import random
import const
import logging
from database import redis_config

rd = redis_config()

# challenge 생성
# 생성된 challenge와 카드에 담겨져 있는 response랑 비교
# key는 어떤 것으로 할지 의논 중
def gen_challenge():
    if rd is None:
        logging.error(msg="redis connection fail")
    
    # 128 bit challenge generate
    challenge = random.getrandbits(128)
    hex_challenge = hex(challenge)[2:].zfill(32)
    
    # 128 bit uuid generate
    uuid = random.getrandbits(128)
    hex_uuid = hex(uuid)[2:].zfill(32)
    
    rd.set(hex_uuid,hex_challenge)
    rd.expire(hex_uuid,const.EXPIRE_KEY) # Key disappears after time expires
    return {
        "key" : hex_uuid,
        "value" : hex_challenge
    }



      