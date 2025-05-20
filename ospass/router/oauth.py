from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Form, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import jwt, JWTError
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import json
import uuid

from common.models.models import Users, API_Key
from common.database.conn_postgre import get_db
from common.database.database import redis_config
from service.ospass_login import process_ospass_login
from service.token import Oauth_Token
from utils.findApikey import find_service_info_by_apikey_value
from utils.redirectError import redirect_with_oauth2_error
from custom_log import LoggerSetup
from .redisConst import (
    REDIS_AUTH_ATTEMPT_PREFIX,
    REDIS_AUTH_CODE_PREFIX,
    REDIS_REFRESH_TOKEN_PREFIX,
    REDIS_SESSION_UUID_MAP_PREFIX,
    REDIS_UUID_SESSION_MAP_PREFIX
)
from schemes import InitLoginRequest

oauth_router = APIRouter(prefix="/api", tags=["oauth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# Redis Connect
rd = redis_config()

token = Oauth_Token()

logger_setup = LoggerSetup()
logger = logger_setup.logger

@oauth_router.post("/v1/ospass-login")
def ospass_login(request : InitLoginRequest,
                 client_id : str=Query(...),
                 redirect_uri : str=Query(...),
                 state : str=Query(...),  
                 db:Session=Depends(get_db)):
    '''
    - OSPASS Login API
    - 사용자가 입력한 ID, Password를 통해 로그인 처리
    - 서비스 서버가 사용할 API
    :params
    - request: sliced_phone_num(010을 제외한 8자리) 
    - client_id : 서비스 서버는 api를 사용할 때 client_id를 쿼리스트링에 포함시켜 요청
    '''
    try:
        return process_ospass_login(request, client_id, redirect_uri, state, db)
    
    except Exception as e:
        logger.error(f"Error in ospass_login: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid Phone Number")

@oauth_router.get("/v1/authorization")
def authorize(response_type:str=Query(...,description="code로 고정"),
              api_key:str=Query(...,),
              redirect_uri:str=Query(...),
              state:Optional[str]=Query(None),
              attempt_id:Optional[str]=Query(None),
              db:Session=Depends(get_db)):
    """
    - 인가코드 제공 API
    - 사용자 브라우저가 호출, 서비스 서버로부터 Redirect 됨
    :params
    - response_type: code로 고정
    - api_key: 등록된 서비스 APIKEY
    - redirect_uri: 등록된 서비스의 Redirect URI
    - state: CSRF 방지용 임의 문자열(필수 X)
    - attempt_id: (NFC 플로우에서 사용) init-auth 시 발급, 
                   NFC 인증 완료 후 '/v1/nfc-status' 성공 응답 받은 후 서비스 서버가 redirect URI에 포함
                   (필수 X)
    """
    s_id = None # 사용자의 OSPASS 세션 ID
    attempt_state = None # 사용 시 해당 상태 정보 저장
    redis_attempt_key = None
    
    try:
        # STEP 1. api_key 및 redirec_uri 유효성 검증
        api_key_row = db.query(API_Key).filter(
            text("EXISTS (SELECT 1 FROM jsonb_each(registered_service) as t WHERE t.value->>'apikey' = :api_key)")
        ).params(api_key=api_key).first()
        
        if not api_key_row:
            logger.warning(f"Authorization failed: Invalid client_id (user apikey) {api_key}.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid api_key")
        
        # registered_service JSONB에 요청된 api_key를 찾음
        matching_service_info = find_service_info_by_apikey_value(api_key_row.registered_service, api_key)
        
        if not matching_service_info:
            logger.error(f"[/v1/authorization] Internal Error: Matched API_Key Row:{api_key_row} but not matched {api_key}")
            return redirect_with_oauth2_error(redirect_uri, status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Service Configuration Error", status)
        
                # 해당 서비스 항목에서 등록된 redirect_uri 목록을 가져와 요청받은 redirect_uri가 포함되는지 확인
        registered_redirect_uris = matching_service_info.get("redirect_uri", [])
        if not isinstance(registered_redirect_uris, list) or redirect_uri not in registered_redirect_uris:
             logger.warning(f"[/v1/authorization] failed: redirect_uri {redirect_uri} not registered for client_id (user apikey) {api_key}. Registered: {registered_redirect_uris}")
             # invalid_request 에러. redirect_uri는 유효하다는 전제 하에 에러 리다이렉션.
             return redirect_with_oauth2_error(redirect_uri, status.HTTP_400_BAD_REQUEST, "Provided redirect_uri is not registered for this client_id.", state)

        # STEP 2. response_type 검증
        if response_type != "code":
            logger.warning(f"[/v1/authorization] faild: Invalid response type:{response_type}")
            return redirect_with_oauth2_error(redirect_uri, status.HTTP_400_BAD_REQUEST,
                                              "Invalid response_type", state)
        
        # STEP 3. 사용자 식별(attempt_id 우선 처리)
        if attempt_id:
            redis_attempt_key = f"{REDIS_AUTH_ATTEMPT_PREFIX}{attempt_id}"
            attempt_state_bytes = rd.get(redis_attempt_key)
            
            if not attempt_state_bytes:
                logger.warning(f"[/v1/authorization] failed: Invalid or Expire attempt_id:{attempt_id}")
                return redirect_with_oauth2_error(redirect_uri, status.HTTP_401_UNAUTHORIZED,
                                                  "Authentication attempt expired or invalid", state)
            attempt_state = json.loads(attempt_state_bytes.decode('utf-8'))
            logger.debug(f"[/v1/authorization] Retrieved attempt state:{attempt_state}")
            
            # attempt_id 상태가 success인지 확인(NFC 인증 성공 완료 및 card-response API 성공 여부)
            if attempt_state.get("status") != "success":
                logger.warning(f"[/v1/authorization] failed: Attempt ID({attempt_id}) is not success({attempt_state.get('status')})")
                return redirect_with_oauth2_error(redirect_uri, status.HTTP_403_FORBIDDEN, 
                                                  "Authentication attempt not successful.", state)
            
            # attempt_id에 저장된 정보와 현재 authorization 요청 파라미터가 일치하는지 검증
            stored_api_key = attempt_state.get("api_key") # attempt_state - {api_key}
            stored_redirect_uri = attempt_state.get("redirect_uri") # attempt_state - {redirect_uri}
            stored_state = attempt_state.get("state") # attempt_state - {state}
            
            if stored_api_key != api_key or stored_redirect_uri != redirect_uri or (state is not None and stored_state != state):
                logger.warning(f"[/v1/authorization] failed: attempt_id({attempt_id}) mismatch request data")
                return redirect_with_oauth2_error(redirect_uri, status.HTTP_400_BAD_REQUEST, 
                                                  "Authorization request parameters do not match the initial attempt", state)
            
            # 성공 상태 attempt_state에서 OSPASS 세션 ID(s_id) 추출
            s_id = attempt_state.get("s_id") 
            # success 상태인데 s_id가 없는 경우
            if not s_id:
                logger.warning(f"[/v1/authorization] s_id missing in successful attempt state, Data:{attempt_state}")
                return redirect_with_oauth2_error(redirect_uri, status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                                  "Internal auth state error (#auth-s-id-missing).", state)
            
            logger.debug(f"Authentication Successful attempt_id:{attempt_id} and s_id:{s_id}")
            
            # 사용된 attempt_id는 필요없어짐 -> Reids에서 삭제
            rd.delete(redis_attempt_key)
            logger.debug(f"Deleted used attempt from Redis:{redis_attempt_key}")
        
        # STEP 4. 인가 코드 생성
        authorization_code = str(uuid.uuid4())
        logger.debug(f"[v1/autorization] Generated authorization code:{authorization_code} of s_id{s_id}")
        
        # STEP 5. Reids에 인가 코드 저장(s_id 포함)
        # auth_data: /v1/token 에서 인가 코드를 토큰으로 교환할 때 사용
        auth_data = {
            "code" : authorization_code,
            "api_key" : api_key,
            "redirect_uri" : redirect_uri,
            "state" : state,
            "session_id" : s_id
        }
        # 인가 코드 TTL 설정
        auth_code_ttl = 600 # 10분
        redis_auth_code_key = f"{REDIS_AUTH_CODE_PREFIX}{authorization_code}"
        rd.setex(redis_auth_code_key, auth_code_ttl, json.dump(auth_data))
        logger.debug(f"[/v1/authorization] Stored auth code")
        
        # STEP 6. 사용자의 브라우저를 서비스 서버의 redirect_uri로 리다이렉트
        # 쿼리 파라미터에 발급된 인가 코드를 포함시킴.
        redirect_query_params = {
            "code" : authorization_code,
            "state" : state
        }
        # None 값은 쿼리 파라미터에 포함하지 않음
        encoded_redirect_params = urlencode({k: v for k, v in redirect_query_params.items() if v is not None})
        redirect_url_with_code = f"{redirect_uri}?{encoded_redirect_params}"
        logger.info(f"[/v1/authorization] Redirecting browser to service redirect_uri: {redirect_url_with_code}")
        
        # 브라우저에게 Reidrection 응답
        return RedirectResponse(
            url=redirect_url_with_code,
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException as he:
        logger.error(f"[/v1/authorization] HTTP Error: {he.status_code}, {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"[v1/authorization] Unexpected Error")
        if redirect_uri:
            return redirect_with_oauth2_error(redirect_uri, status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                              "Unexpected Error occured during Get authorization", state)

@oauth_router.post("/v1/token")
def ospass_login_callback(grant_type:str=Form(...),
                          api_key:str=Form(...),
                          redirect_uri:str=Form(...),
                          code:str=Form(...), 
                          db:Session=Depends(get_db)):
    """
    - Access Token 발급 API
    - 서비스 서버가 호출할 API 
    - 인가 코드를 Access Token으로 교환
    :params
    - grant_type: 'authorization_code'로 고정
    - api_key: 서비스 서버의 APIKEY
    - redirect_uri: 서비스 서버가 등록한 redirect uri
    - code: /v1/authorization 응답으로 받은 인가코드
    """
    logger.info(f"[/v1/token] recevied grant_type{grant_type}, api_key{api_key}, redirect_uri{redirect_uri},code{code}")
    try:
        # grant_type 검증
        if grant_type != "authorization_code":
            logger.warning(f"[/v1/token] failed: Invalid grant type:{grant_type}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Unsupported grant_type. Must be 'authorization_code'")
        
        # api_key 검증
        api_key_row = db.query(API_Key).filter(
            text("EXISTS (SELECT 1 FROM jsonb_each(registered_service) as t WHERE t.value->>'apikey' = :api_key)")
        ).params(api_key=api_key).first()
        
        if not api_key_row:
            logger.warning(f"[/v1/token] failed: Invalid client_id (user apikey: {api_key})")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid api_key")
        
        # 인가 코드 검증 및 정보 조회(Redis에서 데이터 가져옴)
        redis_auth_code_key = f"{REDIS_AUTH_CODE_PREFIX}{code}"
        auth_data_bytes = rd.get(redis_auth_code_key)
        if not auth_data_bytes:
            logger.warning(f"[/v1/token] failed: Invalid or expired authorization code: {code}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid or expired authorization code")
        
        auth_info: Dict[str, Any] = json.loads(auth_data_bytes.decode('utf-8'))
        logger.debug(f"[/v1/token] Retrieved auth code info for:{auth_info}")
        
        # api_key 및 redirect_uri 검증
        stored_auth_api_key = auth_info.get("api_key")
        stored_redirect_uri = auth_info.get("redirect_uri")
        
        if stored_auth_api_key != api_key  or stored_redirect_uri != redirect_uri:
            logger.warning(f"[/v1/token] faild: Mismatch api_key{api_key} or redirect_uri{redirect_uri}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail="Invalid api_key or redirect_uri")
        
        # 토큰 발급
        # 인가 코드에 저장된 s_id를 access token/refresh token Claim에 사용(sub)
        s_id_for_token = auth_info.get("session_id")
        if not s_id_for_token:
            logger.error(f"[/v1/token] faild: Session ID not include authorization code({code})")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Internal server error: Session information missing in auth code")
            
        # Access Token / Refresh Token 생성
        access_token = token.create_access_token(data={"sub":s_id_for_token})
        refresh_token = token.create_refresh_token(data={"sub":s_id_for_token})
        
        logger.info(f"[/v1/token] Tokens issued for s_id: {s_id_for_token} <-api_key: {api_key}")
        
        # Redis에 Refresh Token 저장(s_id 매핑)
        # Key(s_id) : Value(refresh_token)
        refresh_token_redis_key = f"{REDIS_REFRESH_TOKEN_PREFIX}{s_id_for_token}"
        refresh_token_ttl = token.REFRESH_TOKEN_EXPIRE_MINUTES * 60 # 단위: 초
        rd.setex(refresh_token_redis_key, refresh_token_ttl, refresh_token)
        logger.debug(f"[/v1/token] Stored refresh token in Redis: key{refresh_token_redis_key}, ttl{refresh_token_ttl}")
        
        # 사용자 OSPASS 세션(s_id <-> uuid) 정보의 TTL을 Refreseh Token TTL과 동일하게 유지
        session_uuid_key = f"{REDIS_SESSION_UUID_MAP_PREFIX}{s_id_for_token}"
        if rd.exists(session_uuid_key): 
            rd.expire(session_uuid_key, refresh_token_ttl)
            logger.debug(f"[/v1/token] Extended TTL for session s_id key '{session_uuid_key}'")
            user_uuid_bytes = rd.get(session_uuid_key)
            if user_uuid_bytes:
               uuid_to_s_id_key = f"{REDIS_UUID_SESSION_MAP_PREFIX}{user_uuid_bytes.decode('utf-8')}"
               if rd.exists(uuid_to_s_id_key):
                    rd.expire(uuid_to_s_id_key, refresh_token_ttl)
                    logger.debug(f"[/v1/token] Extended TTL for uuid-session key '{uuid_to_s_id_key}'")
        else:
             logger.warning(f"[/v1/token] Session key {session_uuid_key} not found")
        
        # 사용된 인가 코드 삭제(일회성)
        rd.delete(redis_auth_code_key)
        logger.debug(f"[/v1/token] Deleted used authorization code: {redis_auth_code_key}")
        
        # 토큰 반환
        return {
            "token_type" : "bearer",
            "access_token" : access_token,
            "expires_in" : token.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_token" : refresh_token,
            "refresh_token_expires_in" : refresh_token_ttl
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[/v1/token] Unexpected Error for code {code is not None and code[:8] or 'N/A'}, client_id {api_key}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error Issuing Token")
        
@oauth_router.post("/v1/refresh-token")
def issued_refresh_token(grant_type:str=Form(...),
                         api_key:str=Form(...),
                         refresh_token:str=Form(...),
                         db:Session=Depends(get_db)):
    """
    - 토큰 갱신 API
    - 서비스 서버가 사용할 API
    :params
    - grant_type : refresh_token으로 고정
    - api_key : 서비스 서버의 사용자 API KEY
    - refresh_token : 기존에 발급받은 refresh token
    """
    s_id = None
    refresh_token_redis_key = None
    
    try:
        # grant_type 검증
        if grant_type != "refresh_token":
            logger.warning(f"[/v1/refresh-token] failed: Invalid grant type: {grant_type}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Unsupported grant type. Must be 'refresh_token'")
        
        # api_key 검증
        api_key_row = db.query(API_Key).filter(
            text("EXISTS (SELECT 1 FROM jsonb_each(registered_service) as t WHERE t.value->>'apikey' = :api_key)")
        ).params(api_key=api_key).first()
        
        if not api_key_row:
            logger.warning(f"[/v1/token] failed: Invalid client_id (user apikey: {api_key})")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid api_key")
        
        # Refresh Token 검증 및 사용자 식별(s_id 추출)
        try:
            payload = jwt.decode(
                refresh_token,
                token.REFRESH_SECRET_KEY,
                algorithms=[token.ALGORITHM]
            )
            s_id = payload.get("sub")
            if not s_id:
                logger.warning(f"[/v1/refresh-token] failed: Invalid Refresh Token")
                raise JWTError("Token payload missing sub")
            
            refresh_token_redis_key = f"{REDIS_REFRESH_TOKEN_PREFIX}{s_id}"
            stored_refresh_token_bytes = rd.get(refresh_token_redis_key)
            
            if not stored_refresh_token_bytes:
                logger.warning(f"[/v1/refresh-token] failed: Invalid Token or Expired")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Invalid Token or Not Found")
            
            stored_refresh_token = stored_refresh_token_bytes.decode('utf-8')
            
            if stored_refresh_token != refresh_token:
                logger.warning(f"[/v1/refresh-token] faild: not match for s_id:{s_id}")
                rd.delete(refresh_token_redis_key)
            
                # UUID 가져오기 및 삭제
                user_uuid_bytes_for_deletion = rd.get(f"{REDIS_SESSION_UUID_MAP_PREFIX}{s_id}") 
                if user_uuid_bytes_for_deletion:
                    rd.delete(f"{REDIS_UUID_SESSION_MAP_PREFIX}{user_uuid_bytes_for_deletion.decode('utf-8')}")
                
                rd.delete(f"{REDIS_SESSION_UUID_MAP_PREFIX}{s_id}")
            
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Refresh Token or Expried")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Refresh Token or Expried")
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                detail="Internal error during token validation:{e}")
    
        # 기존 사용자 세션이 유효한지 검사
        session_uuid_key = f"{REDIS_SESSION_UUID_MAP_PREFIX}{s_id}"
        user_uuid_bytes = rd.get(session_uuid_key)
        if not user_uuid_bytes:
            logger.warning(f"[v1/refresh-token] failed: User session s_id{s_id} not found")
            if rd.exists(refresh_token_redis_key): 
                rd.delete(refresh_token_redis_key)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                detail="User session has expired")
        
        # 새로운 Access Token 생성
        new_access_token = token.create_access_token(data={"sub":s_id})

        # 현재 Refresh Token TTL을 가져온 후 갱신 여부 판단
        refresh_token_current_ttl = rd.ttl(refresh_token_redis_key)
        if refresh_token_current_ttl < 0:
            refresh_token_current_ttl = token.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        
        issue_new_refresh_token = False
        # 남은 시간이 임계값보다 적으면 갱신
        renewal_threshold = 30 * 24 * 60 * 60 # 30 days
        if refresh_token_current_ttl > 0 and refresh_token_current_ttl < renewal_threshold:
            issue_new_refresh_token = True
            logger.debug(f"[v1/refresh-token] Issued Refressh Token")
        
        response_data = {
            "access_token" : new_access_token,
            "token_type" : "bearer",
            "expires_in" : token.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
        if issue_new_refresh_token:
            new_refresh_token = token.create_refresh_token(data={"sub":s_id})
            rd.setex(refresh_token_redis_key, token.REFRESH_TOKEN_EXPIRE_MINUTES * 60, new_refresh_token)
            response_data.update({
                "refresh_token" : new_refresh_token,
                "refresh_token_expires_in" : refresh_token_current_ttl
            })
            # Session TTL도 Refresh Token TTL로 세팅
            session_ttl = token.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        else:
            response_data.update({
                "refresh_token" : refresh_token,
                "refresh_token_expires_in" : refresh_token_current_ttl
            })
            session_ttl = refresh_token_current_ttl
            
        # STEP 7. 
        session_uuid_key = f"{REDIS_SESSION_UUID_MAP_PREFIX}{s_id}"
        if session_ttl > 0:
            rd.expire(session_uuid_key, session_ttl)
            user_uuid = user_uuid_bytes.decode('utf-8')
            uuid_to_s_id_key = f"{REDIS_UUID_SESSION_MAP_PREFIX}{user_uuid}"
            if rd.exists(uuid_to_s_id_key):
                rd.expire(uuid_to_s_id_key, session_ttl)
        else:
            logger.warning(f"[/v1/refresh-token] Session TTL calculated as non-positive")
        
        return response_data

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[/v1/refresh-token] Unexpected Error for client_id {api_key}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error refreshing token")

