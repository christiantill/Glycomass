# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Glycomass is a Flask web app that computes theoretical masses / isotopic m/z spectra for
glycans, (glyco)peptides, and (glyco)proteins from a sequence + glycan composition. It is
deployed to Heroku (autodeploy from `master`) and served at glycomass.com. Python ~3.7 era;
the dependency stack in `requirements.txt` is pinned to that era and newer numpy/matplotlib
may break the list/array arithmetic in `masscalc.py`.

## Commands

```bash
pip install -r requirements.txt        # needs `git` on PATH: brainpy installs from a pinned git commit
FLASK_APP=glycomass.py flask run       # local dev server
gunicorn glycomass:app                 # production process (this is the entire Procfile)
```

- **WSGI entry point** is `glycomass:app` — i.e. the module-level `app` from `app/__init__.py`, **not** `create_app()`.
- **No test suite, linter config, or build step exists.** There is no npm/webpack — all frontend assets come from Flask-Bootstrap (Bootstrap 3) or CDNs.
- **Headless deploy needs `MPLBACKEND=Agg`** — the code never calls `matplotlib.use('Agg')`, so a server worker can fail or leak figures without it.
- Env vars: `SECRET_KEY`, `LOG_TO_STDOUT`, `S3_BUCKET`/`S3_KEY`/`S3_SECRET`, and for Redis `REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD` (note: `config.py`'s `REDIS_URL` is defined but **nothing reads it** — `redis_resc.py` uses its own host/port/password vars).

## Architecture: the core calculation flow

The product is three near-identical request flows. Tracing one requires reading across
`routes.py` → `forms.py` → `masscalc.py` → a template:

1. `GET /peptide_calculate | /protein_calculate | /glycan_calculate` renders the form-only view.
2. `POST` runs Flask-WTF `validate_on_submit()` (CSRF via `SECRET_KEY`), then the route **casts the WTForms `FloatField`s to `int`** and calls the matching function in `app/masscalc.py`: `peptidemass()`, `proteinmass()`, or `glycanmass()`.
3. **Critical cross-module contract:** each masscalc function returns a *single comma-joined string*. Every route does `result.split(',')` into exactly four positional fields `[monomz, mostab, plot_url, composition]` (e.g. `routes.py:78-82`). `plot_url` is a base64 PNG embedded directly in the page as `data:image/png;base64,...`. This is brittle and key-less — adding a field or letting any field contain a comma breaks all callers.
4. The template uses Jinja `{% if monomz is defined %}` (and `negative_ion`/`cystein_residues`) to toggle between the empty-form and results views. There is **no JSON API and no DB** for these calculations; compute runs **synchronously in the request**.

The mass model (`masscalc.py`): every amino acid and monosaccharide is a hardcoded
`[C, H, N, O, S]` count vector. Total = sum(residue vectors) + one H2O + modifications.
Numeric mass and the isotope envelope are **not** computed here — they are delegated to
**brainpy** (`isotopic_variants`), then convolved with a Gaussian and plotted with matplotlib.

Template inheritance is two levels: page → `base.html` (navbar + Google Analytics) → Flask-Bootstrap's `bootstrap/base.html`. All calculator forms render via `wtf.quick_form(form)`; do not hand-roll form fields.

## High-value gotchas (read before editing)

- **App is a module-level singleton, not a factory.** `app/__init__.py` builds `app = Flask(...)` at import time and that is the live object (routes/errors do `from app import app`). `create_app()` exists but only bolts logging onto the same global app, ignores its `config_class` arg, and is called only by dead code — so its `logs/glycomass.log` setup never runs in production.
- **String literals must match between `forms.py` and `masscalc.py` exactly, including misspellings.** The glycan modification value is `'Peracetly'` (sic) and the protein resolution is `'super high'`. The `masscalc` branches compare against these exact strings; "fixing" the spelling in one place silently disables the branch.
- **Route function typo:** the identifier endpoint function is `glyan_identifier` (missing the `c`) at `routes.py:31`, even though its URL is `/glycan_identifier`. `url_for` must use `'glyan_identifier'`.
- **Secrets are committed.** `config.py` is in `.gitignore` yet tracked, and contains a hardcoded `SECRET_KEY` fallback plus AWS-key-shaped strings. Worse, `S3_KEY`/`S3_SECRET` pass the *credential value as the env-var name* (`os.environ.get("AKIA...")`), so they resolve to `None` and S3 auth is broken as written. Treat the committed strings as exposed/needing rotation; never copy secrets into new files or commits.
- **Charge has no validator** (`forms.py`) — negative/huge charges pass form validation.
- `helper.upload_file_to_s3` **returns the exception object on failure** instead of raising, so a caller can receive an `Exception` where a URL string is expected. Uploads use `public-read` ACL.

## Two async systems, only one wired up

- **Working:** `redis_resc.py` (Redis + RQ `Queue`) + `rd_func.some_long_function` (a 10s sleep demo) exposed via `/enqueue`, `/check_status`, `/get_result`. This is scaffolding — it does no real glyco work, and the **Procfile defines no worker process**, so even this has no consumer in production.
- **Dead (do not extend):** `app/models.py` and `app/tasks.py` are a copied Flask-Mega-Tutorial DB-backed task/progress/notification system. They reference a `db` object that is never created, `current_app.redis`/`current_app.task_queue` that are never set, and **SQLAlchemy, which is not in `requirements.txt`** — `models.py` cannot even be imported as-is.

The heavy compute (`masscalc`) is **never offloaded to a queue**; it runs inline in the request handlers.

## Dead / scratch code (ignore unless explicitly cleaning up)

Treat the following as orphaned — none is reachable from `glycomass:app`. Don't use them as references; several are stale and chemically inconsistent with production.

- `proteincalc_temp.py` (repo root): scratch prototype of `proteinmass` with a hardcoded peptide; `print()`/`plt.show()` instead of returning; its deamidation vector has the *opposite sign* of `masscalc.py` and it has a list-vs-array multiplication bug.
- `app/firstpart_glycopeptide_identifier.py`: an offline MGF-processing research script (inverse problem: spectrum → inferred peptide/glycan mass). **Runs its full pipeline on import** (no `__main__` guard), uses a hardcoded Windows path that is *both input and output* (overwrites the source), and imports `pyteomics`, which is not in `requirements.txt`. The `/glycan_identifier` route does **not** call it — it only uploads the file to S3.
- `app/s3_demo.py` (superseded by `helper.py`), `app/temp` (a corrupted scratch dump, no extension), the empty file named `git`, committed `__pycache__/`, and templates `idiot.html` + `with-footer.html` (the latter is the only template with a footer, so no footer renders site-wide).
- `identifier.html`'s upload `<form>` posts to `action="/"` rather than `/glycan_identifier` — a known mismatch.

## Notable duplication

The full amino-acid + monosaccharide `[C,H,N,O,S]` table is re-declared inline inside
`peptidemass`, `proteinmass`, *and* `proteincalc_temp.py` (no shared constants module). Any
element-vector fix must be made in 2–3 places. The glycopeptide identifier duplicates the same
monosaccharide knowledge again with no shared code.

## 2026 Rewrite (in progress)

The rewrite lives under `src/glycomass/` (FastAPI app to come). Phase 1 delivers the
framework-free domain core in `src/glycomass/core/`:

- `composition.py` — `Composition` `[C,H,N,O,S]` value object.
- `constants.py` — the SINGLE element/monosaccharide table (replaces the legacy 3× duplication).
- `isotopes.py` — brainpy wrapper → mono m/z, most-abundant m/z, stick spectrum.
- `peptide.py` / `protein.py` / `glycan.py` — the three calculators returning a typed `MassResult`.

**Commands:**
- `uv sync --extra dev` — install (builds brainpy from sdist; needs a C compiler).
- `uv run pytest` — tests + coverage (golden parity in `tests/test_golden.py`).
- `uv run mypy` / `uv run ruff check` — types / lint.

**Ground truth:** `fixtures/legacy_masscalc.json` (Phase 0) pins the deployed results;
`tests/test_golden.py` asserts the core reproduces them within 1e-3. Regenerate via
`tools/legacy-fixtures/`. Do not loosen the tolerance to make a test pass.

### Phase 2 — web + API (`src/glycomass/web/`)
- `web/app.py` — `create_app()` factory (`glycomass-api` runs uvicorn on :8000).
- `web/api/v1.py` — JSON: `GET /api/v1/health`, `POST /api/v1/calculate/{peptide,protein,glycan}` → `MassResult`. OpenAPI at `/docs`.
- `web/pages.py` — HTML: `/`, `/peptide`, `/protein`, `/glycan` (HTMX form POST → `_result.html` fragment; uPlot draws the spectrum client-side).
- `config.py` (pydantic-settings, `GLYCOMASS_*`), `logging_config.py` (structlog).
- Static design system in `web/static/css/app.css` (ported from `design/glycomass-landing.html`); HTMX + uPlot vendored under `web/static/vendor/`.
- Run locally: `uv run glycomass-api` → http://localhost:8000 (`/docs` for the API).

### Phase 3 — glycopeptide identifier (`src/glycomass/core/identifier/`, `db/`, `worker/`, `web/identifier.py`)
- `core/identifier/pipeline.py` — pure MGF logic: classify glycopeptide spectra (oxonium windows), find the Pep+HexNAc fragment (NOTE: corrected vs the legacy *lower*-peak double-count bug — selects the higher peak of a HexNAc-separated pair, m/z > 700), peptide mass = fragment − 203.0866, strip glycan/oxonium peaks, rewrite each precursor to (peptide_mass, charge 1). **No legacy ground truth exists for the identifier** — tested structurally on `tests/identifier/sample.mgf`.
- `db/` — async SQLAlchemy `IdentifierJob` (Postgres prod / aiosqlite tests); `make_sessionmaker` uses `StaticPool` for in-memory SQLite. Alembic config in `alembic/` + `alembic.ini`.
- `worker/` — `arq` task `identifier_task` → `run_identifier_job` (process MGF, update job row; `tasks.py` is arq-independent and unit-tested directly).
- `web/identifier.py` — `/identifier` upload (enforces `max_upload_bytes`, streams to disk) → enqueue; `/identifier/{id}` HTMX-polls status; `/identifier/{id}/download`.
- Local infra: `docker compose -f docker-compose.dev.yml up -d` (Postgres+Redis); `uv run alembic upgrade head`; `uv run arq glycomass.worker.settings.WorkerSettings` (worker); `uv run glycomass-api` (web). Tests run on aiosqlite + a synchronous arq stub (no Redis needed); the Postgres+Redis+arq path is validated by the integration smoke.
