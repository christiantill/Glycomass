from glycomass.core.composition import Composition


def test_add_and_scale():
    a = Composition(C=3, H=5, N=1, O=1, S=0)
    b = Composition(C=0, H=2, N=0, O=1, S=0)
    assert (a + b).counts == {"C": 3, "H": 7, "N": 1, "O": 2, "S": 0}
    assert (a * 2).counts == {"C": 6, "H": 10, "N": 2, "O": 2, "S": 0}


def test_formula_string_matches_legacy_format():
    assert Composition(C=34, H=53, N=7, O=15, S=0).formula() == "C34 H53 N7 O15 S0"


def test_to_brainpy_dict():
    assert Composition(C=6, H=12, N=0, O=6, S=0).to_brainpy() == {
        "C": 6, "H": 12, "N": 0, "O": 6, "S": 0,
    }


def test_supports_negative_counts():
    base = Composition(C=4, H=6, N=2, O=2, S=0)
    deamido = Composition(C=0, H=-1, N=-1, O=1, S=0)
    assert (base + deamido).counts == {"C": 4, "H": 5, "N": 1, "O": 3, "S": 0}
