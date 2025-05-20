from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import json
import uuid

from .redisConst import (
    REDIS_AUTH_ATTEMPT_PREFIX,
    REDIS_SESSION_UUID_MAP_PREFIX,
    REDIS_UUID_SESSION_MAP_PREFIX
)
from custom_log import LoggerSetup
from common.database.conn_postgre import get_db
from common.database.database import redis_config
from common.models.models import Users
from service.auth import process_verify_card_response
from service.token import Oauth_Token
from schemes import Card_Data_With_Attempt

cardResponse_router = APIRouter(prefix="/api", tags=["CardResponse"])

rd = redis_config()

token = Oauth_Token()

logger_setup = LoggerSetup()
logger = logger_setup.logger

@cardResponse_router.post("/v1/card-response")
def verify_card_response(data: Card_Data_With_Attempt,
                         service_id: str=Query(..., description="서비스 식별자"),
                         db:Session=Depends(get_db)):
    """
    - OSTOOLS 앱에서 호출될 API (NFC 인증 응답)
    - attempt_id와 NFC 데이터를 받아 해당 시도를 '성공' 상태로 업데이트하고 사용자를 연결
    - 앱은 Push Notification을 통해 받은 service_id(JSON KEY('client_id'))를 사용
    :params
    - data: card_data + attempt_id(카드 데이터(UUID+Response)+ 시도 식별자)
    - service_id: 서비스 등록 시 생성된 client_id(서비스 고유 식별자)
    """
    attempt_id = data.attempt_id
    
    logger.debug(f"[/v1/card-response] received for attempt_id: {attempt_id}, service_id:{service_id}")
    
    redis_attempt_key = f"{REDIS_AUTH_ATTEMPT_PREFIX}{attempt_id}"
    attempt_state_bytes = rd.get(redis_attempt_key)
    attempt_state = None 
    current_ttl = -3 
    
    try:
        # STEP 1. attempt_id 유효성 및 상태(pending) 확인 
        if not attempt_state_bytes:
            logger.warning(f"[/v1/card-response] failed: Invalid or Expired attempt_id:{attempt_id}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid or Expired authentication attempt")
        
        attempt_state = json.loads(attempt_state_bytes.decode('utf-8'))
        current_ttl = rd.ttl(redis_attempt_key) # 추후 업데이트 위해 TTL 가져오기
        
        # 해당 시도가 완료되었거나 다른 서비스의 것인지 확인
        if attempt_state.get("status") != "pending":
            logger.warning(f"[/v1/card-response] failed: Attempt ID{attempt_id} not pending, current status:{attempt_state.get('status')}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Authentication attempt is not pending")
        
        # STEP 2. serivce_id(JSON(client_id)) 일치 여부 확인
        # initiate 시 attempt_state에 저장된 internal_service_id
        # card-response 시 전달된 service_id(client_id) 값 비교
        stored_internal_service_id = attempt_state.get("internal_service_id")
        if stored_internal_service_id != service_id:
            logger.warning(f"[/v1/card-response] failed: service_id mismatch for attempt {attempt_id}" \
                           f"Expected: {stored_internal_service_id}, Received: {service_id}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="serivce_id mismatch for this attempt")
        
        # STEP 3. NFC 데이터 검증 및 UUID 복호화 / 추출출
        decrypted_uuid = process_verify_card_response(data, service_id, db)
        logger.debug(f"[/v1/card-response] Decrypted My-UUID:{decrypted_uuid}")
        
        # STEP 4. 복호화된 UUID로 DB에서 사용자 조회
        user_row = db.query(Users).filter(Users.user_uuid == decrypted_uuid).first()
        if not user_row:
            # 사용자(사용자의 UUID)가 DB에 없으면 해당 시도를 실패로 표시 후 응답
            attempt_state["status"] = "failed"
            attempt_state["error"] = "user_not_found"
            attempt_state["error_description"] = "User associated with NFC card not found."
            
            # Reids 상태 업데이트
            if current_ttl > -2: # 키가 아직 존재하면
                rd.setex(redis_attempt_key, 
                         max(current_ttl, 60) if current_ttl > 0 else 60, 
                         json.dumps(attempt_state))
            logger.warning(f"[/v1/card-response] NFC auth failed for attempt {attempt_id}: Member not found UUID:{decrypted_uuid}")
            raise HTTPException(status_code=404,
                                detail="User not found")
        
        logger.info(f"[/v1/card-response] NFC authentication successful for UUID {decrypted_uuid}, linking to attempt_id:{attempt_id}")
        
        # STEP 5. OSPASS 내부 세션 ID(s_id) 생성 및 Redis 매핑 저장
        s_id = str(uuid.uuid4())
        
        # s_id -> UUID & UUID -> s_id
        # 세션 수명(s_id)은 Refresh Token 수명과 연결
        session_ttl = token.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        rd.setex(f"{REDIS_SESSION_UUID_MAP_PREFIX}{s_id}",
                 session_ttl,
                 decrypted_uuid)
        rd.setex(f"{REDIS_UUID_SESSION_MAP_PREFIX}{decrypted_uuid}",
                 session_ttl,
                 s_id)
        logger.debug(f"[/v1/card-response] Generated OSPASS Session ID (s_id): {s_id}, linked to UUID {decrypted_uuid}, TTL: {session_ttl}")
        
        # STEP 6. Redis 해당 시도 상태를 성공으로 업데이트 후 발급된 s_id 연결
        attempt_state["status"] = "success"
        attempt_state["s_id"] = s_id # 발급된 s_id를 attempt 상태에 저장
        
        # attempt status Redis 업데이트 
        # Service Server가 상태를 Polling해서 가져갈 수 있기 위함
        if current_ttl > -2:
            rd.setex(redis_attempt_key,
                     max(current_ttl, 60) if current_ttl > 0 else 60,
                     json.dumps(attempt_state))
        else:
            logger.error(f"[/v1/card-response] Attempt Key unexpectly expired")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Internal State error during verification")
        
        # STEP 7. OSTOOLS에게 성공 응답 반환
        return {"message" : "NFC Authentication Successful. Status Updated"}
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[/v1/card-response] Unexpected Error for attempt {attempt_id}, service_id {service_id}: {str(e)}", exc_info=True)
        if attempt_state is not None and current_ttl > -2:
            attempt_state["status"] = "failed"
            attempt_state["error"] = "internal_error"
            attempt_state["error_description"] = "An unexpected server error occurred during verification."
            rd.setex(redis_attempt_key, max(current_ttl, 60) if current_ttl > 0 else 60, json.dumps(attempt_state))
            
            