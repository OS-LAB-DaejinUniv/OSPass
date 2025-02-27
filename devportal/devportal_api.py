from fastapi import APIRouter, Depends, status, Response, Request, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from conn_postgre import get_db
from schemes import JoinUser, LoginForm
from .devportal_schemes import ResetPasswordRequestID
from .user.register import register_user
from .user.login import process_login, issued_refresh_token, current_user_info, process_logout
from .user.find_passwd import process_reset_user_password
from .user.delete_user import process_delete_user
from .service_name import process_register_service
from .redirect_uri import process_register_redirect_uri
from .devportal_schemes import RegisterServiceRequset, RegisterRedirectUri
from .register_service._show_service import show_service

devportal_router = APIRouter(prefix="/api", tags=["devportal"])

# auto_error=True(defautl 값) : 요청에 Autorization 헤더가 없으면 401 에러 발생시킴
# auto_error=False : Authorization 헤더 없어도 에러 발생 X, 토큰이 없으면 None 반환, 개발자가 토큰 존재 여부 직접 처리
# False로 설정한 이유 : id-login api 경우 최초 로그인 시 토큰 없는 것이 정상
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

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
def login(response : Response, token:Optional[str]=Depends(oauth2_scheme), 
          db: Session=Depends(get_db), login_form: LoginForm = Depends()):
    '''
    - Devportal 로그인 Endpoint
    '''
    return process_login(response, token, db, login_form)

# Refresh Token 발급 API
@devportal_router.post("/v1/id-refresh-token")
def refresh_token(request : Request):
    '''
    - Refresh Token 발급 Endpoint
    '''
    return issued_refresh_token(request)

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
def logout(response: Response, token: Optional[str] = Depends(oauth2_scheme)):
    '''
    - Devportal Logout Endpoint
    - Token Blacklist 방식
    '''
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token is required for logout")
    return process_logout(response, token)

# Devportal에서 User의 Service 등록 API    
@devportal_router.post("/v1/register-service")
def register_service(request : RegisterServiceRequset, db:Session=Depends(get_db), current_user=Depends(current_user_info)):
    '''
    - Service Name 등록 Endpoint
    '''
    result = process_register_service(request.service_name,db,current_user)
    return result

@devportal_router.get("/v1/services/")
def services(db:Session=Depends(get_db),current_user=Depends(current_user_info)):
    '''
    - 등록된 Service Infomation List Up Endpoint
    '''
    user_name = current_user["user_name"]
    
    return show_service(db, current_user)

# Devportal에서 User의 Service Redirect Uri 등록 API
@devportal_router.post("/v1/redirect-uris")
def register_redirect_uris(data : RegisterRedirectUri,
                           current_user:dict=Depends(current_user_info), 
                           db:Session=Depends(get_db)):
    '''
    - Redirect Uri 등록 Endpoint
    - List Type[] , 여러 개 등록 가능
    - data : client_id, redirect_uri
    '''
    result = process_register_redirect_uri(data,db,current_user)
    return result

# Devportal에서 User의 비밀번호 Reset API
@devportal_router.post("/v1/reset-password")
def reset_user_password(user_id: ResetPasswordRequestID, db:Session=Depends(get_db)):
    '''
    - 비밀번호 찾기 Endpoint
    - user_id : 사용자 ID 입력
    '''
    process_reset_user_password(user_id.user_id, db)
    return {"status" : status.HTTP_200_OK,
            "message" : "Password reset successfully"}

# Devportal에서 User 회원탈퇴 API
@devportal_router.delete("/v1/delete-user")
def delete_user(db:Session=Depends(get_db), current_user:dict=Depends(current_user_info)):
    '''
    - 사용자 탈퇴 Endpoint
    '''
    result = process_delete_user(db, current_user)
    return result