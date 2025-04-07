"""
Current User Information 
토큰 기반 현재 로그인한 사용자 인증 
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from common.database.database import redis_config
from common.token.token_handler import Token_Handler
from custom_log import LoggerSetup

rd = redis_config()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

logger_setup = LoggerSetup()
logger = logger_setup.logger

# Current User Info 
# user_id, user_name 조회
def current_user_info(token: str=Depends(oauth2_scheme)):
    '''
    로그인한 현재 사용자 정보(id,name 조회 가능)
    '''
    token_handler = Token_Handler()
    try:
        # Redis 블랙리스트에서 Access Token 조회
        # Logout 처리된 Access Token 거부
        if rd.get(f"blacklist:{token}"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token has been revoked(Logged Out)")
        
        # Token Decoding
        payload = jwt.decode(token, token_handler.WEB_ACCESS_SECRET_KEY, 
                             algorithms=[token_handler.ALGORITHM])
        _uid = payload.get("sub")
        user_name = payload.get("name")
        print(f'Decoding Payload: {payload}')
        if not _uid or not user_name:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token payload")
        return {
            "status" : status.HTTP_200_OK,
            "uid" : _uid,
            "user_name" : user_name
        }
    except JWTError as e:
        logger.error(f'JWT ERROR: {str(e)}')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Token")