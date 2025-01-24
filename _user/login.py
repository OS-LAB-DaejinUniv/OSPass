# User Login API
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from schemes import JoinUser, LoginForm
from models import Users
from conn_postgre import get_db
from register import verify_password
from ostools.token_handler import Token_Handler

login_router = APIRouter(prefix="/api")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Token Handler Instance
token_handler = Token_Handler()

# User 존재 여부 확인
def get_user_by_id(db : Session, user_id : str):
    return db.query(Users).filter(Users.user_id == user_id).first()

# DevPortal 로그인 API
@login_router.post("/v1/id-login")
def login(response : Response, login_form : LoginForm = Depends(), db : Session = Depends(get_db)):
    print(f"Login Form : {login_form}")
    
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
    access_token = token_handler.create_access_token(data={"sub" : user.user_id})
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

@login_router.post("/v1/refresh-token")
def refresh_token(refresh_token : str):
    # Exception Handling (예외 처리)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Refresh Token",
        headers={"WWW-Authenticate" : "Bearer"}
    )
    try:
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