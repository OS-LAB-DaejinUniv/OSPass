from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session

from conn_postgre import get_db
from schemes import LoginForm
from .login import process_ostools_login, issued_refresh_token, process_ostools_logout

ostools_router = APIRouter(prefix="/api", tags=["ostools"])

# OSTools Login API
@ostools_router.post("/v1/ostools-login", description="OSTools Login API")
def ostools_login(response : Response, db:Session = Depends(get_db), login_form:LoginForm=Depends()):
    '''
    OSTools Login Endpoint(Normal Login: user_id, user_password)
    '''
    return process_ostools_login(response, db,login_form)

# OSTools Refresh Token API
@ostools_router.post("/v1/ostools-refresh", description="OSTools Refresh Token API")
def ostools_refresh(refresh_token:str, db:Session = Depends(get_db)):
    '''
    OSTools Refresh Token Endpoint
    '''
    return issued_refresh_token(refresh_token, db)

# OSTools Logout API
@ostools_router.post("/v1/ostools-logout", description="OSTools Logout API")
def ostools_logout(response : Response, refresh_token : str=Form(...), db:Session = Depends(get_db)):
    '''
    OSTools Logout Endpoint
    '''
    return process_ostools_logout(response, refresh_token, db)