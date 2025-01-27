from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt
from conn_postgre import get_db
from ostools.token_handler import Token_Handler
from models import Users, API_Key
from custom_log import LoggerSetup
import random

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
token_handler = Token_Handler()
logger_setup = LoggerSetup()
logger = logger_setup.logger

# OSPASS API KEY Gen
# Token 확보 판단 후 발급
def gen_api_key(db : Session, token : str = Depends(oauth2_scheme)):
    '''
    - Devportal을 통해서 API KEY를 발급받을 것
    - API KEY 발급 ==> Login한 유저(인증된 유저)만 발급 가능
    '''
    try:
        payload = jwt.decode(token, token_handler.ACCESS_SECRET_KEY,
                             algorithms=[token_handler.ALGORITHM])
        user_id = payload.get("sub")
        # user_id(var: user_id) in JWT == user_id(var: auth_user_id) in DB
        auth_user_id = db.query(Users).filter(Users.user_id == user_id).first()
        
        if not auth_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="user_id not matched")
        new_api_key = API_Key(apikey=hex(random.getrandbits(128))[2:], user_id=user_id)
        db.add(new_api_key)
        db.commit()
        logger.info({"status": status.HTTP_201_CREATED, 
                     "detail": f'Created Success API KEY {new_api_key.apikey}'})
    except Exception as e:
        logger.error({"status":status.HTTP_500_INTERNAL_SERVER_ERROR,
                      "detail": {e}})

