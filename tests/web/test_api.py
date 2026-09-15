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


def test_impossible_disulfide_count_returns_422():
    r = client.post("/api/v1/calculate/protein", json={"sequence": "PEPTIDE", "disulfide_bridges": 1})
    assert r.status_code == 422
    assert "two cysteines" in r.json()["detail"]


def test_overlong_sequences_rejected_before_calculation():
    for kind, maximum in [('protein', 100000), ('peptide', 100)]:
        response = client.post('/api/v1/calculate/'+kind, json={'sequence': 'A'*(maximum+1)})
        assert response.status_code == 422


def test_calculator_request_body_limit():
    response = client.post('/api/v1/calculate/protein', content=b'x'*(1024*1024+1), headers={'Content-Type':'application/json'})
    assert response.status_code == 413
    assert response.json()['detail'] == 'Calculation request is too large.'


def test_streamed_calculator_body_limit_without_content_length():
    response = client.post('/api/v1/calculate/protein', content=iter([b'{"sequence":"', b'A'*(1024*1024), b'"}']), headers={'Content-Type':'application/json'})
    assert response.status_code == 413


def test_glycan_custom_modification_api():
    ok = client.post("/api/v1/calculate/glycan", json={"hex": 5, "hexnac": 4, "custom_modification": "-C2-H6"})
    assert ok.status_code == 200
    assert ok.json()["composition"] == "C60 H98 N4 O46 S0"
    bad = client.post("/api/v1/calculate/glycan", json={"hex": 5, "hexnac": 4, "custom_modification": "C2X"})
    assert bad.status_code == 422
    huge = client.post("/api/v1/calculate/glycan", json={"hex": 5, "custom_modification": "C99999999999999999999"})
    assert huge.status_code == 422
