# API-KEY 사용 관리 및 내역 확인
from fastapi import Request
from app import app

class Api_Key_Log:
    
    @app.middleware("http")
    async def log_request(request : Request, call_next):
        
        # API KEY 가져오기
        api_key = request.headers.get("X-API-KEY", "unknown_key")