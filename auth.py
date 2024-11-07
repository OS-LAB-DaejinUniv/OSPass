from dotenv import load_dotenv
import os
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Union, Any
from fastapi import Depends, HTTPException, status, APIRouter, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from schemes import User
from models import OsMember
from conn_postgre import get_db
import database
from conn_arduino import send_enr_data

# TODO
# 1. Postgre에서 가져온 UUID(Login용 Session ID)와 JavaCard에서 주는 UUID와 비교 및 검증
# 2. 검증이 끝나면 JWT를 발급 함
# 3. Postgre에서 uuid -> session_id로 컬럼명 변경할 것


load_dotenv()

# Redis Connect and receive {key : value}
rd = database.redis_config()

# Arduino Connect : receive encrpyt response
enc_res = send_enr_data()

verify_router = APIRouter(prefix="/api")

# Token Scheme
class Token(BaseModel):
    access_token: str
    token_type: str

# JWT에 담고있을 사용자 정보 스키마
class TokenData(BaseModel):
    uuid : str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Challenge와 Response 비교 후 검증
@verify_router.post("/v1/card_response")
def verify_card_response(challenge : str):
    
    stored_challege = rd.get(challenge)
    print(f'challenge in redis {stored_challege}')
    if not stored_challege:
        raise HTTPException(status_code=404, detail="Key not found or Time Expired")
    
    if stored_challege == enc_res:
        return {"message": "Valid response"}
    else:
        raise HTTPException(status_code=400, detail="Invalid response")


# API KEY 생성
# 생성된 API_KEY를 DB에 INSERT  함

@verify_router.get("/v1/api-key")
def gen_api_key(db : Session = Depends(get_db)):
    api_key = hex(random.getrandbits(128))
    try:
        if api_key not in db:
            return api_key
    except:
        HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API KEY ISSUED FAIL")

# 서비스 서버에서 인가 코드 요청(로그인 시도)했을 시 동작
@verify_router.post("/v1/authorization_code?api-key={API_KEY}&redirect_uri={redirect_uri}")
def post_authrization_code(API_KEY : str,card_uuid : str, challenge : str, response : Response, db : Session = Depends(get_db)):
    authorization_code = hex(random.getrandbits(128))
    stored_challenge = rd.get(challenge)
    session_id = db.query(OsMember).filter(OsMember.uuid == card_uuid).first()
    try:
        if API_KEY in "API-KEY Storage DB.key" and enc_res == stored_challenge and card_uuid in session_id:
            response.status_code = status.HTTP_201_CREATED
            return authorization_code
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Data for authorization_code")


# 서비스 서버가 인가 코드로 access token을 발급 요청했을 시 동작 
@verify_router.post("/v1/access_token")
def issue_access_token(data : dict, expires_delta : timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(ZoneInfo("Asia/Seoul")) + expires_delta
    else:
        expire = datetime.now(ZoneInfo("Asia/Seoul")) + timedelta(minutes=15)
    to_encode.update({"exp" : expire}) # 인증 만료 시간
    encode_jwt = jwt.encode(to_encode, os.getenv('ACCESS_SECRET_KEY'), os.getenv('ALGORITHM'))
    return encode_jwt  

def authentication_user(db, session_id : str):
    user = get_user(db, session_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid Session_ID")







#-------------------------------------------------------#
# 사용자 정보(UUID, 이름, 포지션(0=부원, 1=랩장)) 가져오기
@verify_router.get("/v1/userinfo")
def get_user( db: Session = Depends(get_db)):
    try:
        members = db.query(OsMember).all()
        if not members:
            raise HTTPException(status_code=404, detail="Data Not Found")
        
        return [User(uuid=member.uuid, name=member.name, position=member.position) for member in members]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
