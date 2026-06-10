import asyncio

import pytest
from fastapi.testclient import TestClient

from glycomass.db import Base
from glycomass.db.session import make_engine_and_sessionmaker
from glycomass.web.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A DB-backed TestClient (file SQLite + schema created) for the HTML calculator
    pages, which now persist permalinks. `test_identifier.py` overrides this with its
    own client fixture (adds the arq stub)."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 't.db'}"
    monkeypatch.setenv("GLYCOMASS_DATABASE_URL", db_url)
    from glycomass.config import get_settings

    get_settings.cache_clear()

    async def _create() -> None:
        engine, _ = make_engine_and_sessionmaker(db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())
    with TestClient(create_app()) as c:
        yield c
