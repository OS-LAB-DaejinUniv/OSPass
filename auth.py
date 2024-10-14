from dotenv import load_dotenv
import os
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Union, Any
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from schemes import User
from models import OsMember
from conn_postgre import get_db
import database

# TODO
# 1. Postgre에서 가져온 UUID(Login용 Session ID)와 JavaCard에서 주는 UUID와 비교 및 검증
# 2. 검증이 끝나면 JWT를 발급 함
# 3. Postgre에서 uuid -> session_id로 컬럼명 변경할 것


load_dotenv()

# Redis 
rd = database.redis_config()

verify_router = APIRouter(prefix="/api")

# Serial 통신으로 받아올 복호화 된 response값
decrypted_challenge = '8c64923078d57c8664aee61c2f1dcedc' # decrypted_challenge (response)

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
def verify_card_response(response : str):
    
    stored_challege = rd.get(response)
    print(f'challenge in redis {stored_challege}')
    if not stored_challege:
        raise HTTPException(status_code=404, detail="Key not found or Time Expired")
    
    if stored_challege == decrypted_challenge:
        return {"message": "Valid response"}
    else:
        raise HTTPException(status_code=400, detail="Invalid response")


# API KEY 생성
# 생성된 API_KEY를 DB에 INSERT  함
# 
@verify_router.get("/v1/api-key")
def gen_api_key(db : Session = Depends(get_db)):
    api_key = hex(random.getrandbits(128))
    try:
        if api_key not in db:
            return api_key
    except:
        HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="API KEY ISSUED FAIL")
    return api_key

# TODO : 인가 코드 발급
# 1. 카드를 통해 로그인을 시도
# 2. 정보가 일치하면 인가 코드를 서비스 서버에 제공한다.

# 서비스 서버에서 인가 코드 요청(로그인 시도)했을 시 동작
@verify_router.post("/v1/authorization_code?api-key={API_KEY}&redirect_uri={redirec_uri}")
def sup_authrization_code(API_KEY):
      """
      API KEY가 일치하고 카드의 UUID와 DB의 UUID가 일치하면
      인가코드를 줌
      if user.apikey == server.apikey && card.uuid == db.uuid
        return authcode(random)
      """

#  서비스 서버가 인가 코드로 access token을 발급 요청했을 시 동작 
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


# 사용자 정보(UUID, 이름, 포지션(0=부원, 1=랩장)) 가져오기
@verify_router.get("/v1/userinfo")
def get_user(uuid, name, db: Session = Depends(get_db)):
    try:
        members = db.query(OsMember).all()
        if not members:
            raise HTTPException(status_code=404, detail="Data Not Found")
        
        return [User(uuid=member.uuid, name=member.name, position=member.position) for member in members]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))