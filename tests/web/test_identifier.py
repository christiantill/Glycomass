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
    assert not list((tmp_path / "up").glob("*.mgf"))


def test_oversized_upload_rejected_before_processing(monkeypatch):
    # The Content-Length middleware must reject before the body is buffered/parsed.
    monkeypatch.setenv("GLYCOMASS_MAX_UPLOAD_BYTES", "10")
    from glycomass.config import get_settings

    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        r = c.post("/identifier", files={"mgf_file": ("big.mgf", b"x" * 5000, "text/plain")})
    assert r.status_code == 413
    assert "maximum upload size" in r.text


@pytest.mark.asyncio
@pytest.mark.parametrize("declared_length", [None, b"1"])
async def test_streamed_upload_is_bounded_and_parser_closes_files(monkeypatch, declared_length):
    from starlette import formparsers

    from glycomass.config import get_settings

    monkeypatch.setenv("GLYCOMASS_MAX_UPLOAD_BYTES", "200")
    get_settings.cache_clear()
    opened = []
    original = formparsers.SpooledTemporaryFile

    def track_file(*args, **kwargs):
        file = original(*args, **kwargs)
        opened.append(file)
        return file

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", track_file)
    chunks = iter([
        b'--boundary\r\nContent-Disposition: form-data; name="mgf_file"; filename="s.mgf"\r\n'
        b'Content-Type: text/plain\r\n\r\n',
        b'x' * 150,
        b'--boundary--\r\n',
    ])
    reads = 0

    async def receive():
        nonlocal reads
        reads += 1
        return {"type": "http.request", "body": next(chunks), "more_body": True}

    sent = []

    async def send(message):
        sent.append(message)

    headers = [(b"content-type", b"multipart/form-data; boundary=boundary")]
    if declared_length is not None:
        headers.append((b"content-length", declared_length))
    await create_app()({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/identifier",
        "query_string": b"", "headers": headers,
    }, receive, send)
    assert sent[0]["status"] == 413
    assert reads == 2  # do not consume the rest of the oversized stream
    assert opened and all(file.closed for file in opened)


@pytest.mark.parametrize("body", [b"", b"not an mgf", b"BEGIN IONS\nEND IONS\n", b"BEGIN IONS\nPEPMASS=900\n1 2\n"])
def test_invalid_upload_rejected_before_queue(client, body):
    response = client.post('/identifier', files={'mgf_file': ('invalid.mgf', body, 'text/plain')})
    assert response.status_code == 422
    assert 'valid MGF' in response.text


@pytest.mark.parametrize("failure", ["copy", "path_commit"])
def test_partial_upload_is_removed_and_job_failed(client, monkeypatch, failure):
    from sqlalchemy import select

    from glycomass.config import get_settings
    from glycomass.db.models import IdentifierJob

    def fail_write(src, dest):
        dest.write_bytes(b'partial')
        raise OSError('disk full')

    if failure == "copy":
        monkeypatch.setattr(idmod, '_write_upload', fail_write)
    else:
        from sqlalchemy.ext.asyncio import AsyncSession
        original_commit = AsyncSession.commit
        commits = 0

        async def fail_path_commit(self):
            nonlocal commits
            commits += 1
            if commits == 2:
                raise RuntimeError("path update failed")
            await original_commit(self)

        monkeypatch.setattr(AsyncSession, "commit", fail_path_commit)
    response = client.post('/identifier', files={'mgf_file': ('s.mgf', _SAMPLE.read_bytes(), 'text/plain')})
    assert response.status_code == 503
    assert not list(get_settings().upload_dir.glob('*.mgf'))

    async def check():
        engine, sm = make_engine_and_sessionmaker(get_settings().database_url)
        try:
            async with sm() as session:
                job = (await session.execute(select(IdentifierJob))).scalar_one()
                assert job.status == 'failed'
                assert 'persist' in job.error
        finally:
            await engine.dispose()
    asyncio.run(check())


@pytest.mark.asyncio
async def test_concurrent_first_uploads_share_one_pool(monkeypatch):
    from starlette.requests import Request

    app = create_app()
    request = Request({'type': 'http', 'app': app})
    calls = 0
    pool = object()

    async def create(settings):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return pool

    monkeypatch.setattr(idmod, 'create_pool', create)
    pools = await asyncio.gather(*(idmod._get_arq_pool(request) for _ in range(10)))
    assert all(result is pool for result in pools)
    assert calls == 1


def _set_identifier_enabled(monkeypatch, enabled: bool) -> None:
    from glycomass.config import get_settings

    monkeypatch.setenv("GLYCOMASS_IDENTIFIER_ENABLED", "true" if enabled else "false")
    get_settings.cache_clear()


def test_enabled_identifier_is_linked_from_navigation(client, monkeypatch):
    _set_identifier_enabled(monkeypatch, True)
    r = client.get("/")
    assert r.status_code == 200
    assert 'href="/identifier"' in r.text


def test_disabled_identifier_hides_navigation_and_form(client, monkeypatch):
    _set_identifier_enabled(monkeypatch, False)
    assert 'href="/identifier"' not in client.get("/").text
    r = client.get("/identifier")
    assert r.status_code == 503
    assert "temporarily unavailable" in r.text
    assert 'hx-post="/identifier"' not in r.text


def test_disabled_identifier_refuses_upload_without_queueing(client, monkeypatch, tmp_path):
    _set_identifier_enabled(monkeypatch, False)

    async def no_pool(_redis_settings):
        raise AssertionError("a disabled identifier must not queue jobs")

    monkeypatch.setattr(idmod, "create_pool", no_pool)
    r = client.post(
        "/identifier", files={"mgf_file": ("sample.mgf", _SAMPLE.read_bytes(), "text/plain")}
    )
    assert r.status_code == 503
    assert "temporarily unavailable" in r.text
    assert not list((tmp_path / "up").glob("*.mgf"))


def test_disabled_identifier_keeps_earlier_results_available(client, monkeypatch):
    _set_identifier_enabled(monkeypatch, True)
    r = client.post(
        "/identifier", files={"mgf_file": ("sample.mgf", _SAMPLE.read_bytes(), "text/plain")}
    )
    jid = re.search(r"/identifier/([0-9a-f]{32})", r.text).group(1)

    _set_identifier_enabled(monkeypatch, False)
    status = client.get(f"/identifier/{jid}")
    assert status.status_code == 200
    assert "done" in status.text
    download = client.get(f"/identifier/{jid}/download")
    assert download.status_code == 200
    assert b"BEGIN IONS" in download.content


def test_disabled_identifier_leaves_calculators_working(client, monkeypatch):
    _set_identifier_enabled(monkeypatch, False)
    r = client.post("/api/v1/calculate/peptide", json={"sequence": "PEPTIDE", "charge": 1})
    assert r.status_code == 200
    assert abs(r.json()["mono_mz"] - 800.3672) < 1e-3


@pytest.mark.asyncio
async def test_disabled_identifier_refuses_upload_before_reading_body(monkeypatch):
    _set_identifier_enabled(monkeypatch, False)

    async def receive():
        raise AssertionError("the upload body must not be read")

    sent = []

    async def send(message):
        sent.append(message)

    await create_app()({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/identifier", "raw_path": b"/identifier",
        "query_string": b"", "root_path": "", "server": ("test", 80), "client": ("test", 1),
        "headers": [(b"content-type", b"multipart/form-data; boundary=b"),
                    (b"content-length", b"262144000")],
    }, receive, send)
    assert sent[0]["status"] == 503
