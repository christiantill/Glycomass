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
    params: dict[str, object] = field(default_factory=dict)


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
    apparent double-count bug. We select the higher peak (the Pep+HexNAc fragment). No
    ground truth exists for the identifier; this is the scientifically-intended behavior.

    KNOWN LIMITATION: in a HexNAc ladder (Pep, Pep+HexNAc, Pep+2HexNAc — all 203 apart),
    Pep+2HexNAc is also a valid "higher peak of a 203-pair" and, if more intense, would be
    chosen, overestimating the peptide mass by one HexNAc. We keep the most-intense rule
    (most confident peak) pending real spectra to validate a ladder-aware heuristic.
    """
    # Binary-search the first lower peak with difference < the strict upper bound.
    # Subtract in the same direction as the original pairwise comparison so rounded
    # endpoints keep identical behavior. Memory is O(n), including for dense spectra.
    sorted_mz = np.sort(mz)
    left = np.zeros(mz.size, dtype=np.intp)
    right = np.full(mz.size, mz.size, dtype=np.intp)
    while np.any(left < right):
        active = np.flatnonzero(left < right)
        mid = (left[active] + right[active]) // 2
        inside = mz[active] - sorted_mz[mid] < HEXNAC_DIFF[1]
        right[active[inside]] = mid[inside]
        left[active[~inside]] = mid[~inside] + 1
    cand = np.flatnonzero((left < mz.size) & (mz > MIN_FRAGMENT_MZ))
    cand = cand[mz[cand] - sorted_mz[left[cand]] > HEXNAC_DIFF[0]]
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
    """Zero out oxonium-ion peaks and everything above peptide_mass + 1 (on copies)."""
    mz = mz.copy()
    intensity = intensity.copy()
    kill = mz > peptide_mass + 1
    for lo, hi in FILTER_WINDOWS:
        kill |= (mz > lo) & (mz < hi)
    intensity[kill] = 0.0
    mz[kill] = 0.0
    return mz, intensity


def process_mgf(in_path: str, out_path: str) -> dict[str, int | str]:
    """Read MGF, keep glycopeptide spectra, derive the deglycosylated peptide mass, strip
    glycan/oxonium peaks, rewrite each precursor to (peptide_mass, charge 1), write MGF."""
    spectra = read_mgf(in_path)
    total = len(spectra)
    glyco = [s for s in spectra if is_glycopeptide(s.mz)]
    cleaned: list[dict[str, object]] = []
    identified = 0
    for s in glyco:
        frag = find_pep_hexnac_mz(s.mz, s.intensity)
        if frag is None:
            continue
        identified += 1
        pep_mass = peptide_mass_from_fragment(frag)
        fmz, finten = filter_spectrum(s.mz, s.intensity, peptide_mass=pep_mass)
        new_params: dict[str, object] = {
            k: v for k, v in s.params.items() if k not in ("com", "username")
        }
        new_params["pepmass"] = (pep_mass, 1)
        new_params["charge"] = "1+"
        cleaned.append({"m/z array": fmz, "intensity array": finten, "params": new_params})
    mgf.write(cleaned, output=out_path)
    return {"total": total, "glycopeptides": len(glyco), "identified": identified, "output": out_path}
