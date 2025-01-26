# API-KEY 사용 관리 및 내역 확인
from fastapi import HTTPException, status, APIRouter, Depends
import logging
import random
from models import OsMember, Users
from conn_postgre import get_db
from sqlalchemy.orm import Session
from .token_handler import Token_Handler
from jose import jwt, JWTError
from decrypt import decrypt_pp

api_key_manage = APIRouter(prefix="/api")

token = Token_Handler() # JWT 관련 클래스 객체 생성

### 변경 될 가능성 있음 -> 카드로 로그인 하지 않고 이름과 전화번호로 로그인 할 수도 있음 ###
# -> 카드에 미리 전화번호도 담아두고 이름, 전화번호, UUID 슬라이싱 후 로그인 하는 건 어떨까 
# OStools App에서 최초 로그인 시 사용
# JWT 방식 -> Remember Me(자동 로그인:세션유지)
 
@api_key_manage.post("/v1/login", description="APP CARD LOGIN")
def login(data : str, db : Session = Depends(get_db)):
    decrypted = decrypt_pp(data)
    decrypted_uuid = decrypted.get("card_uuid") # 카드에 담겨있는 데이터 복호화 후 UUID 슬라이싱
     
    member_ssid = db.query(OsMember).filter(OsMember.uuid == decrypted_uuid).first() # DB의 사용자 UUID와 복호화 된 UUID 검증
    # Arduino의 복호화 된 데이터 중 uuid 부분과 검증
    if member_ssid is None: 
        raise HTTPException(status_code=404,
                            detail="해당 UUID가 존재하지 않음")
        
    access_token = token.create_access_token(data={"sub" : member_ssid.uuid}) # access token 생성
    refresh_token = token.create_refresh_token(data={"sub" : member_ssid.uuid}) # refresh token 생성
    return {
        "status" : status.HTTP_200_OK,
        "access_token" : access_token,
        "refresh_token" : refresh_token,
        "token_type" : "bearer",
        "message" : "Login Success"
    }
    
# OStools APP에서 로그인 후 상태 유지 리프레시 토큰 발급 API
# refresh token : login api에서 응답으로 오는 refresh token
@api_key_manage.post("/v1/refresh-token")
def refresh_token(refresh_token : str):
    # 예외 처리
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Refresh Token",
        headers={"WWW-Authenticate" : "Bearer"}
    )
    try:
        payload = jwt.decode(refresh_token, token.REFRESH_SECRET_KEY, algorithms=[token.ALGORITHM])
        user_uuid : str = payload.get("sub")
        if user_uuid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    new_access_token = token.create_access_token(data={"sub" : user_uuid})
    return {
        "status" : status.HTTP_200_OK,
        "access_token" : new_access_token,
        "token_type" : "bearer",
        "message" : "Access Token refreshed successfully"
    }

