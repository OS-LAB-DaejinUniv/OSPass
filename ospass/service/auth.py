from fastapi import HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from challenge import gen_challenge
from schemes import User, Card_Data, SessionKey, Token
from models import OsMember, API_Key
from database import redis_config
from decrypt import decrypt_pp
from custom_log import LoggerSetup
from .token import Oauth_Token 
import const

logger_setup = LoggerSetup()
logger = logger_setup.logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

token = Oauth_Token()

# Redis Connect
rd = redis_config()

# Usage: Challenge 발급 
def get_or_issue_challenge(user_session : SessionKey):
    # exists : user_session이 존재하는지 확인
    # Redis에 저장된 value(challenge) 값이 있는지 확인
    if rd.exists(user_session): 
        stored_challenge = rd.get(user_session)
        decode_challenge = stored_challenge.decode()
        print(f"Stored Challenge: {decode_challenge}")
        return decode_challenge if decode_challenge else None
    
    # Redis에 저장된 value(challenge) 값이 없을 경우
    generated_challenge = gen_challenge()
    value_challenge = generated_challenge["value"]
    # key : user_session , value : value_challenge
    rd.set(user_session, value_challenge)
    print(f'[get_or_issue_challenge] Issued {user_session}->{value_challenge}')
    rd.expire(user_session, const.EXPIRE_KEY)
    return value_challenge

# Usage:  Card Response 검증 
# data: 카드에 담겨온 데이터
# user_session: 사용자 세션 ID
def process_verify_card_response(data:Card_Data, user_session:SessionKey, db: Session):
    # Data 복호화
    decrypted = decrypt_pp(data)
    decrypted_uuid = decrypted.get("card_uuid")
    decrypted_response = decrypted.get("response")
    print(f"Decrypted\nUUID: {decrypted_uuid}, Response: {decrypted_response}")
    
    # Redis에서 챌린지 return 값
    stored_challenge = get_or_issue_challenge(user_session).decode().upper()
    if not stored_challenge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Session not found or expired")
    print(f"Challenge in Redis : {stored_challenge}, Response : {decrypted_response}")
    
    # STEP 1 : Challenge 값 검증
    if stored_challenge != decrypted_response:
        print("Challenge match : Incorrect")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid Response")
    print("Challenge match: Correct")
    
    # STEP 2 : Decrypt된 UUID와 DB에 저장된 UUID 비교 검증
    member_uuid = db.query(OsMember).filter(OsMember.uuid == decrypted_uuid).first()
    if not member_uuid:
        logger.error(f"Member not found: {decrypted_uuid}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Member not found")
    return decrypted_uuid

# access_token 발급 
def issue_access_token(member_uuid: str, response : Response, expires_delta: timedelta | None = None):
    # Access Token 생성
    access_token_data = {
        "sub": member_uuid,  # Decode된 OS Member UUID
        "iat": datetime.now(ZoneInfo("Asia/Seoul")).timestamp()  # 토큰 발급 시간
    }
    # atd : access token data
    access_token = token.create_access_token(data={"atd" : access_token_data}, 
                                             expire_delta=expires_delta)
    print(f"Created Access Token: {access_token}")
    
    # 쿠키에 access_token 저장
    expire = datetime.now(ZoneInfo("Asia/Seoul")) + (expires_delta or timedelta(minutes=token.ACCESS_TOKEN_EXPIRE_MINUTES))
    response.set_cookie(key="access_token", value=access_token, expires=expire, httponly=True)
    
    # Refresh Token 생성
    refresh_token_data = {
        "sub": member_uuid,  # Decode된 OS Member UUID
        "iat": datetime.now(ZoneInfo("Asia/Seoul")).timestamp()
    }
    # refresh token 생성 및 저장
    # rtd : refresh token data
    refresh_token = token.create_refresh_token(data={"rtd" : refresh_token_data})
    print(f"Created Refresh Token: {refresh_token}")
    
    # key : refhresh_token:{member_uuid}, value : refresh_token, ttl : refresh token exprie time * 60 minutes
    rd.set(f"refresh_token:{member_uuid}", refresh_token, ex=token.REFRESH_TOKEN_EXPIRE_MINUTES * 60)  
    
    # Redis에서 Authorization Code 삭제 (재사용 방지)
    rd.delete(member_uuid)
    
    return Token(access_token=access_token, token_type="bearer")

    