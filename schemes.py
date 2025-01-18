# Pydantic 모델 
# 입력과 응답 데이터 정의

from pydantic import BaseModel
from typing import Optional

# Data Validation from PostgreSQL OsMember Table
class User(BaseModel):
    uuid : str
    name : str
    position : Optional[int] = None
    
    class Config:
        orm_mode = True

# Card Data Validation
class Card_Data(BaseModel):
    card_data : str 

# Card - Redis Data Validation
class SessionKey(BaseModel):
    session : str
    
# Token Scheme
class Token(BaseModel):
    access_token: str
    token_type: str

# JWT에 담고있을 사용자 정보 스키마
class TokenData(BaseModel):
    sub : str
    iat : str

