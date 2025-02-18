from jose import jwt, JWTError
from dotenv import load_dotenv
import datetime
import os

load_dotenv()

class Oauth_Token:
    def __init__(self):
        self.ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
        self.ALGORITHM = os.getenv("ALGORITHM")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
        self.REFRESH_TOKEN_EXPIRE_KEY = os.getenv("REFRESH_SECRET_KEY")
        self.REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"))
        
    def create_access_token(self, data:dict, expire_delta:datetime.datetime = None):
        to_encode = data.copy()
            
        if expire_delta:
            expire = datetime.datetime.now() + expire_delta
        else:
            expire = datetime.datetime.now() + datetime.timedelta(
                minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp" : expire})
        return jwt.encode(to_encode, self.ACCESS_SECRET_KEY, algorithm=self.ALGORITHM)
            
    def create_refresh_token(self, data:dict):
        
        to_encode = data.copy()
        expire = datetime.datetime.now() + datetime.timedelta(
            minutes=self.REFRESH_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update({"exp" : expire})
        return jwt.encode(to_encode, self.REFRESH_TOKEN_EXPIRE_KEY,
                          algorithm=self.ALGORITHM)
        