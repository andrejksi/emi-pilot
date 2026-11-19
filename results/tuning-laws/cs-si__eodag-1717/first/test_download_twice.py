"""Rules for downloading the same products twice into the same output directory."""

from __future__ import annotations

import io
import os
import zipfile

import responses

from eodag.api.product import EOProduct
from eodag.api.search_result import SearchResult
from eodag.config import load_default_config
from eodag.plugins.manager import PluginManager

IDS = [
    "S2A_MSIL1C_20231006T102911_N0510_R108_T31TFK_20241102T002017",
    "S2A_MSIL1C_20231006T102911_N0509_R108_T31TFK_20231006T141008",
]
BASE_URL = "https://geodes-portal.cnes.fr/api/download/URN:FEATURE:DATA:gdh:{}:V1/files/data"

_buf = io.BytesIO()
with zipfile.ZipFile(_buf, "w") as _zf:
    _zf.writestr("MTD.xml", "<metadata/>")
ZIP_BYTES = _buf.getvalue()

PLUGINS = PluginManager(load_default_config())


def _product(pid: str) -> EOProduct:
    """A fresh geodes S2_MSI_L1C product, as a new search would return it."""
    product = EOProduct("geodes", dict(geometry="POINT (0 0)", title=pid, id=pid))
    product.product_type = "S2_MSI_L1C"
    product.location = product.remote_location = BASE_URL.format(pid)
    return product


def _serve(mock: responses.RequestsMock, pid: str) -> None:
    mock.add(
        responses.GET,
        BASE_URL.format(pid),
        body=ZIP_BYTES,
        headers={
            "content-disposition": f'attachment; filename="{pid}.zip"',
            "content-length": str(len(ZIP_BYTES)),
        },
    )


def _download_all_twice(output_dir: str):
    """Run download_all(extract=False) on fresh search results twice; return both path lists and the request count."""
    plugin = PLUGINS.get_download_plugin(_product(IDS[0]))
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        for pid in IDS:
            _serve(mock, pid)
        first = plugin.download_all(SearchResult([_product(p) for p in IDS]), output_dir=output_dir, extract=False)
        second = plugin.download_all(SearchResult([_product(p) for p in IDS]), output_dir=output_dir, extract=False)
        return first, second, len(mock.calls)


def test_second_download_all_does_not_download_again(tmp_path):
    """New: running download_all(extract=False) twice on the same two geodes products into the same output_dir requests each product from the server only once."""
    _, _, requests_made = _download_all_twice(str(tmp_path))
    assert requests_made == 2


def test_second_download_all_returns_the_files_already_there(tmp_path):
    """Guard: the second download_all(extract=False) returns the same local paths as the first one."""
    first, second, _ = _download_all_twice(str(tmp_path))
    assert sorted(second) == sorted(first)


def test_second_single_download_does_not_download_again(tmp_path):
    """New: downloading one geodes product with extract=False, then the same product again from a new search result, makes one server request and returns the same path."""
    plugin = PLUGINS.get_download_plugin(_product(IDS[0]))
    with responses.RequestsMock() as mock:
        _serve(mock, IDS[0])
        first = plugin.download(_product(IDS[0]), output_dir=str(tmp_path), extract=False)
        second = plugin.download(_product(IDS[0]), output_dir=str(tmp_path), extract=False)
        assert (second, len(mock.calls)) == (first, 1)
