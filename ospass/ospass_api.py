from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import uuid
import random

from schemes import Card_Data, SessionKey, LoginForm
from models import OsMember, API_Key
from conn_postgre import get_db
from database import redis_config
from custom_log import LoggerSetup
from .service.auth import process_verify_card_response, issue_access_token
from .service.token import Oauth_Token
from .service.ospass_login import process_ospass_login

ospass_router = APIRouter(prefix="/api")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Redis Connect
rd = redis_config()

token = Oauth_Token()

logger_setup = LoggerSetup()
logger = logger_setup.logger

@ospass_router.post("/v1/card-response")
async def verify_card_response(data : Card_Data, user_session : SessionKey, 
                               response : Response, db: Session = Depends(get_db)):
    '''
    - OSTOOLS에서 호출될 API
    - QRcode -> Applink -> API 호출
    '''
    try:
        decrypted_uuid = process_verify_card_response(data, user_session, db)
        print(f"Decrypted MY-UUID: {decrypted_uuid}")
        # My-UUID(Card)와 DB에 저장된 UUID가 일치하는지 확인
        verify_result = db.query(OsMember).filter(OsMember.uuid == decrypted_uuid).first()
        if not verify_result:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # 일치하면 Session ID 발급 후 쿠키에 저장
        s_id = str(uuid.uuid4()) # 세션 아이디 하나 생성
        response.set_cookie(key="MySessionID", value=s_id, 
                            httponly=True, secure=True)
        
        # Redis에 (s_id -> UUID) & (UUID -> s_id) 저장
        rd.setex(s_id, 600, decrypted_uuid)
        rd.setex(decrypted_uuid, 600, s_id)
        
        return {"message": "NFC Authentication Successful", "MySessionID" : {s_id}}
    
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@ospass_router.get("/v1/authorization-code")
def issue_authorization_code(API_KEY : str, redirect_uri : str, 
                             response : Response, request : Request, db : Session = Depends(get_db)):
    '''
    - 인가코드 제공 API
    - API_KEY : Devportal에서 발급받은 API KEY => API 사용자(서비스 서버)는 헤더에 추가하여 Request
    - redirect_uri : 사용자의 서비스 URI
    - 서비스 서버가 사용할 API
    '''
    try:
        # My-Session ID
        s_id = request.cookies.get("MySessionID")
        if not s_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Unauthorized User")
        # My-API KEY
        user_api_key = db.query(API_Key).filter(API_Key.apikey == API_KEY).first() # 생성된 API KEY SELECT 
        if not user_api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid API KEY")
        
        # 인가 코드 생성
        authorization_code = str(uuid.uuid4())
        
        # Redis INSERT -> key : value (session id : authorization code)  
        # 인가 코드 TTL 설정: 600초(10분) 동안 유효
        rd.setex(s_id, 600, authorization_code)
        
        # 리다이렉션 URL에 인가 코드를 포함하여 반환
        redirect_url = f"{redirect_uri}?code={authorization_code}" # redirect_url 
        response.status_code = status.HTTP_302_FOUND
        response.headers["Location"] = redirect_url
        return {"message" : "Redirecting with authorization code"}       
    except HTTPException as e:
        raise f'Error in issue_authorization_code: {str(e)}'
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="Internal Server Error")

@ospass_router.get("/v1/callback")
def ospass_login_callback(code : str, redirect_uri : str, 
                          request : Request, db:Session=Depends(get_db)):
    '''
    - 발급 받은 인가 코드를 통해 access token 발급해주고 redirection 진행
    - code: 인가 코드
    - redirect_uri: Redirection 하고자 하는 uri
    - 서비스 서버가 사용할 API
    '''
    try:
        # 요청 데이터에서 카드 정보(member uuid) 가져옴
        card_data = request.json()
        decrypted_member_uuid = process_verify_card_response(card_data, None, db)
        
        stored_s_id = request.cookies.get("MySessionID") # cookie에서 s_id 가져옴
        if not stored_s_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Session ID not found")
        s_id = stored_s_id.decode()
        
        # 인가 코드 redis에서 가져온 후 검증
        auth_code = rd.get(s_id)
        if not auth_code:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Authorization Code not found")
        if auth_code.decode() != code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Authorization code")

        # access token 발급 -> 서비스 서버를 Redirect
        access_token = issue_access_token(decrypted_member_uuid)
        response = RedirectResponse(url=redirect_uri)
        response.set_cookie(key="access_token", value=access_token, 
                            httponly=True, secure=True)
        return response
        
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="Invalid Authorization code")
        
@ospass_router.post("/v1/refresh-token")
def issued_refresh_token(request:Request, response:Response):
    '''
    - Refresh Token 발급 API
    - Session ID(s_id)를 통해 Redis에 저장된 Refresh Token을 확인하고 새로운 Access Token 발급
    - 서비스 서버가 사용할 API
    '''
    try:
        s_id = request.cookies.get("MySessionID")
        
        if not s_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Session ID(s_id) not found")
        
        # Redis에서 Refresh Token 확인
        stored_refresh_token = rd.get(f"refresh_token:{s_id}")
        if not stored_refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Refresh Token Not found")
        try:
            payload = jwt.decode(stored_refresh_token,token.REFRESH_TOKEN_EXPIRE_KEY,
                                 algorithms=[token.ALGORITHM])
            token_data = payload["rtd"]
            token_s_id = token_data["sub"]
            
            # Session ID 일치 여부 확인
            if token_s_id != s_id:
               raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                   detail="Invalid Session ID(s_id)")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Refresh Token has Expired")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Refresh Token")
        # 새로운 Access Token 발급
        new_access_token = issue_access_token(s_id, response)
        
        return {
            "message" : "Access Token refresh Successfully",
            "access_token" : new_access_token,
            "token_type" : new_access_token.token_type
        }
    except Exception as e:
        logger.error(f"Error in refrehs_access_token: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error during Token Refresh")
        
@ospass_router.post("/v1/ospass-login")
def ospass_login(sliced_phone_num:str, db:Session=Depends(get_db)):
    '''
    - OSPASS Login API
    - 사용자가 입력한 ID, Password를 통해 로그인 처리
    - 서비스 서버가 사용할 API
    '''
    try:
        return process_ospass_login(sliced_phone_num, db)
    
    except Exception as e:
        logger.error(f"Error in ospass_login: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid Phone Number")