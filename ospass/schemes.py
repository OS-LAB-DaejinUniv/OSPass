"""
OSPASS Usage - Validation Data Type
"""
from pydantic import BaseModel

class InitLoginRequest(BaseModel):
    client_id : str
    sliced_phone_num : str