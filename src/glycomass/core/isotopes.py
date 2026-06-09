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
    for mz, inten in zip(peak_mz, peak_int, strict=True):
        profile += inten * np.exp(-((grid - mz) ** 2) / (2 * sigma)) / denom

    most_abundant_mz = float(grid[int(np.argmax(profile))]) + mz_shift
    mono_mz = float(peak_mz[0]) + mz_shift

    norm = float(peak_int.max())
    spectrum = Spectrum(
        mz=[float(mz) + mz_shift for mz in peak_mz],
        intensity=[float(i) / norm * 100 for i in peak_int],
    )
    return IsotopeResult(mono_mz, most_abundant_mz, spectrum)
