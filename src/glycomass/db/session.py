from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from glycomass.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _create_engine(url: str) -> AsyncEngine:
    """Create an async engine for ``url``.

    In-memory SQLite needs a single shared connection (``StaticPool``) so that the
    schema created on one connection is visible to every session — otherwise each
    pooled connection would get its own empty database. File-backed SQLite and
    Postgres use the default pool.
    """
    if ":memory:" in url:
        return create_async_engine(
            url,
            future=True,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_async_engine(url, future=True)


def make_engine_and_sessionmaker(
    url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Build a fresh engine + sessionmaker for ``url``.

    Returning the engine gives callers (notably tests) a documented handle for
    ``create_all``/``dispose`` instead of reaching into ``sessionmaker.kw['bind']``.
    """
    engine = _create_engine(url)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def make_sessionmaker(url: str) -> async_sessionmaker[AsyncSession]:
    return make_engine_and_sessionmaker(url)[1]


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _engine, _sessionmaker
    if _sessionmaker is None:
        _engine, _sessionmaker = make_engine_and_sessionmaker(get_settings().database_url)
    return _sessionmaker


async def dispose_engine() -> None:
    """Dispose the cached engine (call on app shutdown) and reset the cache."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
