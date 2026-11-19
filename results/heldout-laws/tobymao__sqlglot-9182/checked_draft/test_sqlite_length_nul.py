import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from _duck_eval import duckdb_value  # noqa: E402


def _sqlite(q):
    return sqlite3.connect(":memory:").execute(q).fetchone()[0]


def test_length_stops_at_nul_like_sqlite():
    """New: "SELECT LENGTH('a' || CHAR(0) || 'b')" transpiled from sqlite to duckdb computes 1, as SQLite does (A1, A3)."""
    assert duckdb_value("SELECT LENGTH('a' || CHAR(0) || 'b')") == 1


@pytest.mark.parametrize(
    "q",
    [
        "SELECT LENGTH('abc' || CHAR(0) || 'de')",
        "SELECT LENGTH(CHAR(0) || 'xyz')",
        "SELECT LENGTH('hello' || CHAR(0))",
    ],
)
def test_length_with_nul_matches_sqlite(q):
    """New: LENGTH of text containing CHAR(0), such as 'abc' || CHAR(0) || 'de', transpiled to duckdb computes the same count as SQLite (A1, A3)."""
    assert duckdb_value(q) == _sqlite(q)


@pytest.mark.parametrize("q", ["SELECT LENGTH('abc')", "SELECT LENGTH('a' || 'b')"])
def test_length_without_nul_is_full_length(q):
    """Guard: LENGTH of text without a NUL, such as LENGTH('abc'), transpiled to duckdb still computes its full length (A2, A3)."""
    assert duckdb_value(q) == _sqlite(q)
