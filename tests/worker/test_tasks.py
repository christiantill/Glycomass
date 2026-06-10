from pathlib import Path

import pytest
from sqlalchemy import select

from glycomass.db import Base, IdentifierJob
from glycomass.db.session import make_sessionmaker
from glycomass.worker.tasks import run_identifier_job


@pytest.mark.asyncio
async def test_run_identifier_job_processes_and_marks_done(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYCOMASS_RESULT_DIR", str(tmp_path))
    from glycomass.config import get_settings

    get_settings.cache_clear()

    sample = Path(__file__).resolve().parents[1] / "identifier" / "sample.mgf"
    sm = make_sessionmaker("sqlite+aiosqlite:///:memory:")
    engine = sm.kw["bind"]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sm() as s:
        job = IdentifierJob(upload_path=str(sample))
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
    get_settings.cache_clear()
