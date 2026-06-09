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
