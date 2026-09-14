import shutil
from pathlib import Path

import pytest
from sqlalchemy import select

from glycomass.db import Base, IdentifierJob
from glycomass.db.session import make_engine_and_sessionmaker
from glycomass.worker.tasks import run_identifier_job

_SAMPLE = Path(__file__).resolve().parents[1] / "identifier" / "sample.mgf"


async def _make_db():
    engine, sm = make_engine_and_sessionmaker("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, sm


@pytest.mark.asyncio
async def test_run_identifier_job_processes_and_marks_done(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYCOMASS_RESULT_DIR", str(tmp_path))
    from glycomass.config import get_settings

    get_settings.cache_clear()

    upload = tmp_path / "in.mgf"
    shutil.copy(_SAMPLE, upload)  # the worker consumes (deletes) the source upload
    engine, sm = await _make_db()
    try:
        async with sm() as s:
            job = IdentifierJob(upload_path=str(upload))
            s.add(job)
            await s.commit()
            jid = job.id

        await run_identifier_job(jid, sessionmaker=sm)

        async with sm() as s:
            done = (
                await s.execute(select(IdentifierJob).where(IdentifierJob.id == jid))
            ).scalar_one()
            assert done.status == "done"
            assert done.result_path and Path(done.result_path).exists()
            assert done.summary and '"identified": 1' in done.summary
        assert not upload.exists()  # source upload deleted after success
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_run_identifier_job_records_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYCOMASS_RESULT_DIR", str(tmp_path))
    from glycomass.config import get_settings

    get_settings.cache_clear()

    engine, sm = await _make_db()
    try:
        async with sm() as s:
            job = IdentifierJob(upload_path=str(tmp_path / "does-not-exist.mgf"))
            s.add(job)
            await s.commit()
            jid = job.id

        await run_identifier_job(jid, sessionmaker=sm)

        async with sm() as s:
            failed = (
                await s.execute(select(IdentifierJob).where(IdentifierJob.id == jid))
            ).scalar_one()
            assert failed.status == "failed"
            assert failed.error and "FileNotFoundError" in failed.error
            assert failed.result_path is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_commit_failure_retains_input_for_retry(tmp_path, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    from glycomass.config import get_settings

    monkeypatch.setenv("GLYCOMASS_RESULT_DIR", str(tmp_path))
    get_settings.cache_clear()
    upload = tmp_path / "in.mgf"
    shutil.copy(_SAMPLE, upload)
    engine, sm = await _make_db()
    try:
        async with sm() as session:
            job = IdentifierJob(upload_path=str(upload))
            session.add(job)
            await session.commit()
            jid = job.id

        original = AsyncSession.commit
        commits = 0

        async def fail_final_commit(self):
            nonlocal commits
            commits += 1
            if commits == 2:
                raise RuntimeError("database unavailable")
            await original(self)

        monkeypatch.setattr(AsyncSession, "commit", fail_final_commit)
        with pytest.raises(RuntimeError, match="database unavailable"):
            await run_identifier_job(jid, sessionmaker=sm)
        assert upload.exists()
        async with sm() as session:
            assert (await session.get(IdentifierJob, jid)).status == "running"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_processing_leaves_event_loop_responsive_and_reaps_cancelled_child(monkeypatch):
    import asyncio
    import sys

    from glycomass.worker.tasks import process_mgf

    original = asyncio.create_subprocess_exec
    started = asyncio.Event()
    children = []

    async def slow_child(*args, **kwargs):
        child = await original(sys.executable, "-c", "import time; time.sleep(60)", **kwargs)
        children.append(child)
        started.set()
        return child

    monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_child)
    task = asyncio.create_task(process_mgf("unused", "unused"))
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        heartbeat = asyncio.Event()
        asyncio.get_running_loop().call_later(0.02, heartbeat.set)
        await asyncio.wait_for(heartbeat.wait(), timeout=1)
        assert not task.done()
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)
    assert children[0].returncode is not None


@pytest.mark.asyncio
async def test_cancelled_job_reaches_terminal_state_and_retains_upload(tmp_path, monkeypatch):
    import asyncio

    import glycomass.worker.tasks as tasks
    from glycomass.config import get_settings

    monkeypatch.setenv('GLYCOMASS_RESULT_DIR', str(tmp_path))
    get_settings.cache_clear()
    started = asyncio.Event()

    async def blocked(*args):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(tasks, 'process_mgf', blocked)
    upload = tmp_path/'in.mgf'
    shutil.copy(_SAMPLE, upload)
    engine, sm = await _make_db()
    try:
        async with sm() as session:
            job = IdentifierJob(upload_path=str(upload))
            session.add(job)
            await session.commit()
            jid = job.id
        from sqlalchemy.ext.asyncio import AsyncSession
        original_commit = AsyncSession.commit
        cleanup_started = asyncio.Event()
        allow_cleanup = asyncio.Event()
        commits = 0

        async def delayed_cleanup_commit(self):
            nonlocal commits
            commits += 1
            if commits == 2:
                cleanup_started.set()
                await allow_cleanup.wait()
            await original_commit(self)

        monkeypatch.setattr(AsyncSession, "commit", delayed_cleanup_commit)
        task = asyncio.create_task(run_identifier_job(jid, sessionmaker=sm))
        await asyncio.wait_for(started.wait(), timeout=5)
        task.cancel()
        await asyncio.wait_for(cleanup_started.wait(), timeout=5)
        task.cancel()  # repeated shutdown cancellation must not cancel DB cleanup
        allow_cleanup.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)
        async with sm() as session:
            job = await session.get(IdentifierJob, jid)
            assert job.status == 'failed'
            assert 'cancelled' in job.error
        assert upload.exists()
    finally:
        await engine.dispose()
