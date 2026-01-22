from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# SQLite URL
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./trading_bot.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, # Needed for SQLite
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    class_=AsyncSession
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
            
async def init_db():
    # Import models here to ensure they are registered with Base.metadata
    import app.models  # noqa: F401
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
