# Glycomass 2026 Rewrite — Design Spec v1

- **Status:** Draft (awaiting author review)
- **Date:** 2026-06-09
- **Deciders:** Christian (owner)
- **Supersedes:** the 2020 Flask app (`app/`, deployed on Heroku at glycomass.com)

---

## 1. Overview

Glycomass is a public web tool for glycan / glycopeptide / glycoprotein
mass-spectrometry calculations. This spec defines a **full rewrite** to a modern
2026 stack, migrating off Heroku to a single netcup VPS, while preserving the
scientific behavior of the existing calculators (verified against captured
ground-truth fixtures).

### Goals
- Modern, maintainable Python codebase mirroring the conventions of the owner's
  FiberQA project (uv, FastAPI, structlog, ruff/mypy/pytest, numbered `docs/`).
- Preserve calculator results exactly (within float tolerance) — proven by the
  Phase 0 fixtures in `fixtures/legacy_masscalc.json`.
- Four capabilities: **3 mass calculators**, a real **glycopeptide identifier**,
  a **public JSON API**, and **shareable permalinks**.
- Interactive client-side m/z spectra (replacing static matplotlib PNGs).
- Self-hosted on one netcup VPS via **Kamal**.

### Non-goals
- **No user accounts / auth** — everything is public. (If accounts are wanted
  later, that is a separate spec; it changes data model, deploy, and middleware.)
- **No multi-tenancy** (unlike FiberQA — drop `TenantBase`).
- No horizontal scaling / multi-node / Kubernetes.
- No payment, email, or analytics beyond optional privacy-friendly page analytics.

---

## 2. Background

The legacy app (see root `CLAUDE.md` for the full analysis) is a Flask 1.1 app
with three working calculators, a large amount of dead/scratch code, committed
secrets, a fragile comma-joined-string return contract, and triplicated chemistry
tables. The scientific core is sound but structurally entangled. The rewrite keeps
the chemistry, discards the rest, and rebuilds on the owner's standard stack.

---

## 3. Tech stack (locked)

| Layer | Choice |
|---|---|
| Language/runtime | Python 3.14, managed with `uv` |
| Web framework | FastAPI (app-factory + lifespan) |
| Templating/UI | Jinja2 + HTMX + Alpine.js + Tailwind v4 (OKLCH design tokens, IBM Plex Sans/Mono) |
| Charts | uPlot (interactive m/z spectra) |
| Background jobs | `arq` worker + Redis |
| Database | PostgreSQL (local container) + SQLAlchemy 2.0 async (asyncpg) + Alembic |
| File storage | Local Docker volume (MGF uploads + results), with retention cleanup |
| Logging | structlog (JSON in prod) |
| Reverse proxy / TLS | kamal-proxy (auto Let's Encrypt) |
| Deploy | **Kamal 2** on a single netcup VPS; Postgres + Redis as Kamal accessories; web + worker roles from one image; GitHub Actions → GHCR → `kamal deploy` |
| Quality | ruff, mypy --strict, pytest (≥80% cov), pre-commit (ruff + gitleaks), `uv lock --check`, Trivy (image), light semgrep, scheduled `pip-audit` |

Conventions are lifted from FiberQA (`backend/pyproject.toml` `[tool.*]` blocks,
Dockerfile multi-stage pattern, structlog setup, Alembic `NAMING_CONVENTION`,
`docs/` taxonomy, `.claude/rules/`). Enterprise extras (SBOM/cosign,
model-governance, parser-gates, multi-language audits, Better Auth) are **not**
carried over.

---

## 4. Architecture

One FastAPI service split into framework-free domain + thin web/worker shells:

```
core/    pure domain: chemistry + identifier logic. No FastAPI, no I/O.
web/     FastAPI: HTML (Jinja+HTMX) routes + /api/v1 JSON routes. Both call core.
worker/  arq tasks (the MGF identifier). Calls core.
db/      SQLAlchemy models, session, Alembic migrations.
```

**Key principle:** the HTML UI and the JSON API are two faces of the *same* `core`
functions. No logic is duplicated between them, and the legacy comma-joined-string
contract is gone — `core` returns typed Pydantic results.

### 4.1 Calculator request flow (synchronous, fast)
1. `GET /peptide|/protein|/glycan` → render form (HTML) via Jinja.
2. `POST` (HTMX) → Pydantic-validate inputs → call `core.peptide_mass()` /
   `core.protein_mass()` / `core.glycan_mass()` → typed result
   `{ mono_mz, most_abundant_mz, composition, spectrum: {mz[], intensity[]} }`.
3. Return an HTML fragment; HTMX swaps the results panel; **uPlot** renders the
   spectrum client-side from the JSON arrays (zoom/pan/hover m/z readout).
4. `GET|POST /api/v1/calculate/{kind}` calls the same `core` function, returns JSON.

### 4.2 Identifier flow (asynchronous)
1. `POST /identifier` multipart MGF upload → validate type/size → store to the
   uploads volume (`uploads/<uuid>.mgf`) → insert `IdentifierJob(status=queued)` →
   enqueue arq task → return a page that HTMX-polls `/identifier/{id}`.
2. Worker loads the file → runs `core.identifier` pipeline → writes
   `results/<uuid>.mgf` → updates `IdentifierJob(status=done, result_path)`.
3. Poll flips to a download link. Failures set `status=failed` + message (never silent).

### 4.3 Permalink flow
On a successful calculation, persist normalized inputs under a short slug;
`GET /c/{slug}` re-computes and re-renders for sharing.

---

## 5. Domain core (the chemistry) — single source of truth

`core/constants.py` holds the **one** canonical element-composition table
(`[C, H, N, O, S]` per residue), eliminating the legacy 3× duplication. Values are
taken verbatim from the deployed `app/masscalc.py` (the fixtures pin them):

**Amino-acid residues** (peptide = Σ residues + 1 H₂O):
`A[3,5,1,1,0] R[6,12,4,1,0] N[4,6,2,2,0] D[4,5,1,3,0] C[3,5,1,1,1] Q[5,8,2,2,0]
E[5,7,1,3,0] G[2,3,1,1,0] H[6,7,3,1,0] I[6,11,1,1,0] L[6,11,1,1,0] K[6,12,2,1,0]
M[5,9,1,1,1] F[9,9,1,1,0] P[5,7,1,1,0] S[3,5,1,2,0] T[4,7,1,2,0] W[11,10,2,1,0]
Y[9,9,1,2,0] V[5,9,1,1,0]`, `H2O[0,2,0,1,0]`, carbamidomethyl-Cys `[5,8,2,2,1]`.

**Monosaccharide residues:** `Hex[6,10,0,5,0] HexNAc[8,13,1,5,0] Fuc[6,10,0,4,0]
Sia[11,17,1,8,0]`. **Deamidation** `[0,-1,-1,1,0]` (per count). **Disulfide bridge**
`[0,2,0,0,0]` *subtracted* per bridge (−2H).

**Glycan modifications** (free glycan = H₂O + Σ monosaccharides, with vector swaps):
- Permethyl: `Hex[9,16,0,5,0] HexNAc[11,19,1,5,0] Fuc[8,14,0,4,0] Sia[16,27,1,8,0]` + `Add[2,4,0,0,0]`
- Peracetyl: `Hex[12,16,0,8,0] HexNAc[12,17,1,7,0] Fuc[10,14,0,6,0] Sia[17,23,1,11,0]` + `Add[4,4,0,2,0]`
- ReducedEnd `+H2[0,2,0,0,0]`; Label_2AB `+[7,8,2,0,0]`; Label_2AA `+[7,7,1,1,0]`.

**Sodium adduct:** shift m/z by `+22.989770/charge − 1/charge` (proton→Na⁺ swap);
guarded out when `charge ≤ 0` (negative-ion mode).

**Isotopic distribution & spectrum:** `core/isotopes.py` wraps **brainpy**
(`isotopic_variants`) to produce the isotope cluster, from which we derive:
- `mono_mz` = m/z of the monoisotopic (first) peak.
- `most_abundant_mz` = m/z of the most-intense isotopologue.
- `spectrum.mz[] / intensity[]` = arrays for uPlot (normalized 0–100).

brainpy is **pinned to `brain-isotopic-distribution==1.5.19`** (latest). It has no
wheel for Python 3.13+, so it compiles from sdist in the Docker **builder** stage
(needs `build-essential`; the slim runtime stage just copies the resulting venv).
Verified 2026-06-09: 1.5.19 builds cleanly on Python 3.14.5 with modern Cython
(no `Cython<3` workaround needed), and reproduces the legacy monoisotopic value
exactly (PEPTIDE C34H53N7O15S0, z=1 → 800.3672, matching the fixture) — i.e. **no
monoisotopic drift** vs the legacy 2017 pin.

### 5.1 Cleanups vs legacy (none change the numbers)
The legacy chemistry is correct; only structural/cosmetic issues are fixed, so the
rewrite should reproduce **all** fixtures within tolerance:
- Consistent intensity normalization across all three calculators (legacy left it
  commented out for protein/glycan — affected only the PNG y-axis, not `mono`/`most_abundant`).
- No server-side matplotlib → fixes the figure-leak bug; spectra render client-side.
- Misspelled identifiers normalized in code (`Peracetly`→`Peracetyl`) while keeping
  fixture mapping. Form values become a typed enum.

---

## 6. Glycopeptide identifier

Port the orphaned `app/firstpart_glycopeptide_identifier.py` research script into a
real, testable `core/identifier/` module (no run-on-import, no hard-coded Windows
paths, no in-place overwrite of input). Pipeline: read MGF (pyteomics) → classify
glycopeptide spectra by oxonium ions → derive peptide-backbone mass from HexNAc
fragment ladders → strip glycan/oxonium peaks → rewrite precursors to the
deglycosylated peptide mass → emit a cleaned MGF for download. Magic numbers
(203.0866 HexNAc, 1.007276 proton, oxonium windows) become named constants. Runs
as an arq job because MGF processing can be slow. Add a small sample-MGF test.

---

## 7. Frontend

- Jinja2 templates with two-level inheritance (`base.html` → pages), Tailwind v4
  built into `web/static`, HTMX for the form→results swap, Alpine for small
  interactions, uPlot for spectra. Reuse FiberQA's OKLCH token palette + IBM Plex.
- SEO preserved (server-rendered, sitemap, meta) — a key reason for HTMX over a SPA.
- Privacy-friendly analytics optional; no UA/GA legacy tags.

---

## 8. Data model (Postgres)

- `identifier_jobs`: `id (uuid)`, `status (queued|running|done|failed)`,
  `upload_path`, `result_path`, `error`, `created_at`, `updated_at`.
- `permalinks`: `slug`, `kind (peptide|protein|glycan)`, `inputs (jsonb)`,
  `created_at`. (Slug derived from a hash of normalized inputs.)

Alembic migrations under `alembic/`, run on deploy. SQLAlchemy `NAMING_CONVENTION`
copied from FiberQA. No tenant columns.

---

## 9. Deploy & ops (Kamal)

- **One image, two roles:** `web` (uvicorn/gunicorn-uvicorn) and `worker` (arq),
  both from the same multi-stage uv Dockerfile (non-root user, healthcheck).
- **Accessories:** Postgres and Redis run as Kamal accessories on the VPS.
- **Files:** a host-mounted volume for `uploads/` + `results/`, with a retention/
  cleanup job (TTL on old uploads/results).
- **TLS/proxy:** kamal-proxy obtains Let's Encrypt certs for glycomass.com.
- **Secrets:** `.kamal/secrets` sourced from env (DB URL, `SECRET_KEY`, etc.);
  GitHub Actions holds registry + deploy SSH creds. **Nothing sensitive committed.**
- **CI/CD:** GitHub Actions on push to main → build & push image to GHCR →
  `kamal deploy`. Migrations (`alembic upgrade head`) run as a pre-deploy step.
- **Cutover:** build → validate fixture parity → deploy to netcup alongside Heroku
  → smoke test → repoint glycomass.com DNS → decommission Heroku.

---

## 10. Security & secrets (cleanup of legacy exposure)

- The legacy `config.py` (committed despite `.gitignore`) leaks a `SECRET_KEY`
  fallback and AWS-key-shaped strings. **Action:** rotate/deactivate those AWS keys
  in the console, generate a fresh app `SECRET_KEY`, and never commit secrets again.
- All config via env → `pydantic-settings` (`GLYCOMASS_*` prefix). gitleaks in
  pre-commit + CI.

---

## 11. Testing strategy

- **Golden chemistry tests (the anchor):** `tests/test_chemistry.py` loads
  `fixtures/legacy_masscalc.json` (37 ground-truth cases captured from the deployed
  code) and asserts `core` reproduces `mono_mz` / `most_abundant_mz` / `composition`
  within tolerance (~1e-3 on m/z; composition exact). An explicit allow-list covers
  any fixture we *deliberately* change (currently expected to be empty).
- Identifier: sample-MGF test of the pipeline.
- API: schema/contract smoke tests via FastAPI TestClient.
- Web: a few route smoke tests (form renders, POST returns results fragment).
- Gates: ruff, mypy --strict on `src/glycomass`, pytest ≥80% coverage.

---

## 12. Repo layout

```
glycomass/
  pyproject.toml  uv.lock  Dockerfile
  config/deploy.yml          # Kamal: web+worker roles, postgres+redis accessories
  .kamal/secrets
  alembic/                   # migrations
  src/glycomass/
    core/   constants.py peptide.py protein.py glycan.py isotopes.py identifier/
    web/    app.py pages.py api/v1/ templates/ static/
    worker/ tasks.py settings.py
    db/     models.py session.py
    schemas.py  config.py
  frontend/                  # Tailwind v4 source → built into web/static
  fixtures/legacy_masscalc.json     # Phase 0 ground truth (DONE)
  tools/legacy-fixtures/            # Dockerfile + gen_fixtures.py (reproducibility)
  tests/
  docs/                      # numbered taxonomy (this spec lives in 03_specs)
  CLAUDE.md  .claude/rules/
```

---

## 13. Dropped from legacy

All dead/scratch code (`s3_demo.py`, `models.py`, `tasks.py`, `proteincalc_temp.py`,
`app/temp`, `idiot.html`, `with-footer.html`, the import-time identifier script, the
empty `git` file), the matplotlib/Flask/Bootstrap3/Talisman runtime deps, the
comma-joined-string contract, the RQ demo endpoints, committed secrets, and the
broken `os.environ.get("AKIA…")` S3 indirection.

---

## 14. Phased implementation roadmap

- **Phase 0 — Ground truth (DONE):** `fixtures/legacy_masscalc.json` captured from
  the deployed stack via `tools/legacy-fixtures/`.
- **Phase 1 — Core + golden tests:** `core/` chemistry (shared constants, the three
  mass functions, brainpy isotopes) passing the fixtures. Pure, framework-free.
- **Phase 2 — Web + JSON API:** FastAPI app-factory, calculator HTML routes
  (Jinja+HTMX+uPlot) and `/api/v1`, structlog, config. No DB yet.
- **Phase 3 — Identifier + worker:** `core/identifier/`, Postgres `identifier_jobs`,
  arq worker, upload→job→poll→download flow, file volume.
- **Phase 4 — Permalinks:** `permalinks` table + `/c/{slug}`.
- **Phase 5 — Deploy:** Kamal config, Dockerfile, accessories, GHA pipeline, TLS,
  secret rotation, DNS cutover, decommission Heroku.

CI/quality scaffolding (ruff/mypy/pytest/pre-commit, `.claude/rules`, `CLAUDE.md`)
is established in Phase 1 and enforced thereafter.

---

## 15. Open questions / future work

- brainpy pinned to 1.5.19; monoisotopic parity vs legacy confirmed. Still to do:
  validate `most_abundant_mz` across the full fixture set during Phase 1 and set
  per-field tolerances.
- Permalink slug strategy (hash vs random short id) and whether to cache results.
- Identifier result retention policy (TTL) and max upload size.
- Optional: privacy-friendly analytics choice.
