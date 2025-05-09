from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from service.token import Oauth_Token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
tokenInfo = Oauth_Token()

def currentUserInfo(token:str=Depends(oauth2_scheme))->dict:
    """
    JWT 토큰 기반 로그인한 사용자 정보 가져오기
    params:
    - token: 로그인한 사용자가 받은 JWT 기반 토큰, 
                 API 요청 시 Authorization 헤더에 담아 전송 시 필요
    return:
    - Decoding된 Token의 Payload(type:dict) 
    """
    # 공통 예외 처리
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Token",
        headers={"WWW-Authenticate":"Bearer"}
    )
    try:
        payload = jwt.decode(token, tokenInfo.ACCESS_SECRET_KEY,
                             algorithms=[tokenInfo.ALGORITHM])
        if payload.get("sub") is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception