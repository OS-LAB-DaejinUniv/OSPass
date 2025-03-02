from fastapi import HTTPException, status
from jose import jwt, JWTError
from dotenv import load_dotenv
import datetime
import os 
from custom_log import LoggerSetup
load_dotenv() 

logger_setup = LoggerSetup()
logger = logger_setup.logger

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
    
    def verify_token(self, token:str, is_refresh : bool = False):
        try:
            secret_key = self.REFRESH_SECRET_KEY if is_refresh else self.ACCESS_SECRET_KEY
            payload = jwt.decode(token, secret_key, algorithms=[self.ALGORITHM])
            return payload
        except JWTError as je:
            logger.error(f"JWT ERROR: {str(je)}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid Token")