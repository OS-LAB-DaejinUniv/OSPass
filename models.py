from sqlalchemy import Column, Integer, String
from conn_postgre import Base

class OsMember(Base):
    __tablename__ = "osmember"
    
    uuid = Column(String, primary_key = True, index=True)
    name = Column(String, index = True)
    position = Column(Integer,index=True)
    
