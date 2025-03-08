"""
OSPASS Usage - Validation Data Type
"""
from pydantic import BaseModel

class InitLoginRequest(BaseModel):
    sliced_phone_num : str