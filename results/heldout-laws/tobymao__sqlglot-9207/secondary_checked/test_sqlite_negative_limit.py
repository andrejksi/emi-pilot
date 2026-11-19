from sqlglot import transpile


SQLITE_UNBOUNDED_OFFSET = "SELECT x FROM t LIMIT -1 OFFSET 5"


def test_sqlite_negative_limit_with_offset_transpiles_to_duckdb():
    """New: DuckDB receives LIMIT ALL OFFSET 5 for SQLite LIMIT -1 OFFSET 5 (A1)."""
    assert transpile(SQLITE_UNBOUNDED_OFFSET, read="sqlite", write="duckdb") == [
        "SELECT x FROM t LIMIT ALL OFFSET 5"
    ]


def test_sqlite_negative_limit_with_offset_transpiles_to_postgres():
    """New: PostgreSQL receives LIMIT ALL OFFSET 5 for SQLite LIMIT -1 OFFSET 5 (A2)."""
    assert transpile(SQLITE_UNBOUNDED_OFFSET, read="sqlite", write="postgres") == [
        "SELECT x FROM t LIMIT ALL OFFSET 5"
    ]


def test_sqlite_negative_limit_with_offset_transpiles_to_tsql():
    """New: T-SQL receives OFFSET 5 ROWS without a FETCH clause for SQLite LIMIT -1 OFFSET 5 (A3)."""
    assert transpile(SQLITE_UNBOUNDED_OFFSET, read="sqlite", write="tsql") == [
        "SELECT x FROM t ORDER BY (SELECT NULL) OFFSET 5 ROWS"
    ]


def test_a_different_negative_sqlite_limit_also_has_no_upper_bound():
    """New: SQLite LIMIT -2 also means no upper bound (A4)."""
    assert transpile("SELECT x FROM t LIMIT -2 OFFSET 5", read="sqlite", write="duckdb") == [
        "SELECT x FROM t LIMIT ALL OFFSET 5"
    ]


def test_postgres_offset_without_limit_keeps_sqlite_unbounded_limit():
    """Guard: PostgreSQL OFFSET 5 still uses LIMIT -1 OFFSET 5 in SQLite (A5)."""
    assert transpile("SELECT x FROM t OFFSET 5", read="postgres", write="sqlite") == [
        SQLITE_UNBOUNDED_OFFSET
    ]


def test_postgres_offset_without_limit_round_trips_via_sqlite_to_duckdb():
    """New: The PostgreSQL-to-SQLite-to-DuckDB round trip keeps offset 5 and no upper bound (A6)."""
    sqlite_sql = transpile("SELECT x FROM t OFFSET 5", read="postgres", write="sqlite")[0]
    assert transpile(sqlite_sql, read="sqlite", write="duckdb") == [
        "SELECT x FROM t LIMIT ALL OFFSET 5"
    ]


def test_sqlite_zero_limit_remains_zero_in_duckdb():
    """Guard: SQLite LIMIT 0 still sets the limit to zero in DuckDB (A7)."""
    assert transpile("SELECT x FROM t LIMIT 0 OFFSET 5", read="sqlite", write="duckdb") == [
        "SELECT x FROM t LIMIT 0 OFFSET 5"
    ]
