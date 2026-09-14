from __future__ import annotations

from glycomass.core import constants as K
from glycomass.core.errors import GlycomassError
from glycomass.core.isotopes import isotope_profile
from glycomass.core.results import MassResult

_NPEAKS = 200
# Legacy resolution -> Gaussian sigma (== grid step). Keys match the deployed strings.
_RESOLUTION_SIGMA = {"low": 0.05, "medium": 0.003, "super high": 0.001}


def protein_mass(
    sequence: str,
    *,
    hex: int = 0,  # noqa: A002
    hexnac: int = 0,
    fuc: int = 0,
    sia: int = 0,
    charge: int = 1,
    deamidation: int = 0,
    disulfide_bridges: int = 0,
    resolution: str = "medium",
) -> MassResult:
    sigma = _RESOLUTION_SIGMA[resolution]  # KeyError on unknown resolution
    if not 0 <= disulfide_bridges <= sequence.upper().count("C") // 2:
        raise GlycomassError("Disulfide bridges must be nonnegative and require two cysteines each.")
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
        profile=iso.profile,
    )
