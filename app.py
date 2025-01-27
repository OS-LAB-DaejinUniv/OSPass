from fastapi import FastAPI, Request
from fastapi.security import HTTPBasic
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import logging
from ostools.log_manage import api_key_manage
from ostools.qrcode import ostools_api
from devportal.devportal_api import devportal_router
from ospass.ospass_api import ospass_router

app = FastAPI()

security = HTTPBasic()

logging.basicConfig(level=logging.INFO)

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
app.include_router(api_key_manage)
app.include_router(ospass_router)
app.include_router(ostools_api)
app.include_router(devportal_router)


# 서버 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
