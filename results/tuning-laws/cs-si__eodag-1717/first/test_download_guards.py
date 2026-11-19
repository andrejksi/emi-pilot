"""Download behaviour that already holds and must keep holding."""

from __future__ import annotations

import os

import responses

from test_download_twice import IDS, PLUGINS, _product, _serve


def test_first_download_fetches_the_product_file(tmp_path):
    """Guard: the first download of a geodes product with extract=False makes one server request and leaves the zip file in output_dir."""
    plugin = PLUGINS.get_download_plugin(_product(IDS[1]))
    with responses.RequestsMock() as mock:
        _serve(mock, IDS[1])
        path = plugin.download(_product(IDS[1]), output_dir=str(tmp_path), extract=False)
        assert (path, len(mock.calls)) == (str(tmp_path / f"{IDS[1]}.zip"), 1)
    assert os.path.isfile(path)


def test_a_deleted_local_file_is_downloaded_again(tmp_path):
    """Guard: when the previously downloaded file has been deleted, downloading the product again requests it from the server again."""
    plugin = PLUGINS.get_download_plugin(_product(IDS[1]))
    with responses.RequestsMock() as mock:
        _serve(mock, IDS[1])
        path = plugin.download(_product(IDS[1]), output_dir=str(tmp_path), extract=False)
        os.remove(path)
        again = plugin.download(_product(IDS[1]), output_dir=str(tmp_path), extract=False)
        assert (again, len(mock.calls), os.path.isfile(again)) == (path, 2, True)
