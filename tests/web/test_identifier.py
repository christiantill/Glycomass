import asyncio
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import glycomass.db.session as session_mod
import glycomass.web.identifier as idmod
from glycomass.db import Base
from glycomass.web.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # A file-backed test DB (not :memory:) so the schema created on a throwaway engine
    # is visible to the engine the app builds on the TestClient's own event loop — this
    # sidesteps cross-loop reuse of a single shared in-memory connection.
    db_url = f"sqlite+aiosqlite:///{tmp_path / 't.db'}"
    monkeypatch.setenv("GLYCOMASS_UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("GLYCOMASS_RESULT_DIR", str(tmp_path / "res"))
    monkeypatch.setenv("GLYCOMASS_DATABASE_URL", db_url)

    from glycomass.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(session_mod, "_sessionmaker", None)

    async def _create() -> None:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())

    # Stub arq: run the job synchronously in-process instead of enqueueing to Redis.
    async def fake_enqueue(_self, _name, job_id):
        from glycomass.worker.tasks import run_identifier_job

        await run_identifier_job(job_id)

    async def fake_create_pool(_redis_settings):
        class _Pool:
            enqueue_job = fake_enqueue

        return _Pool()

    monkeypatch.setattr(idmod, "create_pool", fake_create_pool)
    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()
    monkeypatch.setattr(session_mod, "_sessionmaker", None)


def test_identifier_page_renders(client):
    r = client.get("/identifier")
    assert r.status_code == 200
    assert "Glycopeptide identifier" in r.text


def test_upload_processes_and_offers_download(client):
    sample = Path("tests/identifier/sample.mgf").read_bytes()
    r = client.post("/identifier", files={"mgf_file": ("sample.mgf", sample, "text/plain")})
    assert r.status_code == 200
    m = re.search(r"/identifier/([0-9a-f]{32})", r.text)
    assert m, r.text
    jid = m.group(1)

    status = client.get(f"/identifier/{jid}")
    assert status.status_code == 200

    download = client.get(f"/identifier/{jid}/download")
    assert download.status_code == 200
    assert b"BEGIN IONS" in download.content
