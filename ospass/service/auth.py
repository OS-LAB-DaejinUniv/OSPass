from fastapi import HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random

from challenge import gen_challenge
from schemes import User, Card_Data, SessionKey, Token
from models import Users, API_Key
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

# Usage: 카드 인증용 Challenge 발급 
def get_or_issue_challenge(client_id : str):
    """
    - client_id 기반으로 Redis에 저장된 Challenge 값 가져오기 없다면 생성
    - :params
    - client_id : 서비스 고유 client_id
    """
    # exists : user_session이 존재하는지 확인
    # Redis에 저장된 value(challenge) 값이 있는지 확인
    if rd.exists(client_id): 
        stored_challenge = rd.get(client_id)
        decode_challenge = stored_challenge.decode()
        print(f"Stored Challenge: {decode_challenge}")
        return decode_challenge if decode_challenge else None
    
    # Redis에 저장된 value(challenge) 값이 없을 경우
    ch = random.getrandbits(128)
    challenge = hex(ch)[2:].zfill(32)
    # key : user_session , value : value_challenge
    rd.setex(client_id, const.EXPIRE_KEY, challenge)
    print(f'[get_or_issue_challenge] Issued {client_id}->{challenge}')
    return challenge

# Usage:  Card Response 검증 
# data: 카드에 담겨온 데이터
# user_session: 사용자 세션 ID
def process_verify_card_response(data:Card_Data, client_id:str, db: Session):
    # Data 복호화
    decrypted = decrypt_pp(data)
    decrypted_uuid = decrypted.get("card_uuid")
    decrypted_response = decrypted.get("response")
    print(f"Decrypted\nUUID: {decrypted_uuid}, Response: {decrypted_response}")
    
    # Redis에서 챌린지 return 값
    stored_challenge = get_or_issue_challenge(client_id).decode().upper()
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
    member_uuid = db.query(Users).filter(Users.user_uuid == decrypted_uuid).first()
    if not member_uuid:
        logger.error(f"Member not found: {decrypted_uuid}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Member not found")
    return decrypted_uuid

    