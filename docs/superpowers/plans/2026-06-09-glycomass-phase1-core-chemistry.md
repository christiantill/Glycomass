# Glycomass Phase 1 — Core Chemistry & Golden Tests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the framework-free `glycomass.core` package — one canonical element-composition table plus `peptide_mass()`, `protein_mass()`, `glycan_mass()` — and prove it reproduces the deployed app's results via the Phase-0 golden fixtures.

**Architecture:** Pure Python domain layer with no web/IO. A `Composition` value object does `[C,H,N,O,S]` arithmetic; `constants.py` holds the single source of truth for residue/monosaccharide/modification compositions (ported verbatim from the deployed `app/masscalc.py`, which the fixtures pin); `isotopes.py` wraps **brainpy** to derive monoisotopic m/z, most-abundant m/z, and the isotope-peak spectrum. The three calculators compose these. Tests are TDD; the anchor is a fixture-driven parity test against `fixtures/legacy_masscalc.json`.

**Tech Stack:** Python 3.14, uv, Pydantic v2 (result models), numpy, brain-isotopic-distribution==1.5.19 (built from sdist), pytest + pytest-cov, ruff, mypy.

---

## File Structure

- `pyproject.toml` — project + deps + ruff/mypy/pytest/coverage config (new).
- `.python-version` — pins `3.14` for uv (new).
- `src/glycomass/__init__.py` — package marker (new).
- `src/glycomass/core/__init__.py` — re-exports the public API (new).
- `src/glycomass/core/results.py` — Pydantic result models `Spectrum`, `MassResult` (new).
- `src/glycomass/core/composition.py` — `Composition` value object (new).
- `src/glycomass/core/constants.py` — the single canonical element table (new).
- `src/glycomass/core/isotopes.py` — brainpy wrapper `isotope_profile()` (new).
- `src/glycomass/core/errors.py` — typed domain errors (new).
- `src/glycomass/core/peptide.py` — `peptide_mass()` (new).
- `src/glycomass/core/protein.py` — `protein_mass()` (new).
- `src/glycomass/core/glycan.py` — `glycan_mass()` (new).
- `tests/conftest.py` — fixture loader (new).
- `tests/test_composition.py`, `tests/test_constants.py`, `tests/test_isotopes.py`,
  `tests/test_peptide.py`, `tests/test_protein.py`, `tests/test_glycan.py`,
  `tests/test_golden.py` (new).

> **Import note:** legacy `glycomass.py` (root) shares the package name. The `src/` layout + `--import-mode=importlib` + editable install make `import glycomass` resolve to `src/glycomass`, not the root module. Legacy `app/` and `glycomass.py` are removed at Phase 5 cutover.

---

### Task 0: Project scaffolding & tooling

**Files:**
- Create: `pyproject.toml`, `.python-version`, `src/glycomass/__init__.py`, `src/glycomass/core/__init__.py`

- [ ] **Step 1: Write `.python-version`**

```
3.14
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "glycomass"
version = "0.1.0"
description = "Exact masses and isotope spectra for glycans, glycopeptides and glycoproteins."
requires-python = ">=3.14,<3.15"
dependencies = [
    "numpy>=2.0",
    "brain-isotopic-distribution==1.5.19",
    "pydantic>=2.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-cov>=5.0",
    "ruff>=0.6",
    "mypy>=1.10",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/glycomass"]

[tool.ruff]
line-length = 100
target-version = "py314"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.14"
strict = true
files = ["src/glycomass"]
[[tool.mypy.overrides]]
module = ["brainpy.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
addopts = "--import-mode=importlib --cov=src/glycomass --cov-report=term-missing --cov-fail-under=80"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
[tool.coverage.report]
fail_under = 80
```

- [ ] **Step 3: Create package markers**

`src/glycomass/__init__.py`:
```python
"""Glycomass — exact masses and isotope spectra for glyco-analytics."""
```
`src/glycomass/core/__init__.py`:
```python
"""Framework-free domain core: chemistry and isotope calculations."""
```

- [ ] **Step 4: Pin Python, sync, verify install (brainpy builds from sdist)**

Run: `uv python pin 3.14 && uv sync --extra dev`
Expected: resolves and installs; brainpy compiles from sdist (needs a C compiler — present on this host). Ends with "Installed N packages".

- [ ] **Step 5: Verify import + lint**

Run: `uv run python -c "import glycomass, glycomass.core; print('ok')"`
Expected: `ok`
Run: `uv run ruff check`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .python-version uv.lock src/glycomass/__init__.py src/glycomass/core/__init__.py
git commit -m "chore: scaffold glycomass core package (uv, py3.14, ruff/mypy/pytest)"
```

---

### Task 1: Result models

**Files:**
- Create: `src/glycomass/core/results.py`
- Test: `tests/test_results.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_results.py
from glycomass.core.results import MassResult, Spectrum


def test_mass_result_holds_values():
    r = MassResult(
        mono_mz=800.3672,
        most_abundant_mz=800.3672,
        composition="C34 H53 N7 O15 S0",
        spectrum=Spectrum(mz=[800.3672, 800.8689], intensity=[100.0, 41.2]),
    )
    assert r.mono_mz == 800.3672
    assert r.composition == "C34 H53 N7 O15 S0"
    assert len(r.spectrum.mz) == len(r.spectrum.intensity) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_results.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glycomass.core.results'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/glycomass/core/results.py
from pydantic import BaseModel


class Spectrum(BaseModel):
    """Isotope-peak stick spectrum (intensity normalized to 100)."""

    mz: list[float]
    intensity: list[float]


class MassResult(BaseModel):
    """Result of a mass calculation."""

    mono_mz: float
    most_abundant_mz: float
    composition: str
    spectrum: Spectrum
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_results.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/glycomass/core/results.py tests/test_results.py
git commit -m "feat(core): add MassResult and Spectrum models"
```

---

### Task 2: Composition value object

**Files:**
- Create: `src/glycomass/core/composition.py`
- Test: `tests/test_composition.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_composition.py
from glycomass.core.composition import Composition


def test_add_and_scale():
    a = Composition(C=3, H=5, N=1, O=1, S=0)
    b = Composition(C=0, H=2, N=0, O=1, S=0)
    assert (a + b).counts == {"C": 3, "H": 7, "N": 1, "O": 2, "S": 0}
    assert (a * 2).counts == {"C": 6, "H": 10, "N": 2, "O": 2, "S": 0}


def test_formula_string_matches_legacy_format():
    # exact legacy display format: "C.. H.. N.. O.. S.." incl S0, in C H N O S order
    assert Composition(C=34, H=53, N=7, O=15, S=0).formula() == "C34 H53 N7 O15 S0"


def test_to_brainpy_dict():
    assert Composition(C=6, H=12, N=0, O=6, S=0).to_brainpy() == {
        "C": 6, "H": 12, "N": 0, "O": 6, "S": 0,
    }


def test_supports_negative_counts():
    # deamidation contributes -1 H, -1 N, +1 O
    base = Composition(C=4, H=6, N=2, O=2, S=0)
    deamido = Composition(C=0, H=-1, N=-1, O=1, S=0)
    assert (base + deamido).counts == {"C": 4, "H": 5, "N": 1, "O": 3, "S": 0}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_composition.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glycomass.core.composition'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/glycomass/core/composition.py
from __future__ import annotations

from dataclasses import dataclass

ELEMENTS = ("C", "H", "N", "O", "S")


@dataclass(frozen=True)
class Composition:
    """An elemental composition over C, H, N, O, S. Counts may be negative
    (e.g. deamidation, disulfide bridges subtract atoms)."""

    C: int = 0
    H: int = 0
    N: int = 0
    O: int = 0
    S: int = 0

    @property
    def counts(self) -> dict[str, int]:
        return {e: getattr(self, e) for e in ELEMENTS}

    def __add__(self, other: Composition) -> Composition:
        return Composition(**{e: getattr(self, e) + getattr(other, e) for e in ELEMENTS})

    def __sub__(self, other: Composition) -> Composition:
        return Composition(**{e: getattr(self, e) - getattr(other, e) for e in ELEMENTS})

    def __mul__(self, n: int) -> Composition:
        return Composition(**{e: getattr(self, e) * n for e in ELEMENTS})

    __rmul__ = __mul__

    def formula(self) -> str:
        """Legacy display format, e.g. 'C34 H53 N7 O15 S0' (C H N O S order)."""
        return " ".join(f"{e}{getattr(self, e)}" for e in ELEMENTS)

    def to_brainpy(self) -> dict[str, int]:
        """Atom dict for brainpy.isotopic_variants()."""
        return self.counts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_composition.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/glycomass/core/composition.py tests/test_composition.py
git commit -m "feat(core): add Composition value object"
```

---

### Task 3: Canonical constants table

**Files:**
- Create: `src/glycomass/core/constants.py`
- Test: `tests/test_constants.py`

> These values are ported verbatim from the deployed `app/masscalc.py`. Do not "correct" them — the fixtures pin them.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_constants.py
from glycomass.core.composition import Composition
from glycomass.core import constants as K


def test_water_and_a_few_residues():
    assert K.WATER == Composition(C=0, H=2, N=0, O=1, S=0)
    assert K.AMINO_ACIDS["A"] == Composition(C=3, H=5, N=1, O=1, S=0)
    assert K.AMINO_ACIDS["W"] == Composition(C=11, H=10, N=2, O=1, S=0)
    assert K.CARBAMIDOMETHYL_CYS == Composition(C=5, H=8, N=2, O=2, S=1)


def test_all_twenty_amino_acids_present():
    assert set(K.AMINO_ACIDS) == set("ARNDCQEGHILKMFPSTWYV")


def test_peptide_composition_matches_legacy_formula():
    # PEPTIDE = sum residues + 1 water -> C34 H53 N7 O15 S0 (legacy fixture)
    comp = K.WATER
    for aa in "PEPTIDE":
        comp = comp + K.AMINO_ACIDS[aa]
    assert comp.formula() == "C34 H53 N7 O15 S0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_constants.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glycomass.core.constants'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/glycomass/core/constants.py
"""Single source of truth for elemental compositions.

Ported verbatim from the deployed app/masscalc.py; pinned by fixtures/legacy_masscalc.json.
"""
from glycomass.core.composition import Composition as C

WATER = C(C=0, H=2, N=0, O=1, S=0)

# Amino-acid RESIDUE compositions (peptide = sum(residues) + 1 WATER).
AMINO_ACIDS: dict[str, C] = {
    "A": C(C=3, H=5, N=1, O=1, S=0),
    "R": C(C=6, H=12, N=4, O=1, S=0),
    "N": C(C=4, H=6, N=2, O=2, S=0),
    "D": C(C=4, H=5, N=1, O=3, S=0),
    "C": C(C=3, H=5, N=1, O=1, S=1),
    "Q": C(C=5, H=8, N=2, O=2, S=0),
    "E": C(C=5, H=7, N=1, O=3, S=0),
    "G": C(C=2, H=3, N=1, O=1, S=0),
    "H": C(C=6, H=7, N=3, O=1, S=0),
    "I": C(C=6, H=11, N=1, O=1, S=0),
    "L": C(C=6, H=11, N=1, O=1, S=0),
    "K": C(C=6, H=12, N=2, O=1, S=0),
    "M": C(C=5, H=9, N=1, O=1, S=1),
    "F": C(C=9, H=9, N=1, O=1, S=0),
    "P": C(C=5, H=7, N=1, O=1, S=0),
    "S": C(C=3, H=5, N=1, O=2, S=0),
    "T": C(C=4, H=7, N=1, O=2, S=0),
    "W": C(C=11, H=10, N=2, O=1, S=0),
    "Y": C(C=9, H=9, N=1, O=2, S=0),
    "V": C(C=5, H=9, N=1, O=1, S=0),
}
CARBAMIDOMETHYL_CYS = C(C=5, H=8, N=2, O=2, S=1)  # Cys + carbamidomethyl

# Per-count modifiers.
DEAMIDATION = C(C=0, H=-1, N=-1, O=1, S=0)       # added Deamidation times
DISULFIDE_BRIDGE = C(C=0, H=2, N=0, O=0, S=0)    # SUBTRACTED per bridge (-2 H)

# Native (underivatized) monosaccharide RESIDUE compositions.
HEX = C(C=6, H=10, N=0, O=5, S=0)
HEXNAC = C(C=8, H=13, N=1, O=5, S=0)
FUC = C(C=6, H=10, N=0, O=4, S=0)
SIA = C(C=11, H=17, N=1, O=8, S=0)

# Permethylated monosaccharides + reducing-end add group.
HEX_PERMETHYL = C(C=9, H=16, N=0, O=5, S=0)
HEXNAC_PERMETHYL = C(C=11, H=19, N=1, O=5, S=0)
FUC_PERMETHYL = C(C=8, H=14, N=0, O=4, S=0)
SIA_PERMETHYL = C(C=16, H=27, N=1, O=8, S=0)
PERMETHYL_ADD = C(C=2, H=4, N=0, O=0, S=0)

# Peracetylated monosaccharides + reducing-end add group.
HEX_PERACETYL = C(C=12, H=16, N=0, O=8, S=0)
HEXNAC_PERACETYL = C(C=12, H=17, N=1, O=7, S=0)
FUC_PERACETYL = C(C=10, H=14, N=0, O=6, S=0)
SIA_PERACETYL = C(C=17, H=23, N=1, O=11, S=0)
PERACETYL_ADD = C(C=4, H=4, N=0, O=2, S=0)

# Reducing-end labels (added to the native glycan).
REDUCED_END = C(C=0, H=2, N=0, O=0, S=0)
LABEL_2AB = C(C=7, H=8, N=2, O=0, S=0)
LABEL_2AA = C(C=7, H=7, N=1, O=1, S=0)

# Sodium adduct shift constants (m/z): swap a proton for Na+.
SODIUM_MASS = 22.989770
PROTON_MASS = 1.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_constants.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/glycomass/core/constants.py tests/test_constants.py
git commit -m "feat(core): add canonical element/monosaccharide constants"
```

---

### Task 4: Isotope profile (brainpy wrapper)

**Files:**
- Create: `src/glycomass/core/isotopes.py`
- Test: `tests/test_isotopes.py`

> Replicates the deployed algorithm: a Gaussian profile over an m/z grid (step = sigma), mono = first cluster peak, most-abundant = grid m/z at peak intensity. The exponent denominator uses `2*sigma` (matching the deployed code, not the textbook `2*sigma**2`); preserved for fixture parity. The returned `Spectrum` is the compact isotope-peak stick list, not the dense grid.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_isotopes.py
from glycomass.core.composition import Composition
from glycomass.core.isotopes import isotope_profile


def test_monoisotopic_matches_legacy_peptide():
    # PEPTIDE: C34 H53 N7 O15 S0, charge 1 -> mono m/z 800.3672 (legacy fixture)
    comp = Composition(C=34, H=53, N=7, O=15, S=0)
    res = isotope_profile(comp, charge=1, npeaks=10, sigma=0.0005)
    assert abs(res.mono_mz - 800.3672) < 1e-3
    assert abs(res.most_abundant_mz - 800.3672) < 1e-3  # small molecule: mono is most abundant
    assert len(res.spectrum.mz) == len(res.spectrum.intensity) == 10
    assert max(res.spectrum.intensity) == 100.0


def test_mz_shift_applies_to_mono_and_most_abundant():
    comp = Composition(C=34, H=53, N=7, O=15, S=0)
    base = isotope_profile(comp, charge=1, npeaks=10, sigma=0.0005)
    shifted = isotope_profile(comp, charge=1, npeaks=10, sigma=0.0005, mz_shift=21.9898)
    assert abs((shifted.mono_mz - base.mono_mz) - 21.9898) < 1e-6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_isotopes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glycomass.core.isotopes'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/glycomass/core/isotopes.py
from __future__ import annotations

import numpy as np
from brainpy import isotopic_variants

from glycomass.core.composition import Composition
from glycomass.core.results import Spectrum


class IsotopeResult:
    """Lightweight carrier for isotope-profile outputs."""

    def __init__(self, mono_mz: float, most_abundant_mz: float, spectrum: Spectrum) -> None:
        self.mono_mz = mono_mz
        self.most_abundant_mz = most_abundant_mz
        self.spectrum = spectrum


def isotope_profile(
    comp: Composition,
    *,
    charge: int,
    npeaks: int,
    sigma: float,
    mz_shift: float = 0.0,
) -> IsotopeResult:
    """Theoretical isotope distribution for an elemental composition.

    Returns mono m/z (lightest peak), most-abundant m/z (grid argmax of a Gaussian
    profile, matching the deployed code), and a compact stick Spectrum normalized to 100.
    `mz_shift` adds to mono and most-abundant m/z (e.g. sodium adduct).
    """
    cluster = isotopic_variants(comp.to_brainpy(), npeaks=npeaks, charge=charge)
    peak_mz = np.array([p.mz for p in cluster], dtype=float)
    peak_int = np.array([p.intensity for p in cluster], dtype=float)

    # Gaussian profile over an m/z grid (step == sigma), matching app/masscalc.py.
    grid = np.arange(peak_mz[0] - 1, peak_mz[-1] + 1, sigma)
    profile = np.zeros_like(grid)
    denom = np.sqrt(2 * np.pi) * sigma
    for mz, inten in zip(peak_mz, peak_int):
        profile += inten * np.exp(-((grid - mz) ** 2) / (2 * sigma)) / denom

    most_abundant_mz = float(grid[int(np.argmax(profile))]) + mz_shift
    mono_mz = float(peak_mz[0]) + mz_shift

    norm = float(peak_int.max())
    spectrum = Spectrum(
        mz=[float(mz) + mz_shift for mz in peak_mz],
        intensity=[float(i) / norm * 100 for i in peak_int],
    )
    return IsotopeResult(mono_mz, most_abundant_mz, spectrum)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_isotopes.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/glycomass/core/isotopes.py tests/test_isotopes.py
git commit -m "feat(core): add brainpy isotope-profile wrapper"
```

---

### Task 5: Peptide / glycopeptide calculator

**Files:**
- Create: `src/glycomass/core/peptide.py`
- Test: `tests/test_peptide.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_peptide.py
from glycomass.core.peptide import peptide_mass


def test_bare_peptide():
    r = peptide_mass("PEPTIDE", charge=1)
    assert abs(r.mono_mz - 800.3672) < 1e-3
    assert r.composition == "C34 H53 N7 O15 S0"


def test_glycopeptide_with_carbamidomethyl():
    # NLTSVCWK + Hex5HexNAc4Fuc1Sia2, z=2, carbamidomethyl -> 1679.6678 (fixture)
    r = peptide_mass("NLTSVCWK", hex=5, hexnac=4, fuc=1, sia=2, charge=2, carbamidomethyl=True)
    assert abs(r.mono_mz - 1679.6678) < 1e-3


def test_deamidation_shifts_mass():
    # NLTSVK, z=1, deamidation 1 -> 662.3719 ; deamidation 2 -> 663.3559 (fixtures)
    assert abs(peptide_mass("NLTSVK", charge=1, deamidation=1).mono_mz - 662.3719) < 1e-3
    assert abs(peptide_mass("NLTSVK", charge=1, deamidation=2).mono_mz - 663.3559) < 1e-3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_peptide.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glycomass.core.peptide'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/glycomass/core/peptide.py
from __future__ import annotations

from glycomass.core import constants as K
from glycomass.core.composition import Composition
from glycomass.core.isotopes import isotope_profile
from glycomass.core.results import MassResult

_NPEAKS = 10
_SIGMA = 0.0005


def _backbone(sequence: str, *, carbamidomethyl: bool) -> Composition:
    comp = K.WATER
    for aa in sequence.upper():
        if aa not in K.AMINO_ACIDS:
            continue  # legacy ignores unknown characters
        if aa == "C" and carbamidomethyl:
            comp = comp + K.CARBAMIDOMETHYL_CYS
        else:
            comp = comp + K.AMINO_ACIDS[aa]
    return comp


def _glycan(comp: Composition, hex: int, hexnac: int, fuc: int, sia: int) -> Composition:
    return comp + K.HEX * hex + K.HEXNAC * hexnac + K.FUC * fuc + K.SIA * sia


def peptide_mass(
    sequence: str,
    *,
    hex: int = 0,
    hexnac: int = 0,
    fuc: int = 0,
    sia: int = 0,
    charge: int = 1,
    carbamidomethyl: bool = False,
    deamidation: int = 0,
) -> MassResult:
    comp = _backbone(sequence, carbamidomethyl=carbamidomethyl)
    comp = _glycan(comp, hex, hexnac, fuc, sia)
    comp = comp + K.DEAMIDATION * deamidation
    iso = isotope_profile(comp, charge=charge, npeaks=_NPEAKS, sigma=_SIGMA)
    return MassResult(
        mono_mz=round(iso.mono_mz, 4),
        most_abundant_mz=round(iso.most_abundant_mz, 4),
        composition=comp.formula(),
        spectrum=iso.spectrum,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_peptide.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/glycomass/core/peptide.py tests/test_peptide.py
git commit -m "feat(core): add peptide/glycopeptide mass calculator"
```

---

### Task 6: Protein / glycoprotein calculator

**Files:**
- Create: `src/glycomass/core/protein.py`
- Test: `tests/test_protein.py`

> Resolution maps to the deployed Gaussian sigma; npeaks is 200. Accepts the legacy
> resolution strings exactly (`"low"`, `"medium"`, `"super high"`) so fixtures pass.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_protein.py
import pytest

from glycomass.core.protein import protein_mass


def test_protein_medium_resolution():
    # ACDEFGHIKLMNPQRSTVWY, z=5, medium -> mono 479.8323 (fixture)
    r = protein_mass("ACDEFGHIKLMNPQRSTVWY", charge=5, resolution="medium")
    assert abs(r.mono_mz - 479.8323) < 1e-3


def test_disulfide_bridges_subtract_two_hydrogens_each():
    # CCACCAGGKL, z=3, medium: 0 bridges 310.1218; 1 -> 309.4499; 2 -> 308.778 (fixtures)
    base = protein_mass("CCACCAGGKL", charge=3, resolution="medium", disulfide_bridges=0)
    one = protein_mass("CCACCAGGKL", charge=3, resolution="medium", disulfide_bridges=1)
    two = protein_mass("CCACCAGGKL", charge=3, resolution="medium", disulfide_bridges=2)
    assert abs(base.mono_mz - 310.1218) < 1e-3
    assert abs(one.mono_mz - 309.4499) < 1e-3
    assert abs(two.mono_mz - 308.778) < 1e-3


def test_unknown_resolution_raises():
    with pytest.raises(KeyError):
        protein_mass("PEPTIDE", charge=1, resolution="ultra")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_protein.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glycomass.core.protein'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/glycomass/core/protein.py
from __future__ import annotations

from glycomass.core import constants as K
from glycomass.core.composition import Composition
from glycomass.core.isotopes import isotope_profile
from glycomass.core.results import MassResult

_NPEAKS = 200
# Legacy resolution -> Gaussian sigma (== grid step). Keys match the deployed strings.
_RESOLUTION_SIGMA = {"low": 0.05, "medium": 0.003, "super high": 0.001}


def protein_mass(
    sequence: str,
    *,
    hex: int = 0,
    hexnac: int = 0,
    fuc: int = 0,
    sia: int = 0,
    charge: int = 1,
    deamidation: int = 0,
    disulfide_bridges: int = 0,
    resolution: str = "medium",
) -> MassResult:
    sigma = _RESOLUTION_SIGMA[resolution]  # KeyError on unknown resolution
    comp = K.WATER
    for aa in sequence.upper():
        if aa in K.AMINO_ACIDS:
            comp = comp + K.AMINO_ACIDS[aa]
    comp = comp - K.DISULFIDE_BRIDGE * disulfide_bridges
    comp = comp + K.HEX * hex + K.HEXNAC * hexnac + K.FUC * fuc + K.SIA * sia
    comp = comp + K.DEAMIDATION * deamidation
    iso = isotope_profile(comp, charge=charge, npeaks=_NPEAKS, sigma=sigma)
    return MassResult(
        mono_mz=round(iso.mono_mz, 4),
        most_abundant_mz=round(iso.most_abundant_mz, 4),
        composition=comp.formula(),
        spectrum=iso.spectrum,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_protein.py -v`
Expected: PASS (3 tests). Note: `super high` at low charge is CPU-heavy; tests above use modest sizes/charges.

- [ ] **Step 5: Commit**

```bash
git add src/glycomass/core/protein.py tests/test_protein.py
git commit -m "feat(core): add protein/glycoprotein mass calculator"
```

---

### Task 7: Free-glycan calculator + domain error

**Files:**
- Create: `src/glycomass/core/errors.py`, `src/glycomass/core/glycan.py`
- Test: `tests/test_glycan.py`

> Replaces the legacy "return None" guard with a typed exception. Accepts the legacy
> modification strings exactly, including the misspelled `"Peracetly"`, plus a
> `"Peracetyl"` alias.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_glycan.py
import pytest

from glycomass.core.errors import NegativeIonSodiumError
from glycomass.core.glycan import glycan_mass


def test_native_glycan():
    # Hex5HexNAc4Fuc1Sia2, z=1 -> 2369.8482, C90 H148 N6 O66 S0 (fixture)
    r = glycan_mass(hex=5, hexnac=4, fuc=1, sia=2, charge=1)
    assert abs(r.mono_mz - 2369.8482) < 1e-3
    assert r.composition == "C90 H148 N6 O66 S0"


def test_sodium_adduct_shift():
    # Hex5HexNAc4, z=1: native 1641.5994 ; sodium 1663.5892 (fixtures)
    assert abs(glycan_mass(hex=5, hexnac=4, charge=1).mono_mz - 1641.5994) < 1e-3
    assert abs(glycan_mass(hex=5, hexnac=4, charge=1, sodium=True).mono_mz - 1663.5892) < 1e-3


def test_permethyl_and_peracetyl():
    # Hex5HexNAc4Fuc1Sia2, z=1: Permethyl 2944.4898 ; Peracetly 3756.1968 (fixtures)
    assert abs(glycan_mass(5, 4, 1, 2, charge=1, modification="Permethyl").mono_mz - 2944.4898) < 1e-3
    assert abs(glycan_mass(5, 4, 1, 2, charge=1, modification="Peracetly").mono_mz - 3756.1968) < 1e-3


def test_sodium_in_negative_mode_raises():
    with pytest.raises(NegativeIonSodiumError):
        glycan_mass(hex=5, hexnac=4, charge=-1, sodium=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_glycan.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glycomass.core.errors'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/glycomass/core/errors.py
class GlycomassError(ValueError):
    """Base class for glycomass domain errors."""


class NegativeIonSodiumError(GlycomassError):
    """Sodium adduct requested in negative-ion mode (charge <= 0)."""
```

```python
# src/glycomass/core/glycan.py
from __future__ import annotations

from glycomass.core import constants as K
from glycomass.core.composition import Composition
from glycomass.core.errors import NegativeIonSodiumError
from glycomass.core.isotopes import isotope_profile
from glycomass.core.results import MassResult

_NPEAKS = 10
_SIGMA = 0.0005

# modification -> (Hex, HexNAc, Fuc, Sia tables, extra reducing-end group)
_MODS: dict[str, tuple[Composition, Composition, Composition, Composition, Composition]] = {
    "none": (K.HEX, K.HEXNAC, K.FUC, K.SIA, Composition()),
    "Permethyl": (K.HEX_PERMETHYL, K.HEXNAC_PERMETHYL, K.FUC_PERMETHYL, K.SIA_PERMETHYL, K.PERMETHYL_ADD),
    "Peracetly": (K.HEX_PERACETYL, K.HEXNAC_PERACETYL, K.FUC_PERACETYL, K.SIA_PERACETYL, K.PERACETYL_ADD),
    "Peracetyl": (K.HEX_PERACETYL, K.HEXNAC_PERACETYL, K.FUC_PERACETYL, K.SIA_PERACETYL, K.PERACETYL_ADD),
    "ReducedEnd": (K.HEX, K.HEXNAC, K.FUC, K.SIA, K.REDUCED_END),
    "Label_2AB": (K.HEX, K.HEXNAC, K.FUC, K.SIA, K.LABEL_2AB),
    "Label_2AA": (K.HEX, K.HEXNAC, K.FUC, K.SIA, K.LABEL_2AA),
}


def glycan_mass(
    hex: int = 0,
    hexnac: int = 0,
    fuc: int = 0,
    sia: int = 0,
    *,
    charge: int = 1,
    sodium: bool = False,
    modification: str = "none",
) -> MassResult:
    if sodium and charge <= 0:
        raise NegativeIonSodiumError(
            "Sodium adducts are not expected in negative-ion mode (charge <= 0)."
        )
    h, hn, f, s, extra = _MODS.get(modification, _MODS["none"])
    comp = K.WATER + h * hex + hn * hexnac + f * fuc + s * sia + extra

    mz_shift = 0.0
    if sodium:
        mz_shift = (K.SODIUM_MASS / charge) - (K.PROTON_MASS / charge)

    iso = isotope_profile(comp, charge=charge, npeaks=_NPEAKS, sigma=_SIGMA, mz_shift=mz_shift)
    return MassResult(
        mono_mz=round(iso.mono_mz, 4),
        most_abundant_mz=round(iso.most_abundant_mz, 4),
        composition=comp.formula(),
        spectrum=iso.spectrum,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_glycan.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/glycomass/core/errors.py src/glycomass/core/glycan.py tests/test_glycan.py
git commit -m "feat(core): add free-glycan calculator + typed negative-ion guard"
```

---

### Task 8: Golden parity test against all fixtures (the anchor)

**Files:**
- Create: `tests/conftest.py`, `tests/test_golden.py`
- Modify: `src/glycomass/core/__init__.py` (re-export public API)

- [ ] **Step 1: Re-export the public API**

```python
# src/glycomass/core/__init__.py
"""Framework-free domain core: chemistry and isotope calculations."""
from glycomass.core.errors import GlycomassError, NegativeIonSodiumError
from glycomass.core.glycan import glycan_mass
from glycomass.core.peptide import peptide_mass
from glycomass.core.protein import protein_mass
from glycomass.core.results import MassResult, Spectrum

__all__ = [
    "peptide_mass", "protein_mass", "glycan_mass",
    "MassResult", "Spectrum", "GlycomassError", "NegativeIonSodiumError",
]
```

- [ ] **Step 2: Write the fixture loader**

```python
# tests/conftest.py
import json
from pathlib import Path

import pytest

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "legacy_masscalc.json"


@pytest.fixture(scope="session")
def legacy_fixtures() -> dict:
    return json.loads(_FIXTURES.read_text())
```

- [ ] **Step 3: Write the failing golden test**

```python
# tests/test_golden.py
import json
from pathlib import Path

import pytest

from glycomass.core import glycan_mass, peptide_mass, protein_mass
from glycomass.core.errors import NegativeIonSodiumError

_FIXTURES = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "legacy_masscalc.json").read_text()
)
_TOL = 1e-3


def _ids(group):
    return [f"{group}-{i}" for i in range(len(_FIXTURES[group]))]


@pytest.mark.parametrize("case", _FIXTURES["peptidemass"], ids=_ids("peptidemass"))
def test_peptide_parity(case):
    i = case["inputs"]
    r = peptide_mass(
        i["Peptide"], hex=i["Hex"], hexnac=i["HexNAc"], fuc=i["Fuc"], sia=i["Sia"],
        charge=i["Charge"], carbamidomethyl=bool(i["Carbamido"]), deamidation=i["Deamidation"],
    )
    assert abs(r.mono_mz - case["monomz"]) < _TOL
    assert abs(r.most_abundant_mz - case["mostab"]) < _TOL
    assert r.composition == case["composition"]


@pytest.mark.parametrize("case", _FIXTURES["proteinmass"], ids=_ids("proteinmass"))
def test_protein_parity(case):
    i = case["inputs"]
    r = protein_mass(
        i["Protein"], hex=i["Hex"], hexnac=i["HexNAc"], fuc=i["Fuc"], sia=i["Sia"],
        charge=i["Charge"], deamidation=i["Deamidation"],
        disulfide_bridges=i["Disulfidebridges"], resolution=i["resolution"],
    )
    assert abs(r.mono_mz - case["monomz"]) < _TOL
    assert abs(r.most_abundant_mz - case["mostab"]) < _TOL
    assert r.composition == case["composition"]


@pytest.mark.parametrize("case", _FIXTURES["glycanmass"], ids=_ids("glycanmass"))
def test_glycan_parity(case):
    i = case["inputs"]
    kwargs = dict(
        hex=i["Hex"], hexnac=i["HexNAc"], fuc=i["Fuc"], sia=i["Sia"],
        charge=i["Charge"], sodium=i["Sodium"], modification=i["Modification"],
    )
    if case.get("result", "x") is None:  # legacy returned None -> we now raise
        with pytest.raises(NegativeIonSodiumError):
            glycan_mass(**kwargs)
        return
    r = glycan_mass(**kwargs)
    assert abs(r.mono_mz - case["monomz"]) < _TOL
    assert abs(r.most_abundant_mz - case["mostab"]) < _TOL
    assert r.composition.replace(" S0", "") == case["composition"].replace(" S0", "")
```

- [ ] **Step 4: Run the golden test — verify every fixture passes**

Run: `uv run pytest tests/test_golden.py -v`
Expected: PASS for all parametrized cases (13 peptide + 10 protein + 14 glycan). The single
glycan guard case (`Sodium=true, Charge=-1`) passes via the `pytest.raises` branch.
If any case fails, do NOT loosen the tolerance — investigate the composition/algorithm port.

- [ ] **Step 5: Run the full suite with coverage + types**

Run: `uv run pytest`
Expected: all tests pass, coverage ≥ 80%.
Run: `uv run mypy`
Expected: `Success: no issues found`.
Run: `uv run ruff check`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_golden.py src/glycomass/core/__init__.py
git commit -m "test(core): golden parity against legacy fixtures; export public API"
```

---

### Task 9: Document the core in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (append a rewrite section; do not delete the legacy analysis yet)

- [ ] **Step 1: Append a "2026 Rewrite — core" section to `CLAUDE.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document the rewrite core package and commands"
```

---

## Self-Review

**1. Spec coverage (Phase 1 scope only):** ✅ single canonical constants table (Task 3, kills 3× duplication); ✅ typed `MassResult` replacing the comma-string contract (Task 1); ✅ all three calculators (Tasks 5–7); ✅ brainpy isotopes (Task 4); ✅ golden fixtures parity (Task 8); ✅ typed domain error replacing the `None` guard (Task 7); ✅ uv/ruff/mypy/pytest scaffolding (Task 0). Out of Phase-1 scope (later plans): web/HTMX, JSON API, identifier/worker, permalinks, Postgres, Kamal deploy, spectrum downsampling.

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code; every test step shows real assertions with concrete fixture values.

**3. Type consistency:** `Composition` arithmetic (`+`, `-`, `*`, `counts`, `formula`, `to_brainpy`) is used identically across constants/calculators. `isotope_profile(comp, *, charge, npeaks, sigma, mz_shift)` signature matches all call sites (peptide/protein/glycan). `MassResult(mono_mz, most_abundant_mz, composition, spectrum)` constructed identically in all three calculators. `IsotopeResult.mono_mz/most_abundant_mz/spectrum` consumed consistently.

**Known intentional quirks (documented in code):** Gaussian exponent uses `2*sigma` (legacy parity, not textbook `2*sigma**2`); unknown amino-acid characters are ignored (legacy behavior); the sodium m/z shift uses `PROTON_MASS = 1.0` (legacy used integer 1, not 1.00728) — preserved for fixture parity, flagged for a future correctness pass.
