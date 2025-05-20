from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from typing import Optional
import uuid
import json

from .redisConst import REDIS_AUTH_ATTEMPT_PREFIX
from common.database.conn_postgre import get_db
from common.database.database import redis_config
from common.models.models import API_Key
from utils.findApikey import find_service_info_by_apikey_value, find_internal_service_id_by_apikey_value
from schemes import InitAuthResponse, NfcStatusResponse
from custom_log import LoggerSetup

# Redis Connect
rd = redis_config()

logger_setup = LoggerSetup()
logger = logger_setup.logger

nfc_router = APIRouter(prefix="/api", tags=["NFC Authentication"])

# @nfc_router.post("/v1/nfc-init-auth", response_model=InitAuthResponse)
# def initiate_nfc_authentication(
#     api_key: str = Query(..., description="서비스 서버의 **사용자 apikey 값**"), # api_key 파라미터 사용
#     redirect_uri: str = Query(..., description="인증 완료 후 브라우저가 리다이렉트될 서비스 URI"),
#     state: Optional[str] = Query(None, description="OAuth 2.0 state 파라미터 (CSRF 방지 및 상태 유지)"),
#     db: Session = Depends(get_db) # 클라이언트 유효성 검증에 DB 사용
# ):
#     '''
#     - 서비스 서버가 호출: NFC 인증 시도 시작을 요청하고 시도 ID를 발급받음. Polling 방식에 사용.
#     - :params
#       - api_key: 서비스 서버의 **사용자 apikey 값** (Query)
#       - redirect_uri: 인증 완료 후 서비스 서버가 리다이렉트 받을 URI
#       - state: 서비스 서버가 요청에 대한 응답을 연결하기 위한 임의의 문자열 (OAuth 2.0 표준)
#     - :returns
#       - attempt_id: 이번 NFC 인증 시도를 고유하게 식별하는 ID
#     '''
#     try:
#         # 1. api_key(사용자 apikey 값) 유효성 검증 및 해당 서비스의 상세 정보, 특히 redirect_uri 목록 확인 (DB)
#         # API_Key 테이블에서 요청받은 api_key 값을 가지는 서비스가 등록된 행 찾음
#         api_key_entry = db.query(API_Key).filter(
#             text("EXISTS (SELECT 1 FROM jsonb_each(registered_service) as t WHERE t.value->>'apikey' = :api_key)")
#         ).params(api_key=api_key).first() # :api_key 파라미터는 요청받은 api_key 값

#         if not api_key_entry:
#             logger.warning(f"Initiate NFC Auth failed: Invalid api_key: {api_key}")
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid api_key.") # invalid_client

#         # API_Key entry를 찾았으므로 해당 row의 registered_service JSONB에서 요청된 api_key 값을 가지는 특정 서비스 항목을 찾습니다.
#         matching_service_info = find_service_info_by_apikey_value(api_key_entry.registered_service, api_key)

#         if not matching_service_info:
#              # 이 경우는 DB 데이터 불일치 또는 로직 오류 가능성.
#              logger.error(f"Internal error: Matched API_Key row ({api_key_entry.id}) but could not find specific service details for api_key {api_key}.")
#              raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal service configuration error.") # server_error

#         # 해당 서비스 항목에서 등록된 redirect_uri 목록을 가져와 요청받은 redirect_uri가 포함되는지 확인
#         registered_redirect_uris = matching_service_info.get("redirect_uri", [])
#         if not isinstance(registered_redirect_uris, list) or redirect_uri not in registered_redirect_uris:
#              logger.warning(f"Initiate NFC Auth failed: redirect_uri {redirect_uri} not registered for api_key {api_key}. Registered: {registered_redirect_uris}")
#              # 이 경우 OAuth2 error redirect가 불가능하므로 400 Bad Request
#              raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provided redirect_uri is not registered for this api_key.") # invalid_request

        
#         # 해당 서비스 항목의 내부 service_id(client_id:JSONB 키) 찾음
#         # service_id는 attemtp_state에 저장되어 '/card-response'에서 앱으로부터 전달받을 값과 일치하는지 검증
#         internal_service_id = find_internal_service_id_by_apikey_value(api_key_entry.registered_service, api_key)
#         if not internal_service_id:
#              # API_Key row는 찾았는데 apikey로 service info 찾는 것과 달리, 해당 apikey에 대응하는 JSONB 키(internal_service_id)를 못 찾은 경우
#              logger.error(f"Internal error: Could not find internal_service_id (JSONB key) for api_key {api_key} in API_Key row {api_key_entry.id}.")
#              raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal service configuration error (service ID missing).") # server_error

#         # 2. 고유한 시도 ID (attempt_id) 생성
#         attempt_id = str(uuid.uuid4())

#         # 3. Redis에 시도 상태 저장 (pending)
#         # attempt_id 키에 api_key (사용자 apikey 값), internal_service_id (JSONB 키 값), redirect_uri, state, 상태("pending") 및 TTL 저장
#         attempt_state = {
#             "status": "pending",
#             "api_key": api_key, # 요청받은 api_key 저장 (Authorization endpoint에서 사용)
#             "internal_service_id": internal_service_id, # 앱이 `/v1/card-response`에 보낼 값 (Card Response endpoint에서 검증)
#             "redirect_uri": redirect_uri,
#             "state": state,
#             "s_id": None # NFC 인증 완료 시 채워질 예정
#         }
#         # 시도 유효 시간 안에 NFC 인증 및 후속 처리가 완료되어야 함
#         attempt_ttl_seconds = 300 # 5분
#         redis_key = f"{REDIS_AUTH_ATTEMPT_PREFIX}{attempt_id}"
#         rd.setex(redis_key, attempt_ttl_seconds, json.dumps(attempt_state))

#         logger.info(f"NFC authentication attempt initiated. attempt_id: {attempt_id} for api_key: {api_key}, internal_service_id: {internal_service_id}")

#         # 4. 생성된 attempt_id 등을 포함한 응답 반환. Service Server는 attempt_id를 브라우저/앱에 전달
#         return InitAuthResponse(attempt_id=attempt_id)

#     except HTTPException as he:
#          raise he
#     except SQLAlchemyError as se:
#          logger.error(f"Database Error in initiate_nfc_authentication for api_key {api_key}: {str(se)}", exc_info=True)
#          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during initiation.") # server_error
#     except Exception as e:
#         logger.error(f"Unexpected Error in initiate_nfc_authentication for api_key {api_key}: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                             detail="Failed to initiate NFC authentication.") # server_error

@nfc_router.get("v1/nfc-status", response_model=NfcStatusResponse)
def get_nfc_authentication_status(attempt_id:str=Query(..., description="상태 조회용 NFC 인증 시도 식별자"),
                                  api_key:str=Query(..., description="사용자 서비스 APIKEY 값")):
    """
    - 서비스 서버가 호출할 API
    - NFC 인증 시도의 현재 상태 조회(Polling 용)
    :params
    - attempt_id: init-auth 시 발급받은 시도 식별자(ID)
    - api_key: 서비스 등록 시 발급받은 APIKEY
    :returns
    - NfcStatusResponse: status, optional(s_id, error_info)
    """
    try:
        redis_attempt_key = f"{REDIS_AUTH_ATTEMPT_PREFIX}{attempt_id}"
        attempt_state_bytes = rd.get(redis_attempt_key)
        
        # STEP 1. attempt_id 유효성 확인
        if not attempt_state_bytes:
            logger.warning(f"[/v1/nfc-status] failed: Invalid or Expired attempt_id{attempt_id}")
            return NfcStatusResponse(status="expired", 
                                     error="attempt_expired",
                                     error_description="Auth attempt expired or not exist")
        attempt_state = json.loads(attempt_state_bytes.decode('utf-8'))
        
        # STEP 2. api_key 일치 확인
        stored_api_key = attempt_state.get("api_key")
        if stored_api_key != api_key:
            logger.warning(f"[/v1/nfc-status] failed: api_key mismatch for attempt {attempt_id}. Expected: {stored_api_key}, Received: {api_key}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="api_key mismatch")
        
        # STEP 3. 현재 상태 정보를 포함한 응답 반환
        status_response = NfcStatusResponse(
            status=attempt_state.get("status", "unknown status"),
            s_id=attempt_state.get("s_id"),
            error=attempt_state.get("error")
        )
        
        logger.debug(f"[/v1/nfc-status] queried for attempt_id {attempt_id} (api_key {api_key}): Status {status_response.status}")
        return status_response
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[/v1/nfc-status] Unexpected Error for attempt {attempt_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error Occured while Retrieved NFC Auth Status")
        
            