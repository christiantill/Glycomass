# Glycomass Phase 2 — Web App & JSON API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the existing `glycomass.core` in a FastAPI app that serves a documented JSON API (`/api/v1`) and three server-rendered calculator pages (Jinja + HTMX forms + interactive uPlot spectra), plus a landing page — all on the navy/gold design system.

**Architecture:** A FastAPI app-factory (`create_app()`) with a structlog-configured lifespan mounts a JSON router and an HTML pages router; both call the SAME `core` functions (no logic duplicated). HTML pages POST via HTMX and swap in a result fragment whose spectrum arrays are rendered client-side by uPlot. Config via `pydantic-settings`. No database, identifier, or permalinks (Phases 3–4).

**Tech Stack:** FastAPI, uvicorn, Jinja2, python-multipart, pydantic-settings, structlog; HTMX + uPlot (vendored, pinned); hand-authored design-token CSS ported from `design/glycomass-landing.html`. Tests via FastAPI `TestClient` (httpx).

---

## File Structure

- `pyproject.toml` — add web deps + `[project.scripts] glycomass-api` (modify).
- `src/glycomass/config.py` — `Settings` (pydantic-settings, `GLYCOMASS_*`) + `get_settings()` (new).
- `src/glycomass/logging_config.py` — structlog `configure_logging()` + `get_logger()` (new; named `logging_config` to avoid shadowing stdlib `logging`).
- `src/glycomass/schemas.py` — API request models `PeptideRequest`/`ProteinRequest`/`GlycanRequest` (new; response reuses `core.MassResult`).
- `src/glycomass/web/__init__.py`, `src/glycomass/web/api/__init__.py` (new).
- `src/glycomass/web/api/v1.py` — JSON router: health + 3 calculate endpoints (new).
- `src/glycomass/web/pages.py` — HTML routes: index + 3 calculator GET/POST (new).
- `src/glycomass/web/app.py` — `create_app()` factory, lifespan, mounts, `main()` entrypoint (new).
- `src/glycomass/web/templates/` — `base.html`, `index.html`, `peptide.html`, `protein.html`, `glycan.html`, `_result.html`, `_error.html` (new).
- `src/glycomass/web/static/css/app.css` — design-token CSS ported from the prototype (new).
- `src/glycomass/web/static/js/app.js` — uPlot init on `htmx:afterSwap` (new).
- `src/glycomass/web/static/vendor/` — pinned `htmx.min.js`, `uPlot.iife.min.js`, `uPlot.min.css` (new).
- `tests/web/test_api.py`, `tests/web/test_pages.py`, `tests/test_config.py` (new).

---

### Task 0: Web dependencies, config, structlog

**Files:** Modify `pyproject.toml`; Create `src/glycomass/config.py`, `src/glycomass/logging_config.py`, `tests/test_config.py`.

- [ ] **Step 1: Add deps + script to `pyproject.toml`.** In `[project] dependencies`, append:
```toml
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    "pydantic-settings>=2.3",
    "structlog>=24.1",
```
In `[project.optional-dependencies] dev`, append `"httpx>=0.27",`. After `[tool.hatch.build.targets.wheel]` add a scripts entry to `[project]`:
```toml
[project.scripts]
glycomass-api = "glycomass.web.app:main"
```

- [ ] **Step 2: Sync.** Run: `uv sync --extra dev` → expect success (no compilation; all wheels).

- [ ] **Step 3: Write failing test** `tests/test_config.py`:
```python
from glycomass.config import Settings, get_settings


def test_defaults():
    s = Settings()
    assert s.environment == "development"
    assert s.log_json is False


def test_env_prefix_override(monkeypatch):
    monkeypatch.setenv("GLYCOMASS_LOG_JSON", "true")
    monkeypatch.setenv("GLYCOMASS_ENVIRONMENT", "production")
    s = Settings()
    assert s.log_json is True
    assert s.environment == "production"


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
```

- [ ] **Step 4: Run, verify FAIL:** `uv run pytest tests/test_config.py -v --no-cov`.

- [ ] **Step 5: Implement** `src/glycomass/config.py`:
```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration from environment (prefix GLYCOMASS_)."""

    model_config = SettingsConfigDict(env_prefix="GLYCOMASS_", env_file=".env", extra="ignore")

    environment: str = "development"
    log_json: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Implement** `src/glycomass/logging_config.py`:
```python
from __future__ import annotations

import logging

import structlog


def configure_logging(*, json_output: bool, level: str = "INFO") -> None:
    """Configure structlog + stdlib logging once at startup."""
    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    renderer = structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "glycomass") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

- [ ] **Step 7: Run, verify PASS:** `uv run pytest tests/test_config.py -v --no-cov` (3 passed). Then `uv run ruff check` and `uv run mypy` (fix minimally; structlog is typed).

- [ ] **Step 8: Commit:**
```bash
git add pyproject.toml uv.lock src/glycomass/config.py src/glycomass/logging_config.py tests/test_config.py
git commit -m "feat(web): add web deps, settings, and structlog config"
```

---

### Task 1: API request schemas

**Files:** Create `src/glycomass/schemas.py`, `tests/test_schemas.py`.

- [ ] **Step 1: Write failing test** `tests/test_schemas.py`:
```python
from glycomass.schemas import GlycanRequest, PeptideRequest, ProteinRequest


def test_peptide_request_defaults():
    r = PeptideRequest(sequence="PEPTIDE")
    assert r.charge == 1 and r.hex == 0 and r.carbamidomethyl is False and r.deamidation == 0


def test_protein_request_resolution_default():
    assert ProteinRequest(sequence="ACDE").resolution == "medium"


def test_glycan_request_defaults():
    r = GlycanRequest(hex=5, hexnac=4)
    assert r.charge == 1 and r.sodium is False and r.modification == "None"
```

- [ ] **Step 2: Run, verify FAIL:** `uv run pytest tests/test_schemas.py -v --no-cov`.

- [ ] **Step 3: Implement** `src/glycomass/schemas.py`:
```python
from pydantic import BaseModel


class PeptideRequest(BaseModel):
    sequence: str
    hex: int = 0
    hexnac: int = 0
    fuc: int = 0
    sia: int = 0
    charge: int = 1
    carbamidomethyl: bool = False
    deamidation: int = 0


class ProteinRequest(BaseModel):
    sequence: str
    hex: int = 0
    hexnac: int = 0
    fuc: int = 0
    sia: int = 0
    charge: int = 1
    deamidation: int = 0
    disulfide_bridges: int = 0
    resolution: str = "medium"


class GlycanRequest(BaseModel):
    hex: int = 0
    hexnac: int = 0
    fuc: int = 0
    sia: int = 0
    charge: int = 1
    sodium: bool = False
    modification: str = "None"
```

- [ ] **Step 4: Run, verify PASS:** `uv run pytest tests/test_schemas.py -v --no-cov` (3 passed). Run ruff + mypy.

- [ ] **Step 5: Commit:**
```bash
git add src/glycomass/schemas.py tests/test_schemas.py
git commit -m "feat(web): add API request schemas"
```

---

### Task 2: App factory + JSON API router

**Files:** Create `src/glycomass/web/__init__.py`, `src/glycomass/web/api/__init__.py`, `src/glycomass/web/api/v1.py`, `src/glycomass/web/app.py`, `tests/web/__init__.py` (empty? NO — with importlib mode, do NOT add `__init__.py` to tests), `tests/web/test_api.py`. Also create an empty `src/glycomass/web/static/.gitkeep` and `src/glycomass/web/templates/.gitkeep` so the directories exist for mounting (replaced in Tasks 3–5).

- [ ] **Step 1: Create package markers + placeholder dirs.**
`src/glycomass/web/__init__.py`: `"""FastAPI web layer."""`
`src/glycomass/web/api/__init__.py`: `"""JSON API."""`
Create empty files `src/glycomass/web/static/.gitkeep` and `src/glycomass/web/templates/.gitkeep`.

- [ ] **Step 2: Implement the API router** `src/glycomass/web/api/v1.py`:
```python
from fastapi import APIRouter, HTTPException

from glycomass.core import (
    MassResult,
    NegativeIonSodiumError,
    glycan_mass,
    peptide_mass,
    protein_mass,
)
from glycomass.schemas import GlycanRequest, PeptideRequest, ProteinRequest

router = APIRouter(prefix="/api/v1", tags=["calculate"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/calculate/peptide", response_model=MassResult)
def calculate_peptide(req: PeptideRequest) -> MassResult:
    return peptide_mass(
        req.sequence, hex=req.hex, hexnac=req.hexnac, fuc=req.fuc, sia=req.sia,
        charge=req.charge, carbamidomethyl=req.carbamidomethyl, deamidation=req.deamidation,
    )


@router.post("/calculate/protein", response_model=MassResult)
def calculate_protein(req: ProteinRequest) -> MassResult:
    try:
        return protein_mass(
            req.sequence, hex=req.hex, hexnac=req.hexnac, fuc=req.fuc, sia=req.sia,
            charge=req.charge, deamidation=req.deamidation,
            disulfide_bridges=req.disulfide_bridges, resolution=req.resolution,
        )
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown resolution: {req.resolution}") from exc


@router.post("/calculate/glycan", response_model=MassResult)
def calculate_glycan(req: GlycanRequest) -> MassResult:
    try:
        return glycan_mass(
            hex=req.hex, hexnac=req.hexnac, fuc=req.fuc, sia=req.sia,
            charge=req.charge, sodium=req.sodium, modification=req.modification,
        )
    except NegativeIonSodiumError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
```

- [ ] **Step 3: Implement the app factory** `src/glycomass/web/app.py`:
```python
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from glycomass.config import get_settings
from glycomass.logging_config import configure_logging
from glycomass.web.api.v1 import router as api_router

_HERE = Path(__file__).parent
_STATIC = _HERE / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(json_output=settings.log_json, level=settings.log_level)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Glycomass", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
    app.include_router(api_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("glycomass.web.app:app", host="0.0.0.0", port=8000)
```

- [ ] **Step 4: Write the failing test** `tests/web/test_api.py`:
```python
from fastapi.testclient import TestClient

from glycomass.web.app import create_app

client = TestClient(create_app())


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_calculate_glycan_matches_fixture():
    # Hex5HexNAc4Fuc1Sia2, z=1 -> mono 2369.8482, C90 H148 N6 O66 S0
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
    r = client.post("/api/v1/calculate/peptide", json={"charge": 1})  # no sequence
    assert r.status_code == 422
```

- [ ] **Step 5: Run, verify PASS:** `uv run pytest tests/web/test_api.py -v --no-cov` (6 passed). Then ruff + mypy. (mypy may need `fastapi`/`starlette` types — they ship inline; if mypy flags the StaticFiles directory arg, pass `directory=str(_STATIC)`.)

- [ ] **Step 6: Commit:**
```bash
git add src/glycomass/web tests/web/test_api.py
git commit -m "feat(web): FastAPI app factory + /api/v1 JSON calculate endpoints"
```

---

### Task 3: Base template, design-system CSS, vendored HTMX/uPlot

**Files:** Create `src/glycomass/web/templates/base.html`, `src/glycomass/web/static/css/app.css`, `src/glycomass/web/static/js/app.js`, vendored libs under `src/glycomass/web/static/vendor/`. Modify `src/glycomass/web/app.py` (add Jinja templates + a pages router stub will come in Task 4 — for now just confirm static serves).

- [ ] **Step 1: Vendor pinned HTMX + uPlot** (download into the static vendor dir):
```bash
mkdir -p src/glycomass/web/static/vendor
curl -fsSL https://cdn.jsdelivr.net/npm/htmx.org@2.0.3/dist/htmx.min.js -o src/glycomass/web/static/vendor/htmx.min.js
curl -fsSL https://cdn.jsdelivr.net/npm/uplot@1.6.32/dist/uPlot.iife.min.js -o src/glycomass/web/static/vendor/uPlot.iife.min.js
curl -fsSL https://cdn.jsdelivr.net/npm/uplot@1.6.32/dist/uPlot.min.css -o src/glycomass/web/static/vendor/uPlot.min.css
```
Verify each file is non-empty (`wc -c`); if a download fails (no network), STOP and report BLOCKED.

- [ ] **Step 2: Create `src/glycomass/web/static/css/app.css`** by extracting the entire contents of the `<style>...</style>` block from `design/glycomass-landing.html` (the design-token + component CSS — `:root` variables, reset, atmosphere, header/nav, hero, cards, etc.). Copy it verbatim into `app.css` (no `<style>` tags). This is the approved design system; do not redesign it. Append these calculator-form helpers at the end:
```css
/* ---- calculator form + result (Phase 2) ---- */
.calc-shell{display:grid;grid-template-columns:minmax(280px,360px) 1fr;gap:clamp(1.5rem,4vw,3rem);align-items:start}
@media (max-width:820px){.calc-shell{grid-template-columns:1fr}}
.calc-form{display:grid;gap:1rem;border:1px solid var(--line);border-radius:var(--radius-lg);padding:1.5rem;background:var(--navy-950)}
.calc-form label{display:block;font-family:var(--font-mono);font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:.35rem}
.calc-form input,.calc-form select{width:100%;background:var(--ink);border:1px solid var(--line);border-radius:10px;color:var(--paper);padding:.6rem .7rem;font-family:var(--font-mono);font-size:.95rem}
.calc-form input:focus,.calc-form select:focus{outline:none;border-color:var(--line-gold);box-shadow:0 0 0 3px color-mix(in oklch,var(--gold) 18%,transparent)}
.calc-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.8rem}
.result-panel{border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--navy-950);padding:1.4rem;min-height:320px}
.result-readout{display:flex;gap:1.6rem;flex-wrap:wrap;font-family:var(--font-mono);margin-bottom:1rem}
.result-readout .k{font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}
.result-readout .v{font-size:1.15rem;color:var(--paper)}
.result-readout .v small{color:var(--gold);font-size:.7rem;margin-left:.25rem}
.spectrum{width:100%;height:240px}
.error-note{border:1px solid var(--line-gold);border-radius:12px;padding:1rem;color:var(--gold-soft);font-size:.95rem;background:color-mix(in oklch,var(--gold) 6%,transparent)}
.u-legend{color:var(--muted)!important}
```

- [ ] **Step 3: Create `src/glycomass/web/static/js/app.js`** (init uPlot on HTMX swap):
```javascript
function drawSpectra(root) {
  root.querySelectorAll("[data-spectrum]").forEach((el) => {
    if (el.dataset.drawn) return;
    el.dataset.drawn = "1";
    const data = JSON.parse(el.getAttribute("data-spectrum"));
    const mz = data.mz, inten = data.intensity;
    const opts = {
      width: el.clientWidth || 600,
      height: 240,
      scales: { x: { time: false } },
      axes: [
        { stroke: "#9aa7c7", grid: { stroke: "rgba(255,255,255,0.06)" }, label: "m/z" },
        { stroke: "#9aa7c7", grid: { stroke: "rgba(255,255,255,0.06)" }, label: "rel. intensity" },
      ],
      series: [
        {},
        { stroke: "#FFD009", width: 2, fill: "rgba(255,208,9,0.15)", points: { show: true, size: 5 } },
      ],
    };
    new uPlot(opts, [mz, inten], el);
  });
}

document.addEventListener("DOMContentLoaded", () => drawSpectra(document));
document.body.addEventListener("htmx:afterSwap", (e) => drawSpectra(e.target));
```

- [ ] **Step 4: Create `src/glycomass/web/templates/base.html`** by porting the prototype shell. Use the header/nav and footer markup from `design/glycomass-landing.html`, but replace the inline `<style>` with a stylesheet link and add the vendored scripts + a `{% block content %}`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{% block title %}GlycoMass{% endblock %}</title>
<meta name="description" content="Exact masses and isotope spectra for glycans, glycopeptides and glycoproteins." />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,900&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;450;500;600&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="{{ url_for('static', path='css/app.css') }}" />
<link rel="stylesheet" href="{{ url_for('static', path='vendor/uPlot.min.css') }}" />
</head>
<body>
<svg class="grain"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>
<header>
  <div class="wrap">
    <nav class="nav">
      <a class="brand" href="/" aria-label="GlycoMass home">
        <svg class="mark" viewBox="0 0 32 32" fill="none" aria-hidden="true">
          <rect x="1" y="1" width="30" height="30" rx="9" fill="#002C73"/>
          <path d="M5 22 L9 22 L11 13 L14 24 L17 8 L20 19 L23 15 L27 15" stroke="#FFD009" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
        </svg>
        Glyco<b>Mass</b>
      </a>
      <ul class="navlinks">
        <li><a href="/peptide">Glycopeptide</a></li>
        <li><a href="/protein">Glycoprotein</a></li>
        <li><a href="/glycan">Glycan</a></li>
        <li><a href="/docs">API</a></li>
      </ul>
      <a class="nav-cta" href="/glycan">Open calculators</a>
    </nav>
  </div>
</header>
<main class="wrap" style="padding-block:clamp(2.5rem,6vw,5rem)">
  {% block content %}{% endblock %}
</main>
<footer>
  <div class="wrap"><div class="legal"><span>© 2026 GlycoMass · glycomass.com</span><span>monoisotopic · most-abundant · brainpy</span></div></div>
</footer>
<script src="{{ url_for('static', path='vendor/htmx.min.js') }}"></script>
<script src="{{ url_for('static', path='vendor/uPlot.iife.min.js') }}"></script>
<script src="{{ url_for('static', path='js/app.js') }}"></script>
</body>
</html>
```

- [ ] **Step 5: Wire Jinja + static into the app.** Modify `src/glycomass/web/app.py`: add `from fastapi.templating import Jinja2Templates` and, after `_STATIC`, add `_TEMPLATES = _HERE / "templates"`. (The `templates` object is created in `pages.py` in Task 4; nothing else changes here yet.) Verify the app still imports: `uv run python -P -c "from glycomass.web.app import create_app; create_app(); print('ok')"` → `ok`.

- [ ] **Step 6: Test static serving** — add to `tests/web/test_api.py`:
```python
def test_static_css_served():
    r = client.get("/static/css/app.css")
    assert r.status_code == 200
    assert "--gold" in r.text
```
Run: `uv run pytest tests/web/test_api.py -v --no-cov` (7 passed).

- [ ] **Step 7: Commit:**
```bash
git add src/glycomass/web/static src/glycomass/web/templates/base.html src/glycomass/web/app.py tests/web/test_api.py
git commit -m "feat(web): base template, design-system CSS, vendored htmx/uplot"
```

---

### Task 4: Calculator pages (forms + HTMX results + uPlot)

**Files:** Create `src/glycomass/web/pages.py`, templates `peptide.html`, `protein.html`, `glycan.html`, `_result.html`, `_error.html`; Modify `src/glycomass/web/app.py` (include pages router); Create `tests/web/test_pages.py`.

- [ ] **Step 1: Implement the pages router** `src/glycomass/web/pages.py`:
```python
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from glycomass.core import NegativeIonSodiumError, glycan_mass, peptide_mass, protein_mass

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/peptide", response_class=HTMLResponse)
def peptide_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "peptide.html")


@router.post("/peptide", response_class=HTMLResponse)
def peptide_result(
    request: Request,
    sequence: str = Form(...),
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), carbamidomethyl: bool = Form(False), deamidation: int = Form(0),
) -> HTMLResponse:
    result = peptide_mass(
        sequence, hex=hex, hexnac=hexnac, fuc=fuc, sia=sia,
        charge=charge, carbamidomethyl=carbamidomethyl, deamidation=deamidation,
    )
    return templates.TemplateResponse(request, "_result.html", {"result": result})


@router.get("/protein", response_class=HTMLResponse)
def protein_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "protein.html")


@router.post("/protein", response_class=HTMLResponse)
def protein_result(
    request: Request,
    sequence: str = Form(...),
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), deamidation: int = Form(0),
    disulfide_bridges: int = Form(0), resolution: str = Form("medium"),
) -> HTMLResponse:
    result = protein_mass(
        sequence, hex=hex, hexnac=hexnac, fuc=fuc, sia=sia, charge=charge,
        deamidation=deamidation, disulfide_bridges=disulfide_bridges, resolution=resolution,
    )
    return templates.TemplateResponse(request, "_result.html", {"result": result})


@router.get("/glycan", response_class=HTMLResponse)
def glycan_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "glycan.html")


@router.post("/glycan", response_class=HTMLResponse)
def glycan_result(
    request: Request,
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), sodium: bool = Form(False), modification: str = Form("None"),
) -> HTMLResponse:
    try:
        result = glycan_mass(
            hex=hex, hexnac=hexnac, fuc=fuc, sia=sia,
            charge=charge, sodium=sodium, modification=modification,
        )
    except NegativeIonSodiumError as exc:
        return templates.TemplateResponse(request, "_error.html", {"message": str(exc)})
    return templates.TemplateResponse(request, "_result.html", {"result": result})
```

- [ ] **Step 2: Result + error fragments.**
`src/glycomass/web/templates/_result.html`:
```html
<div class="result-readout">
  <div><div class="k">Monoisotopic</div><div class="v">{{ "%.4f"|format(result.mono_mz) }}<small>m/z</small></div></div>
  <div><div class="k">Most abundant</div><div class="v">{{ "%.4f"|format(result.most_abundant_mz) }}<small>m/z</small></div></div>
  <div><div class="k">Formula</div><div class="v" style="font-size:.95rem">{{ result.composition }}</div></div>
</div>
<div class="spectrum" data-spectrum='{"mz": {{ result.spectrum.mz|tojson }}, "intensity": {{ result.spectrum.intensity|tojson }}}'></div>
```
`src/glycomass/web/templates/_error.html`:
```html
<div class="error-note">{{ message }}</div>
```

- [ ] **Step 3: Calculator page templates.** Each extends base, shows a form that `hx-post`s to its own URL and swaps the result into `#result`. `src/glycomass/web/templates/glycan.html`:
```html
{% extends "base.html" %}
{% block title %}Free-glycan calculator · GlycoMass{% endblock %}
{% block content %}
<span class="eyebrow">Calculator</span>
<h1 style="font-family:var(--font-display);font-weight:400;font-size:var(--step-3);color:var(--paper);margin:.6rem 0 1.6rem">Free glycan</h1>
<div class="calc-shell">
  <form class="calc-form" hx-post="/glycan" hx-target="#result" hx-swap="innerHTML">
    <div class="calc-grid">
      <div><label>Hex</label><input type="number" name="hex" value="5" min="0"></div>
      <div><label>HexNAc</label><input type="number" name="hexnac" value="4" min="0"></div>
      <div><label>Fuc</label><input type="number" name="fuc" value="0" min="0"></div>
      <div><label>Sia</label><input type="number" name="sia" value="0" min="0"></div>
      <div><label>Charge</label><input type="number" name="charge" value="1"></div>
      <div><label>Modification</label>
        <select name="modification">
          <option>None</option><option>Permethyl</option><option>Peracetly</option>
          <option>ReducedEnd</option><option>Label_2AB</option><option>Label_2AA</option>
        </select>
      </div>
    </div>
    <label style="display:flex;gap:.5rem;align-items:center;text-transform:none;letter-spacing:0">
      <input type="checkbox" name="sodium" value="true" style="width:auto"> Sodium adduct
    </label>
    <button class="btn btn-primary" type="submit">Calculate</button>
  </form>
  <div id="result" class="result-panel"><p style="color:var(--muted)">Enter a composition and calculate.</p></div>
</div>
{% endblock %}
```
`src/glycomass/web/templates/peptide.html` — same structure, form `hx-post="/peptide"`, fields: `sequence` (text input, value "PEPTIDE"), hex/hexnac/fuc/sia/charge (numbers), `deamidation` (number, 0), and a checkbox `carbamidomethyl` (value "true"). Heading "Glycopeptide".
`src/glycomass/web/templates/protein.html` — form `hx-post="/protein"`, fields: `sequence` (text), hex/hexnac/fuc/sia/charge/deamidation/disulfide_bridges (numbers), and `resolution` (`<select>` with options `low`, `medium`, `super high`). Heading "Glycoprotein".

- [ ] **Step 4: Include the pages router** — modify `src/glycomass/web/app.py`: add `from glycomass.web.pages import router as pages_router` and `app.include_router(pages_router)` (after the api router).

- [ ] **Step 5: Write the failing test** `tests/web/test_pages.py`:
```python
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
```

- [ ] **Step 6: Run, verify PASS:** `uv run pytest tests/web/test_pages.py -v --no-cov` (5 passed). Then ruff + mypy. (mypy: FastAPI `Form(False)` for bool is fine; if mypy complains about `bool = Form(False)`, it's accepted — Form returns Any.)

- [ ] **Step 7: Commit:**
```bash
git add src/glycomass/web/pages.py src/glycomass/web/templates src/glycomass/web/app.py tests/web/test_pages.py
git commit -m "feat(web): calculator pages with HTMX forms and uPlot results"
```

---

### Task 5: Landing page

**Files:** Create `src/glycomass/web/templates/index.html`; Modify `tests/web/test_pages.py`.

- [ ] **Step 1: Create `index.html`** extending base. Port the hero + three calculator cards + identifier/API/about sections from `design/glycomass-landing.html`'s `<main>`/section markup into `{% block content %}` (drop the duplicate header/footer — base provides them; drop the inline `<style>`). Make the three calculator cards link to `/peptide`, `/protein`, `/glycan` (replace the `#calculators` anchors). Keep the hero instrument spectrum SVG (it's static decoration). Use the verified hero numbers (mono 1185.428 / most-abundant 1185.929 / C₉₀H₁₄₈N₆O₆₆).

- [ ] **Step 2: Add test** to `tests/web/test_pages.py`:
```python
def test_index_renders_brand_and_links():
    r = client.get("/")
    assert r.status_code == 200
    assert "GlycoMass" in r.text
    assert 'href="/glycan"' in r.text
```

- [ ] **Step 3: Run:** `uv run pytest tests/web/test_pages.py -v --no-cov` (6 passed).

- [ ] **Step 4: Commit:**
```bash
git add src/glycomass/web/templates/index.html tests/web/test_pages.py
git commit -m "feat(web): landing page"
```

---

### Task 6: Full-suite gate, manual smoke, docs

**Files:** Modify `CLAUDE.md`.

- [ ] **Step 1: Full suite + gates.**
Run: `uv run pytest` → all pass, coverage ≥80%.
Run: `uv run mypy` → Success.
Run: `uv run ruff check` → pass.

- [ ] **Step 2: Manual smoke (headless).** Start the server, hit endpoints, stop it:
```bash
uv run glycomass-api &  # or: uv run uvicorn glycomass.web.app:app --port 8000
sleep 3
curl -fsS localhost:8000/api/v1/health
curl -fsS -X POST localhost:8000/api/v1/calculate/glycan -H 'content-type: application/json' -d '{"hex":5,"hexnac":4,"fuc":1,"sia":2,"charge":2}'
curl -fsS localhost:8000/ | head -c 200
kill %1
```
Expected: health `{"status":"ok"}`; glycan returns JSON with `mono_mz` ≈ 1185.4277; `/` returns HTML starting with `<!DOCTYPE html>`. If anything fails, fix before committing.

- [ ] **Step 3: Update `CLAUDE.md`** — under the "## 2026 Rewrite (in progress)" section, append:
```markdown
### Phase 2 — web + API (`src/glycomass/web/`)
- `web/app.py` — `create_app()` factory (`glycomass-api` runs uvicorn on :8000).
- `web/api/v1.py` — JSON: `GET /api/v1/health`, `POST /api/v1/calculate/{peptide,protein,glycan}` → `MassResult`. OpenAPI at `/docs`.
- `web/pages.py` — HTML: `/`, `/peptide`, `/protein`, `/glycan` (HTMX form POST → `_result.html` fragment; uPlot draws the spectrum client-side).
- `config.py` (pydantic-settings, `GLYCOMASS_*`), `logging_config.py` (structlog).
- Static design system in `web/static/css/app.css` (ported from `design/glycomass-landing.html`); HTMX + uPlot vendored under `web/static/vendor/`.
- Run locally: `uv run glycomass-api` → http://localhost:8000 (`/docs` for the API).
```

- [ ] **Step 4: Commit:**
```bash
git add CLAUDE.md
git commit -m "docs: document Phase 2 web + API"
```

---

## Self-Review

**1. Spec coverage (Phase 2 = web + JSON API):** ✅ FastAPI app-factory + lifespan (Task 2); ✅ config via pydantic-settings (Task 0); ✅ structlog (Task 0); ✅ JSON API `/api/v1` with OpenAPI at `/docs` (Task 2); ✅ three calculator HTML pages with Jinja + HTMX + uPlot spectra (Tasks 3–4); ✅ landing page (Task 5); ✅ same `core` called by both UI and API (Tasks 2 & 4 both import from `glycomass.core`); ✅ typed error → friendly HTML / 422 JSON (Tasks 2 & 4). Out of scope (later phases): DB, identifier/worker, permalinks, Kamal deploy, Tailwind build pipeline (using ported static CSS instead — noted deviation).

**2. Placeholder scan:** No TBD/TODO. The only "extract from existing file" steps (CSS in Task 3, landing markup in Task 5) reference a concrete in-repo artifact (`design/glycomass-landing.html`), not an unwritten one. All Python/test/Jinja code is shown in full.

**3. Type consistency:** `MassResult` (from `core`, fields `mono_mz`/`most_abundant_mz`/`composition`/`spectrum.{mz,intensity}`) is the response model in the API and is consumed identically in `_result.html`. Request models (`PeptideRequest`/`ProteinRequest`/`GlycanRequest`) field names match both the `core` function kwargs and the HTML `Form(...)` parameter names (`sequence`, `hex`, `hexnac`, `fuc`, `sia`, `charge`, `carbamidomethyl`, `deamidation`, `disulfide_bridges`, `resolution`, `sodium`, `modification`). `create_app()` / `app` / `main` names match `pyproject` `[project.scripts]` and the test imports. Router `prefix="/api/v1"` matches all test URLs.

**Noted deviations from spec (deliberate):** (a) static hand-authored design-token CSS instead of a Tailwind v4 build — avoids adding a Node toolchain to the Python app/Docker image; the CSS embodies the same OKLCH tokens. Revisit if a Tailwind build is wanted. (b) Alpine.js omitted (YAGNI — HTMX + uPlot cover Phase 2 interactions); add when a real client-side interaction needs it.
