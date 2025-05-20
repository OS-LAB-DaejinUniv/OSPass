"""
OSPASS Usage - Validation Data Type
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class InitLoginRequest(BaseModel):
    sliced_phone_num : str
    
# Card Data Validation
class Card_Data(BaseModel):
    card_data: str 

# Card Data + 시도 식별자(attempt_id)
class Card_Data_With_Attempt(Card_Data):
    attempt_id: str = Field(...,description="NFC 인증 시도 식별자")

class InitAuthResponse(BaseModel):
    attempt_id: str = Field(...,description="생성된 NFC 인증 시도 식별자")

class NfcStatusResponse(BaseModel):
    status: str = Field(...,description="인증 시도 상태(pending, success, failed, expired)")    
    s_id: Optional[str] = Field(None, description="성공 시 발급된 OSPASS 세션 ID")
    # 기타 상태 정보(부가 정보)
    error: Optional[str] = Field(None, description="오류 발생 시 에러 코드")
    error_description : Optional[str] = Field(None, description="오류 발생 시 상세 설명")
    
# client id Validation
class Client_ID(BaseModel):
    client_id : str

# Card - Redis Data Validation
class SessionKey(BaseModel):
    session : str
    
class Profile(BaseModel):
    user_name: str
    phone_num: str
    birth_date : date
    stud_num : str
    
    model_config = {
        "from_attributes" : True
    }