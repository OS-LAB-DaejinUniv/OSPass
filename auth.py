from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from schemes import User
from models import OsMember
from conn_postgre import get_db
import database

# TODO
# 1. Postgre에서 가져온 UUID(Login용 Session ID)와 JavaCard에서 주는 UUID와 비교 및 검증
# 2. 검증이 끝나면 JWT를 발급 함
# 3. 


load_dotenv()

# Redis  
rd = database.redis_config()

verify_router = APIRouter(prefix="/api")

# Serial 통신으로 받아올 암호화가 풀린 response값
fake = '8c64923078d57c8664aee61c2f1dcedc' # fake response

# Token Scheme
class Token(BaseModel):
    access_token: str
    token_type: str

# JWT에 담고있을 사용자 정보 스키마
class TokenData(BaseModel):
    uuid : str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Challenge와 Response 비교 후 검증
@verify_router.post("/v1/card_response")
def verify_card_response(response : str):
    
    stored_challege = rd.get(response)
    if not stored_challege:
        raise HTTPException(status_code=404, detail="Key not found or Time Expired")
    
    
    if  stored_challege == fake:
        return {"message": "Valid response"}
    else:
        raise HTTPException(status_code=400, detail="Invalid response")

@verify_router.get("/v1/user")
def get_user(db: Session = Depends(get_db)):
    try:
        members = db.query(OsMember).all()
        if not members:
            raise HTTPException(status_code=404, detail="No members found")
        
        return [User(uuid=member.uuid, name=member.name, position=member.position) for member in members]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))