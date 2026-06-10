import asyncio
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import glycomass.web.identifier as idmod
from glycomass.db import Base
from glycomass.db.session import make_engine_and_sessionmaker
from glycomass.web.app import create_app

_SAMPLE = Path("tests/identifier/sample.mgf")


@pytest.fixture
def client(tmp_path, monkeypatch):
    # A file-backed test DB (not :memory:) so the schema created on a throwaway engine
    # is visible to the engine the app builds on the TestClient's own event loop — this
    # sidesteps cross-loop reuse of a single shared in-memory connection. Global state
    # (settings cache, cached engine) is reset by the autouse reset_app_globals fixture.
    db_url = f"sqlite+aiosqlite:///{tmp_path / 't.db'}"
    monkeypatch.setenv("GLYCOMASS_UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("GLYCOMASS_RESULT_DIR", str(tmp_path / "res"))
    monkeypatch.setenv("GLYCOMASS_DATABASE_URL", db_url)

    from glycomass.config import get_settings

    get_settings.cache_clear()

    async def _create() -> None:
        engine, _ = make_engine_and_sessionmaker(db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())

    # Stub arq: run the job synchronously in-process instead of enqueueing to Redis.
    async def fake_enqueue(_self, name, job_id):
        assert name == "identifier_task"  # pin the route<->worker dispatch contract
        from glycomass.worker.tasks import run_identifier_job

        await run_identifier_job(job_id)

    class _Pool:
        enqueue_job = fake_enqueue

        async def aclose(self):  # closed by the lifespan on shutdown
            pass

    async def fake_create_pool(_redis_settings):
        return _Pool()

    monkeypatch.setattr(idmod, "create_pool", fake_create_pool)
    with TestClient(create_app()) as c:
        yield c


def test_identifier_page_renders(client):
    r = client.get("/identifier")
    assert r.status_code == 200
    assert "Glycopeptide identifier" in r.text


def test_upload_processes_and_offers_download(client):
    r = client.post(
        "/identifier", files={"mgf_file": ("sample.mgf", _SAMPLE.read_bytes(), "text/plain")}
    )
    assert r.status_code == 200
    m = re.search(r"/identifier/([0-9a-f]{32})", r.text)
    assert m, r.text
    jid = m.group(1)

    status = client.get(f"/identifier/{jid}")
    assert status.status_code == 200

    download = client.get(f"/identifier/{jid}/download")
    assert download.status_code == 200
    assert b"BEGIN IONS" in download.content


def test_download_missing_job_returns_404(client):
    r = client.get(f"/identifier/{'0' * 32}/download")
    assert r.status_code == 404


def test_status_unknown_job_renders_not_found(client):
    r = client.get(f"/identifier/{'0' * 32}")
    assert r.status_code == 200
    assert "not found" in r.text.lower()


def test_enqueue_failure_marks_job_failed_and_returns_503(tmp_path, monkeypatch):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 't.db'}"
    monkeypatch.setenv("GLYCOMASS_UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("GLYCOMASS_DATABASE_URL", db_url)
    from glycomass.config import get_settings

    get_settings.cache_clear()

    async def _create() -> None:
        engine, _ = make_engine_and_sessionmaker(db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())

    async def boom_create_pool(_redis_settings):
        raise RuntimeError("redis down")

    monkeypatch.setattr(idmod, "create_pool", boom_create_pool)
    with TestClient(create_app()) as c:
        r = c.post(
            "/identifier", files={"mgf_file": ("s.mgf", _SAMPLE.read_bytes(), "text/plain")}
        )
    assert r.status_code == 503
    assert "retry" in r.text.lower()


def test_oversized_upload_rejected_before_processing(monkeypatch):
    # The Content-Length middleware must reject before the body is buffered/parsed.
    monkeypatch.setenv("GLYCOMASS_MAX_UPLOAD_BYTES", "10")
    from glycomass.config import get_settings

    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        r = c.post("/identifier", files={"mgf_file": ("big.mgf", b"x" * 5000, "text/plain")})
    assert r.status_code == 413
    assert "maximum upload size" in r.text
