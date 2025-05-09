from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from common.models.models import Users
from schemes import Profile
from common.database.database import redis_config

rd = redis_config()

def getProfileInfo(db:Session,token_paylaod:dict) -> Profile:
    '''
    OSPASS로 로그인한 사용자 프로필 가져오기
    이름, 학번, 전화번호, 생일
    '''
    try:
        # Access Token Palyoad에서 s_id(session id) 추출
        s_id = token_paylaod.get("sub")
        if not s_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                detail="Invalid token payload")
        # s_id를 키 값으로 가지고 있는 사용자 UUID 추출
        user_uuid = rd.get("s_id")
        if not user_uuid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Session Expired or Invalidated")
        # Querying Result
        result = db.query(Users).filter(Users.user_uuid==user_uuid).first()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User profile data not found")
        profile_data = Profile.model_validate(result)
        return profile_data
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error while Retrieving Profile")