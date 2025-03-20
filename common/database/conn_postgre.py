import os
import logging
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from custom_log import LoggerSetup

load_dotenv()

logger_setup = LoggerSetup()
logger = logger_setup.logger

DATABASE_URL = os.getenv("POSTGRESQL_URL")
logging.info(f"DataBaseUrl: {DATABASE_URL}")
# SQLAlchemy engine 생성
try:
    engine = create_engine(DATABASE_URL)
    logger.info(f"POSTGRESQL CONNECTED SUCCESSFULLY")
except exc.SQLAlchemyError as e:
    logger.error(f"Error creating engine: {e}")

# SessionLocal 클래스 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

Base = declarative_base()

# Dependency Injection: 요청마다 데이터베이스 세션 생성
def get_db():
    db = SessionLocal()
    try:
        yield db # 요청 처리 중에는 세션 유지
        db.commit() # 요청이 성공적으로 끝나면 commit 실행
    except exc.SQLAlchemyError as e:
        db.rollback() # 예외 발생 시 롤백
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()
