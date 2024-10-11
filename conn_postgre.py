import os
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("POSTGRESQL_URL")

# SQLAlchemy engine 생성
try:
    engine = create_engine(DATABASE_URL)
except exc.SQLAlchemyError as e:
    print(f"Error creating engine: {e}")
    # 적절한 오류 처리를 위한 추가 로직을 여기에 추가할 수 있습니다.

# SessionLocal 클래스 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency Injection: 요청마다 데이터베이스 세션 생성
def get_db():
    db = SessionLocal()
    try:
        yield db
    except exc.SQLAlchemyError as e:
        print(f"Database session error: {e}")
        # 추가적인 오류 처리를 위한 로직을 여기에 추가할 수 있습니다.
    finally:
        db.close()
