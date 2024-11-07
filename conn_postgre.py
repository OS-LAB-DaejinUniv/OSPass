import os
import logging
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("POSTGRESQL_URL")
logging.info(f"DataBaseUrl: {DATABASE_URL}")
# SQLAlchemy engine 생성
try:
    engine = create_engine(DATABASE_URL)
    logging.info(f"POSTGRESQL CONNECTED SUCCESSFULLY")
except exc.SQLAlchemyError as e:
    logging.error(f"Error creating engine: {e}")

# SessionLocal 클래스 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency Injection: 요청마다 데이터베이스 세션 생성
def get_db():
    db = SessionLocal()
    try:
        yield db
    except exc.SQLAlchemyError as e:
        logging.error(f"Database session error: {e}")
        
    finally:
        db.close()
