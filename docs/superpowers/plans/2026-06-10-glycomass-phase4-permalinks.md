# Glycomass Phase 4 — Shareable Permalinks — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Every successful calculation gets a stable, shareable URL (`/c/{slug}`) that re-renders the calculator with the inputs pre-filled and the result shown.

**Architecture:** A `permalinks` table (async SQLAlchemy, reuses the Phase 3 DB layer) stores `(slug, kind, inputs JSON, created_at)`. The slug is a deterministic 12-char SHA-256 of the normalized `(kind, inputs)`, so identical calculations dedupe to one row (idempotent, no row growth on re-runs). The three HTML calculator POST handlers become async, persist the inputs (best-effort — a DB hiccup never breaks the calc), and surface a "Share" link. `GET /c/{slug}` loads the row, **re-computes** the result (always fresh), and renders the calculator template with the form pre-filled. The JSON API is unchanged.

**Tech Stack:** SQLAlchemy 2.0 async + Alembic (existing), FastAPI form handlers, Jinja2 templates (made input-aware), HTMX (existing). No new dependencies.

**Design decisions (confirmed):** auto-save on every successful calc; slug = hash of normalized inputs (dedup); `/c/{slug}` renders the **prefilled calculator** (form populated + result inline).

---

## File Structure

- `src/glycomass/db/models.py` — add `Permalink` model (modify).
- `alembic/versions/0002_permalinks.py` — migration (new).
- `.gitignore` — ignore the dev `glycomass.db` (modify).
- `src/glycomass/web/permalinks.py` — defaults, normalize, slug, recompute, save/get helpers (new).
- `src/glycomass/web/pages.py` — async POST handlers save permalink + pass slug; `GET /c/{slug}`; GET pages pass input defaults (modify).
- `src/glycomass/web/templates/{peptide,protein,glycan}.html` — input-aware (modify).
- `src/glycomass/web/templates/_result.html` — share link (modify).
- `src/glycomass/web/templates/_not_found.html` — friendly 404 for unknown slugs (new).
- `src/glycomass/web/static/css/app.css` — `.permalink` style (modify).
- `tests/web/test_permalinks.py` — unit + route tests (new).
- `tests/web/test_pages.py` — convert to a DB-backed fixture client (modify).
- `CLAUDE.md` — Phase 4 docs (modify).

---

### Task 1: `Permalink` model + migration

**Files:** Modify `src/glycomass/db/models.py`, `src/glycomass/db/__init__.py`, `.gitignore`; Create `alembic/versions/0002_permalinks.py`, `tests/db/test_permalink_model.py`.

- [ ] **Step 1: failing test** `tests/db/test_permalink_model.py`:
```python
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
            row = (await s.execute(select(Permalink).where(Permalink.slug == "abc123"))).scalar_one()
            assert row.kind == "glycan"
            assert row.inputs["hex"] == 5
    finally:
        await engine.dispose()
```

- [ ] **Step 2: run, verify FAIL** (`Permalink` undefined): `uv run pytest tests/db/test_permalink_model.py --no-cov`.

- [ ] **Step 3: implement** — append to `src/glycomass/db/models.py`:
```python
from typing import Any

from sqlalchemy import JSON


class Permalink(Base):
    __tablename__ = "permalinks"

    slug: Mapped[str] = mapped_column(String(16), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # peptide|protein|glycan
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
```
(Place the `from typing import Any` and `from sqlalchemy import JSON` imports with the existing import groups, not mid-file; merge `JSON` into the existing `from sqlalchemy import DateTime, String, Text` line.)

- [ ] **Step 4: export it** — in `src/glycomass/db/__init__.py` add `Permalink`:
```python
from glycomass.db.models import IdentifierJob, Permalink

__all__ = ["Base", "IdentifierJob", "Permalink"]
```

- [ ] **Step 5: migration** `alembic/versions/0002_permalinks.py`:
```python
"""permalinks

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.create_table(
        "permalinks",
        sa.Column("slug", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("slug", name="pk_permalinks"),
    )


def downgrade() -> None:
    op.drop_table("permalinks")
```

- [ ] **Step 6:** `.gitignore` — add a line `glycomass.db` (the alembic default dev DB; keep the tree clean).

- [ ] **Step 7: run, verify PASS** + alembic applies both revisions on a clean sqlite file:
```bash
uv run pytest tests/db/test_permalink_model.py --no-cov
rm -f glycomass.db && uv run alembic upgrade head && \
  uv run python -c "import sqlite3;c=sqlite3.connect('glycomass.db');print(sorted(r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")))" && \
  rm -f glycomass.db
```
Expected: 1 passed; tables include `identifier_jobs`, `permalinks`, `alembic_version`. Then `uv run ruff check src/glycomass/db alembic tests/db` and `uv run mypy`.

- [ ] **Step 8: commit:**
```bash
git add src/glycomass/db/models.py src/glycomass/db/__init__.py alembic/versions/0002_permalinks.py tests/db/test_permalink_model.py .gitignore
git commit -m "feat(permalinks): Permalink model + migration 0002"
```

---

### Task 2: Permalink helper (`web/permalinks.py`)

**Files:** Create `src/glycomass/web/permalinks.py`, `tests/web/test_permalinks.py`.

- [ ] **Step 1: failing test** `tests/web/test_permalinks.py` (unit portion only for now):
```python
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
    assert norm["hex"] == 7 and norm["hexnac"] == 4  # default
    assert "bogus" not in norm


def test_compute_result_dispatches_by_kind():
    r = P.compute_result("glycan", {"hex": 5, "hexnac": 4, "fuc": 1, "sia": 2, "charge": 1})
    assert abs(r.mono_mz - 2369.8482) < 1e-3
    assert r.composition == "C90 H148 N6 O66 S0"


@pytest.mark.asyncio
async def test_save_permalink_dedupes():
    from glycomass.db import Base
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
        from sqlalchemy import func, select
        from glycomass.db import Permalink
        async with sm() as s:
            count = (await s.execute(select(func.count()).select_from(Permalink))).scalar_one()
            assert count == 1
    finally:
        await engine.dispose()
```

- [ ] **Step 2: run, verify FAIL:** `uv run pytest tests/web/test_permalinks.py --no-cov`.

- [ ] **Step 3: implement** `src/glycomass/web/permalinks.py`:
```python
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from glycomass.core import MassResult, glycan_mass, peptide_mass, protein_mass
from glycomass.db.models import Permalink

# Default form inputs per calculator — drive the empty pages AND fill missing keys
# during normalization. Values match the original Phase 2 template defaults.
DEFAULTS: dict[str, dict[str, Any]] = {
    "peptide": {
        "sequence": "PEPTIDE", "hex": 0, "hexnac": 0, "fuc": 0, "sia": 0,
        "charge": 1, "carbamidomethyl": False, "deamidation": 0,
    },
    "protein": {
        "sequence": "ACDEFGHIKLMNPQRSTVWY", "hex": 0, "hexnac": 0, "fuc": 0, "sia": 0,
        "charge": 5, "deamidation": 0, "disulfide_bridges": 0, "resolution": "medium",
    },
    "glycan": {
        "hex": 5, "hexnac": 4, "fuc": 0, "sia": 0,
        "charge": 1, "sodium": False, "modification": "None",
    },
}
TEMPLATES = {"peptide": "peptide.html", "protein": "protein.html", "glycan": "glycan.html"}


def normalize(kind: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize inputs so equivalent calculations hash identically: fill missing keys
    from DEFAULTS, drop unknown keys, upper-case the sequence (calculators do too)."""
    out = {**DEFAULTS[kind], **{k: v for k, v in inputs.items() if k in DEFAULTS[kind]}}
    if "sequence" in out:
        out["sequence"] = str(out["sequence"]).upper()
    return out


def compute_slug(kind: str, inputs: dict[str, Any]) -> str:
    payload = json.dumps(
        {"kind": kind, **normalize(kind, inputs)}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def compute_result(kind: str, inputs: dict[str, Any]) -> MassResult:
    i = normalize(kind, inputs)
    if kind == "peptide":
        return peptide_mass(
            i["sequence"], hex=i["hex"], hexnac=i["hexnac"], fuc=i["fuc"], sia=i["sia"],
            charge=i["charge"], carbamidomethyl=i["carbamidomethyl"], deamidation=i["deamidation"],
        )
    if kind == "protein":
        return protein_mass(
            i["sequence"], hex=i["hex"], hexnac=i["hexnac"], fuc=i["fuc"], sia=i["sia"],
            charge=i["charge"], deamidation=i["deamidation"],
            disulfide_bridges=i["disulfide_bridges"], resolution=i["resolution"],
        )
    return glycan_mass(
        hex=i["hex"], hexnac=i["hexnac"], fuc=i["fuc"], sia=i["sia"],
        charge=i["charge"], sodium=i["sodium"], modification=i["modification"],
    )


async def save_permalink(session: AsyncSession, kind: str, inputs: dict[str, Any]) -> str:
    norm = normalize(kind, inputs)
    slug = compute_slug(kind, norm)
    if await session.get(Permalink, slug) is None:
        session.add(Permalink(slug=slug, kind=kind, inputs=norm))
        try:
            await session.commit()
        except IntegrityError:  # concurrent insert of the same slug — fine
            await session.rollback()
    return slug
```

- [ ] **Step 4: run, verify PASS:** `uv run pytest tests/web/test_permalinks.py --no-cov` (5 passed). Then `uv run ruff check src/glycomass/web/permalinks.py` + `uv run mypy`.

- [ ] **Step 5: commit:**
```bash
git add src/glycomass/web/permalinks.py tests/web/test_permalinks.py
git commit -m "feat(permalinks): slug/normalize/recompute/save helper"
```

---

### Task 3: Input-aware templates + share link + 404 page

**Files:** Modify `src/glycomass/web/templates/{peptide,protein,glycan}.html`, `_result.html`, `static/css/app.css`; Create `_not_found.html`.

> The three calc pages are driven by an `inputs` dict (always supplied by the routes) and an optional `result`/`slug`. The empty page passes `inputs=DEFAULTS[kind]` and `result=None`, so it renders identically to today.

- [ ] **Step 1: `peptide.html`** — replace the form + result panel body with:
```html
  <form class="calc-form" hx-post="/peptide" hx-target="#result" hx-swap="innerHTML">
    <div><label>Peptide sequence</label><input type="text" name="sequence" value="{{ inputs.sequence }}"></div>
    <div class="calc-grid">
      <div><label>Hex</label><input type="number" name="hex" value="{{ inputs.hex }}" min="0"></div>
      <div><label>HexNAc</label><input type="number" name="hexnac" value="{{ inputs.hexnac }}" min="0"></div>
      <div><label>Fuc</label><input type="number" name="fuc" value="{{ inputs.fuc }}" min="0"></div>
      <div><label>Sia</label><input type="number" name="sia" value="{{ inputs.sia }}" min="0"></div>
      <div><label>Charge</label><input type="number" name="charge" value="{{ inputs.charge }}"></div>
      <div><label>Deamidation</label><input type="number" name="deamidation" value="{{ inputs.deamidation }}" min="0"></div>
    </div>
    <label style="display:flex;gap:.5rem;align-items:center;text-transform:none;letter-spacing:0">
      <input type="checkbox" name="carbamidomethyl" value="true" style="width:auto" {% if inputs.carbamidomethyl %}checked{% endif %}> Carbamidomethyl (Cys)
    </label>
    <button class="btn btn-primary" type="submit">Calculate</button>
  </form>
  <div id="result" class="result-panel">{% if result %}{% include "_result.html" %}{% else %}<p style="color:var(--muted)">Enter a peptide and calculate.</p>{% endif %}</div>
```

- [ ] **Step 2: `protein.html`** — same pattern; the resolution `<select>` marks the stored value selected:
```html
  <form class="calc-form" hx-post="/protein" hx-target="#result" hx-swap="innerHTML">
    <div><label>Protein sequence</label><input type="text" name="sequence" value="{{ inputs.sequence }}"></div>
    <div class="calc-grid">
      <div><label>Hex</label><input type="number" name="hex" value="{{ inputs.hex }}" min="0"></div>
      <div><label>HexNAc</label><input type="number" name="hexnac" value="{{ inputs.hexnac }}" min="0"></div>
      <div><label>Fuc</label><input type="number" name="fuc" value="{{ inputs.fuc }}" min="0"></div>
      <div><label>Sia</label><input type="number" name="sia" value="{{ inputs.sia }}" min="0"></div>
      <div><label>Charge</label><input type="number" name="charge" value="{{ inputs.charge }}"></div>
      <div><label>Deamidation</label><input type="number" name="deamidation" value="{{ inputs.deamidation }}" min="0"></div>
      <div><label>Disulfide bridges</label><input type="number" name="disulfide_bridges" value="{{ inputs.disulfide_bridges }}" min="0"></div>
      <div><label>Resolution</label><select name="resolution">
        <option {% if inputs.resolution == 'low' %}selected{% endif %}>low</option>
        <option {% if inputs.resolution == 'medium' %}selected{% endif %}>medium</option>
        <option {% if inputs.resolution == 'super high' %}selected{% endif %}>super high</option>
      </select></div>
    </div>
    <button class="btn btn-primary" type="submit">Calculate</button>
  </form>
  <div id="result" class="result-panel">{% if result %}{% include "_result.html" %}{% else %}<p style="color:var(--muted)">Enter a protein and calculate.</p>{% endif %}</div>
```

- [ ] **Step 3: `glycan.html`** — modification `<select>` selected logic + sodium checkbox:
```html
  <form class="calc-form" hx-post="/glycan" hx-target="#result" hx-swap="innerHTML">
    <div class="calc-grid">
      <div><label>Hex</label><input type="number" name="hex" value="{{ inputs.hex }}" min="0"></div>
      <div><label>HexNAc</label><input type="number" name="hexnac" value="{{ inputs.hexnac }}" min="0"></div>
      <div><label>Fuc</label><input type="number" name="fuc" value="{{ inputs.fuc }}" min="0"></div>
      <div><label>Sia</label><input type="number" name="sia" value="{{ inputs.sia }}" min="0"></div>
      <div><label>Charge</label><input type="number" name="charge" value="{{ inputs.charge }}"></div>
      <div><label>Modification</label>
        <select name="modification">
          {% for m in ["None", "Permethyl", "Peracetly", "ReducedEnd", "Label_2AB", "Label_2AA"] %}
          <option {% if inputs.modification == m %}selected{% endif %}>{{ m }}</option>
          {% endfor %}
        </select>
      </div>
    </div>
    <label style="display:flex;gap:.5rem;align-items:center;text-transform:none;letter-spacing:0">
      <input type="checkbox" name="sodium" value="true" style="width:auto" {% if inputs.sodium %}checked{% endif %}> Sodium adduct
    </label>
    <button class="btn btn-primary" type="submit">Calculate</button>
  </form>
  <div id="result" class="result-panel">{% if result %}{% include "_result.html" %}{% else %}<p style="color:var(--muted)">Enter a composition and calculate.</p>{% endif %}</div>
```

- [ ] **Step 4: `_result.html`** — append the share link after the spectrum div:
```html
{% if slug %}
<div class="permalink"><a href="/c/{{ slug }}">🔗 Share this calculation</a></div>
{% endif %}
```

- [ ] **Step 5: `app.css`** — append:
```css
.permalink{margin-top:1.1rem;font:500 .72rem/1 var(--font-mono);letter-spacing:.1em;text-transform:uppercase}
.permalink a{color:var(--gold);text-decoration:none;border-bottom:1px solid var(--line-gold);padding-bottom:2px}
.permalink a:hover{color:var(--gold-soft)}
```

- [ ] **Step 6: `_not_found.html`** (new):
```html
{% extends "base.html" %}
{% block title %}Not found · GlycoMass{% endblock %}
{% block content %}
<span class="eyebrow">404</span>
<h1 style="font-family:var(--font-display);font-weight:400;font-size:var(--step-3);color:var(--paper);margin:.6rem 0 1.2rem">Shared calculation not found</h1>
<p style="color:var(--muted)">This permalink may never have existed. Open a calculator:
  <a href="/peptide" style="color:var(--gold)">Glycopeptide</a> ·
  <a href="/protein" style="color:var(--gold)">Glycoprotein</a> ·
  <a href="/glycan" style="color:var(--gold)">Glycan</a></p>
{% endblock %}
```

- [ ] **Step 7: sanity render** (templates still parse; covered by route tests in Task 4). Commit:
```bash
git add src/glycomass/web/templates/peptide.html src/glycomass/web/templates/protein.html src/glycomass/web/templates/glycan.html src/glycomass/web/templates/_result.html src/glycomass/web/templates/_not_found.html src/glycomass/web/static/css/app.css
git commit -m "feat(permalinks): input-aware calc templates + share link + 404 page"
```

---

### Task 4: Wire `pages.py` (save on POST, `/c/{slug}`, prefilled GETs) + tests

**Files:** Modify `src/glycomass/web/pages.py`, `tests/web/test_pages.py`; extend `tests/web/test_permalinks.py`.

- [ ] **Step 1: rewrite** `src/glycomass/web/pages.py`:
```python
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from glycomass.core import NegativeIonSodiumError
from glycomass.db.session import get_sessionmaker
from glycomass.web.permalinks import DEFAULTS, TEMPLATES, compute_result, save_permalink

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()


async def _try_save(kind: str, inputs: dict) -> str | None:
    """Persist a permalink best-effort; never let a DB problem break the calculation."""
    try:
        sm = get_sessionmaker()
        async with sm() as session:
            return await save_permalink(session, kind, inputs)
    except Exception:
        return None


def _page(request: Request, kind: str, *, inputs=None, result=None, slug=None) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        TEMPLATES[kind],
        {"inputs": inputs or DEFAULTS[kind], "result": result, "slug": slug},
    )


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/peptide", response_class=HTMLResponse)
def peptide_page(request: Request) -> HTMLResponse:
    return _page(request, "peptide")


@router.post("/peptide", response_class=HTMLResponse)
async def peptide_result(
    request: Request,
    sequence: str = Form(...),
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), carbamidomethyl: bool = Form(False), deamidation: int = Form(0),
) -> HTMLResponse:
    inputs = {
        "sequence": sequence, "hex": hex, "hexnac": hexnac, "fuc": fuc, "sia": sia,
        "charge": charge, "carbamidomethyl": carbamidomethyl, "deamidation": deamidation,
    }
    result = compute_result("peptide", inputs)
    slug = await _try_save("peptide", inputs)
    return templates.TemplateResponse(request, "_result.html", {"result": result, "slug": slug})


@router.get("/protein", response_class=HTMLResponse)
def protein_page(request: Request) -> HTMLResponse:
    return _page(request, "protein")


@router.post("/protein", response_class=HTMLResponse)
async def protein_result(
    request: Request,
    sequence: str = Form(...),
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), deamidation: int = Form(0),
    disulfide_bridges: int = Form(0), resolution: str = Form("medium"),
) -> HTMLResponse:
    inputs = {
        "sequence": sequence, "hex": hex, "hexnac": hexnac, "fuc": fuc, "sia": sia,
        "charge": charge, "deamidation": deamidation,
        "disulfide_bridges": disulfide_bridges, "resolution": resolution,
    }
    try:
        result = compute_result("protein", inputs)
    except KeyError:
        return templates.TemplateResponse(
            request, "_error.html", {"message": f"Unknown resolution: {resolution}"}
        )
    slug = await _try_save("protein", inputs)
    return templates.TemplateResponse(request, "_result.html", {"result": result, "slug": slug})


@router.get("/glycan", response_class=HTMLResponse)
def glycan_page(request: Request) -> HTMLResponse:
    return _page(request, "glycan")


@router.post("/glycan", response_class=HTMLResponse)
async def glycan_result(
    request: Request,
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), sodium: bool = Form(False), modification: str = Form("None"),
) -> HTMLResponse:
    inputs = {
        "hex": hex, "hexnac": hexnac, "fuc": fuc, "sia": sia,
        "charge": charge, "sodium": sodium, "modification": modification,
    }
    try:
        result = compute_result("glycan", inputs)
    except NegativeIonSodiumError as exc:
        return templates.TemplateResponse(request, "_error.html", {"message": str(exc)})
    slug = await _try_save("glycan", inputs)
    return templates.TemplateResponse(request, "_result.html", {"result": result, "slug": slug})


@router.get("/c/{slug}", response_class=HTMLResponse)
async def shared(request: Request, slug: str) -> HTMLResponse:
    from glycomass.db.models import Permalink

    sm = get_sessionmaker()
    async with sm() as session:
        row = await session.get(Permalink, slug)
    if row is None:
        return templates.TemplateResponse(request, "_not_found.html", {}, status_code=404)
    result = compute_result(row.kind, row.inputs)
    return _page(request, row.kind, inputs=row.inputs, result=result, slug=slug)
```

- [ ] **Step 2: convert `tests/web/test_pages.py`** to a DB-backed fixture client (the POST handlers now persist permalinks). Replace the module-level client with:
```python
import asyncio

import pytest
from fastapi.testclient import TestClient

from glycomass.db import Base
from glycomass.db.session import make_engine_and_sessionmaker
from glycomass.web.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 't.db'}"
    monkeypatch.setenv("GLYCOMASS_DATABASE_URL", db_url)
    from glycomass.config import get_settings

    get_settings.cache_clear()

    async def _create() -> None:
        engine, _ = make_engine_and_sessionmaker(db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())
    with TestClient(create_app()) as c:
        yield c
```
Then change each `test_*` to take `client` as a parameter (replace the module-level `client`). Keep all existing assertions; add to `test_glycan_post_returns_result_fragment` a `assert "/c/" in r.text` (share link present).

- [ ] **Step 3: add route tests** to `tests/web/test_permalinks.py` (reuse the same fixture — duplicate it locally or import; duplicating the small fixture is fine):
```python
def test_permalink_roundtrip_prefills_and_recomputes(client):
    r = client.post("/glycan", data={"hex": 5, "hexnac": 4, "fuc": 1, "sia": 2, "charge": 1})
    assert r.status_code == 200
    import re
    m = re.search(r"/c/([0-9a-f]{12})", r.text)
    assert m, r.text
    slug = m.group(1)

    page = client.get(f"/c/{slug}")
    assert page.status_code == 200
    assert 'value="5"' in page.text and 'value="1"' in page.text  # form prefilled (hex=5, fuc=1)
    assert "2369.8482" in page.text                                # recomputed result shown
    assert "data-spectrum" in page.text                            # spectrum rendered server-side


def test_unknown_slug_renders_404(client):
    r = client.get("/c/deadbeef0000")
    assert r.status_code == 404
    assert "not found" in r.text.lower()


def test_repeat_calc_is_same_link(client):
    a = client.post("/peptide", data={"sequence": "PEPTIDE", "charge": 1})
    b = client.post("/peptide", data={"sequence": "peptide", "charge": 1})  # case-insensitive
    import re
    pa = re.search(r"/c/([0-9a-f]{12})", a.text).group(1)
    pb = re.search(r"/c/([0-9a-f]{12})", b.text).group(1)
    assert pa == pb
```
(Add the `client` fixture from Step 2 to this file too — copy it in.)

- [ ] **Step 4: run, verify PASS** (per-file then full):
```bash
uv run pytest tests/web/test_pages.py tests/web/test_permalinks.py -v --no-cov
uv run pytest          # full suite + coverage ≥80%
uv run ruff check && uv run mypy
```
Expected: all pass. (If a calc page test that does NOT set a DB remains, it would create `glycomass.db`; the fixture in Step 2 prevents that. `_try_save` is also resilient regardless.)

- [ ] **Step 5: commit:**
```bash
git add src/glycomass/web/pages.py tests/web/test_pages.py tests/web/test_permalinks.py
git commit -m "feat(permalinks): auto-save on calc, /c/{slug} prefilled re-render"
```

---

### Task 5: Integration smoke + docs + final review

**Files:** Modify `CLAUDE.md`.

- [ ] **Step 1: full gates:** `uv run pytest` (pass, ≥80%), `uv run mypy` (Success), `uv run ruff check` (pass), and grid parity unaffected: `uv run pytest -m grid --no-cov` (795 passed).

- [ ] **Step 2: integration smoke** (Postgres-backed permalink round-trip via the real stack):
```bash
docker compose -f docker-compose.dev.yml up -d
export GLYCOMASS_DATABASE_URL="postgresql+asyncpg://glycomass:glycomass@localhost:5432/glycomass"
sleep 5
uv run alembic upgrade head            # creates permalinks (+ identifier_jobs) in PG
uv run glycomass-api &
API=$!
sleep 4
SLUG=$(curl -fsS -d "hex=5&hexnac=4&fuc=1&sia=2&charge=1" localhost:8000/glycan | grep -oE '/c/[0-9a-f]{12}' | head -1)
echo "permalink: $SLUG"
curl -fsS "localhost:8000$SLUG" | grep -oE '2369\.8482|value="5"' | head -3   # recomputed + prefilled
kill $API 2>/dev/null
docker compose -f docker-compose.dev.yml down
```
Expected: a `/c/<12hex>` slug; GET re-renders with `2369.8482` and prefilled `value="5"`. Paste output. (DONE_WITH_CONCERNS escape if Docker infra misbehaves — the unit suite already covers the logic.)

- [ ] **Step 3: update `CLAUDE.md`** under "## 2026 Rewrite", append:
```markdown
### Phase 4 — shareable permalinks (`src/glycomass/web/permalinks.py`, `db.Permalink`)
- Every successful HTML calculation auto-saves its normalized inputs under a deterministic 12-char slug (`compute_slug` = SHA-256 of `{kind, normalized inputs}`); identical calcs dedupe to one row. Saving is best-effort — a DB failure never breaks the calculation (`_try_save`).
- `GET /c/{slug}` loads the row, **re-computes** the result (always fresh), and renders the calc template with the form prefilled (`pages.shared`). Unknown slug → `_not_found.html` (404).
- The 3 calc templates are input-aware (driven by an `inputs` dict; `_result.html` shows the share link when `slug` is set). The JSON API is unchanged.
- DB: `db.Permalink` (slug PK, kind, inputs JSON, created_at); Alembic `0002_permalinks`.
```

- [ ] **Step 4: commit:**
```bash
git add CLAUDE.md
git commit -m "docs(permalinks): Phase 4 integration smoke + CLAUDE.md"
```

---

## Self-Review

**1. Spec coverage (Phase 4 = permalinks, spec §4.3 + §data-model):** ✅ `permalinks` table with `slug, kind, inputs(JSON), created_at` (Task 1); ✅ slug = hash of normalized inputs (Task 2 `compute_slug`); ✅ persist on successful calculation (Task 4 POST handlers); ✅ `GET /c/{slug}` re-computes and re-renders (Task 4 `shared`). Open question from spec ("hash vs random; cache results") resolved: **hash** (dedup) + **re-compute** (no result caching — always fresh, and immune to chemistry corrections like the HexNAc fix). Out of scope (later): permalinks for the JSON API and the identifier (HTML calculators only this phase).

**2. Placeholder scan:** No TBD/TODO. Every code step is complete. The integration smoke (Task 5) has a DONE_WITH_CONCERNS escape if Docker misbehaves (unit suite already covers the logic).

**3. Type consistency:** `DEFAULTS`, `TEMPLATES`, `normalize`, `compute_slug`, `compute_result`, `save_permalink` are defined in Task 2 and used identically in Task 4. `Permalink(slug, kind, inputs, created_at)` matches across model (Task 1), migration (Task 1), helper (Task 2), and routes (Task 4). The route context keys (`inputs`, `result`, `slug`) match what the templates read (Task 3). `_page()`/`_try_save()` signatures match their call sites.

**Documented decisions:** (a) auto-save every calc, dedup by deterministic slug; (b) `/c/{slug}` re-computes rather than caching the stored result, so shared links stay correct if the chemistry is later corrected; (c) saving is best-effort so the calculator never depends on the DB being up; (d) JSON API and identifier are intentionally out of scope for permalinks this phase.
```
