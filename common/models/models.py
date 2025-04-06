from sqlalchemy import Column, Integer, String, ForeignKey, Sequence, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import TIMESTAMP, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.sql import func # func.now() == 현재 시간
from datetime import timedelta
from common.database.conn_postgre import Base

class Users(Base):
    __tablename__ = "users"
    uid = Column(String, primary_key=True, nullable=False, index=True)
    user_id = Column(String, unique=True, nullable=False)
    user_password = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    phone_num = Column(String, nullable=False, unique=True)
    birth_date = Column(Date, nullable=False)
    stud_num = Column(String, nullable=False, unique=True)
    signup_date = Column(TIMESTAMP, server_default=func.now())
    user_uuid = Column(String, nullable=True, unique=True)
    
    # Users와 API_Key 테이블 간 관계 설정
    apikey = relationship("API_Key", back_populates="user", foreign_keys="API_Key.uid")
    
    # Users와 APP_Refresh_Tokens 테이블 간 관계 설정
    app_refresh_tokens = relationship("APP_Refresh_Tokens", back_populates="user")
    
    calendars = relationship("Calendar", back_populates="user")
    notes = relationship("Notes", back_populates="user")
class API_Key(Base):
    __tablename__ = "apikey"
    
    idx = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    uid = Column(String, ForeignKey('users.uid'), nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now()) # key 생성 시간 
    # SQLAlchmey에서 JSON 타입 컬럼은 Immutable 함 -> MutableDict로 변경
    registered_service = Column(MutableDict.as_mutable(JSONB), nullable=True)
    
    user = relationship("Users", back_populates="apikey", foreign_keys=[uid])

class APP_Refresh_Tokens(Base):
    __tablename__ = "app_refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    token = Column(String, unique=True, nullable=False) # Refresh Token
    expires_at = Column(TIMESTAMP, nullable=False, server_default=func.now() + timedelta(days=30))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    
    user = relationship("Users", back_populates="app_refresh_tokens")
    
class Calendar(Base):
    __tablename__ = "calendar"
    
    idx = Column(Integer, autoincrement=True, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True), nullable=False)
    time_zone = Column(String(50), nullable=True, default='UTC')
    user_id = Column(String(255), ForeignKey('users.uid'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now()) # UTC Timezone processing
    updated_at = Column(TIMESTAMP(True), server_default=func.now(), onupdate=func.now()) 
    
    user = relationship("Users", back_populates="calendars")
    notes = relationship("Notes", back_populates="calendars")
    
class Notes(Base):
    __tablename__ = "notes"
    
    note_id = Column(Integer, primary_key=True, autoincrement=True)
    calendar_id = Column(Integer, ForeignKey('calendar.idx'), nullable=False)
    user_id = Column(String(255), ForeignKey('users.uid'), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 관계 설정
    calendars = relationship("Calendar", back_populates="notes")
    user = relationship("Users", back_populates="notes")