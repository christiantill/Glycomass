import pytest
from sqlalchemy import select

from glycomass.db import Base, IdentifierJob
from glycomass.db.session import make_engine_and_sessionmaker


@pytest.mark.asyncio
async def test_insert_and_read_job():
    engine, sm = make_engine_and_sessionmaker("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with sm() as s:
            job = IdentifierJob(upload_path="/tmp/x.mgf")
            s.add(job)
            await s.commit()
            jid = job.id
            assert job.status == "queued"
            assert len(jid) == 32
        async with sm() as s:
            got = (
                await s.execute(select(IdentifierJob).where(IdentifierJob.id == jid))
            ).scalar_one()
            assert got.upload_path == "/tmp/x.mgf"
    finally:
        await engine.dispose()
