import pytest

from glycomass.core.errors import NegativeIonSodiumError
from glycomass.core.glycan import glycan_mass


def test_native_glycan():
    # Hex5HexNAc4Fuc1Sia2, z=1 -> 2369.8482, C90 H148 N6 O66 S0 (fixture)
    r = glycan_mass(hex=5, hexnac=4, fuc=1, sia=2, charge=1)
    assert abs(r.mono_mz - 2369.8482) < 1e-3
    assert r.composition == "C90 H148 N6 O66 S0"


def test_sodium_adduct_shift():
    # Hex5HexNAc4, z=1: native 1641.5994 ; sodium 1663.5892 (fixtures)
    assert abs(glycan_mass(hex=5, hexnac=4, charge=1).mono_mz - 1641.5994) < 1e-3
    assert abs(glycan_mass(hex=5, hexnac=4, charge=1, sodium=True).mono_mz - 1663.5892) < 1e-3


def test_permethyl_and_peracetyl():
    # Hex5HexNAc4Fuc1Sia2, z=1: Permethyl 2944.4898 ; Peracetly 3756.1968 (fixtures)
    assert abs(glycan_mass(5, 4, 1, 2, charge=1, modification="Permethyl").mono_mz - 2944.4898) < 1e-3
    assert abs(glycan_mass(5, 4, 1, 2, charge=1, modification="Peracetly").mono_mz - 3756.1968) < 1e-3


def test_sodium_in_negative_mode_raises():
    with pytest.raises(NegativeIonSodiumError):
        glycan_mass(hex=5, hexnac=4, charge=-1, sodium=True)
