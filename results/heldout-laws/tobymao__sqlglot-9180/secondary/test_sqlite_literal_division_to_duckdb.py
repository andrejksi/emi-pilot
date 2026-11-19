import pytest

from sqlglot import parse_one, transpile
from sqlglot.optimizer.annotate_types import annotate_types


def test_unannotated_sqlite_integer_literals_use_duckdb_integer_division():
    """New: Directly transpiling SQLite SELECT 5 / 2 to DuckDB preserves the integer quotient 2 (A1)."""
    assert transpile("SELECT 5 / 2", read="sqlite", write="duckdb") == [
        "SELECT 5 // NULLIF(2, 0)"
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("SELECT -5 / 2", "SELECT -5 // NULLIF(2, 0)"),
        ("SELECT 5 / -2", "SELECT 5 // NULLIF(-2, 0)"),
    ],
)
def test_unannotated_sqlite_negative_integer_quotients_truncate_toward_zero(source, expected):
    """New: A negative quotient of SQLite integer literals remains integer division in DuckDB (A2)."""
    assert transpile(source, read="sqlite", write="duckdb") == [expected]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("SELECT 5.0 / 2", "SELECT 5.0 / NULLIF(2, 0)"),
        ("SELECT 5 / 2.0", "SELECT 5 / NULLIF(2.0, 0)"),
    ],
)
def test_sqlite_decimal_literal_keeps_floating_point_division(source, expected):
    """Guard: A decimal literal on either side of SQLite division keeps DuckDB floating-point division (A3)."""
    assert transpile(source, read="sqlite", write="duckdb") == [expected]


def test_sqlite_integer_division_by_zero_keeps_null_result():
    """Guard: Directly transpiling SQLite division by zero to DuckDB preserves the NULL result (A4)."""
    assert transpile("SELECT 5 / 0", read="sqlite", write="duckdb") in (
        ["SELECT 5 / NULLIF(0, 0)"],
        ["SELECT 5 // NULLIF(0, 0)"],
        ["SELECT NULL"],
    )


def test_type_annotated_sqlite_integer_division_still_transpiles_correctly():
    """Guard: Type-annotated SQLite integer division still uses DuckDB integer division (A5)."""
    expression = parse_one("SELECT 5 / 2", read="sqlite")
    assert annotate_types(expression, dialect="sqlite").sql("duckdb") == (
        "SELECT 5 // NULLIF(2, 0)"
    )
