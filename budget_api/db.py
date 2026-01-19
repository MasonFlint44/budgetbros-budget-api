from __future__ import annotations

import os
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from budget_api.tables import Base

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _normalize_asyncpg_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def _create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(_normalize_asyncpg_url(database_url))


def init_engine(database_url: str) -> None:
    global _engine, _sessionmaker
    _engine = _create_engine(database_url)
    _sessionmaker = async_sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def init_from_env() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set for postgres-backed runtime.")
    init_engine(database_url)


async def init_db() -> None:
    if _engine is None:
        init_from_env()
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    if _sessionmaker is None:
        init_from_env()
    session = _sessionmaker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def reset_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        _engine.sync_engine.dispose()
    _engine = None
    _sessionmaker = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        init_from_env()
    return _engine
