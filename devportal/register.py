from sqlalchemy.orm import Session
from models import Users
from schemes import JoinUser
from fastapi import HTTPException, status, APIRouter, Depends
from passlib.context import CryptContext
from conn_postgre import get_db
from custom_log import LoggerSetup

register_router = APIRouter(prefix="/api")

# bcrypt context 초기화
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger_setup = LoggerSetup()
logger = logger_setup.logger

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
            user_name = new_user.user_name,
            phone_num = new_user.phone_num,
            stud_num = new_user.stud_num,
            birth_date = new_user.birth_date
        )
        logger.info(f"New User: {newbie.user_id, newbie.user_name}")
        db.add(newbie)
        db.commit()
        db.refresh(newbie)
        
        return newbie
    except Exception as e:
        logger.error(f"Error while Creating User: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {e}")
    
def verify_password(plain_password : str, hashed_password : str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)

@register_router.post("/v1/register",  response_model=JoinUser)
def register(new_user : JoinUser, db : Session = Depends(get_db)):
    return register_user(new_user, db)