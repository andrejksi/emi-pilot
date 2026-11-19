"""Scheme selection that already holds and must keep holding."""

from trino import constants
from trino.dbapi import Connection


def test_scheme_in_host_wins_over_explicit_scheme_and_port():
    """Guard: a scheme in the host wins: Connection("https://trino.server.io", port=8080, http_scheme="http") uses https."""
    assert Connection("https://trino.server.io", port=8080, http_scheme="http").http_scheme == "https"


def test_http_scheme_in_host_wins_over_tls_port():
    """Guard: Connection("http://trino.server.io", port=443) uses http, because the host's scheme comes first."""
    assert Connection("http://trino.server.io", port=443).http_scheme == "http"


def test_explicit_https_wins_over_the_default_port():
    """Guard: an explicit http_scheme="https" wins over port 8080."""
    assert Connection("trino.server.io", port=8080, http_scheme="https").http_scheme == "https"


def test_explicit_http_wins_over_the_tls_port():
    """Guard: an explicit http_scheme="http" wins over port 443."""
    assert Connection("trino.server.io", port=443, http_scheme="http").http_scheme == "http"


def test_default_port_infers_http():
    """Guard: Connection("trino.server.io", port=8080) with no scheme uses http."""
    assert Connection("trino.server.io", port=8080).http_scheme == constants.HTTP


def test_no_scheme_and_no_port_falls_back_to_http_on_8080():
    """Guard: Connection("trino.server.io") with no scheme and no port uses http on port 8080."""
    conn = Connection("trino.server.io")
    assert (conn.http_scheme, conn.port) == ("http", 8080)


def test_another_port_falls_back_to_http():
    """Guard: Connection("trino.server.io", port=9000) with no scheme falls back to http and keeps port 9000."""
    conn = Connection("trino.server.io", port=9000)
    assert (conn.http_scheme, conn.port) == ("http", 9000)


def test_https_host_without_port_uses_443():
    """Guard: Connection("https://trino.server.io") uses https on port 443 and strips the scheme from host."""
    conn = Connection("https://trino.server.io")
    assert (conn.http_scheme, conn.port, conn.host) == ("https", 443, "trino.server.io")


def test_other_connection_arguments_reach_the_client_session():
    """Guard: user, source, catalog and schema given to Connection still reach its client session unchanged."""
    conn = Connection("trino.server.io", port=443, user="user", source="laws", catalog="data", schema="schema")
    session = conn._client_session
    assert (session.user, session.source, session.catalog, session.schema) == ("user", "laws", "data", "schema")
