from fastapi import FastAPI, Request, Response
from fastapi.security import HTTPBasic
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import iterate_in_threadpool
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import uvicorn
from ostools.ostools_api import ostools_router
from devportal.devportal_api import devportal_router
from ospass.ospass_api import ospass_router
from custom_log import LoggerSetup

from models import API_Key
from conn_postgre import get_db

app = FastAPI()
security = HTTPBasic()

logger_setup = LoggerSetup()
logger = logger_setup.logger

# CORS 미들웨어 설정 - 빈 리스트로 초기화
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://devportal.oslab", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*","Authorization"]
)

@app.middleware("http")
async def request_log(request: Request, call_next):
    '''
    요청 로깅을 처리하는 미들웨어
    '''
    client_ip = request.headers.get("x-forwarded-for") # 실제 IP 받아오기
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.headers.get("x-real-ip") or request.client.host
    
    logger.info(f"Request from IP: {client_ip}")
    response = await call_next(request)
    return response

@app.get("/")
async def main():
    return {"message": "Hello Guys from OS-LAB"}

@app.get("/log")
async def proxy_log(request: Request):
    ip = request.headers.get("x-forwarded-for")
    logger.info(f"IP: {ip}")
    return ip

# 라우터 등록
app.include_router(devportal_router)
app.include_router(ostools_router)
app.include_router(ospass_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
