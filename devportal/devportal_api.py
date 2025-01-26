from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from conn_postgre import get_db
from key_gen import gen_api_key

devportal_router = APIRouter(prefix="/api")

token = OAuth2PasswordBearer(tokenUrl="token")

@devportal_router.post("/v1/apikey")
def get_apikey(token: str=Depends(token), db: Session=Depends(get_db)):
    '''
    - API KEY 발급 Endpoint
    '''
    gen_api_key(token,db)
    return {"status" : status.HTTP_201_CREATED,
            "message": "API KEY CREATED SUCCESSFULLY"}