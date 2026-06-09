from glycomass.core import constants as K
from glycomass.core.composition import Composition


def test_water_and_a_few_residues():
    assert Composition(C=0, H=2, N=0, O=1, S=0) == K.WATER
    assert K.AMINO_ACIDS["A"] == Composition(C=3, H=5, N=1, O=1, S=0)
    assert K.AMINO_ACIDS["W"] == Composition(C=11, H=10, N=2, O=1, S=0)
    assert Composition(C=5, H=8, N=2, O=2, S=1) == K.CARBAMIDOMETHYL_CYS


def test_all_twenty_amino_acids_present():
    assert set(K.AMINO_ACIDS) == set("ARNDCQEGHILKMFPSTWYV")


def test_peptide_composition_matches_legacy_formula():
    comp = K.WATER
    for aa in "PEPTIDE":
        comp = comp + K.AMINO_ACIDS[aa]
    assert comp.formula() == "C34 H53 N7 O15 S0"
