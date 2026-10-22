from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.settings import settings


engine: Optional[AsyncEngine] = None
session_maker: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db() -> None:
    global engine, session_maker

    if engine is not None and session_maker is not None:
        return

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def close_db() -> None:
    global engine, session_maker

    if engine is not None:
        await engine.dispose()

    engine = None
    session_maker = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if session_maker is None:
        raise RuntimeError("Database is not initialized.")

    async with session_maker() as session:
        yield session


@asynccontextmanager
async def with_session() -> AsyncGenerator[AsyncSession, None]:
    if session_maker is None:
        raise RuntimeError("Database is not initialized.")

    async with session_maker() as session:
        yield session
