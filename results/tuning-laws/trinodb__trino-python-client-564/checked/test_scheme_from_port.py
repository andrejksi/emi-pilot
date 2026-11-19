"""Rule the task adds: port 443 without any scheme means HTTPS."""

from trino import constants
from trino.dbapi import Connection


def test_tls_port_without_scheme_infers_https():
    """New: Connection("trino.server.io", port=443) with no scheme in the host and no http_scheme uses https."""
    assert Connection("trino.server.io", port=443).http_scheme == constants.HTTPS


def test_tls_port_without_scheme_keeps_port_443():
    """New: Connection("trino.server.io", port=443) connects to https on port 443."""
    conn = Connection("trino.server.io", port=443, user="user")
    assert (conn.http_scheme, conn.port) == ("https", 443)
