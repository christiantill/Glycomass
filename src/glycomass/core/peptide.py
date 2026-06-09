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
    hex: int = 0,  # noqa: A002
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
