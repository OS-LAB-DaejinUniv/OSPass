# API-KEY 사용 관리 및 내역 확인
from fastapi import HTTPException, status, Request, APIRouter, Depends
import logging
from models import OsMember, APIKeyLog
from conn_postgre import get_db
from sqlalchemy.orm import Session

api_key_manage = APIRouter(prefix="/api")

# OsUtility App에서 로그인 시 사용
# OSCard 로그인 API : API kEY 생성 전 검증 처리(로그인)
# 로그인 후 인가코드 발급도 같이 수행
api_key_manage.post("/v1/login")
def login(enc_data_uuid : str, db : Session = Depends(get_db)):
    import binascii
    from conn_arduino.dec_data import conn_hsm
    dec_uuid = conn_hsm.decrypt(data=binascii.unhexlify(enc_data_uuid))
    member_ssid = db.query(OsMember).filter(OsMember.uuid == dec_uuid).first()
    # Arduino의 복호화 된 데이터 중 uuid 부분과 검증
    if member_ssid is None: 
        raise HTTPException(status_code=404,
                            detail="해당 UUID가 존재하지 않음")
    else:
        return status.HTTP_200_OK
   
# 로그인 된 사용자가 API KEY 발급 시 호출
# API KEY 생성하기
# api key 생성, 해당 uuid와 api key 매핑 후 Insert to Apikeylog table
@api_key_manage.get("/v1/api-key")
def gen_api_key(uuid:str, db:Session=Depends(get_db)):
    try:
        if login():
            import random
            new_api_key = APIKeyLog(key=hex(random.getrandbits(128)), user_uuid=uuid) # mapping
            db.add(new_api_key) # generated api key & user's uuid insert to APIKeyLog Table
            db.commit()
    except:
        return status.HTTP_401_UNAUTHORIZED

async def check_api_key_match_uuid(uuid:str, api_key:str, db:Session=Depends(get_db)):
    
    result = await db.query(APIKeyLog).filter(APIKeyLog.key==api_key, APIKeyLog.uuid==uuid)
    
    if result:
        logging.info(f"UUID {uuid} & API kEY {api_key} matched")
        return True
    else:
        logging.error(f"No match found for UUID {uuid} & API KEY {api_key}")
        return False

# 만들어진 API KEY와 UUID, SOURCE(사용 출처), Timestamp DB에 저장
# uuid : 사용자 고유 uuid(카드에 담겨있음)
# api_key : 사용자가 신청한 api key
# souce : api key 사용 출처
# timestamp : api key 생성 시간

def insert_key_log(uuid:str, api_key:str, source:str, timestamp:str, db:Session=Depends(get_db)):
    
    result = db.add()