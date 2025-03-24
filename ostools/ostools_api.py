from fastapi import APIRouter, Depends, Form, Response, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from common.database.conn_postgre import get_db
from schemes import LoginForm
from login import process_ostools_login, issued_refresh_token, process_ostools_logout, current_user_info
from register_uuid import process_register_uuid

ostools_router = APIRouter(prefix="/api", tags=["ostools"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# OSTools Login API
@ostools_router.post("/v1/ostools-login", description="OSTools Login API")
def ostools_login(response : Response, db:Session = Depends(get_db), login_form:LoginForm=Depends()):
    '''
    OSTools Login Endpoint(Normal Login: user_id, user_password)
    '''
    return process_ostools_login(response, db,login_form)

# OSTools Refresh Token API
@ostools_router.post("/v1/ostools-refresh", description="OSTools Refresh Token API")
def ostools_refresh(request:Request, 
                    db:Session = Depends(get_db)):
    '''
    OSTools Refresh Token Endpoint
    '''
    return issued_refresh_token(request, db)

# OSTools Logout API
@ostools_router.post("/v1/ostools-logout", description="OSTools Logout API")
def ostools_logout(request : Request,
                   response : Response, 
                   db:Session = Depends(get_db)):
    '''
    OSTools Logout Endpoint
    '''
    return process_ostools_logout(request, response, db)

# OSTools Register UUID API
@ostools_router.post("/v1/uuid", description="OSTools Register User's Card UUID")
def ostools_register_uuid(user_uuid:str=Form(...), 
                          current_user:str=Depends(current_user_info),
                          db:Session=Depends(get_db)):
    '''
    OSTools Register User's UUID Endpoint
    '''
    return process_register_uuid(user_uuid, current_user, db)