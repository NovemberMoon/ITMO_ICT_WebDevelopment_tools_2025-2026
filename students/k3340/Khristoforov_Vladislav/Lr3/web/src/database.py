from typing import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)

async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий.
    """
    async with async_session_factory() as session:
        yield session