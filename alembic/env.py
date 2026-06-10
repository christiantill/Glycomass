import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from glycomass.config import get_settings
from glycomass.db import models  # noqa: F401  (import registers tables on Base.metadata)
from glycomass.db.base import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit migration SQL without a DB connection (`alembic upgrade head --sql`)."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as conn:
        await conn.run_sync(_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
