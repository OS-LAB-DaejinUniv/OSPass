from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import uvicorn

from common.database.conn_postgre import get_db
from common.models.models import API_Key
from ospass_api import ospass_router
from custom_log import LoggerSetup

app = FastAPI()

logger_setup = LoggerSetup()
logger = logger_setup.logger

def get_registered_domain(db:Session):
    """
    Devportal에 등록된 서비스의 Redirect URIS 조회
    Dynamic Cors -> 등록된 Redirect URI 허용 전 Setting
    """
    # 허용된 도메인
    allowed_domains = set()
    try:
        domains = db.query(API_Key).filter(API_Key.registered_service.isnot(None)).all()
        print(f"domains 객체 타입:{type(domains)}")
        for domain in domains:
            registered_service = domain.registered_service
            
            for client_data in registered_service.values():
                redirect_uris = client_data.get("redirect_uri", [])

                for uri in redirect_uris:
                    parsed_uri = urlparse(uri)
                    domain = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                    allowed_domains.add(domain)
        
        logger.debug(f"Allowed Domains:{allowed_domains}")
        return allowed_domains
    
    except Exception as e:
        logger.error(f"Error Occured while fetching registerd domains:{str(e)}")
        return set()
    
    except HTTPException as he:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                      detail=f"Not Found Registered Redirect URI:{he.detail}")
        
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=True,
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*","Authorization"]
)

@app.middleware("http")
async def dynamic_cors_middleware(request:Request, call_next):
    """
    Dynamic Cors(동적 CORS 설정)
    """
    origin = request.headers.get("origin")
    
    # OPTIONS 요청인 경우 즉시 응답
    if request.method == "OPTIONS":
        response = Response()
        if origin:
            db = next(get_db())
            allowd_domains = get_registered_domain(db)
            
            if origin in allowd_domains:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
                response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
    
    response = await call_next(request)
    
    if origin:
        db = next(get_db())
        allowed_domains = get_registered_domain(db)
            
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
    # Proxy Server IP
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        # Real IP
        client_ip = request.headers.get("x-real-ip") or request.client.host
    
    logger.info(f"Request from IP: {client_ip}")
    response = await call_next(request)
    return response

@app.get("/")
def main():
    return {"message":"This is OSPASS"}

app.include_router(ospass_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)