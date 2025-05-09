"""
OSPASS Usage - Validation Data Type
"""
from pydantic import BaseModel
from typing import Optional
from datetime import date

class InitLoginRequest(BaseModel):
    sliced_phone_num : str
    
# Card Data Validation
class Card_Data(BaseModel):
    card_data : str 

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