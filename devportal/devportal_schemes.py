from fastapi import Form
from pydantic import BaseModel, HttpUrl, field_validator
from typing import List, Optional, Union
from datetime import date, datetime
from zoneinfo import ZoneInfo
import re

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

# Login Form
class LoginForm:
    def __init__(self, user_id : str = Form(...), user_password : str = Form(...)):
        self.user_id = user_id
        self.user_password = user_password

# Service Request 
class RegisterServiceRequset(BaseModel):
    service_name : str

# Redirect URI HTTP Schema
class RegisterRedirectUri(BaseModel):
    client_id : str
    redirect_uri : List[HttpUrl] # HTTP, HTTPS Network Type Validation

# 단일 서비스 응답 모델
class SingleServiceReponse(BaseModel):
    idx : int
    client_id : str
    service_name : str
    redirect_uris : List[HttpUrl]

# 전체 서비스 응답 모델(client_id 미제공 시)
class AllServiceResponse(BaseModel):
    idx: int
    services: dict[str,dict] # key: client id, value: service information

RedirectUriResponse = Union[SingleServiceReponse, AllServiceResponse]

# 비밀번호 Reset API Request user_id    
class ResetPasswordRequestID():
    def __init__(self, user_id:str=Form(...)):
        self.user_id = user_id
        
class UpdateUser(BaseModel):
    user_password : Optional[str] = None
    user_name : Optional[str] = None
    phone_num : Optional[str] = None
    stud_num : Optional[str] = None
    
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
    
class ScheduleCreate(BaseModel):
    title : str
    content : str
    start_time : datetime
    end_time : datetime
    time_zone : str = "UTC"
    
    def convert_to_utc(self):
        tz = ZoneInfo(self.time_zone)
        self.start_time = self.start_time.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
        self.end_time = self.end_time.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))

class ScheduleResponse(BaseModel):
    idx: int
    title: str
    content: str
    start_time: datetime
    end_time: datetime
    time_zone: str
    creator: str
    
class ShareSchedule(BaseModel):
    idx: int
    title: str
    start_time: datetime
    end_time: datetime
    creator: str
    
    class Confing:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }