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
