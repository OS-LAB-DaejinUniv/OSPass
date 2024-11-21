# API-KEY 사용 관리 및 내역 확인
from fastapi import HTTPException, status, Request, APIRouter, Depends
import logging
from models import OsMember, APIKeyLog
from conn_postgre import get_db
from sqlalchemy.orm import Session

api_key_manage = APIRouter(prefix="/api")

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
    
# 검증(로그인) 성공 시 API kEY 생성
# API KEY 생성하기 버튼?
@api_key_manage.get("/v1/api-key?uuid={uuid}")
def gen_api_key(db : Session = Depends(get_db)):
    import random
    api_key = hex(random.getrandbits(128))
    return api_key
    # try:
        # if api_key in check_api_key_match_uuid:
        #     return api_key
    # except:
    #     HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
    #                   detail="API KEY ISSUED FAIL") 

async def check_api_key_match_uuid(uuid:str, api_key:str, db:Session=Depends(get_db)):
    result = await db.query(APIKeyLog).filter(APIKeyLog.key==api_key,
                                        APIKeyLog.uuid==uuid)
    if result:
        logging.info(f"UUID {uuid} & API kEY {api_key} matched")
        return True
    else:
        logging.error(f"No match found for UUID {uuid} & API KEY {api_key}")
        return False

# 만들어진 API KEY와 UUID, SOURCE(사용 출처), Timestamp DB에 저장
def insert_log(uuid:str, api_key:str,source:str,timestamp:str,db:Session=Depends(get_db)):
    
    result = db.add