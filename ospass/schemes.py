"""
OSPASS Usage - Validation Data Type
"""
from pydantic import BaseModel

class InitLoginRequest(BaseModel):
    sliced_phone_num : str
    
# Card Data Validation
class Card_Data(BaseModel):
    card_data : str 

# Card - Redis Data Validation
class SessionKey(BaseModel):
    session : str