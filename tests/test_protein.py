import pytest

from glycomass.core.protein import protein_mass


def test_protein_medium_resolution():
    # ACDEFGHIKLMNPQRSTVWY, z=5, medium -> mono 479.8323 (fixture)
    r = protein_mass("ACDEFGHIKLMNPQRSTVWY", charge=5, resolution="medium")
    assert abs(r.mono_mz - 479.8323) < 1e-3


def test_disulfide_bridges_subtract_two_hydrogens_each():
    # CCACCAGGKL, z=3, medium: 0 bridges 310.1218; 1 -> 309.4499; 2 -> 308.778 (fixtures)
    base = protein_mass("CCACCAGGKL", charge=3, resolution="medium", disulfide_bridges=0)
    one = protein_mass("CCACCAGGKL", charge=3, resolution="medium", disulfide_bridges=1)
    two = protein_mass("CCACCAGGKL", charge=3, resolution="medium", disulfide_bridges=2)
    assert abs(base.mono_mz - 310.1218) < 1e-3
    assert abs(one.mono_mz - 309.4499) < 1e-3
    assert abs(two.mono_mz - 308.778) < 1e-3


def test_unknown_resolution_raises():
    with pytest.raises(KeyError):
        protein_mass("PEPTIDE", charge=1, resolution="ultra")
