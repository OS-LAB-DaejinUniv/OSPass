from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from models import Users
from .login import current_user_info
from ..devportal_schemes import UpdateUser, UpdateUserResponse
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def process_modify_user(_updateUser: UpdateUser, db:Session, current_user_uid:str):
    """
    회원정보 수정
    원하는 데이터만 수정 가능
    :수정 가능 데이터: user_password, user_name, phone_num, stud_num
    """
    try:
        # 로그인 된 사용자만 접근 가능
        if not current_user_uid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid User")
            
        user = db.query(Users).filter(Users.uid == current_user_uid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User Not Found")
            
        # 요청 데이터 중 None이 아닌 값만 업데이트(빈 문자열 유지)
        # update_data = {k: v for k,v in _updateUser.model_dump().items() if v is not None}
        update_data = _updateUser.model_dump(exclude_unset=True)
        if "user_password" in update_data:
            update_data["user_password"] = bcrypt_context.hash(update_data["user_password"])
        
        for key, value in update_data.items():
            setattr(user, key, value)
            
        db.commit()
        db.refresh(user)
        logger.debug(f"Update Successfully User Info:{update_data}")
        
        return UpdateUserResponse(
            message="Update Successfully User Info",
            update_data=update_data
        )
        
    except HTTPException as he:
        db.rollback()
        raise he 
    except Exception as e:
        db.rollback()
        logger.error(f"Error Occured: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal server error while Modifying User Information")
    