from jose import jwt, JWTError
from dotenv import load_dotenv
import datetime
import os 

load_dotenv() 

class Token_Handler:
    def __init__(self):
        self.ACCESS_SECRET_KEY = os.getenv("APP_ACCESS_SECRET_KEY")
        self.ALGORITHM = os.getenv("APP_ALGORITHM")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("APP_ACCESS_TOKEN_EXPIRE_MINUTES"))
        self.REFRESH_SECRET_KEY = os.getenv("APP_REFRESH_SECRET_KEY")
        self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("APP_REFRESH_TOKEN_EXPIRE_DAYS")) 
        
    def create_access_token(self, data:dict, expire_delta : datetime.timedelta = None):
        
        to_encode = data.copy()
        
        if expire_delta:
            expire = datetime.datetime.now() + expire_delta
        else:
            expire = datetime.datetime.now() + datetime.timedelta(minutes= self.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp" : expire})
        return jwt.encode(to_encode, self.ACCESS_SECRET_KEY, algorithm = self.ALGORITHM)
    
    def create_refresh_token(self, data:dict):
        
        to_encode = data.copy()
        expire = datetime.datetime.now() + datetime.timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp" : expire})
        return jwt.encode(to_encode, self.REFRESH_SECRET_KEY, algorithm= self.ALGORITHM)
        