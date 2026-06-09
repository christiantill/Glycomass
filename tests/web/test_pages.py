from fastapi.testclient import TestClient

from glycomass.web.app import create_app

client = TestClient(create_app())


def test_glycan_form_page_renders():
    r = client.get("/glycan")
    assert r.status_code == 200
    assert "Free glycan" in r.text
    assert 'hx-post="/glycan"' in r.text


def test_glycan_post_returns_result_fragment():
    r = client.post("/glycan", data={"hex": 5, "hexnac": 4, "fuc": 1, "sia": 2, "charge": 1})
    assert r.status_code == 200
    assert "2369.8482" in r.text
    assert "data-spectrum" in r.text
    assert "C90 H148 N6 O66 S0" in r.text


def test_glycan_sodium_negative_renders_error_not_500():
    r = client.post("/glycan", data={"hex": 5, "hexnac": 4, "charge": -1, "sodium": "true"})
    assert r.status_code == 200
    assert "error-note" in r.text


def test_peptide_post_returns_mono():
    r = client.post("/peptide", data={"sequence": "PEPTIDE", "charge": 1})
    assert r.status_code == 200
    assert "800.3672" in r.text


def test_protein_form_has_resolution_select():
    r = client.get("/protein")
    assert "super high" in r.text


def test_index_renders_brand_and_links():
    r = client.get("/")
    assert r.status_code == 200
    assert "GlycoMass" in r.text
    assert 'href="/glycan"' in r.text


def test_protein_bad_resolution_renders_error_not_500():
    r = client.post("/protein", data={"sequence": "PEPTIDE", "charge": 1, "resolution": "ultra"})
    assert r.status_code == 200
    assert "error-note" in r.text
