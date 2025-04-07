"""
Authenticate API Router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from auth.currentUser import current_user_info

auth_router = APIRouter(prefix="/api", tags=["Authenticate Service"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# MSA를 위한 사용자 인증 API
@auth_router.get("/v1/protected-service")
def protected_service(user_info:dict=Depends(current_user_info)):
    """
    인증된 사용자만 접근할 수 있는 서비스(인증 Endpoint)
    Micro Service에서 호출할 API
    """
    if user_info["status"] != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized")
    
    # 인증된 사용자에게 제공
    return {"message" : "인증된 상태입니다.",
            "user" : user_info}
