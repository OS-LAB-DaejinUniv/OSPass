from pydantic import BaseModel, HttpUrl
from typing import List

class RegisterServiceRequset(BaseModel):
    service_name : str
    
class RegisterRedirectUri(BaseModel):
    client_id : str
    redirect_uri : List[HttpUrl] # HTTP, HTTPS Network Type Validation
    
# 비밀번호 Reset API Request user_id    
class ResetPasswordRequestID(BaseModel):
    user_id : str