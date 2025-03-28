from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from urllib.parse import urlencode
import uuid
import json

from schemes import Card_Data
from common.models.models import Users, API_Key
from common.database.conn_postgre import get_db
from common.database.database import redis_config
from custom_log import LoggerSetup
from service.auth import process_verify_card_response
from service.token import Oauth_Token
from service.ospass_login import process_ospass_login
from schemes import InitLoginRequest

ospass_router = APIRouter(prefix="/api", tags=["ospass"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Redis Connect
rd = redis_config()

token = Oauth_Token()

logger_setup = LoggerSetup()
logger = logger_setup.logger

@ospass_router.post("/v1/ospass-login")
def ospass_login(request : InitLoginRequest,
                 client_id : str=Query(...),  
                 db:Session=Depends(get_db)):
    '''
    - OSPASS Login API
    - 사용자가 입력한 ID, Password를 통해 로그인 처리
    - 서비스 서버가 사용할 API
    :params 
    - client_id : 서비스 서버는 api를 사용할 때 client_id를 쿼리스트링에 포함시켜 요청
    '''
    try:
        return process_ospass_login(request, client_id, db)
    
    except Exception as e:
        logger.error(f"Error in ospass_login: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid Phone Number")

@ospass_router.post("/v1/card-response")
async def verify_card_response(response : Response, 
                               data : Card_Data, 
                               client_id : str=Query(..., description="서비스 식별자"), 
                               db: Session = Depends(get_db)):
    '''
    - OSTOOLS에서 호출될 API
    - QRcode -> Applink -> API 호출
    '''
    try:
        print(f"[DEBUG] Recieved Data:{data.model_dump()}")
        print(f"[DEBUG] Client ID: {client_id}")
        decrypted_uuid = process_verify_card_response(data, client_id, db)
        print(f"Decrypted MY-UUID: {decrypted_uuid}")
        # My-UUID(Card)와 DB에 저장된 UUID가 일치하는지 확인
        verify_result = db.query(Users).filter(Users.user_uuid == decrypted_uuid).first()
        if not verify_result:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # 일치하면 Session ID 발급 후 쿠키에 저장
        s_id = str(uuid.uuid4()) # 세션 아이디 하나 생성 : 사용자 식별용
        response.set_cookie(key="MySessionID", value=s_id, 
                            httponly=True, secure=True)
        
        # Redis에 (s_id -> UUID) & (UUID -> s_id) 저장
        rd.setex(s_id, 600, decrypted_uuid)
        rd.setex(decrypted_uuid, 600, s_id)
        
        return {"message": "NFC Authentication Successful", "MySessionID" : {s_id}}
    
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@ospass_router.get("/v1/authorization")
async def authorize(request : Request,
                    response_type : str = Query(...), # "code"로 고정
                    APIKEY : str = Query(...), 
                    redirect_uri : str = Query(...), 
                    db : Session = Depends(get_db)):
    '''
    - 인가코드 제공 API
    - API_KEY : Devportal에서 발급받은 API KEY => API 사용자(서비스 서버)는 헤더에 추가하여 Request
    - redirect_uri : 사용자의 서비스 URI
    - 서비스 서버가 사용할 API
    :params 
    - response_type : code로 고정 -> {인가코드}
    - API_KEY : 사용자의 서비스 API_KEY
    - redirect_uri : devportal에 등록한 서비스의 redirect uri
    '''
    try:
        # STEP 1. API KEY 검증
        user_api_key = db.query(API_Key).filter(
            text("EXISTS (SELECT 1 FROM jsonb_each(registered_service) as t WHERE t.value->>'apikey' = :api_key)")
            ).params(api_key=APIKEY).first()
        if not user_api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid API KEY")
        
        # STEP 2. response_type 검증
        if response_type != "code":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid Response Type!")
        
        # STEP 3. Session ID 검증
        s_id = request.cookies.get("MySessionID")
        print(f"Saved Cookie Data MYSessionID:{s_id}")
        if not s_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Unauthorized User")
        
        # STEP 4. 인가 코드 생성
        authorization_code = str(uuid.uuid4())
        
        # STEP 5. Redis에 인가 코드 저장(추가 정보 포함)
        auth_data = {
            "code" : authorization_code,
            "api_key" : APIKEY,
            "redirect_uri" : redirect_uri,
            "session_id" : s_id
        }
        # Redis INSERT -> key : value (auth_cde: auth_data)
        # 인가 코드 TTL 설정: 600초(10분) 동안 유효
        rd.setex(f"auth_code:{authorization_code}", 600, json.dumps(auth_data))
        
        # STEP 6. Redirection
        query_params = {
            "code" : authorization_code
        }
        # 리다이렉션 URI + 인가 코드를 포함하여 반환
        redirect_url = f"{redirect_uri}?{urlencode(query_params)}" # redirect_url 
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )
    
    except Exception as e:
        logger.error(f"Authorization Error:{str(e)}")
        # Error 발생 시 Redirection
        error_redirect = f"{redirect_uri}?error=server_error&error_description={str(e)}"
        return RedirectResponse(url=error_redirect)

@ospass_router.post("/v1/token")
def ospass_login_callback(grant_type:str=Form(...),
                          APIKEY:str=Form(...),
                          redirect_uri:str=Form(...),
                          code:str=Form(...), 
                          db:Session=Depends(get_db)):
    '''
    - 발급 받은 인가 코드를 통해 access token 발급해주고 redirection 진행
    - code: 인가 코드
    - redirect_uri: Redirection 하고자 하는 uri
    - 서비스 서버가 사용할 API
    :params
    - grant_type : authorization_code로 고정
    - APIKEY : Devportal에서 발급받은 서비스의 APIKEY
    - redirect_uri : Devportal에 등록한 서비스의 redirect uri
    - code: 인가 코드(authorization에서 받은 인가코드)
    '''
    try:
        # STEP 1. grant_type 검증
        if grant_type != "authorization_code":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid grant_type")
        
        # STEP 2. API KEY 검증
        api_key = db.query(API_Key).filter(
            text("EXISTS (SELECT 1 FROM jsonb_each(registered_service) as t WHERE t.value->>'apikey' = :api_key)")
            ).params(api_key=APIKEY).first()
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid API KEY")
        
        # STEP 3. 인가 코드 검증
        auth_data = rd.get(f"auth_code:{code}")
        if not auth_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid Authorization Code")
        auth_info = json.loads(auth_data)
        
        # STEP 4. redirect uri 검증
        if auth_info["redirect_uri"] != redirect_uri:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid redirect_uri")
        
        # STEP 5. 토큰 발급
        access_token = token.create_access_token(data={"sub":auth_info["session_id"]})
        refresh_token = token.create_refresh_token(data={"sub":auth_info["session_id"]})
        
        # STEP 6. Redis에 Refresh Token 저장
        rd.setex(f"refresh_token:{auth_info['session_id']}", 
                 token.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
                 refresh_token)
        
        # STEP 7. 사용된 인가 코드 삭제
        rd.delete(f"auth_code:{code}")
        
        return {
            "token_type" : "bearer",
            "access_token" : access_token,
            "expires_in" : token.ACCESS_TOKEN_EXPIRE_MINUTES * 60, # 초 단위로 변환
            "refresh_token" : refresh_token,
            "refresh_token_expires_in" : token.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Token Issuance Error:{str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="Error Issuing Token")
        
@ospass_router.post("/v1/refresh-token")
def issued_refresh_token(grant_type:str=Form(...),
                         API_KEY:str=Form(...),
                         refresh_token:str=Form(...),
                         db:Session=Depends(get_db)):
    '''
    - 토큰 갱신 API
    - 서비스 서버가 사용할 API
    :params
    - grant_type : refresh_token으로 고정
    - API KEY : Devportal에서 발급받은 서비스의 API KEY
    - refresh_token : 기존에 발급받은 refresh token
    '''
    try:
        # STEP 1. grant type 검증
        if grant_type != "refresh_token":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid grant type")
        
        # STEP 2. API KEY 검증
        api_key = db.query(API_Key).filter(API_Key.registered_service["apikey"] == API_KEY).first()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API KEY")
        
        # STEP 3. Refresh Token 검증
        try:
            payload = jwt.decode(
                refresh_token,
                token.REFRESH_SECRET_KEY,
                algorithms=[token.ALGORITHM]
            )
            s_id = payload["sub"]
            
            # Redis에 저장된 refresh token과 비교
            stored_refresh_token = rd.get(f"refresh_token:{s_id}")
            if not stored_refresh_token or stored_refresh_token != refresh_token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Invalid Refresh Token")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid or Expried Refresh Token")
        
        # STEP 4. 새로운 access token 발급
        new_access_token = token.create_access_token(data={"sub" : s_id})
        
        # STEP 5. Refresh Token 갱신 여부 확인
        # Refresh Token의 만료 기간이 1개월 미만일 경우 새로 발급
        remaining_time = rd.ttl(f"refresh_token:{s_id}")
        response_data = {
            "access_token" : new_access_token,
            "token_type" : "bearer",
            "expires_in" : token.ACCESS_TOKEN_EXPIRE_MINUTES * 60 
        }
        if remaining_time and remaining_time < (30 * 24 * 60 * 60): # 30일 미만
            new_refresh_token = token.create_refresh_token(data={"sub" : s_id})
            rd.setex(f"refresh_token:{new_refresh_token}", token.REFRESH_TOKEN_EXPIRE_MINUTES * 60, new_refresh_token)
            response_data.update({
                "refresh_token" : new_refresh_token,
                "refresh_token_expires_in" : token.REFRESH_TOKEN_EXPIRE_MINUTES * 60
            })
        
        return response_data
    
    except HTTPException as he:
        raise he
    
    except Exception as e:
        logger.error(f"Token Refresh Error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error refresh token")

@ospass_router.post("/v1/logout")
def logout(response : Response, access_token:str=Depends(oauth2_scheme)):
    """
    - 로그아웃 API
    - 클라이언트가 전달한 access token을 이용하여 세션을 식별하고,
      Redis에 저장된 refresh token과 세션 정보를 삭제합니다.
    - 쿠키에 저장된 MySessionID도 삭제하여 클라이언트 측 인증 정보를 제거합니다.
    :param 
    - access_token: OAuth2 Bearer 토큰
    :return: 로그아웃 성공 메시지
    """
    try:
        payload = jwt.decode(access_token, token.ACCESS_SECRET_KEY,
                            algorithms=[token.ALGORITHM])
        s_id = payload.get("sub")
        if not s_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token")

        # Redis에 저장된 refresh token 및 Session Data(s_id) 삭제
        rd.delete(f"refresh_token:{s_id}")
        rd.delete(s_id)
        
        # 클라이언트 쿠키 삭제
        response.delete_cookie(key="MySessionID")
        
        return {"message" : "Logged Out Successfully"}

    except JWTError as je:
        logger.error(f"JWT Error:{str(je)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Token")
    except Exception as e:
        logger.error(f"Error Occured while Logout:{str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error during Logout")