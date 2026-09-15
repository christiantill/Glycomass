import pytest

from glycomass.core.composition import Composition, parse_composition_delta
from glycomass.core.errors import InvalidCompositionError


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



@pytest.mark.parametrize(("text", "counts"), [
    ("C2H5O", {"C": 2, "H": 5, "O": 1}),
    ("-C2-H6", {"C": -2, "H": -6}),
    ("-C2H6", {"C": -2, "H": -6}),
    ("C2H5O-H2O", {"C": 2, "H": 3}),
    ("+C2-H2O+N", {"C": 2, "H": -2, "O": -1, "N": 1}),
    (" C 2 ", {"C": 2}),
    ("C", {"C": 1}),
    ("CC", {"C": 2}),
    ("−H2O", {"H": -2, "O": -1}),
    ("", {}),
])
def test_parse_composition_delta(text, counts):
    expected = {"C": 0, "H": 0, "N": 0, "O": 0, "S": 0, **counts}
    assert parse_composition_delta(text).counts == expected


@pytest.mark.parametrize(("text", "message"), [
    ("Na", "Unsupported element 'Na'"),
    ("c2", "Could not read"),
    ("2C", "Could not read"),
    ("C-", "Could not read"),
    ("C2X", "Unsupported element 'X'"),
    ("C" * 65, "limited to 64"),
])
def test_parse_composition_delta_rejects(text, message):
    with pytest.raises(InvalidCompositionError, match=message):
        parse_composition_delta(text)
