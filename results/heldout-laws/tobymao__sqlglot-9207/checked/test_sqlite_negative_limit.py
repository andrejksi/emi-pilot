import pytest

import sqlglot

SQLITE = "SELECT x FROM t LIMIT -1 OFFSET 5"
POSTGRES_ALL = "SELECT x FROM t LIMIT ALL OFFSET 5"


@pytest.mark.parametrize("write", ["duckdb", "postgres", "tsql", "mysql"])
def test_sqlite_limit_minus_one_matches_postgres_limit_all(write):
    """New: "SELECT x FROM t LIMIT -1 OFFSET 5" read from sqlite gives the same output as "LIMIT ALL OFFSET 5" read from postgres, for duckdb, postgres, tsql and mysql (A1)."""
    assert sqlglot.transpile(SQLITE, read="sqlite", write=write) == sqlglot.transpile(POSTGRES_ALL, read="postgres", write=write)


def test_sqlite_limit_minus_one_to_duckdb():
    """New: "SELECT x FROM t LIMIT -1 OFFSET 5" from sqlite is written for duckdb as "SELECT x FROM t LIMIT ALL OFFSET 5" (A1)."""
    assert sqlglot.transpile(SQLITE, read="sqlite", write="duckdb") == ["SELECT x FROM t LIMIT ALL OFFSET 5"]


def test_sqlite_limit_minus_one_to_tsql():
    """New: "SELECT x FROM t LIMIT -1 OFFSET 5" from sqlite is written for tsql with "OFFSET 5 ROWS" and no FETCH (A1)."""
    assert sqlglot.transpile(SQLITE, read="sqlite", write="tsql") == ["SELECT x FROM t ORDER BY (SELECT NULL) OFFSET 5 ROWS"]


def test_postgres_sqlite_duckdb_round_trip():
    """New: postgres "SELECT x FROM t OFFSET 5" sent through sqlite and then to duckdb gives "SELECT x FROM t LIMIT ALL OFFSET 5" (A2)."""
    via_sqlite = sqlglot.transpile("SELECT x FROM t OFFSET 5", read="postgres", write="sqlite")[0]
    assert sqlglot.transpile(via_sqlite, read="sqlite", write="duckdb") == ["SELECT x FROM t LIMIT ALL OFFSET 5"]


def test_postgres_offset_written_as_limit_minus_one_for_sqlite():
    """Guard: postgres "SELECT x FROM t OFFSET 5" is still written for sqlite as "SELECT x FROM t LIMIT -1 OFFSET 5" (A2)."""
    assert sqlglot.transpile("SELECT x FROM t OFFSET 5", read="postgres", write="sqlite") == ["SELECT x FROM t LIMIT -1 OFFSET 5"]
