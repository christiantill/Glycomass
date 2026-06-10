import numpy as np

from glycomass.core.identifier import pipeline as P


def test_is_glycopeptide_detects_oxonium():
    assert P.is_glycopeptide(np.array([100.0, 366.14, 900.0])) is True
    assert P.is_glycopeptide(np.array([100.0, 657.2, 900.0])) is True
    assert P.is_glycopeptide(np.array([100.0, 500.0, 900.0])) is False


def test_find_pep_hexnac_mz_picks_higher_peak_of_hexnac_pair():
    mz = np.array([400.0, 800.0, 1003.0794])
    inten = np.array([10.0, 50.0, 90.0])
    assert abs(P.find_pep_hexnac_mz(mz, inten) - 1003.0794) < 1e-3


def test_find_pep_hexnac_mz_none_when_no_pair():
    mz = np.array([400.0, 500.0, 600.0])
    inten = np.array([10.0, 20.0, 30.0])
    assert P.find_pep_hexnac_mz(mz, inten) is None


def test_peptide_mass_subtracts_one_hexnac():
    assert abs(P.peptide_mass_from_fragment(1003.0794) - 800.0) < 1e-6


def test_precursor_neutral_mass_formula():
    # Retained for legacy parity (not wired into output); pin the formula so the
    # constant + helper aren't silently broken: mz*z - z*proton + proton.
    from glycomass.core.identifier.constants import PROTON

    assert abs(P.precursor_neutral_mass(401.0, 2) - (401.0 * 2 - 2 * PROTON + PROTON)) < 1e-9


def test_filter_spectrum_zeros_oxonium_and_above_peptide():
    mz = np.array([292.2, 366.2, 800.0, 900.0])
    inten = np.array([5.0, 5.0, 5.0, 5.0])
    fmz, finten = P.filter_spectrum(mz, inten, peptide_mass=850.0)
    assert finten[0] == 0 and finten[1] == 0 and finten[3] == 0
    assert finten[2] == 5.0


def test_process_mgf_end_to_end(tmp_path):
    from pathlib import Path
    src = Path(__file__).parent / "sample.mgf"
    out = tmp_path / "cleaned.mgf"
    summary = P.process_mgf(str(src), str(out))
    assert summary["total"] == 2
    assert summary["glycopeptides"] == 1
    assert summary["identified"] == 1
    assert out.exists()
    reread = P.read_mgf(str(out))
    assert len(reread) == 1
    assert abs(reread[0].pepmass - 800.0) < 1e-2
    assert reread[0].charge == 1
