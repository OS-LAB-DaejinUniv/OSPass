from fastapi import HTTPException, status, Depends, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime

from conn_postgre import get_db
from models import OsMember, Users, APP_Refresh_Tokens
from .token_handler import Token_Handler
from devportal.user.register import verify_password
from schemes import LoginForm
from decrypt import decrypt_pp
from custom_log import LoggerSetup

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

token_handler = Token_Handler() # JWT 관련 클래스 객체 생성

logger_setup = LoggerSetup()
logger = logger_setup.logger


def process_ostools_login(response : Response, db:Session, login_form:LoginForm=Depends()):
    '''
    OSTools Login Process
    일반 로그인(user_id, user_password) -> 카드 로그인으로 변경 가능성 염두
    기존 Devportal에서 사용된 회원과 동일
    :param login_form : LoginForm(user_id, user_password) 
    '''
    user = db.query(Users).filter(Users.user_id == login_form.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Invalid User ID or Password")
        
    user_password = verify_password(login_form.user_password, user.user_password)
    if not user_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid User ID or Password")
    
    # access token 생성
    access_token = token_handler.create_access_token(data={"sub" : user.user_id})
    # refresh token 생성
    refresh_token = token_handler.create_refresh_token(data={"sub" : user.user_id})
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, 
                        secure=True)
    
    # Refresh Token 저장
    new_refresh_token = APP_Refresh_Tokens(user_id=user.user_id, token=refresh_token)
    
    db.add(new_refresh_token)
    db.commit()
    
    return {
        "status" : status.HTTP_200_OK,
        "access_token" : access_token,
        "refresh_token" : refresh_token,
        "token_type" : "bearer",
        "message" : "Login Success"
    }

def issued_refresh_token(refresh_token:str, db:Session):
    '''
    Refresh Token 발급 
    DB에서 Refresh Token 관리 및 검증
    :param refresh_token : refresh token
    '''
    payload = token_handler.verify_token(refresh_token, is_refresh=True)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Refresh Token")
    
    # DB에서 Refresh Token 확인
    stored_refresh_token = db.query(APP_Refresh_Tokens).filter(APP_Refresh_Tokens.token == refresh_token).first()
    if not stored_refresh_token or stored_refresh_token.expires_at < datetime.now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh Token Not Found or Expired")
        
    # 새로운 Access Token 발급 : paylaod["sub"] -> user_id
    new_access_token = token_handler.create_access_token(data={"sub":payload["sub"]})
    return {
        "access_token" : new_access_token,
        "token_type" : "bearer"
    }

def process_ostools_logout(response : Response, refresh_token : str, db:Session):
    '''
    DB에 저장된 Refresh Token 삭제
    :param refresh_token : refresh token
    '''
    # DB에 저장된 Refresh Token
    stored_refresh_token = db.query(APP_Refresh_Tokens).filter(APP_Refresh_Tokens.token == refresh_token).first()
    if stored_refresh_token:
        db.delete(stored_refresh_token)
        db.commit()
    response.delete_cookie(key="access_token")
    return {
        "status" : status.HTTP_200_OK,
        "message" : "Logout Success"
    }

def login(data : str, db : Session = Depends(get_db)):
    '''
    Card Login Function
    일반 로그인(아이디, 비번) -> 카드 로그인으로 변경 가능
    '''
    decrypted = decrypt_pp(data)
    decrypted_uuid = decrypted.get("card_uuid") # 카드에 담겨있는 데이터 복호화 후 UUID 슬라이싱
     
    member_ssid = db.query(OsMember).filter(OsMember.uuid == decrypted_uuid).first() # DB의 사용자 UUID와 복호화 된 UUID 검증
    
    if member_ssid is None: 
        raise HTTPException(status_code=404,
                            detail="해당 UUID가 존재하지 않음")
        
    access_token = token_handler.create_access_token(data={"sub" : member_ssid.uuid}) # access token 생성
    refresh_token = token_handler.create_refresh_token(data={"sub" : member_ssid.uuid}) # refresh token 생성
    return {
        "status" : status.HTTP_200_OK,
        "access_token" : access_token,
        "refresh_token" : refresh_token,
        "token_type" : "bearer",
        "message" : "Login Success"
    }

# Current User Info
async def current_user_info(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    '''
    로그인 한 사용자 정보(user_id 조회 가능)
    '''
    try:
        data = token_handler.verify_token(token)
        user_id: str = data.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Token payload"
            )
        
        # 로그아웃 상태 확인
        refresh_token = db.query(APP_Refresh_Tokens).filter(
            APP_Refresh_Tokens.user_id == user_id,
            APP_Refresh_Tokens.expires_at > datetime.now()
        ).first()
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is logged out"
            )
        
        return user_id
        
    except JWTError as je:
        logger.error(f'JWT ERROR:{str(je)}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token"
        )
    except HTTPException as he:
        logger.error(f'Get Current User Info Error Occured:{str(he)}')
        raise he

        