"""
Join OSPASS Service API Router
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from common.database.conn_postgre import get_db
from devportal_schemes import RegisterServiceRequset, RegisterRedirectUri, RedirectUriResponse
from register_service.service_name import process_register_service
from register_service.redirect_uri import process_register_redirect_uri, get_service_redirect_uri
from register_service.remove_service import process_remove_service
from register_service._show_service import show_service
from auth.currentUser import current_user_info

from custom_log import LoggerSetup

ospassSerivce_router = APIRouter(prefix="/api", tags=["OSPASS Service"])

logger_setup = LoggerSetup()
logger = logger_setup.logger

# Devportal에서 User의 Service 등록 API    
@ospassSerivce_router.post("/v1/register-service")
def register_service(request : RegisterServiceRequset, db:Session=Depends(get_db), current_user=Depends(current_user_info)):
    '''
    - Service Name 등록 Endpoint
    '''
    result = process_register_service(request.service_name,db,current_user)
    return result

@ospassSerivce_router.get("/v1/services/")
def services(db:Session=Depends(get_db),current_user=Depends(current_user_info)):
    '''
    - 등록된 Service Infomation List Up Endpoint
    '''
    user_name = current_user["user_name"]
    
    return show_service(db, current_user)

# Devportal에서 User의 Service Redirect Uri 등록 API
@ospassSerivce_router.post("/v1/redirect-uris")
def register_redirect_uris(data : RegisterRedirectUri,
                           current_user:dict=Depends(current_user_info), 
                           db:Session=Depends(get_db)):
    '''
    - Redirect Uri 등록 Endpoint
    - List Type[] , 여러 개 등록 가능
    - data : client_id, redirect_uri
    '''
    result = process_register_redirect_uri(data,db,current_user)
    return result

# Devportal에서 User가 등록한 개별 Serivce에 대한 Redirect Uri Showing API
@ospassSerivce_router.get("/v1/redirect_uris", response_model=RedirectUriResponse)
def get_redirect_uris(idx: int=Query(...,description="API_KEY Idx"),
                        client_id:Optional[str]=Query(None, description="Filter by client ID"), # 선택적
                        db:Session=Depends(get_db),
                        current_user:dict=Depends(current_user_info)):
    
    return get_service_redirect_uri(idx, client_id, db, current_user)
    
# Devportal에서 User가 등록한 개별 Service에 대한 Service 삭제 API
@ospassSerivce_router.delete("/v1/service/{client_id}")
async def remove_service(client_id:str,
                         db:Session=Depends(get_db),
                         current_user:str=Depends(current_user_info)):
    '''
    - 서비스 삭제 Endpoint
    Args:
    - client_id : 삭제할 서비스의 client_id(고유번호)
    '''
    return process_remove_service(client_id, db, current_user)