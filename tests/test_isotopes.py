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


def test_display_profile_preserves_legacy_gaussian_samples_and_maximum():
    import numpy as np
    from brainpy import isotopic_variants

    comp = Composition(C=34, H=53, N=7, O=15, S=0)
    sigma = 0.0005
    shift = 21.98977
    peaks = isotopic_variants(comp.to_brainpy(), npeaks=10, charge=1)
    grid = np.arange(peaks[0].mz - 1, peaks[-1].mz + 1, sigma)
    values = sum(p.intensity * np.exp(-(grid - p.mz)**2 / (2 * sigma))
                 / (np.sqrt(2 * np.pi) * sigma) for p in peaks)
    result = isotope_profile(comp, charge=1, npeaks=10, sigma=sigma, mz_shift=shift)
    x = np.array(result.profile.mz)
    y = np.array(result.profile.intensity)
    indices = np.rint((x - shift - grid[0]) / sigma).astype(int)
    assert len(grid) > 12000
    assert len(x) <= 12000
    assert np.all(np.diff(x) > 0)
    np.testing.assert_allclose(x, grid[indices] + shift)
    np.testing.assert_allclose(y, values[indices] / values.max() * 100)
    assert indices[0] == 0 and indices[-1] == len(grid) - 1
    assert x[y.argmax()] == result.most_abundant_mz
    assert y.max() == 100


def test_protein_resolution_changes_profile_but_not_isotope_centers():
    from glycomass.core.protein import protein_mass

    low = protein_mass("PEPTIDE", resolution="low")
    high = protein_mass("PEPTIDE", resolution="super high")
    assert low.spectrum == high.spectrum
    assert low.profile is not None and high.profile is not None
    assert low.profile != high.profile
    assert max(low.profile.intensity) == max(high.profile.intensity) == 100
