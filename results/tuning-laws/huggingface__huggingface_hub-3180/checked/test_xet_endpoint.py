"""Rules the task adds: refresh routes pointing at huggingface.co follow the configured endpoint."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

import requests

from huggingface_hub.utils._xet import parse_xet_file_data_from_response

HASH = "a24f4ebae72bd0ae8ea5962912e838391092a7408702fa7c38291ab61026143e"
HF_ROUTE = "https://huggingface.co/api/models/HuggingFaceTB/SmolLM2-360M-Instruct/xet-read-token/cxx3xx"
MIRROR = "https://hf-mirror.example.com"
MIRROR_ROUTE = MIRROR + "/api/models/HuggingFaceTB/SmolLM2-360M-Instruct/xet-read-token/cxx3xx"


def _response(headers: dict) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response.headers.update(headers)
    return response


def test_header_refresh_route_is_rewritten_to_the_given_endpoint():
    """New: a huggingface.co X-Xet-Refresh-Route header is rewritten to start with the endpoint passed in, keeping its path and the file hash."""
    response = _response({"X-Xet-Hash": HASH, "X-Xet-Refresh-Route": HF_ROUTE})
    data = parse_xet_file_data_from_response(response, endpoint=MIRROR)
    assert (data.file_hash, data.refresh_route) == (HASH, MIRROR_ROUTE)


def test_link_refresh_route_is_rewritten_to_the_given_endpoint():
    """New: a huggingface.co refresh route given in the xet-auth Link header is rewritten to start with the endpoint passed in."""
    response = _response({"X-Xet-Hash": HASH, "Link": f'<{HF_ROUTE}>; rel="xet-auth"'})
    data = parse_xet_file_data_from_response(response, endpoint=MIRROR)
    assert (data.file_hash, data.refresh_route) == (HASH, MIRROR_ROUTE)


def test_a_route_on_another_host_is_left_alone():
    """New: a refresh route that does not start with https://huggingface.co is returned unchanged even when an endpoint is passed."""
    other = "https://cas.other.example/api/models/x/xet-read-token/abc"
    response = _response({"X-Xet-Hash": HASH, "X-Xet-Refresh-Route": other})
    assert parse_xet_file_data_from_response(response, endpoint=MIRROR).refresh_route == other


def _run_with_hf_endpoint(code: str) -> dict:
    """Run code in a fresh interpreter where HF_ENDPOINT is the mirror; it prints one JSON object."""
    env = {**os.environ, "HF_ENDPOINT": MIRROR}
    out = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)], env=env, capture_output=True, text=True, check=True
    ).stdout
    return json.loads(out.strip().splitlines()[-1])


def test_omitted_endpoint_uses_hf_endpoint():
    """New: with HF_ENDPOINT set to a mirror and no endpoint passed, a huggingface.co refresh route is rewritten to the mirror."""
    result = _run_with_hf_endpoint(
        f"""
        import json, requests
        from huggingface_hub.utils._xet import parse_xet_file_data_from_response
        r = requests.Response(); r.status_code = 200
        r.headers.update({{"X-Xet-Hash": "{HASH}", "X-Xet-Refresh-Route": "{HF_ROUTE}"}})
        print(json.dumps({{"route": parse_xet_file_data_from_response(r).refresh_route}}))
        """
    )
    assert result == {"route": MIRROR_ROUTE}


def test_get_hf_file_metadata_reports_the_mirror_refresh_route():
    """New: with HF_ENDPOINT set to a mirror, get_hf_file_metadata returns xet_file_data whose refresh_route uses the mirror, not huggingface.co."""
    result = _run_with_hf_endpoint(
        f"""
        import json, requests
        from unittest.mock import patch
        from huggingface_hub import file_download
        url = "{MIRROR}/HuggingFaceTB/SmolLM2-360M-Instruct/resolve/main/model.safetensors"
        r = requests.Response(); r.status_code = 200; r.url = url
        r.request = requests.Request("HEAD", url).prepare()
        r.headers.update({{"X-Xet-Hash": "{HASH}", "X-Xet-Refresh-Route": "{HF_ROUTE}",
                           "ETag": '"abc"', "X-Repo-Commit": "deadbeef", "Content-Length": "10"}})
        with patch.object(file_download, "_request_wrapper", return_value=r):
            meta = file_download.get_hf_file_metadata(url)
        print(json.dumps({{"route": meta.xet_file_data.refresh_route, "hash": meta.xet_file_data.file_hash}}))
        """
    )
    assert result == {"route": MIRROR_ROUTE, "hash": HASH}
