import os
import zipfile
from tempfile import TemporaryDirectory

from eodag.config import PluginConfig
from eodag.plugins.download.http import HTTPDownload


def _plugin(archive_depth):
    config = PluginConfig.from_mapping(
        {
            "type": "HTTPDownload",
            "extract": True,
            "archive_depth": archive_depth,
            "output_dir": "/tmp",
        }
    )
    return HTTPDownload("dedl", config)


def _make_zip(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def _all_files(root):
    found = set()
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            found.add(os.path.relpath(os.path.join(dirpath, f), root))
    return found


def test_hrseviri_zip_with_depth_2_extracts_both_metadata_and_nat():
    """New: a zip holding EOPMetadata.xml and a .nat file, downloaded with archive_depth 2 and extract, ends up as a folder containing both files (A1)."""
    with TemporaryDirectory() as out:
        arch = os.path.join(out, "MSG4-SEVI-MSG15-0100-NA-20260711001242.zip")
        _make_zip(
            arch,
            {
                "EOPMetadata.xml": "<xml/>",
                "MSG4-SEVI-MSG15-0100-NA-20260711001242.nat": "data",
            },
        )
        path = _plugin(2)._finalize(
            arch, output_dir=out, extract=True, delete_archive=False
        )
        names = {os.path.basename(f) for f in _all_files(path)}
        assert names == {
            "EOPMetadata.xml",
            "MSG4-SEVI-MSG15-0100-NA-20260711001242.nat",
        }


def test_hrseviri_zip_with_depth_2_keeps_archive_when_delete_archive_false():
    """Guard: with extract and delete_archive=False the downloaded zip stays next to the extracted folder (A2)."""
    with TemporaryDirectory() as out:
        arch = os.path.join(out, "PROD.zip")
        _make_zip(arch, {"PROD/EOPMetadata.xml": "<xml/>", "PROD/PROD.nat": "data"})
        path = _plugin(2)._finalize(
            arch, output_dir=out, extract=True, delete_archive=False
        )
        assert os.path.isfile(arch) and os.path.isdir(path)
