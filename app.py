from fastapi import FastAPI, Request
from fastapi.security import HTTPBasic
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import iterate_in_threadpool

import uvicorn
import logging
from ostools.log_manage import api_key_manage
from ostools.qrcode import ostools_api
from devportal.devportal_api import devportal_router
from ospass.ospass_api import ospass_router
from custom_log import LoggerSetup

app = FastAPI()

security = HTTPBasic()

logging.basicConfig(level=logging.INFO)

logger_setup = LoggerSetup()
logger = logger_setup.logger

origins = [
    "*",
    "http://devportal.oslab",
]

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Request Log Middleware
@app.middleware("http")
async def request_log(request: Request, call_next):
    client_ip = request.headers.get("x-forwarded-for")
    
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.headers.get("x-real-ip") or request.client.host
    
    logger.info(f"Middleware hit: Client IP is {client_ip}")
    
    response = await call_next(request)
    return response

# Response Log Middleware
@app.middleware("http")
async def response_log(request: Request, call_next):
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    
    response_body = [chunk async for chunk in response.body_iterator]
    response.body_iterator = iterate_in_threadpool(iter(response_body))
    
    logger.info(f"Reponse Body: {response_body[0].decode()}")
    
    return response

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
