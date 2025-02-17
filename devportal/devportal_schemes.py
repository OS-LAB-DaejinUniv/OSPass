from pydantic import BaseModel, HttpUrl
from typing import List

class RegisterServiceRequset(BaseModel):
    service_name : str
    
class RegisterRedirectUri(BaseModel):
    client_id : str
    redirect_uri : List[HttpUrl] # HTTP, HTTPS Network Type Validation