from packaging.requirements import Requirement
from packaging.specifiers import Specifier, SpecifierSet


def test_requirement_parses_space_after_greater_equal_operator():
    """New: The requirement x===0,>= 0 parses as two version specifiers (A1)."""
    assert sorted(map(str, Requirement("x===0,>= 0").specifier)) == ["===0", ">=0"]


def test_requirement_parses_space_after_comma():
    """New: The requirement x===0, >=0 parses as two version specifiers (A2)."""
    assert sorted(map(str, Requirement("x===0, >=0").specifier)) == ["===0", ">=0"]


def test_requirement_parses_space_after_not_equal_operator():
    """New: The requirement x===0,!= 1.0 parses as two version specifiers (A3)."""
    assert sorted(map(str, Requirement("x===0,!= 1.0").specifier)) == ["!=1.0", "===0"]


def test_parenthesized_requirement_parses_spaced_specifier():
    """New: The requirement x (===0,>= 0) parses as two version specifiers (A4)."""
    assert sorted(map(str, Requirement("x (===0,>= 0)").specifier)) == ["===0", ">=0"]


def test_requirement_parses_specifiers_without_a_space():
    """Guard: The unspaced requirement x===0,>=0 continues to parse as two version specifiers (A5)."""
    assert sorted(map(str, Requirement("x===0,>=0").specifier)) == ["===0", ">=0"]


def test_direct_specifier_set_parses_spaced_specifier():
    """Guard: The direct SpecifierSet API continues to accept ===0,>= 0 as two specifiers (A6)."""
    assert sorted(map(str, SpecifierSet("===0,>= 0"))) == ["===0", ">=0"]


def test_standalone_specifier_keeps_a_comma_in_its_version():
    """Guard: The standalone arbitrary-equality specifier ===a,b keeps the comma in its version (A7)."""
    assert Specifier("===a,b").version == "a,b"
