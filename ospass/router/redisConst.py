REDIS_AUTH_ATTEMPT_PREFIX = "nfc_attempt:" # NFC 인증 시도 상태 저장 키
REDIS_AUTH_CODE_PREFIX = "auth_code:"     # 인가 코드 저장 키
REDIS_REFRESH_TOKEN_PREFIX = "refresh_token:" # 리프레시 토큰 저장 키
REDIS_SESSION_UUID_MAP_PREFIX = "sess_uuid:" # OSPASS 세션 ID -> User UUID 매핑 키 (s_id -> uuid)
REDIS_UUID_SESSION_MAP_PREFIX = "uuid_sess:" # User UUID -> OSPASS 세션 ID 역매핑 키 (uuid -> s_id) - Optional tracking