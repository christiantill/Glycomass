from glycomass.core.results import MassResult, Spectrum


def test_mass_result_holds_values():
    r = MassResult(
        mono_mz=800.3672,
        most_abundant_mz=800.3672,
        composition="C34 H53 N7 O15 S0",
        spectrum=Spectrum(mz=[800.3672, 800.8689], intensity=[100.0, 41.2]),
    )
    assert r.mono_mz == 800.3672
    assert r.composition == "C34 H53 N7 O15 S0"
    assert len(r.spectrum.mz) == len(r.spectrum.intensity) == 2
