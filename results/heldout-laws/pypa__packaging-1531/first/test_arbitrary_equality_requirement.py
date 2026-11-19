import pytest

from packaging.requirements import Requirement
from packaging.specifiers import Specifier, SpecifierSet


@pytest.mark.parametrize(
    "req, spec",
    [
        ("x===0,>= 0", "===0,>= 0"),
        ("x===0, >=0", "===0, >=0"),
        ("x===0,!= 1.0", "===0,!= 1.0"),
        ("x (===0,>= 0)", "===0,>= 0"),
    ],
)
def test_arbitrary_equality_then_spaced_specifier_parses(req, spec):
    """New: Requirement("x===0,>= 0"), "x===0, >=0", "x===0,!= 1.0" and "x (===0,>= 0)" parse with the same specifiers as SpecifierSet gives for that list (A1)."""
    r = Requirement(req)
    assert (r.name, r.specifier) == ("x", SpecifierSet(spec))


def test_arbitrary_equality_then_spaced_ge_has_two_specifiers():
    """New: Requirement("x===0,>= 0") has exactly the specifiers ===0 and >=0 (A1)."""
    assert set(Requirement("x===0,>= 0").specifier) == {Specifier("===0"), Specifier(">=0")}


def test_no_space_form_still_parses():
    """Guard: Requirement("x===0,>=0") still parses with specifier '===0,>=0' (A2)."""
    assert str(Requirement("x===0,>=0").specifier) == "===0,>=0"


def test_specifier_set_with_spaced_second_specifier():
    """Guard: SpecifierSet("===0,>= 0") still gives '===0,>=0' (A1)."""
    assert str(SpecifierSet("===0,>= 0")) == "===0,>=0"


def test_specifier_arbitrary_literal_may_hold_comma():
    """Guard: Specifier("===a,b") is still accepted with version "a,b" (A3)."""
    assert Specifier("===a,b").version == "a,b"
