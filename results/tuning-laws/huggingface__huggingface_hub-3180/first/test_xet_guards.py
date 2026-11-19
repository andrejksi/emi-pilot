"""Parsing behaviour that already holds and must keep holding."""

from __future__ import annotations

import requests

from huggingface_hub.utils._xet import parse_xet_file_data_from_response


def _response(headers: dict) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response.headers.update(headers)
    return response


def test_missing_xet_headers_give_none():
    """Guard: a response without the X-Xet-Hash header gives None."""
    assert parse_xet_file_data_from_response(_response({"X-Xet-Refresh-Route": "/api/refresh"})) is None


def test_relative_refresh_route_is_kept():
    """Guard: a relative refresh route like /api/refresh is returned as is, with the file hash from X-Xet-Hash."""
    data = parse_xet_file_data_from_response(_response({"X-Xet-Hash": "sha256:abcdef", "X-Xet-Refresh-Route": "/api/refresh"}))
    assert (data.file_hash, data.refresh_route) == ("sha256:abcdef", "/api/refresh")


def test_a_response_of_none_gives_none():
    """Guard: passing None instead of a response gives None."""
    assert parse_xet_file_data_from_response(None) is None
