"""Async SQLAlchemy 2.0 engine + session helpers.

Adapted from job7_chatbot/app/db/session.py. Works against both Postgres
(postgresql+asyncpg://) and SQLite (sqlite+aiosqlite://) so the same code
runs in docker-compose and in zero-install local dev.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_settings = get_settings()
_is_sqlite = _settings.database_url.startswith("sqlite")

# SQLite does not accept pool sizing kwargs; Postgres benefits from them.
_engine_kwargs: dict = {"pool_pre_ping": True}
if not _is_sqlite:
    _engine_kwargs.update(pool_size=5, max_overflow=5, pool_recycle=240)

engine = create_async_engine(_settings.database_url, **_engine_kwargs)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Transactional scope — commits on success, rolls back on error."""
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
