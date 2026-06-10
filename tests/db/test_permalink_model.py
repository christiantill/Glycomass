import pytest
from sqlalchemy import select

from glycomass.db import Base, Permalink
from glycomass.db.session import make_engine_and_sessionmaker


@pytest.mark.asyncio
async def test_insert_and_read_permalink():
    engine, sm = make_engine_and_sessionmaker("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with sm() as s:
            s.add(Permalink(slug="abc123", kind="glycan", inputs={"hex": 5, "hexnac": 4}))
            await s.commit()
        async with sm() as s:
            row = (
                await s.execute(select(Permalink).where(Permalink.slug == "abc123"))
            ).scalar_one()
            assert row.kind == "glycan"
            assert row.inputs["hex"] == 5
    finally:
        await engine.dispose()
