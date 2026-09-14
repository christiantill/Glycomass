def test_glycan_form_page_renders(client):
    r = client.get("/glycan")
    assert r.status_code == 200
    assert "Free glycan" in r.text
    assert 'hx-post="/glycan"' in r.text


def test_glycan_post_returns_result_fragment(client):
    r = client.post("/glycan", data={"hex": 5, "hexnac": 4, "fuc": 1, "sia": 2, "charge": 1})
    assert r.status_code == 200
    assert "2369.8482" in r.text
    assert "data-spectrum" in r.text
    assert "C90 H148 N6 O66 S0" in r.text
    assert "/c/" in r.text  # share link present


def test_glycan_sodium_negative_renders_error_not_500(client):
    r = client.post("/glycan", data={"hex": 5, "hexnac": 4, "charge": -1, "sodium": "true"})
    assert r.status_code == 200
    assert "error-note" in r.text


def test_peptide_post_returns_mono(client):
    r = client.post("/peptide", data={"sequence": "PEPTIDE", "charge": 1})
    assert r.status_code == 200
    assert "800.3672" in r.text


def test_protein_form_has_resolution_select(client):
    r = client.get("/protein")
    assert "super high" in r.text


def test_index_renders_brand_and_links(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "GlycoMass" in r.text
    assert 'href="/glycan"' in r.text


def test_protein_bad_resolution_renders_error_not_500(client):
    r = client.post("/protein", data={"sequence": "PEPTIDE", "charge": 1, "resolution": "ultra"})
    assert r.status_code == 200
    assert "error-note" in r.text


def test_impossible_disulfide_count_renders_error(client):
    r = client.post("/protein", data={"sequence": "PEPTIDE", "disulfide_bridges": 1})
    assert r.status_code == 200
    assert "two cysteines" in r.text
    assert "data-spectrum" not in r.text


def test_legacy_bookmarks_redirect_permanently(client):
    for old, new in {
        "/peptide_calculate": "/peptide", "/protein_calculate": "/protein",
        "/glycan_calculate": "/glycan", "/glycan_identifier": "/identifier",
    }.items():
        r = client.get(old, follow_redirects=False)
        assert r.status_code == 308
        assert r.headers["location"] == new
        assert client.get(old).status_code == 200


def test_overlong_html_sequences_return_visible_error(client):
    for kind, maximum in [('protein', 100000), ('peptide', 100)]:
        response = client.post('/'+kind, data={'sequence':'A'*(maximum+1)})
        assert response.status_code == 422
        assert 'error-note' in response.text


def test_spectrum_response_is_compressed_and_defaults_to_profile(client):
    response = client.post('/glycan', data={'hex': 5, 'hexnac': 4, 'charge': 1},
                           headers={'Accept-Encoding': 'gzip'})
    assert response.headers['content-encoding'] == 'gzip'
    assert int(response.headers['content-length']) < 50000
    assert 'data-spectrum-mode="profile" aria-pressed="true"' in response.text
    assert 'data-profile=' in response.text


def test_calculators_have_live_submission_status(client):
    for kind in ('glycan', 'peptide', 'protein'):
        response = client.get('/' + kind)
        assert 'role="status"' in response.text
        assert 'hx-disabled-elt="find button[type=submit]"' in response.text
        assert 'aria-busy="false"' in response.text
