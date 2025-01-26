# User Login API
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from schemes import JoinUser, LoginForm
from models import Users
from conn_postgre import get_db
from .register import verify_password
from ostools.token_handler import Token_Handler
from database import redis_config
import datetime

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Redis Connection
rd = redis_config()

# Token Handler Instance
token_handler = Token_Handler()

# User 존재(가입) 여부 확인
def get_user_by_id(db : Session, user_id : str):
    return db.query(Users).filter(Users.user_id == user_id).first()

# Token Validation Verifying
# When to Use: 인증이 필요한 경우 사용 -> 토큰의 존재 여부를 판단 
def verify_token(token:str):
    try:
        # Redis 블랙리스트에서 Token 조회
        if rd.get(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token is blacklisted")
        # Token 디코딩 및 검증
        payload = jwt.decode(token, token_handler.ACCESS_SECRET_KEY, 
                             algorithms=[token_handler.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Token")

# Devportal Login Function
def process_login(response : Response, db : Session, login_form : LoginForm=Depends()):
    
    user = get_user_by_id(db, login_form.user_id)
    # ID 검증
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid User ID or Password")
    
    # Password 검증
    res = verify_password(login_form.user_password, user.user_password)
    if not res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid User ID or Password")
    # access token 생성
    access_token = token_handler.create_access_token(data={"sub" : user.user_id, "name" : user.user_name})
    # refresh token 생성
    refresh_token = token_handler.create_refresh_token(data={"sub" : user.user_id})
    
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    
    return {
        "status" : status.HTTP_200_OK,
        "access_token" : access_token,
        "refresh_token" : refresh_token,
        "token_type" : "bearer",
        "message" : "Login Success"
    }

def issued_refresh_token(refresh_token : str):
    # Exception Handling (예외 처리)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Refresh Token",
        headers={"WWW-Authenticate" : "Bearer"}
    )
    try:
        # refresh token 유효성 검증(블랙리스트 포함 여부)
        if rd.get(refresh_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Refresh Token is Blacklisted")
            
        payload = jwt.decode(refresh_token, token_handler.REFRESH_SECRET_KEY, 
                             algorithms=[token_handler.ALGORITHM])
        user_id  : str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # New Access Token 생성
    new_access_token = token_handler.create_access_token(data={"sub" : user_id})
    return {
        "status" : status.HTTP_200_OK,
        "access_token" : new_access_token,
        "token_type" : "bearer",
        "message" : "Access Token refreshed successfully"
    }
    
# Current User Info 
# user_id, user_name 조회
def current_user_info(token: str=Depends(oauth2_scheme)):
    '''
    로그인한 현재 사용자 정보(id,name 조회 가능)
    '''
    try:
        # Token Decoding
        payload = jwt.decode(token, token_handler.ACCESS_SECRET_KEY, 
                             algorithms=[token_handler.ALGORITHM])
        user_id = payload.get("sub")
        user_name = payload.get("name")
        
        if not user_id or not user_name:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token payload")
        return {
            "status" : status.HTTP_200_OK,
            "user_id" : user_id,
            "user_name" : user_name
        }
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Token")

def process_logout(response : Response, token : str = Depends(oauth2_scheme)):
    '''
    OS Dev Portal에서 로그아웃 시 사용되는 API
    Redis에서 token을 블랙리스트로 관리하는 방식으로 처리
    token : access token을 Header에 담아 보내면 Logout 처리 
    '''
    try:
        print(f"Extracted Token {token}")
        payload = jwt.decode(token, token_handler.ACCESS_SECRET_KEY,
                             algorithms=[token_handler.ALGORITHM])
        # Expire Time (만료 시간)
        exp = payload.get("exp")
        print(f"Expire Time(만료시간):{exp}")
        if exp is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail="Invalid Token")
        
        # Redis에 토큰 저장(key: f"blacklist{token}", value: "blacklisted", expire_time: 만료 시간)
        now = int(datetime.datetime.now().timestamp())
        ttl = min(exp - now, 7 * 24 * 60 * 60) # 7일로 설정
        if ttl > 0:
            rd.set(f"blacklist:{token}", "blacklisted")
            rd.expire(f"blacklist{token}",ttl)
             
    # Cookie 삭제(Token 삭제)
        response.delete_cookie(key="access_token")
        return {"status" : status.HTTP_200_OK, "message" : "Logout Success"}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid Token")
    

