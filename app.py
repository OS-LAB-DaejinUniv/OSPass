from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from typing import Annotated
import uvicorn
import logging
import secrets

from challenge import challenge_router
from auth import verify_router
from ostools.log_manage import api_key_manage


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
    
    print(f"Middleware hit: Client IP is {client_ip}")  # Print for direct stdout confirmation
    logging.info(f"Client IP: {client_ip}")
    
    response = await call_next(request)
    return response

# 기본 경로
@app.get("/")
async def main():
    return {"message": "Hello Guys from OS-LAB"}

# 로그 확인용 엔드포인트
@app.get("/log")
async def proxy_log(request: Request):
    ip = request.headers.get("x-forwarded-for")
    logging.info(f"IP: {ip}")
    
    return ip

# 라우터 포함
app.include_router(challenge_router)
app.include_router(verify_router)
app.include_router(api_key_manage)

# 서버 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
