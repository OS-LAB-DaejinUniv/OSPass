from fastapi import APIRouter, Depends, status, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from conn_postgre import get_db

from schemes import JoinUser, LoginForm
from .register import register_user
from .login import process_login, issued_refresh_token, current_user_info, process_logout
from .service_name import process_register_service
from .redirect_uri import process_register_redirect_uri
from .devportal_schemes import RegisterServiceRequset, RegisterRedirectUri

devportal_router = APIRouter(prefix="/api")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Devportal Register API
@devportal_router.post("/v1/register")
def register(new_user:JoinUser, db:Session=Depends(get_db)):
    '''
    - Devportal 회원가입 Endpoint
    '''
    register_user(new_user, db)
    return {"status" : status.HTTP_201_CREATED,
            "message" : "User registration successful"}

# Devportal Login API
@devportal_router.post("/v1/id-login")
def login(response : Response, db: Session=Depends(get_db), login_form: LoginForm = Depends()):
    '''
    - Devportal 로그인 Endpoint
    '''
    return process_login(response, db, login_form)

# Refresh Token 발급 API
@devportal_router.post("/v1/id-refresh-token")
def refresh_token(refresh_token:str):
    '''
    - Refresh Token 발급 Endpoint
    '''
    return issued_refresh_token(refresh_token)

# Currnet User Information API
@devportal_router.get("/v1/current-user")
def get_current_user(token: str = Depends(oauth2_scheme)):
    '''
    - Devportal Current User Information Endpoint
    - user_id, user_name 제공
    '''
    return current_user_info(token)

# Devportal Logout API
@devportal_router.post("/v1/id-logout")
def logout(response: Response, token: str = Depends(oauth2_scheme)):
    '''
    - Devportal Logout Endpoint
    - Token Blacklist 방식
    '''
    return process_logout(response, token)
    
# # Devportal에서 API KEY를 발급받을 수 있는 API
# @devportal_router.post("/v1/apikey")
# def get_apikey(token: str=Depends(oauth2_scheme), db: Session=Depends(get_db)):
#     '''
#     - API KEY 발급 Endpoint
#     '''
#     gen_api_key(db, token)
#     return {"status" : status.HTTP_201_CREATED,
#             "message": "API KEY CREATED SUCCESSFULLY"}

# Devportal에서 User의 Service 등록 API    
@devportal_router.post("/v1/register-service")
def register_service(request : RegisterServiceRequset, db:Session=Depends(get_db), current_user=Depends(current_user_info)):
    '''
    - Service Name 등록 Endpoint
    '''
    result = process_register_service(request.service_name,db,current_user)
    return result

@devportal_router.post("/v1/redirect-uris")
def register_redirect_uris(data : RegisterRedirectUri,
                           current_user:dict=Depends(current_user_info), 
                           db:Session=Depends(get_db)):
    '''
    - Redirect Uri 등록 Endpoint
    - List Type , 여러 개 등록 가능
    - data : client_id, redirect_uri
    '''
    result = process_register_redirect_uri(data,db,current_user)
    return result