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


def test_slug_golden_values_are_stable():
    # Pin slugs to literals: a change to normalize/DEFAULTS/serialization must be a visible,
    # intentional break rather than silently invalidating every existing shared link.
    assert P.compute_slug("glycan", {"hex": 5, "hexnac": 4}) == "adb4375565e2"
    assert P.compute_slug("peptide", {"sequence": "PEPTIDE"}) == "82e45e5f7255"


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


# --- route tests (use the DB-backed `client` fixture from tests/web/conftest.py) ---


def test_permalink_roundtrip_prefills_and_recomputes(client):
    import re

    r = client.post("/glycan", data={"hex": 5, "hexnac": 4, "fuc": 1, "sia": 2, "charge": 1})
    assert r.status_code == 200
    m = re.search(r"/c/([0-9a-f]{12})", r.text)
    assert m, r.text
    slug = m.group(1)

    page = client.get(f"/c/{slug}")
    assert page.status_code == 200
    # fuc=1 and sia=2 differ from the glycan defaults (both 0), so these uniquely prove the
    # form was prefilled from the STORED inputs (not a fallback to DEFAULTS).
    assert 'name="fuc" value="1"' in page.text
    assert 'name="sia" value="2"' in page.text
    assert "2369.8482" in page.text  # recomputed result shown
    assert "data-spectrum" in page.text  # spectrum rendered server-side


def test_unknown_slug_renders_404(client):
    r = client.get("/c/deadbeef0000")
    assert r.status_code == 404
    assert "not found" in r.text.lower()


def test_repeat_calc_is_same_link(client):
    import re

    a = client.post("/peptide", data={"sequence": "PEPTIDE", "charge": 1})
    b = client.post("/peptide", data={"sequence": "peptide", "charge": 1})  # case-insensitive
    pa = re.search(r"/c/([0-9a-f]{12})", a.text).group(1)
    pb = re.search(r"/c/([0-9a-f]{12})", b.text).group(1)
    assert pa == pb


def test_calc_still_works_when_save_fails(client, monkeypatch):
    # Best-effort persistence: a DB/save error must NOT break the calculation; the result
    # still renders, just without a share link.
    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr("glycomass.web.pages.save_permalink", boom)
    r = client.post("/glycan", data={"hex": 5, "hexnac": 4, "fuc": 1, "sia": 2, "charge": 1})
    assert r.status_code == 200
    assert "2369.8482" in r.text  # calc succeeded
    assert "/c/" not in r.text  # save failed -> no share link


def test_peracetyl_aliases_share_slug_and_roundtrip_selection(client):
    import re

    assert P.compute_slug("glycan", {"modification": "Peracetyl"}) == P.compute_slug(
        "glycan", {"modification": "Peracetly"}
    )
    response = client.post("/glycan", data={"hex": 5, "hexnac": 4, "modification": "Peracetyl"})
    slug = re.search(r"/c/([0-9a-f]{12})", response.text).group(1)
    page = client.get(f"/c/{slug}")
    assert '<option value="Peracetly" selected>Peracetyl</option>' in page.text
