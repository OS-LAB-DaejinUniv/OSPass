from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TIMESTAMP
from conn_postgre import Base

class OsMember(Base):
    __tablename__ = "osmember"
    
    uuid = Column(String, primary_key = True, index=True)
    name = Column(String, index = True)
    position = Column(Integer,index=True)
    
    # OsMember와 APIKeyLog 테이블 간 관계 설정
    apikey_logs = relationship("APIKeyLog", back_populates="os_member")
    
class APIKeyLog(Base):
    __tablename__ = "apikeylog"
    
    id = Column(Integer,primary_key=True, index=True)
    key = Column(String, unique=True)
    uuid = Column(String, ForeignKey('osmember.uuid'))
    timestamp = Column(TIMESTAMP) # key 생성 시간
    source = "" # Api key 사용 출처
    
    os_member = relationship("OsMember", back_populates="apikey_logs")
