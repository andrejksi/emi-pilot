import math
import sqlite3

import pytest

import sqlglot
from sqlglot import exp


def _eval(node):
    """Evaluate a constant DuckDB expression tree with DuckDB division semantics."""
    if isinstance(node, exp.Paren):
        return _eval(node.this)
    if isinstance(node, exp.Literal) and not node.is_string:
        text = node.this
        return int(text) if node.is_int else float(text)
    if isinstance(node, exp.Null):
        return None
    if isinstance(node, exp.Neg):
        v = _eval(node.this)
        return None if v is None else -v
    if isinstance(node, exp.Nullif):
        a, b = _eval(node.this), _eval(node.expression)
        return None if a == b else a
    if isinstance(node, exp.Cast):
        v = _eval(node.this)
        if v is None:
            return None
        if node.to.is_type(*exp.DataType.INTEGER_TYPES):
            return int(v) if isinstance(v, int) else int(round(v))
        if node.to.is_type(*exp.DataType.REAL_TYPES):
            return float(v)
        raise AssertionError(f"unsupported cast {node.sql('duckdb')}")
    if isinstance(node, exp.Trunc):
        v = _eval(node.this)
        return None if v is None else math.trunc(v)
    if isinstance(node, (exp.Div, exp.IntDiv)):
        a, b = _eval(node.this), _eval(node.expression)
        if a is None or b is None:
            return None
        if isinstance(node, exp.IntDiv):
            return int(a / b) if isinstance(a, int) and isinstance(b, int) else math.floor(a / b)
        return a / b  # DuckDB "/" is always floating-point division
    raise AssertionError(f"unsupported node {type(node).__name__}: {node.sql('duckdb')}")


def _duckdb_value(sql):
    translated = sqlglot.transpile(sql, read="sqlite", write="duckdb")[0]
    tree = sqlglot.parse_one(translated, read="duckdb")
    return _eval(tree.expressions[0])


def _sqlite_value(sql):
    return sqlite3.connect(":memory:").execute(sql).fetchone()[0]


def test_integer_literal_division_matches_sqlite():
    """New: "SELECT 5 / 2" transpiled from sqlite to duckdb computes 2, as SQLite does (A1, A6)."""
    assert _duckdb_value("SELECT 5 / 2") == 2


@pytest.mark.parametrize("sql", ["SELECT -5 / 2", "SELECT 5 / -2", "SELECT -7 / 2"])
def test_negative_integer_literal_division_matches_sqlite(sql):
    """New: negative integer quotients such as "SELECT -5 / 2" transpiled to duckdb compute the same value as SQLite (A2, A6)."""
    assert _duckdb_value(sql) == _sqlite_value(sql)


def test_decimal_operand_keeps_float_division():
    """Guard: "SELECT 5.0 / 2" transpiled from sqlite to duckdb still computes 2.5 (A3, A6)."""
    assert _duckdb_value("SELECT 5.0 / 2") == 2.5


def test_integer_division_by_zero_is_null():
    """Guard: "SELECT 5 / 0" transpiled from sqlite to duckdb still computes NULL (A4, A6)."""
    assert _duckdb_value("SELECT 5 / 0") is None


def test_annotated_integer_division_still_integer():
    """Guard: "SELECT CAST(5 AS INTEGER) / CAST(2 AS INTEGER)" transpiled from sqlite to duckdb still computes 2 (A5, A6)."""
    assert _duckdb_value("SELECT CAST(5 AS INTEGER) / CAST(2 AS INTEGER)") == 2
