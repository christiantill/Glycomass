"""Comprehensive legacy-parity grid (~800 cases) — marked `grid`, excluded by default.

Run explicitly:  uv run pytest -m grid --no-cov

Asserts the rewritten core reproduces the deployed app/masscalc.py outputs across a
large input grid captured in the pinned py3.7 stack (fixtures/legacy_masscalc_grid.json).
"""
import json
from pathlib import Path

import pytest

from glycomass.core import glycan_mass, peptide_mass, protein_mass
from glycomass.core.errors import NegativeIonSodiumError

pytestmark = pytest.mark.grid

_GRID = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "legacy_masscalc_grid.json").read_text()
)
_TOL = 1e-3


def _ids(group: str) -> list[str]:
    return [f"{group}-{i}" for i in range(len(_GRID[group]))]


def _check(result, case) -> None:
    assert abs(result.mono_mz - case["monomz"]) < _TOL
    assert abs(result.most_abundant_mz - case["mostab"]) < _TOL
    assert result.composition == case["composition"]


@pytest.mark.parametrize("case", _GRID["peptidemass"], ids=_ids("peptidemass"))
def test_peptide_grid(case):
    if "error" in case:
        pytest.skip("legacy errored on this case")
    i = case["inputs"]
    _check(
        peptide_mass(
            i["Peptide"], hex=i["Hex"], hexnac=i["HexNAc"], fuc=i["Fuc"], sia=i["Sia"],
            charge=i["Charge"], carbamidomethyl=bool(i["Carbamido"]), deamidation=i["Deamidation"],
        ),
        case,
    )


@pytest.mark.parametrize("case", _GRID["proteinmass"], ids=_ids("proteinmass"))
def test_protein_grid(case):
    if "error" in case:
        pytest.skip("legacy errored on this case")
    i = case["inputs"]
    _check(
        protein_mass(
            i["Protein"], hex=i["Hex"], hexnac=i["HexNAc"], fuc=i["Fuc"], sia=i["Sia"],
            charge=i["Charge"], deamidation=i["Deamidation"],
            disulfide_bridges=i["Disulfidebridges"], resolution=i["resolution"],
        ),
        case,
    )


@pytest.mark.parametrize("case", _GRID["glycanmass"], ids=_ids("glycanmass"))
def test_glycan_grid(case):
    if "error" in case:
        pytest.skip("legacy errored on this case")
    i = case["inputs"]
    kwargs = dict(
        hex=i["Hex"], hexnac=i["HexNAc"], fuc=i["Fuc"], sia=i["Sia"],
        charge=i["Charge"], sodium=i["Sodium"], modification=i["Modification"],
    )
    if case.get("result", "x") is None:
        with pytest.raises(NegativeIonSodiumError):
            glycan_mass(**kwargs)
        return
    _check(glycan_mass(**kwargs), case)
