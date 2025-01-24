# Pydantic 모델 
# 입력과 응답 데이터 정의
from fastapi import HTTPException, Form
from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from typing import Optional

# Data Validation from PostgreSQL OsMember Table
class User(BaseModel):
    uuid : str
    name : str
    position : Optional[int] = None
    
    class Config:
        orm_mode = True

# Join User Data Validation
class JoinUser(BaseModel):
    user_id : str
    user_password : str
    user_name : str
    phone_num : str
    stud_num : str
    birth_date : str
    user_uuid : Optional[str] = None
    
    class Config:
        orm_mode = True

class LoginForm:
    def __init__(self, user_id : str = Form(...), user_password : str = Form(...)):
        self.user_id = user_id
        self.user_password = user_password
        

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

