# User Login API
from fastapi import Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import Optional
from schemes import LoginForm
from models import Users
from .register import verify_password
from ostools.token_handler import Token_Handler
from database import redis_config
from custom_log import LoggerSetup
import datetime

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

logger_setup = LoggerSetup()
logger = logger_setup.logger

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
        if rd.get(f"blacklist:{token}"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token is blacklisted")
        # Token 디코딩 및 검증
        payload = jwt.decode(token, token_handler.WEB_ACCESS_SECRET_KEY, 
                             algorithms=[token_handler.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Token")

# Devportal Login Function
def process_login(response : Response, token : Optional[str], 
                  db : Session, login_form : LoginForm=Depends()):
    
    # token이 있는 경우에만 블랙리스트 체크
    # 기존 Access Token이 블랙리스트에 있는지 확인
    if token:
        if rd.get(f"blacklist:{token}"):
            print(f'이미 토큰 있음:{token}')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is blacklisted"
            )
        # 이미 로그인된 상태라면 로그인 거부
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Alreay Logged in. Plz logout first")
        
    # ID 검증
    user = get_user_by_id(db, login_form.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid User ID or Password")
    
    # Password 검증
    res = verify_password(login_form.user_password, user.user_password)
    if not res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid User ID or Password")
    # access token 생성
    access_token = token_handler.web_create_access_token(data={"sub" : user.user_id, "name" : user.user_name})
    # refresh token 생성
    refresh_token = token_handler.web_create_refresh_token(data={"sub" : user.user_id, "name" : user.user_name})
    
    # Refresh Token을 Redis에 저장
    refresh_payload = jwt.decode(refresh_token, token_handler.WEB_REFRESH_SECRET_KEY,
                                 algorithms=[token_handler.ALGORITHM])
    refresh_exp = refresh_payload.get("exp")
    now = int(datetime.datetime.now().timestamp())
    ttl = refresh_exp - now
    rd.set(f"refresh_token:{user.user_id}", refresh_token, ex=ttl)
    
    # Refresh Token : HTTP-ONLY & Secure 쿠키 저장
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True, # XSS 보호
        secure=True, # HTTPS 환경에서만 전송
        samesite="lax", # CSRF 보호
        max_age=ttl)
    
    return {
        "status" : status.HTTP_200_OK,
        "access_token" : access_token,
        "token_type" : "bearer",
        "message" : "Login Success"
    }

def issued_refresh_token(request : Request):
    '''
    - 쿠키에서 Refresh Token을 가져와 검증 후 새로운 Access Token 발급
    '''
    # cookie에서 refresh token 가져오기
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh Token No Found")
    try:
        # refresh token decoding
        payload = jwt.decode(refresh_token, token_handler.WEB_REFRESH_SECRET_KEY, 
                             algorithms=[token_handler.ALGORITHM])
        user_id  : str = payload.get("sub")
        user_name : str = payload.get("name")
        
        # Redis에 저장된 refresh token 확인
        stored_refresh_token = rd.get(f"refresh_token:{user_id}")
        
        # refresh token 유효성 검증(블랙리스트 포함 여부)
        if not stored_refresh_token or stored_refresh_token.decode() != refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Refresh Token",
                                headers={"WWW-Authenticate" : "Bearer"})
        # New Access Token 생성
        new_access_token = token_handler.web_create_access_token(data={"sub" : user_id, "name" : user_name})
        
        return {
        "status" : status.HTTP_200_OK,
        "access_token" : new_access_token,
        "token_type" : "bearer",
        "message" : "Access Token refreshed successfully"}
        
    except JWTError:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Refresh Token",
        headers={"WWW-Authenticate" : "Bearer"})
    
# Current User Info 
# user_id, user_name 조회
def current_user_info(token: str=Depends(oauth2_scheme)):
    '''
    로그인한 현재 사용자 정보(id,name 조회 가능)
    '''
    try:
        # Redis 블랙리스트에서 Access Token 조회
        # Logout 처리된 Access Token 거부
        if rd.get(f"blacklist:{token}"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token has been revoked(Logged Out)")
        
        # Token Decoding
        payload = jwt.decode(token, token_handler.WEB_ACCESS_SECRET_KEY, 
                             algorithms=[token_handler.ALGORITHM])
        user_id = payload.get("sub")
        user_name = payload.get("name")
        print(f'Decoding Payload: {payload}')
        if not user_id or not user_name:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token payload")
        return {
            "status" : status.HTTP_200_OK,
            "user_id" : user_id,
            "user_name" : user_name
        }
    except JWTError as e:
        logger.error(f'JWT ERROR: {str(e)}')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Token")

def process_logout(response : Response, token : str = Depends(oauth2_scheme)):
    '''
    OS Dev Portal에서 로그아웃 시 사용되는 API
    Redis에서 token을 블랙리스트로 관리하는 방식으로 처리
    token : access token을 Header에 담아 보내면 Logout 처리 
    '''
    try:
        print(f"Extracted Access Token {token}") # 추출된 access token
        payload = jwt.decode(token, token_handler.WEB_ACCESS_SECRET_KEY,
                             algorithms=[token_handler.ALGORITHM])
        # Expire Time (만료 시간)
        exp = payload.get("exp")
        print(f"Expire Time(만료시간):{exp}")
        if exp is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail="Invalid Token")
        
        # Redis에 토큰 저장(key: f"blacklist{token}", value: "blacklisted", expire_time: 만료 시간)
        now = int(datetime.datetime.now().timestamp())
        ttl = max(exp -now , 0) # 0 이하 방지
        ttl = min(exp - now, 7 * 24 * 60 * 60) # 최대 7일 유지
        if ttl > 0:
            rd.set(f"blacklist:{token}", "blacklisted")
            rd.expire(f"blacklist:{token}", ttl)
             
    # Cookie 삭제(Token 삭제)
        response.delete_cookie(key="access_token")
        return {"status" : status.HTTP_200_OK, "message" : "Logout Success"}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid Token")


