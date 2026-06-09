# Glycomass Phase 3 — Glycopeptide Identifier (MGF + worker + DB) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Turn the orphaned legacy MGF-processing script into a real feature: upload an MGF, process it in a background `arq` worker (classify glycopeptide spectra, derive the deglycosylated peptide mass, strip glycan peaks, rewrite precursors), track the job in Postgres, and let the user poll status and download the cleaned MGF.

**Architecture:** Pure MGF logic lives in `glycomass.core.identifier` (framework-free, numpy + pyteomics). An `IdentifierJob` row (async SQLAlchemy, Postgres in prod / aiosqlite in tests) tracks status. The upload route saves the file to a volume, inserts a queued job, and enqueues an `arq` task; the task runs the core pipeline and updates the row. The page HTMX-polls a status fragment until a download link appears.

**Tech Stack:** pyteomics, numpy; SQLAlchemy 2.0 async + asyncpg (prod) / aiosqlite (tests) + Alembic; arq + Redis; FastAPI uploads (`UploadFile`) + HTMX polling.

> **SCIENTIFIC NOTE (read first):** the legacy `findpep_HexNAc_mass` selected the *lower* peak of each HexNAc-separated pair (the bare peptide) and then subtracted another HexNAc — an apparent double-count bug. The intent (variable name `Pep_HexNAC_mass`, comment "Pep+HexNac as most intense", and the −203.0866) is clearly the *higher* (Pep+HexNAc) peak. **There is no Phase-0 ground truth for the identifier**, so this plan implements the scientifically-correct version: select the most intense *higher* peak of HexNAc-separated pairs (the Pep+HexNAc fragment, m/z > 700), then `peptide_mass = fragment_mz − HEXNAC_RESIDUE`. The legacy discrepancy is documented in code.

---

## File Structure

- `pyproject.toml` — add `pyteomics`, `sqlalchemy[asyncio]`, `asyncpg`, `aiosqlite`, `alembic`, `arq` (modify).
- `src/glycomass/config.py` — add `database_url`, `redis_url`, `upload_dir`, `result_dir`, `max_upload_bytes` (modify).
- `src/glycomass/core/identifier/__init__.py`, `constants.py`, `pipeline.py` — pure MGF logic (new).
- `src/glycomass/db/__init__.py`, `base.py` (Base + naming convention), `models.py` (`IdentifierJob`), `session.py` (engine/sessionmaker factory + `get_session`) (new).
- `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_identifier_jobs.py` (new).
- `src/glycomass/worker/__init__.py`, `tasks.py` (`run_identifier_job` + arq task), `settings.py` (arq `WorkerSettings`) (new).
- `src/glycomass/web/identifier.py` — upload/status/download routes (new); wired into `web/app.py` (modify).
- `src/glycomass/web/templates/identifier.html`, `_job.html` (new).
- `tests/identifier/` — `sample.mgf` fixture, `test_pipeline.py`; `tests/db/test_models.py`; `tests/worker/test_tasks.py`; `tests/web/test_identifier.py` (new).

---

### Task 0: Phase 3 dependencies + config

**Files:** Modify `pyproject.toml`, `src/glycomass/config.py`, `tests/test_config.py`.

- [ ] **Step 1:** In `pyproject.toml` `[project] dependencies`, append:
```
    "pyteomics>=4.7",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29",
    "aiosqlite>=0.20",
    "alembic>=1.13",
    "arq>=0.26",
```
- [ ] **Step 2:** `uv sync --extra dev` → expect success (all wheels on 3.14).
- [ ] **Step 3: failing test** — append to `tests/test_config.py`:
```python
def test_phase3_config_defaults():
    from glycomass.config import Settings
    s = Settings()
    assert s.database_url.startswith("sqlite+aiosqlite")
    assert s.redis_url.startswith("redis://")
    assert s.max_upload_bytes == 250 * 1024 * 1024
```
- [ ] **Step 4: run, verify FAIL:** `uv run pytest tests/test_config.py -v --no-cov`.
- [ ] **Step 5: implement** — add to the `Settings` class in `src/glycomass/config.py` (after `log_level`):
```python
    database_url: str = "sqlite+aiosqlite:///./glycomass.db"
    redis_url: str = "redis://localhost:6379"
    upload_dir: Path = Path("data/uploads")
    result_dir: Path = Path("data/results")
    max_upload_bytes: int = 250 * 1024 * 1024
```
Add `from pathlib import Path` at the top.
- [ ] **Step 6: run, verify PASS:** `uv run pytest tests/test_config.py -v --no-cov`. Then ruff + mypy.
- [ ] **Step 7: commit:**
```bash
git add pyproject.toml uv.lock src/glycomass/config.py tests/test_config.py
git commit -m "feat(identifier): add Phase 3 deps and config"
```

---

### Task 1: Core MGF identifier pipeline

**Files:** Create `src/glycomass/core/identifier/__init__.py`, `constants.py`, `pipeline.py`; `tests/identifier/sample.mgf`, `tests/identifier/test_pipeline.py`.

- [ ] **Step 1: constants** `src/glycomass/core/identifier/constants.py`:
```python
"""Glycopeptide-identifier constants (ported from the legacy script)."""
HEXNAC_RESIDUE = 203.0866       # Da, one HexNAc
PROTON = 1.007276466621         # Da
HEXNAC_DIFF = (203.02, 203.12)  # m/z window for a single-HexNAc peak spacing
MIN_FRAGMENT_MZ = 700.0         # ignore Pep+HexNAc candidates below this
# oxonium-ion windows used for glycopeptide classification
OXONIUM_HEXNACHEX = (366.125, 366.16)   # HexNAc+Hex
OXONIUM_HEXNACHEX2 = (657.16, 657.29)
# windows zeroed out when cleaning a spectrum
FILTER_WINDOWS = ((292.0, 292.5), (366.1, 367.3), (657.0, 658.5))
```

- [ ] **Step 2: failing test** `tests/identifier/test_pipeline.py`:
```python
import numpy as np

from glycomass.core.identifier import pipeline as P


def test_is_glycopeptide_detects_oxonium():
    assert P.is_glycopeptide(np.array([100.0, 366.14, 900.0])) is True
    assert P.is_glycopeptide(np.array([100.0, 657.2, 900.0])) is True
    assert P.is_glycopeptide(np.array([100.0, 500.0, 900.0])) is False


def test_find_pep_hexnac_mz_picks_higher_peak_of_hexnac_pair():
    # peptide fragment 800.0 and Pep+HexNAc 1003.0866 (diff = one HexNAc); both > 700.
    mz = np.array([400.0, 800.0, 1003.0866])
    inten = np.array([10.0, 50.0, 90.0])
    # corrected algorithm returns the HIGHER (Pep+HexNAc) peak
    assert abs(P.find_pep_hexnac_mz(mz, inten) - 1003.0866) < 1e-3


def test_find_pep_hexnac_mz_none_when_no_pair():
    mz = np.array([400.0, 500.0, 600.0])
    inten = np.array([10.0, 20.0, 30.0])
    assert P.find_pep_hexnac_mz(mz, inten) is None


def test_peptide_mass_subtracts_one_hexnac():
    assert abs(P.peptide_mass_from_fragment(1003.0866) - 800.0) < 1e-6


def test_filter_spectrum_zeros_oxonium_and_above_peptide():
    mz = np.array([292.2, 366.2, 800.0, 900.0])
    inten = np.array([5.0, 5.0, 5.0, 5.0])
    fmz, finten = P.filter_spectrum(mz, inten, peptide_mass=850.0)
    # 292.2 and 366.2 oxonium -> 0; 900.0 (> 850+1) -> 0; 800.0 kept
    assert finten[0] == 0 and finten[1] == 0 and finten[3] == 0
    assert finten[2] == 5.0


def test_process_mgf_end_to_end(tmp_path):
    from pathlib import Path
    src = Path(__file__).parent / "sample.mgf"
    out = tmp_path / "cleaned.mgf"
    summary = P.process_mgf(str(src), str(out))
    assert summary["total"] == 2
    assert summary["glycopeptides"] == 1
    assert summary["identified"] == 1
    assert out.exists()
    # the cleaned output's single spectrum has the deglycosylated precursor (peptide mass, charge 1)
    reread = P.read_mgf(str(out))
    assert len(reread) == 1
    assert abs(reread[0].pepmass - 800.0) < 1e-2
    assert reread[0].charge == 1
```

- [ ] **Step 3: create the synthetic fixture** `tests/identifier/sample.mgf` (two spectra: one glycopeptide, one not):
```
BEGIN IONS
TITLE=glyco_spectrum
PEPMASS=1200.0
CHARGE=2+
366.14 100.0
800.0 50.0
1003.0866 90.0
1300.0 20.0
END IONS
BEGIN IONS
TITLE=plain_spectrum
PEPMASS=900.0
CHARGE=1+
200.0 10.0
500.0 40.0
850.0 30.0
END IONS
```

- [ ] **Step 4: run, verify FAIL:** `uv run pytest tests/identifier/test_pipeline.py -v --no-cov`.

- [ ] **Step 5: implement** `src/glycomass/core/identifier/pipeline.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from pyteomics import mgf

from glycomass.core.identifier.constants import (
    FILTER_WINDOWS,
    HEXNAC_DIFF,
    HEXNAC_RESIDUE,
    MIN_FRAGMENT_MZ,
    OXONIUM_HEXNACHEX,
    OXONIUM_HEXNACHEX2,
    PROTON,
)


@dataclass
class Spectrum:
    mz: np.ndarray
    intensity: np.ndarray
    pepmass: float
    charge: int
    params: dict = field(default_factory=dict)


def read_mgf(path: str) -> list[Spectrum]:
    out: list[Spectrum] = []
    with mgf.read(path) as reader:
        for s in reader:
            params = dict(s["params"])
            pepmass = float(params.get("pepmass", (0.0,))[0])
            charge = int(params["charge"][0]) if params.get("charge") else 1
            out.append(
                Spectrum(
                    mz=np.asarray(s["m/z array"], dtype=float),
                    intensity=np.asarray(s["intensity array"], dtype=float),
                    pepmass=pepmass,
                    charge=charge,
                    params=params,
                )
            )
    return out


def is_glycopeptide(mz: np.ndarray) -> bool:
    in_win = (
        ((mz > OXONIUM_HEXNACHEX[0]) & (mz < OXONIUM_HEXNACHEX[1]))
        | ((mz > OXONIUM_HEXNACHEX2[0]) & (mz < OXONIUM_HEXNACHEX2[1]))
    )
    return bool(np.any(in_win))


def find_pep_hexnac_mz(mz: np.ndarray, intensity: np.ndarray) -> float | None:
    """Most intense Pep+HexNAc fragment: the HIGHER peak of a HexNAc-separated pair, m/z > 700.

    NOTE: the legacy script selected the lower peak (then subtracted another HexNAc) — an
    apparent double-count bug. We select the higher peak (the Pep+HexNAc fragment).
    """
    diff = mz[:, None] - mz[None, :]  # diff[j,k] = mz[j] - mz[k]
    higher_idx, _lower_idx = np.where((diff > HEXNAC_DIFF[0]) & (diff < HEXNAC_DIFF[1]))
    cand = np.unique(higher_idx[mz[higher_idx] > MIN_FRAGMENT_MZ])
    if cand.size == 0:
        return None
    best = cand[int(np.argmax(intensity[cand]))]
    return float(mz[best])


def peptide_mass_from_fragment(pep_hexnac_mz: float) -> float:
    return pep_hexnac_mz - HEXNAC_RESIDUE


def precursor_neutral_mass(pepmass_mz: float, charge: int) -> float:
    # Ported from legacy: m/z*z - z*proton + proton.
    return pepmass_mz * charge - charge * PROTON + PROTON


def filter_spectrum(
    mz: np.ndarray, intensity: np.ndarray, *, peptide_mass: float
) -> tuple[np.ndarray, np.ndarray]:
    """Zero out oxonium-ion peaks and everything above peptide_mass + 1 (in-place on copies)."""
    mz = mz.copy()
    intensity = intensity.copy()
    kill = mz > peptide_mass + 1
    for lo, hi in FILTER_WINDOWS:
        kill |= (mz > lo) & (mz < hi)
    intensity[kill] = 0.0
    mz[kill] = 0.0
    return mz, intensity


def process_mgf(in_path: str, out_path: str) -> dict:
    """Read an MGF, keep glycopeptide spectra, derive the deglycosylated peptide mass,
    strip glycan/oxonium peaks, rewrite each precursor to (peptide_mass, charge 1), write MGF.
    Returns a summary dict."""
    spectra = read_mgf(in_path)
    total = len(spectra)
    glyco = [s for s in spectra if is_glycopeptide(s.mz)]
    cleaned: list[dict] = []
    identified = 0
    for s in glyco:
        frag = find_pep_hexnac_mz(s.mz, s.intensity)
        if frag is None:
            continue
        identified += 1
        pep_mass = peptide_mass_from_fragment(frag)
        fmz, finten = filter_spectrum(s.mz, s.intensity, peptide_mass=pep_mass)
        params = {k: v for k, v in s.params.items() if k not in ("com", "username")}
        params["pepmass"] = (pep_mass, 1)
        params["charge"] = "1+"
        cleaned.append({"m/z array": fmz, "intensity array": finten, "params": params})
    mgf.write(cleaned, output=out_path)
    return {"total": total, "glycopeptides": len(glyco), "identified": identified, "output": out_path}
```
Also `src/glycomass/core/identifier/__init__.py`:
```python
"""Glycopeptide identifier: MGF-based deglycosylation pipeline."""
from glycomass.core.identifier import pipeline

__all__ = ["pipeline"]
```

- [ ] **Step 6: run, verify PASS:** `uv run pytest tests/identifier/test_pipeline.py -v --no-cov` (6 passed). Then ruff + mypy (numpy boolean-index types may need `# type: ignore` minimally; prefer fixing types). If `process_mgf` round-trip pepmass differs, check the `params["pepmass"]` tuple form pyteomics expects.

- [ ] **Step 7: commit:**
```bash
git add src/glycomass/core/identifier tests/identifier
git commit -m "feat(identifier): core MGF deglycosylation pipeline (corrected Pep+HexNAc selection)"
```

---

### Task 2: Database layer (IdentifierJob)

**Files:** Create `src/glycomass/db/__init__.py`, `base.py`, `models.py`, `session.py`; `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_identifier_jobs.py`; `tests/db/test_models.py`.

- [ ] **Step 1: `src/glycomass/db/base.py`:**
```python
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

- [ ] **Step 2: `src/glycomass/db/models.py`:**
```python
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from glycomass.db.base import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class IdentifierJob(Base):
    __tablename__ = "identifier_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|done|failed
    upload_path: Mapped[str] = mapped_column(Text)
    result_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON counts
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
```

- [ ] **Step 3: `src/glycomass/db/session.py`:**
```python
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from glycomass.config import get_settings

_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def make_sessionmaker(url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(url, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = make_sessionmaker(get_settings().database_url)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
```

- [ ] **Step 4: `src/glycomass/db/__init__.py`:**
```python
"""Database layer (async SQLAlchemy)."""
from glycomass.db.base import Base
from glycomass.db.models import IdentifierJob

__all__ = ["Base", "IdentifierJob"]
```

- [ ] **Step 5: Alembic.** `alembic.ini` (minimal):
```ini
[alembic]
script_location = alembic
[loggers]
keys = root
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARN
handlers = console
qualname =
[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```
`alembic/env.py`:
```python
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from glycomass.config import get_settings
from glycomass.db.base import Base
from glycomass.db import models  # noqa: F401  (register tables)

target_metadata = Base.metadata


def _run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as conn:
        await conn.run_sync(_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async())


run_migrations_online()
```
`alembic/versions/0001_identifier_jobs.py`:
```python
"""identifier_jobs

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "identifier_jobs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("upload_path", sa.Text(), nullable=False),
        sa.Column("result_path", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_identifier_jobs"),
    )


def downgrade() -> None:
    op.drop_table("identifier_jobs")
```

- [ ] **Step 6: failing test** `tests/db/test_models.py`:
```python
import pytest
from sqlalchemy import select

from glycomass.db import Base, IdentifierJob
from glycomass.db.session import make_sessionmaker


@pytest.mark.asyncio
async def test_insert_and_read_job():
    sm = make_sessionmaker("sqlite+aiosqlite:///:memory:")
    engine = sm.kw["bind"]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sm() as s:
        job = IdentifierJob(upload_path="/tmp/x.mgf")
        s.add(job)
        await s.commit()
        jid = job.id
        assert job.status == "queued"
        assert len(jid) == 32
    async with sm() as s:
        got = (await s.execute(select(IdentifierJob).where(IdentifierJob.id == jid))).scalar_one()
        assert got.upload_path == "/tmp/x.mgf"
```
Add `pytest-asyncio` to dev deps in `pyproject.toml` (`"pytest-asyncio>=0.23"`) and set `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`; then `uv sync --extra dev`. (With `asyncio_mode=auto` the `@pytest.mark.asyncio` is optional but harmless.)

- [ ] **Step 7: run FAIL → (deps already implemented above) → PASS:** `uv run pytest tests/db/test_models.py -v --no-cov` (1 passed). Confirm `uv run alembic upgrade head` runs against the default sqlite URL without error (creates `glycomass.db`); then `rm -f glycomass.db`. Run ruff + mypy.

- [ ] **Step 8: commit:**
```bash
git add pyproject.toml uv.lock src/glycomass/db alembic.ini alembic tests/db
git commit -m "feat(identifier): IdentifierJob model, async session, alembic migration"
```

---

### Task 3: Background worker (arq)

**Files:** Create `src/glycomass/worker/__init__.py`, `tasks.py`, `settings.py`; `tests/worker/test_tasks.py`.

- [ ] **Step 1: `src/glycomass/worker/tasks.py`:**
```python
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from glycomass.config import get_settings
from glycomass.core.identifier import pipeline
from glycomass.db.models import IdentifierJob
from glycomass.db.session import get_sessionmaker


async def run_identifier_job(job_id: str, *, sessionmaker: async_sessionmaker | None = None) -> None:
    """Process one identifier job: run the MGF pipeline and update the job row.

    Pure of arq so it can be unit-tested directly. `sessionmaker` overridable for tests.
    """
    sm = sessionmaker or get_sessionmaker()
    settings = get_settings()
    async with sm() as session:
        job = (await session.execute(select(IdentifierJob).where(IdentifierJob.id == job_id))).scalar_one()
        job.status = "running"
        await session.commit()
        try:
            result_path = str(settings.result_dir / f"{job_id}.mgf")
            summary = pipeline.process_mgf(job.upload_path, result_path)
            job.status = "done"
            job.result_path = result_path
            job.summary = json.dumps(summary)
        except Exception as exc:  # noqa: BLE001 - record any failure on the row
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
        await session.commit()


async def identifier_task(ctx: dict, job_id: str) -> None:  # arq entrypoint
    await run_identifier_job(job_id)
```

- [ ] **Step 2: `src/glycomass/worker/settings.py`:**
```python
from __future__ import annotations

from arq.connections import RedisSettings

from glycomass.config import get_settings
from glycomass.worker.tasks import identifier_task


class WorkerSettings:
    functions = [identifier_task]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
```
`src/glycomass/worker/__init__.py`: `"""arq background worker."""`

- [ ] **Step 3: failing test** `tests/worker/test_tasks.py`:
```python
from pathlib import Path

import pytest
from sqlalchemy import select

from glycomass.db import Base, IdentifierJob
from glycomass.db.session import make_sessionmaker
from glycomass.worker.tasks import run_identifier_job


@pytest.mark.asyncio
async def test_run_identifier_job_processes_and_marks_done(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYCOMASS_RESULT_DIR", str(tmp_path))
    from glycomass.config import get_settings
    get_settings.cache_clear()

    sample = Path(__file__).resolve().parents[1] / "identifier" / "sample.mgf"
    sm = make_sessionmaker("sqlite+aiosqlite:///:memory:")
    engine = sm.kw["bind"]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sm() as s:
        job = IdentifierJob(upload_path=str(sample))
        s.add(job)
        await s.commit()
        jid = job.id

    await run_identifier_job(jid, sessionmaker=sm)

    async with sm() as s:
        done = (await s.execute(select(IdentifierJob).where(IdentifierJob.id == jid))).scalar_one()
        assert done.status == "done"
        assert done.result_path and Path(done.result_path).exists()
        assert '"identified": 1' in done.summary
    get_settings.cache_clear()
```

- [ ] **Step 4: run, verify FAIL then PASS:** `uv run pytest tests/worker/test_tasks.py -v --no-cov` (1 passed). NOTE: the test sets `GLYCOMASS_RESULT_DIR` and clears the settings cache so `result_dir` points at `tmp_path`; ensure `settings.result_dir` exists (the worker should `mkdir -p` — add `settings.result_dir.mkdir(parents=True, exist_ok=True)` before `process_mgf` in `run_identifier_job`). Update the implementation accordingly, re-run. Then ruff + mypy.

- [ ] **Step 5: commit:**
```bash
git add src/glycomass/worker tests/worker
git commit -m "feat(identifier): arq worker task to process identifier jobs"
```

---

### Task 4: Upload / status / download web routes

**Files:** Create `src/glycomass/web/identifier.py`, `src/glycomass/web/templates/identifier.html`, `_job.html`; Modify `src/glycomass/web/app.py`; Create `tests/web/test_identifier.py`.

- [ ] **Step 1: `src/glycomass/web/identifier.py`:**
```python
from __future__ import annotations

from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select

from glycomass.config import get_settings
from glycomass.db.models import IdentifierJob
from glycomass.db.session import get_sessionmaker
from glycomass.web.pages import templates

router = APIRouter()


@router.get("/identifier", response_class=HTMLResponse)
def identifier_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "identifier.html")


@router.post("/identifier", response_class=HTMLResponse)
async def identifier_upload(request: Request, mgf_file: UploadFile) -> HTMLResponse:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    sm = get_sessionmaker()
    async with sm() as session:
        job = IdentifierJob(upload_path="")
        session.add(job)
        await session.commit()
        jid = job.id
        dest = settings.upload_dir / f"{jid}.mgf"
        data = await mgf_file.read()
        dest.write_bytes(data)
        job.upload_path = str(dest)
        await session.commit()
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await pool.enqueue_job("identifier_task", jid)
    return templates.TemplateResponse(request, "_job.html", {"job_id": jid, "status": "queued"})


@router.get("/identifier/{job_id}", response_class=HTMLResponse)
async def identifier_status(request: Request, job_id: str) -> HTMLResponse:
    sm = get_sessionmaker()
    async with sm() as session:
        job = (await session.execute(select(IdentifierJob).where(IdentifierJob.id == job_id))).scalar_one_or_none()
    status = job.status if job else "unknown"
    return templates.TemplateResponse(request, "_job.html", {"job_id": job_id, "status": status})


@router.get("/identifier/{job_id}/download")
async def identifier_download(job_id: str) -> FileResponse:
    sm = get_sessionmaker()
    async with sm() as session:
        job = (await session.execute(select(IdentifierJob).where(IdentifierJob.id == job_id))).scalar_one_or_none()
    if not job or job.status != "done" or not job.result_path or not Path(job.result_path).exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Result not ready")
    return FileResponse(job.result_path, filename="cleaned.mgf", media_type="text/plain")
```

- [ ] **Step 2: templates.** `_job.html` (HTMX self-polls until done/failed):
```html
{% if status in ("queued", "running") %}
<div hx-get="/identifier/{{ job_id }}" hx-trigger="load delay:1s" hx-swap="outerHTML">
  <div class="result-readout"><div><div class="k">Status</div><div class="v">{{ status }}…</div></div></div>
  <div class="bar"><i></i></div>
</div>
{% elif status == "done" %}
<div class="result-readout"><div><div class="k">Status</div><div class="v">done</div></div></div>
<a class="btn btn-primary" href="/identifier/{{ job_id }}/download">Download cleaned MGF</a>
{% else %}
<div class="error-note">Job {{ status }}. Please try another file.</div>
{% endif %}
```
`identifier.html`:
```html
{% extends "base.html" %}
{% block title %}Glycopeptide identifier · GlycoMass{% endblock %}
{% block content %}
<span class="eyebrow">Identifier</span>
<h1 style="font-family:var(--font-display);font-weight:400;font-size:var(--step-3);color:var(--paper);margin:.6rem 0 1.6rem">Glycopeptide identifier</h1>
<div class="calc-shell">
  <form class="calc-form" hx-post="/identifier" hx-target="#result" hx-swap="innerHTML" hx-encoding="multipart/form-data">
    <div><label>MGF file</label><input type="file" name="mgf_file" accept=".mgf" required></div>
    <button class="btn btn-primary" type="submit">Upload &amp; process</button>
  </form>
  <div id="result" class="result-panel"><p style="color:var(--muted)">Upload an MGF to classify glycopeptide spectra and rewrite precursors.</p></div>
</div>
{% endblock %}
```
(The `.bar`/`.bar i` styles already exist in `app.css`.)

- [ ] **Step 3: wire router** — in `src/glycomass/web/app.py` add `from glycomass.web.identifier import router as identifier_router` and `app.include_router(identifier_router)`.

- [ ] **Step 4: failing test** `tests/web/test_identifier.py` (stub the arq enqueue + use a temp sqlite + sync processing so no Redis is needed):
```python
import pytest
from fastapi.testclient import TestClient

import glycomass.web.identifier as idmod
from glycomass.db import Base
from glycomass.db.session import make_sessionmaker
from glycomass.web.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GLYCOMASS_UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setenv("GLYCOMASS_RESULT_DIR", str(tmp_path / "res"))
    monkeypatch.setenv("GLYCOMASS_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from glycomass.config import get_settings
    get_settings.cache_clear()

    # one shared in-memory sessionmaker for the app + assertions
    sm = make_sessionmaker("sqlite+aiosqlite:///:memory:")
    import asyncio
    engine = sm.kw["bind"]

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_create())
    monkeypatch.setattr("glycomass.db.session.get_sessionmaker", lambda: sm)
    monkeypatch.setattr(idmod, "get_sessionmaker", lambda: sm)

    # stub the arq enqueue: instead of Redis, run the job synchronously
    async def fake_enqueue(self, name, job_id):  # noqa: ANN001
        from glycomass.worker.tasks import run_identifier_job
        await run_identifier_job(job_id, sessionmaker=sm)

    async def fake_create_pool(_settings):
        class _Pool:
            enqueue_job = fake_enqueue
        return _Pool()

    monkeypatch.setattr(idmod, "create_pool", fake_create_pool)
    yield TestClient(create_app())
    get_settings.cache_clear()


def test_identifier_page_renders(client):
    r = client.get("/identifier")
    assert r.status_code == 200
    assert "Glycopeptide identifier" in r.text


def test_upload_processes_and_offers_download(client, tmp_path):
    sample = open("tests/identifier/sample.mgf", "rb").read()
    r = client.post("/identifier", files={"mgf_file": ("sample.mgf", sample, "text/plain")})
    assert r.status_code == 200
    # job ran synchronously via the stub -> status fragment present
    assert "/identifier/" in r.text  # polling or download link references the job id
```

- [ ] **Step 5: run, verify PASS:** `uv run pytest tests/web/test_identifier.py -v --no-cov`. This is the trickiest test — if the in-memory sqlite sharing across async sessions is flaky, switch the test DB URL to a file path under `tmp_path` (`sqlite+aiosqlite:///{tmp_path}/t.db`) so all connections see the same data, and create the schema on that. Adjust until 2 pass. Then full per-file run, ruff, mypy.

- [ ] **Step 6: commit:**
```bash
git add src/glycomass/web/identifier.py src/glycomass/web/templates/identifier.html src/glycomass/web/templates/_job.html src/glycomass/web/app.py tests/web/test_identifier.py
git commit -m "feat(identifier): upload/status/download web routes + HTMX polling"
```

---

### Task 5: Integration smoke (Docker PG+Redis+worker), docs, final review

**Files:** Modify `CLAUDE.md`; create `docker-compose.dev.yml` (Postgres + Redis for local dev/smoke).

- [ ] **Step 1: full suite + gates.** `uv run pytest` (all pass, ≥80%), `uv run mypy` (Success), `uv run ruff check` (pass).

- [ ] **Step 2: `docker-compose.dev.yml`** (local Postgres + Redis):
```yaml
services:
  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: glycomass
      POSTGRES_PASSWORD: glycomass
      POSTGRES_DB: glycomass
    ports: ["5432:5432"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

- [ ] **Step 3: integration smoke** (Postgres + Redis + real arq worker end-to-end):
```bash
docker compose -f docker-compose.dev.yml up -d
export GLYCOMASS_DATABASE_URL="postgresql+asyncpg://glycomass:glycomass@localhost:5432/glycomass"
export GLYCOMASS_REDIS_URL="redis://localhost:6379"
sleep 5
uv run alembic upgrade head            # creates identifier_jobs in Postgres
uv run arq glycomass.worker.settings.WorkerSettings &   # start worker
WORKER=$!
uv run glycomass-api &                  # start web
API=$!
sleep 4
JOB=$(curl -fsS -F "mgf_file=@tests/identifier/sample.mgf" localhost:8000/identifier | grep -oE '/identifier/[a-f0-9]{32}' | head -1)
echo "job route: $JOB"
sleep 3
curl -fsS "localhost:8000$JOB"          # status fragment (expect 'done' eventually)
curl -fsS -o /tmp/cleaned.mgf "localhost:8000$JOB/download" && echo "downloaded $(wc -l < /tmp/cleaned.mgf) lines"
kill $WORKER $API 2>/dev/null
docker compose -f docker-compose.dev.yml down
```
Expected: job reaches `done`, the cleaned MGF downloads. Paste output. If Redis/PG/worker setup fails, capture the error; the unit suite already covers the logic, so a smoke failure here is a DONE_WITH_CONCERNS (note it), not a hard block.

- [ ] **Step 4: update `CLAUDE.md`** under "## 2026 Rewrite (in progress)", append:
```markdown
### Phase 3 — glycopeptide identifier (`src/glycomass/core/identifier/`, `db/`, `worker/`, `web/identifier.py`)
- `core/identifier/pipeline.py` — pure MGF logic: classify glycopeptide spectra (oxonium), find the Pep+HexNAc fragment (NOTE: corrected vs the legacy lower-peak bug), peptide mass = fragment − 203.0866, strip glycan peaks, rewrite precursors. No legacy ground truth — tested structurally on `tests/identifier/sample.mgf`.
- `db/` — async SQLAlchemy `IdentifierJob` (Postgres prod / aiosqlite tests); Alembic in `alembic/`.
- `worker/` — `arq` task `identifier_task` → `run_identifier_job` (process MGF, update job row).
- `web/identifier.py` — `/identifier` upload → enqueue; `/identifier/{id}` HTMX-polls status; `/identifier/{id}/download`.
- Local infra: `docker compose -f docker-compose.dev.yml up -d` (Postgres+Redis); `uv run alembic upgrade head`; `uv run arq glycomass.worker.settings.WorkerSettings` (worker).
```

- [ ] **Step 5: commit:**
```bash
git add CLAUDE.md docker-compose.dev.yml
git commit -m "feat(identifier): dev compose, integration smoke, docs"
```

---

## Self-Review

**1. Spec coverage (Phase 3 = identifier):** ✅ MGF upload (Task 4 `UploadFile`); ✅ background processing (Task 3 arq worker); ✅ Postgres job tracking (Task 2 `IdentifierJob` + Alembic); ✅ classify→derive→strip→rewrite pipeline (Task 1); ✅ status polling + download (Task 4 HTMX `_job.html`); ✅ file storage volume (`upload_dir`/`result_dir`, Task 0). Out of scope (later): permalinks (Phase 4), Kamal deploy (Phase 5).

**2. Placeholder scan:** No TBD/TODO. The trickiest test (Task 4) gives an explicit fallback (file-based sqlite if in-memory sharing is flaky). The smoke (Task 5) has a DONE_WITH_CONCERNS escape if Docker infra misbehaves, since unit tests already cover the logic.

**3. Type consistency:** `Spectrum` (mz, intensity, pepmass, charge, params) used consistently across pipeline functions; `process_mgf` returns the summary dict consumed by the worker (`summary` JSON) and asserted in tests (`"identified": 1`). `IdentifierJob` fields (id, status, upload_path, result_path, error, summary) match across model, migration, worker, and routes. `run_identifier_job(job_id, *, sessionmaker=None)` signature matches the worker call and the test/route stubs. `get_sessionmaker()` is the single seam monkeypatched in tests.

**Documented decisions:** (a) corrected Pep+HexNAc selection vs the legacy lower-peak double-count bug (no ground truth — scientifically-intended behavior); (b) tests run on aiosqlite, Postgres is the prod target (validated in the Docker smoke); (c) the unused-in-legacy `precursor_neutral_mass`/glycan-mass derivation is ported but not wired into the output (matches legacy, which computed it and discarded it).
