import os 
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import exc
from dotenv import load_dotenv
from custom_log import LoggerSetup

load_dotenv()

logger_setup = LoggerSetup()
logger = logger_setup.logger

# Async 엔진 생성을 위한 환경 변수 : postgresql -> postgresql+asyncpg
DATABASE_URL = os.getenv("POSTGRESQL_URL").replace(
    "postgresql://", "postgresql+asyncpg://", 1
)

# SQLAlchemy 비동기 엔진 생성
try:
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=True, # SQL Query Log
        pool_size=20, # Connection Pool Size
        max_overflow=10, # Max Overflow Connection Count
        pool_timeout=30, # Pool Timeout(초)
        pool_recycle=3600 # Connection Recycle(초)
    )
    logger.info("Async PostgreSQL engine created successfully")
except exc.SQLAlchemyError as e:
    logger.error(f"Error Creating Async Engine:{str(e)}")
    raise

# 비동기 세션 팩토리 생성
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 커밋 후 객체 만료 방지
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# 비동기 의존성 주입
async def get_async_db():
    """
    비동기 데이터베이스 세션 생성기
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()  # 성공 시 커밋
        except exc.SQLAlchemyError as e:
            await db.rollback()  # 예외 발생 시 롤백
            logger.error(f"Async database error: {e}")
            raise
        finally:
            await db.close()  # 세션 반환