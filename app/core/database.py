from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base
from backend.app.core.config import settings

db_url = settings.async_database_url
if "sslmode=" in db_url:
    db_url = (
        db_url.replace("sslmode=require", "ssl=require")
        .replace("sslmode=verify-full", "ssl=require")
        .replace("sslmode=verify-ca", "ssl=require")
        .replace("sslmode=prefer", "ssl=require")
    )

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    poolclass=NullPool
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
