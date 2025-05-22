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

@nfc_router.get("/v1/nfc-status", response_model=NfcStatusResponse)
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
        
            