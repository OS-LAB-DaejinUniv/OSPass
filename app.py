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

def get_registered_domains(db: Session):
    '''
    DB에서 등록된 리다이렉트 URI의 도메인들을 가져와서 허용할 도메인 목록 생성
    '''
    allowed_domains = set()
    try:
        domains = db.query(API_Key).filter(API_Key.registered_service.isnot(None)).all()
        
        for domain in domains:
            registered_service = domain.registered_service
            
            for client_data in registered_service.values():
                redirect_uris = client_data.get("redirect_uri", [])
                
                for uri in redirect_uris:
                    parsed_uri = urlparse(uri)
                    domain = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                    allowed_domains.add(domain)
        
        logger.debug(f'Allowed domains: {allowed_domains}')
        return allowed_domains
    except Exception as e:
        logger.error(f"Error fetching domains: {str(e)}")
        return set()

# CORS 미들웨어 설정 - 빈 리스트로 초기화
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"], # OPTIONS 명시적 추가
    allow_headers=["*","Authorization"]
)

@app.middleware("http")
async def dynamic_cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    
    # OPTIONS 요청인 경우 즉시 응답
    if request.method == "OPTIONS":
        response = Response()
        if origin:
            db = next(get_db())
            allowed_domains = get_registered_domains(db)
            
            if origin in allowed_domains:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
                response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    response = await call_next(request)
    
    if origin:
        db = next(get_db())
        allowed_domains = get_registered_domains(db)
        
        if origin in allowed_domains:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    
    return response


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
app.include_router(ostools_router)
app.include_router(ospass_router)
app.include_router(devportal_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
