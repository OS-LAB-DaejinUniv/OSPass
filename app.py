from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from typing import Annotated
import uvicorn
import logging
import secrets

from auth import verify_router
from ostools.log_manage import api_key_manage
from ostools.qrcode import ostools_api
from _user.register import register_router
from _user.login import login_router

app = FastAPI()

security = HTTPBasic()

logging.basicConfig(level=logging.INFO & logging.DEBUG & logging.ERROR)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)



# 로그 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    client_ip = request.headers.get("x-forwarded-for")
    
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.headers.get("x-real-ip") or request.client.host
    
    logger.info(f"Middleware hit: Client IP is {client_ip}")
    
    response = await call_next(request)
    return response

from custom_log import LoggerSetup
logger_setup = LoggerSetup()
logger = logger_setup.logger

# 기본 경로
@app.get("/")
async def main():
    return {"message": "Hello Guys from OS-LAB"}

# 로그 확인용 엔드포인트
@app.get("/log")
async def proxy_log(request: Request):
    ip = request.headers.get("x-forwarded-for")
    logger.info(f"IP: {ip}")
    
    return ip

# 라우터 포함
app.include_router(verify_router)
app.include_router(api_key_manage)
app.include_router(ostools_api)
app.include_router(register_router)
app.include_router(login_router)

# 서버 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
