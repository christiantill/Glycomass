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
    hex: int = 0,  # noqa: A002
    hexnac: int = 0,
    fuc: int = 0,  # noqa: A002
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
