from fastapi.testclient import TestClient

from glycomass.web.app import create_app

client = TestClient(create_app())


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_calculate_glycan_matches_fixture():
    r = client.post("/api/v1/calculate/glycan", json={"hex": 5, "hexnac": 4, "fuc": 1, "sia": 2, "charge": 1})
    assert r.status_code == 200
    body = r.json()
    assert abs(body["mono_mz"] - 2369.8482) < 1e-3
    assert body["composition"] == "C90 H148 N6 O66 S0"
    assert len(body["spectrum"]["mz"]) == len(body["spectrum"]["intensity"]) == 10


def test_calculate_peptide_matches_fixture():
    r = client.post("/api/v1/calculate/peptide", json={"sequence": "PEPTIDE", "charge": 1})
    assert r.status_code == 200
    assert abs(r.json()["mono_mz"] - 800.3672) < 1e-3


def test_sodium_negative_ion_returns_422():
    r = client.post("/api/v1/calculate/glycan", json={"hex": 5, "hexnac": 4, "charge": -1, "sodium": True})
    assert r.status_code == 422


def test_unknown_resolution_returns_422():
    r = client.post("/api/v1/calculate/protein", json={"sequence": "PEPTIDE", "charge": 1, "resolution": "ultra"})
    assert r.status_code == 422


def test_missing_required_field_returns_422():
    r = client.post("/api/v1/calculate/peptide", json={"charge": 1})
    assert r.status_code == 422


def test_static_css_served():
    r = client.get("/static/css/app.css")
    assert r.status_code == 200
    assert "--gold" in r.text
