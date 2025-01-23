from sqlalchemy.orm import Session
from models import Users
from schemes import JoinUser
from fastapi import HTTPException, status, APIRouter, Depends
from passlib import CryptoContext
from conn_postgre import get_db
import logging

register_router = APIRouter(prefix="/api")

# bcrypt context 초기화
bcrypt_context = CryptoContext(schemes=["bcrypt"], deprecated="auto")

# 회원가입(Register USER)
def register_user(new_user : JoinUser, db : Session):
    try:
        # 사용자 ID가 존재하는지 확인
        existing_user= db.query(Users).filter(Users.user_id == new_user.user_id).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail="User ID already exists")
        
        # password hashing
        hashed_password = bcrypt_context.hash(new_user.user_password)
        # 새로운 사용자 생성
        newbie = Users(
            user_id = new_user.user_id,
            user_password = hashed_password,
            phone_num = new_user.phone_num,
            stud_num = new_user.stud_num,
            birth_date = new_user.birth_date
        )
        logging.info(f"New User: {newbie}")
        db.add(newbie)
        db.commit()
        db.refresh(newbie)
        
        return newbie
    except Exception as e:
        logging.error(f"Error while Creating User: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {e}")
    
def verify_password(plain_password : str, hashed_password : str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)

@register_router.post("/v1/register")
def register(new_user : JoinUser, db : Session = Depends(get_db)):
    return register_user(new_user, db)