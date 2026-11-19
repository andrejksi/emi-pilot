import sqlite3
from contextlib import closing

from sqlglot import transpile


def _split_part(value, separator, index):
    if value is None or separator is None or index is None:
        return None
    parts = value.split(separator) if separator else [value]
    if 1 <= index <= len(parts):
        return parts[index - 1]
    if -len(parts) <= index < 0:
        return parts[index]
    return ""


def _evaluate_translated_length(sql):
    """Evaluate scalar SQL with text length that counts NULs as DuckDB does."""
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.create_function("CHR", 1, chr)
        connection.create_function("LENGTH", 1, lambda value: None if value is None else len(value))
        connection.create_function("SPLIT_PART", 3, _split_part)
        connection.create_function("STRPOS", 2, lambda value, needle: value.find(needle) + 1)
        connection.create_function("TYPEOF", 1, lambda value: "BLOB" if isinstance(value, bytes) else "VARCHAR")
        return connection.execute(sql).fetchone()[0]


def test_sqlite_text_length_stops_at_nul_after_transpilation():
    """New: SQLite LENGTH for the text a followed by a NUL and b still returns 1 in DuckDB SQL (A1)."""
    assert _evaluate_translated_length(
        transpile("SELECT LENGTH('a' || CHAR(0) || 'b')", read="sqlite", write="duckdb")[0]
    ) == 1


def test_sqlite_text_length_counts_every_character_without_nul():
    """Guard: The translated LENGTH counts both characters of text without a NUL (A2)."""
    assert _evaluate_translated_length(
        transpile("SELECT LENGTH('ab')", read="sqlite", write="duckdb")[0]
    ) == 2


def test_sqlite_blob_length_does_not_truncate_zero_bytes():
    """Guard: The translated BLOB length counts all three bytes of the BLOB 610062 (A3)."""
    assert _evaluate_translated_length(
        transpile("SELECT LENGTH(X'610062')", read="sqlite", write="duckdb")[0]
    ) == 3
