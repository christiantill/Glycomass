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
    kwargs = {
        "hex": i["Hex"],
        "hexnac": i["HexNAc"],
        "fuc": i["Fuc"],
        "sia": i["Sia"],
        "charge": i["Charge"],
        "sodium": i["Sodium"],
        "modification": i["Modification"],
    }
    if case.get("result", "x") is None:  # legacy returned None -> we now raise
        with pytest.raises(NegativeIonSodiumError):
            glycan_mass(**kwargs)
        return
    r = glycan_mass(**kwargs)
    assert abs(r.mono_mz - case["monomz"]) < _TOL
    assert abs(r.most_abundant_mz - case["mostab"]) < _TOL
    assert r.composition == case["composition"]
