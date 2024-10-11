# Pydantic 모델 
# 입력과 응답 데이터 정의

from pydantic import BaseModel
from typing import Optional

# Data Validation from PostgreSQL OsMember Table
class User(BaseModel):
    uuid : str
    name : str
    position : Optional[int] = None
    
    class Config:
        orm_mode = True
