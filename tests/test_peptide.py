from glycomass.core.peptide import peptide_mass


def test_bare_peptide():
    r = peptide_mass("PEPTIDE", charge=1)
    assert abs(r.mono_mz - 800.3672) < 1e-3
    assert r.composition == "C34 H53 N7 O15 S0"


def test_glycopeptide_with_carbamidomethyl():
    # NLTSVCWK + Hex5HexNAc4Fuc1Sia2, z=2, carbamidomethyl -> 1679.6678 (fixture)
    r = peptide_mass("NLTSVCWK", hex=5, hexnac=4, fuc=1, sia=2, charge=2, carbamidomethyl=True)
    assert abs(r.mono_mz - 1679.6678) < 1e-3


def test_deamidation_shifts_mass():
    # NLTSVK, z=1, deamidation 1 -> 662.3719 ; deamidation 2 -> 663.3559 (fixtures)
    assert abs(peptide_mass("NLTSVK", charge=1, deamidation=1).mono_mz - 662.3719) < 1e-3
    assert abs(peptide_mass("NLTSVK", charge=1, deamidation=2).mono_mz - 663.3559) < 1e-3


def test_non_amino_acid_chars_ignored():
    assert peptide_mass("PEP-TIDE", charge=1).mono_mz == peptide_mass("PEPTIDE", charge=1).mono_mz
