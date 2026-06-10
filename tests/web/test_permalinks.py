import pytest

from glycomass.web import permalinks as P


def test_slug_is_deterministic_and_case_insensitive_on_sequence():
    a = P.compute_slug("peptide", {"sequence": "peptide", "charge": 1})
    b = P.compute_slug("peptide", {"sequence": "PEPTIDE", "charge": 1})
    assert a == b
    assert len(a) == 12


def test_slug_differs_by_kind_and_inputs():
    base = {"hex": 5, "hexnac": 4}
    assert P.compute_slug("glycan", base) != P.compute_slug("peptide", {"sequence": "X"})
    assert P.compute_slug("glycan", base) != P.compute_slug("glycan", {"hex": 6, "hexnac": 4})


def test_normalize_fills_defaults_and_drops_extras():
    norm = P.normalize("glycan", {"hex": 7, "bogus": 1})
    assert norm["hex"] == 7 and norm["hexnac"] == 4  # hexnac filled from default
    assert "bogus" not in norm


def test_compute_result_dispatches_by_kind():
    r = P.compute_result("glycan", {"hex": 5, "hexnac": 4, "fuc": 1, "sia": 2, "charge": 1})
    assert abs(r.mono_mz - 2369.8482) < 1e-3
    assert r.composition == "C90 H148 N6 O66 S0"


@pytest.mark.asyncio
async def test_save_permalink_dedupes():
    from sqlalchemy import func, select

    from glycomass.db import Base, Permalink
    from glycomass.db.session import make_engine_and_sessionmaker

    engine, sm = make_engine_and_sessionmaker("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with sm() as s:
            slug1 = await P.save_permalink(s, "glycan", {"hex": 5, "hexnac": 4})
        async with sm() as s:
            slug2 = await P.save_permalink(s, "glycan", {"hex": 5, "hexnac": 4})
        assert slug1 == slug2
        async with sm() as s:
            count = (await s.execute(select(func.count()).select_from(Permalink))).scalar_one()
            assert count == 1
    finally:
        await engine.dispose()
