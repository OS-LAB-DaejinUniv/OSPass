from fastapi import FastAPI, Request, Response
import uvicorn

from ostools_api import ostools_router
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger

app = FastAPI()

@app.middleware("http")
async def request_log(request: Request, call_next):
    '''
    요청 로그 처리하는 미들웨어
    실제 IP 조회
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
def main():
    return {"message" : "This is OSTOOLS from OS-LAB"}

app.include_router(ostools_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)