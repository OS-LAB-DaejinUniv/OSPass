from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TIMESTAMP, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.sql import func # func.now() == 현재 시간
from datetime import timedelta
from conn_postgre import Base

# created
class OsMember(Base):
    __tablename__ = "osmember"
    
    uuid = Column(String, primary_key = True, index=True)
    name = Column(String, index = True)
    position = Column(Integer,index=True)

class Users(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    user_password = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    phone_num = Column(String, nullable=False, unique=True)
    birth_date = Column(Date, nullable=False)
    stud_num = Column(String, nullable=False, unique=True)
    signup_date = Column(TIMESTAMP, server_default=func.now())
    user_uuid = Column(String, nullable=True, unique=True)
    
    # Users와 API_Key 테이블 간 관계 설정
    apikey = relationship("API_Key", back_populates="user")
    
    # Users와 APP_Refresh_Tokens 테이블 간 관계 설정
    app_refresh_tokens = relationship("APP_Refresh_Tokens", back_populates="user")
    
class API_Key(Base):
    __tablename__ = "apikey"
    
    idx = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now()) # key 생성 시간 
    # SQLAlchmey에서 JSON 타입 컬럼은 Immutable 함 -> MutableDict로 변경
    registered_service = Column(MutableDict.as_mutable(JSONB), nullable=True)
    
    user = relationship("Users", back_populates="apikey")

class APP_Refresh_Tokens(Base):
    __tablename__ = "app_refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    token = Column(String, unique=True, nullable=False) # Refresh Token
    expires_at = Column(TIMESTAMP, nullable=False, server_default=func.now() + timedelta(days=30))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    
    user = relationship("Users", back_populates="app_refresh_tokens")