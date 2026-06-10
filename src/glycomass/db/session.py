from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from glycomass.config import get_settings

_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def make_sessionmaker(url: str) -> async_sessionmaker[AsyncSession]:
    """Build an async sessionmaker bound to a fresh engine for ``url``.

    In-memory SQLite needs a single shared connection (``StaticPool``) so that the
    schema created on one connection is visible to every session — otherwise each
    pooled connection would get its own empty database. File-backed SQLite and
    Postgres use the default pool.
    """
    if ":memory:" in url:
        engine = create_async_engine(
            url,
            future=True,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_async_engine(url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = make_sessionmaker(get_settings().database_url)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
