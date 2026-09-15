import pytest

from glycomass.core.errors import InvalidCompositionError, NegativeIonSodiumError
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


def test_unknown_modification_falls_back_to_native():
    native = glycan_mass(5, 4, 1, 2, charge=1, modification="None")
    bogus = glycan_mass(5, 4, 1, 2, charge=1, modification="Permethy")  # typo -> native
    assert bogus.mono_mz == native.mono_mz
    assert bogus.composition == native.composition


# Procainamide values are independently derived, not legacy fixtures: C13H21N3 label
# increment (+219.1735 Da, Waters app note 720004212); FA2G1-ProA [M+2H]2+ reported
# as m/z 922.8 by the Ludger CPROC-FA2G1 standard.
def test_procainamide_label_fa2():
    z1 = glycan_mass(3, 4, 1, 0, charge=1, modification="Label_ProA")
    assert z1.composition == "C69 H115 N7 O40 S0"
    assert abs(z1.mono_mz - 1682.7253) < 1e-3
    assert abs(glycan_mass(3, 4, 1, 0, charge=2, modification="Label_ProA").mono_mz - 841.8663) < 1e-3
    native = glycan_mass(3, 4, 1, 0, charge=1)
    assert abs((z1.mono_mz - native.mono_mz) - 219.1735) < 1e-3


def test_procainamide_label_matches_ludger_fa2g1():
    assert abs(glycan_mass(4, 4, 1, 0, charge=2, modification="Label_ProA").mono_mz - 922.8) < 0.1


def test_custom_modification_matches_procainamide_label():
    label = glycan_mass(3, 4, 1, 0, charge=2, modification="Label_ProA")
    custom = glycan_mass(3, 4, 1, 0, charge=2, custom_modification="C13H21N3")
    assert custom.composition == label.composition
    assert custom.mono_mz == label.mono_mz


def test_custom_modification_stacks_on_derivatization():
    base = glycan_mass(5, 4, charge=1, modification="Permethyl")
    shifted = glycan_mass(5, 4, charge=1, modification="Permethyl", custom_modification="-C2-H6")
    assert shifted.composition == "C89 H156 N4 O46 S0"
    assert base.composition == "C91 H162 N4 O46 S0"


def test_empty_custom_modification_is_unchanged():
    assert glycan_mass(5, 4, 1, 2, custom_modification="  ") == glycan_mass(5, 4, 1, 2)


def test_custom_modification_cannot_remove_missing_atoms():
    with pytest.raises(InvalidCompositionError, match="removes more N"):
        glycan_mass(1, 0, custom_modification="-N")
    with pytest.raises(InvalidCompositionError, match="no atoms"):
        glycan_mass(0, 0, custom_modification="-H2O")
