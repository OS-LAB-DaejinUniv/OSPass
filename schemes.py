# Pydantic 모델 
# 입력과 응답 데이터 정의
from fastapi import HTTPException, Form
from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from typing import Optional
from datetime import date
import re

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
    birth_date : date
    user_uuid : Optional[str] = None
    
    @field_validator("user_id")
    def validate_user_id(cls, value):
        """
        user_id는 8~16자리이며, 영문과 숫자 조합만 허용 (기호는 불가)
        """
        pattern = re.compile(r"^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{8,16}$")
        if not pattern.match(value):
            raise ValueError("user_id : length 8~16, using english and number, no symbol")
        return value

    @field_validator("user_password")
    def validate_user_password(cls, value):
        """
        user_password는 8~16자리이며, 영문, 숫자, 기호 조합이어야 함
        """
        pattern = re.compile(r"^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>])[a-zA-Z\d!@#$%^&*(),.?\":{}|<>]{8,16}$")
        if not pattern.match(value):
            raise ValueError("user_password : length 8~16, using english and number, must use symbol at least one")
        return value
    
    
    @field_validator("user_name")
    def validate_user_name(cls, value):
        """
        user_name은 한글 이름으로 자음만 포함되지 않도록 검증
        """
        pattern = re.compile(r"^[가-힣]{2,}$")  # 최소 2글자 이상의 한글 이름만 허용
        if not pattern.match(value):
            raise ValueError("user_name : must be a valid Korean name (at least 2 characters)")
        
        # 한글 이름에서 자음만 들어가는 경우를 막기 위한 체크 (모음이 있는지 확인)
        for char in value:
            if ord(char) in range(0x3131, 0x314F):  # 자음 범위
                raise ValueError("user_name : cannot contain only consonants (must have vowels)")
        
        return value
        
    class Config:
        orm_mode = True

class LoginForm:
    def __init__(self, user_id : str = Form(...), user_password : str = Form(...)):
        self.user_id = user_id
        self.user_password = user_password

# OSPASS Login Data Validation
class Init_Login(BaseModel):
    sliced_phone_num : str
    user_id : str

# Card Data Validation
class Card_Data(BaseModel):
    card_data : str 

# Card - Redis Data Validation
class SessionKey(BaseModel):
    session : str
    
# Token Scheme
class Token(BaseModel):
    access_token: dict
    token_type: str

# JWT에 담고있을 사용자 정보 스키마
class TokenData(BaseModel):
    sub : str
    iat : str

