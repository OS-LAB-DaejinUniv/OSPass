import random
import const
from fastapi import APIRouter
from database import redis_config

challenge_router = APIRouter(prefix="/api")
rd = redis_config()

# challenge 생성
# 왜? 생성? => 앱에서 호출 할 api임
# 앱은 이 api 가지고 뭘 하냐
# 걍 uuid랑 challenge 랜덤하게 생성하고 레디스에 담을거임
# 그리고 이 생성된 값으로 검증할거임
# 뭘 검증? 생성된 value(challenge) 랑 카드에 담겨져 있는 response랑 비교함
@challenge_router.get("/v1/challenge")
def gen_challenge():
    
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



      