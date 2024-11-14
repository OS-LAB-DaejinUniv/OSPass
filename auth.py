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
from models import OsMember, APIKeyLog
from conn_postgre import get_db
import database
from conn_arduino.dec_data import conn_hsm
from log_manage import login

load_dotenv()

# Redis Connect and receive {key : value}
rd = database.redis_config()

verify_router = APIRouter(prefix="/api")

# Token Scheme
class Token(BaseModel):
    access_token: str
    token_type: str

# JWT에 담고있을 사용자 정보 스키마
class TokenData(BaseModel):
    uuid : str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@verify_router.post("/v1/card_response")
async def verify_card_response(data, challenge, db: Session = Depends(get_db)):
    try:
        import binascii
        # 앱에서 전달된 데이터 복호화
        dec_data = conn_hsm.decrypt(data=binascii.unhexlify(data))
        
        # Redis에서 기존 challenge 키로 저장된 값 조회
        stored_challenge = rd.get(challenge)
        if stored_challenge is None:
            raise HTTPException(status_code=404, detail="Key not found or expired")
        
        print(f"Challenge in Redis: {stored_challenge.decode()}")  # Redis에서 가져온 챌린지 값 출력
        print(f"Decrypted data: {dec_data.hex()}")  # 복호화된 데이터 출력
        
        # 챌린지 값만 추출 (예시, 실제 데이터 구조에 맞게 수정 필요)
        dec_challenge = dec_data.hex()  
        print(f"Extracted challenge: {dec_challenge}")
        
        # 저장된 챌린지 값과 비교
        if stored_challenge.decode() == dec_challenge:
            print("Challenge match: correct")
        else:
            print("Challenge match: incorrect")
            raise HTTPException(status_code=400, detail="Invalid response")
        
        # UUID 확인
        member_ssid = db.query(OsMember).filter(OsMember.uuid == dec_data.hex()).first()
        if not member_ssid:
            print("Member not found in database")
            raise HTTPException(status_code=404, detail="Member not found")
        
        return {"message": "Valid response"}
    
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


### 인가 코드 발급 ### 
# 서비스 서버에서 인가 코드 요청(로그인(유저 검증)을 한 후) 했을 시 기능 수행
@verify_router.get("/v1/authorization_code")
def post_authrization_code(API_KEY : str, redirect_uri : str, response : Response, db : Session = Depends(get_db)):
    user_api_key = db.query(APIKeyLog).filter(APIKeyLog.key == API_KEY).first() # 생성된 API KEY SELECT 
    session_id = login()
    try:
        if not user_api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid API KEY")
        if not session_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Unauthorized User")
        
        # 인가 코드 생성
        authorization_code = hex(random.getrandbits(128))
        
        # 리디렉션 URL에 인가 코드를 포함하여 반환
        response.status_code = status.HTTP_302_FOUND
        response.headers["Location"] = f"{redirect_uri}?code={authorization_code}"
        return response       
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Data for authorization_code")


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
