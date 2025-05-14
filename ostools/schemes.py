from fastapi import Form
from pydantic import BaseModel
class LoginForm:
    def __init__(self, user_id : str = Form(...), user_password : str = Form(...)):
        self.user_id = user_id
        self.user_password = user_password
        
class RefreshRequest(BaseModel):
    refresh_token:str
class LogoutRequest(BaseModel):
    refresh_token:str