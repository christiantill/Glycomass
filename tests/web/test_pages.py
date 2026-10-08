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
        "/index": "/",
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


def test_sequence_validation_is_shared_by_html_and_api(client):
    for kind in ("peptide", "protein"):
        for sequence in (" \t\n", "XXX", "PEPXTIDE", "PEP-TIDE", "ß"):
            html = client.post('/' + kind, data={"sequence": sequence})
            api = client.post('/api/v1/calculate/' + kind, json={"sequence": sequence})
            assert html.status_code == api.status_code == 422
            assert 'error-note' in html.text
            assert 'data-spectrum=' not in html.text
        raw = " pep \n tide "
        api = client.post('/api/v1/calculate/' + kind, json={"sequence": raw})
        expected = client.post('/api/v1/calculate/' + kind, json={"sequence": "PEPTIDE"})
        assert api.status_code == 200
        assert api.json() == expected.json()
        html = client.post('/' + kind, data={"sequence": raw})
        assert html.status_code == 200 and 'data-spectrum=' in html.text


def test_sitemap_lists_current_public_routes(client):
    from xml.etree import ElementTree

    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    root = ElementTree.fromstring(response.text)
    urls = [node.text for node in root.findall("{*}url/{*}loc")]
    assert "https://glycomass.com/" in urls
    assert "https://glycomass.com/glycan" in urls
    for url in urls:
        assert client.get(url.replace("https://glycomass.com", "")).status_code == 200


def test_glycan_custom_modification_result_and_error(client):
    ok = client.post("/glycan", data={"hex": 3, "hexnac": 4, "fuc": 1, "charge": 2,
                                      "modification": "Label_ProA"})
    assert "841.8663" in ok.text and "C69 H115 N7 O40 S0" in ok.text
    custom = client.post("/glycan", data={"hex": 5, "hexnac": 4, "custom_modification": "C2H5O-H2O"})
    assert "C64 H107 N4 O46 S0" in custom.text
    bad = client.post("/glycan", data={"hex": 5, "hexnac": 4, "custom_modification": "Na"})
    assert bad.status_code == 200
    assert "error-note" in bad.text and "Unsupported element" in bad.text


def test_pages_carry_a_link_preview(client):
    pages = (
        ("/", "GlycoMass — exact masses"),
        ("/glycan", "Free-glycan calculator · GlycoMass"),
    )
    for path, title in pages:
        html = client.get(path).text
        assert html.count('property="og:image"') == 1
        assert 'content="https://glycomass.com/static/og.png?v=' in html
        assert f'property="og:title" content="{title}' in html
        assert 'name="twitter:card" content="summary_large_image"' in html
    image = client.get("/static/og.png")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
