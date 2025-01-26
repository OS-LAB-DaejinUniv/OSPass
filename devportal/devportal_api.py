from fastapi import APIRouter, Depends, status, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from conn_postgre import get_db

from schemes import JoinUser, LoginForm
from .key_gen import gen_api_key
from .register import register_user
from .login import process_login, issued_refresh_token, current_user_info, process_logout

devportal_router = APIRouter(prefix="/api")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Devportal Register API
@devportal_router.post("v1/register")
def register(new_user:JoinUser, db:Session=Depends(get_db)):
    '''
    - Devportal 회원가입 Endpoint
    '''
    register_user(new_user, db)
    return {"status" : status.HTTP_201_CREATED,
            "message" : "User registration successful"}

# Devportal Login API
@devportal_router.post("v1/id-login")
def login(response : Response, db: Session=Depends(get_db), login_form: LoginForm = Depends()):
    '''
    - Devportal 로그인 Endpoint
    '''
    return process_login(response, db, login_form)

# Refresh Token 발급 API
@devportal_router.post("v1/id-refresh-token")
def refresh_token(refresh_token:str):
    '''
    - Refresh Token 발급 Endpoint
    '''
    return issued_refresh_token(refresh_token)

# Currnet User Information API
@devportal_router.get("v1/current-user")
def get_current_user(token: str = Depends(oauth2_scheme)):
    '''
    - Devportal Current User Information Endpoint
    - user_id, user_name 제공
    '''
    return current_user_info(token)

# Devportal Logout API
@devportal_router.post("v1/id-logout")
def logout(response: Response, token: str = Depends(oauth2_scheme)):
    '''
    - Devportal Logout Endpoint
    - Token Blacklist 방식
    '''
    return process_logout(response, token)
    
# Devportal에서 API KEY를 발급받을 수 있는 API
@devportal_router.post("/v1/apikey")
def get_apikey(token: str=Depends(oauth2_scheme), db: Session=Depends(get_db)):
    '''
    - API KEY 발급 Endpoint
    '''
    gen_api_key(db, token)
    return {"status" : status.HTTP_201_CREATED,
            "message": "API KEY CREATED SUCCESSFULLY"}