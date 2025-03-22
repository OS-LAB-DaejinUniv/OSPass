from fastapi import FastAPI, Request
from fastapi.security import HTTPBasic
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from devportal_api import devportal_router

app = FastAPI()
security = HTTPBasic()

# Devportal Cors 설정
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
    # 실제 IP 가져오기
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.headers.get("x-real-ip") or request.client.host
    
    logging.info(f"Request from IP: {client_ip}")
    response = await call_next(request)
    return response

@app.get("/")
async def main():
    return {"message": "Devportal from OS-LAB"}

app.include_router(devportal_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)