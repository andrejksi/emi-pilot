from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest

from eodag.api.product import EOProduct
from eodag.config import DEFAULT_PROVIDERS_DIR, load_config
from eodag.plugins.download.http import HTTPDownload


METADATA_NAME = "EOPMetadata.xml"
METADATA = b"<metadata>HRSEVIRI</metadata>"


def product_for(title, output_dir):
    config = load_config(str(DEFAULT_PROVIDERS_DIR / "dedl.yml"))["dedl"].download
    config.output_dir = str(output_dir)
    product = EOProduct(
        "dedl",
        {
            "id": title,
            "title": title,
            "eodag:download_link": f"https://dedl.example/{title}.zip",
        },
        collection="MSG_HRSEVIRI",
    )
    product.register_downloader(HTTPDownload("dedl", config), None)
    product.filename = f"{title}.zip"
    return product


def zip_payload(files):
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        for name, contents in files:
            archive.writestr(name, contents)
    return payload.getvalue()


def supply_downloaded_zip(monkeypatch, product, payload):
    product._stream = Mock()
    monkeypatch.setattr(
        product.downloader, "_raw_stream_download", lambda *a, **kw: iter([payload])
    )


def extracted_files(path):
    return {
        member.name: member.read_bytes()
        for member in Path(path).rglob("*")
        if member.is_file()
    }


def test_clean_download_extracts_both_hrseviri_files(tmp_path, monkeypatch):
    """New: a clean DEDL HRSEVIRI download extracts both the .nat data and EOPMetadata.xml for each product (A1)."""
    first_product = product_for("MSG_HRSEVIRI_0000", tmp_path)
    second_product = product_for("MSG_HRSEVIRI_0015", tmp_path)
    first_files = [(METADATA_NAME, METADATA), ("first.nat", b"first native data")]
    second_files = [("second.nat", b"second native data"), (METADATA_NAME, METADATA)]
    supply_downloaded_zip(monkeypatch, first_product, zip_payload(first_files))
    supply_downloaded_zip(monkeypatch, second_product, zip_payload(second_files))
    downloaded = [
        product.download(extract=True, delete_archive=False)
        for product in (first_product, second_product)
    ]

    assert [extracted_files(path) for path in downloaded] == [
        dict(first_files),
        dict(second_files),
    ]


@pytest.mark.parametrize("present_file", [METADATA_NAME, "product.nat"])
def test_recorded_download_returns_complete_hrseviri_product(
    tmp_path, monkeypatch, present_file
):
    """New: re-running a recorded DEDL HRSEVIRI download returns both files when its extracted folder contains only one and the ZIP is complete (A2)."""
    title = "MSG_HRSEVIRI_0000"
    product = product_for(title, tmp_path)
    files = {METADATA_NAME: METADATA, "product.nat": b"native data"}
    payload = zip_payload(files.items())
    (tmp_path / f"{title}.zip").write_bytes(payload)
    incomplete = tmp_path / title
    incomplete.mkdir()
    (incomplete / present_file).write_bytes(files[present_file])
    records = tmp_path / ".downloaded"
    records.mkdir()
    record = records / product.downloader.generate_record_hash(product)
    record.write_text(product.remote_location, encoding="utf-8")

    supply_downloaded_zip(monkeypatch, product, payload)
    path = product.download(extract=True, delete_archive=False)

    assert extracted_files(path) == files


def test_hrseviri_extraction_keeps_zip_when_archive_deletion_is_disabled(
    tmp_path, monkeypatch
):
    """Guard: a DEDL HRSEVIRI download with delete_archive=False keeps the complete ZIP beside the extracted product (A3)."""
    title = "MSG_HRSEVIRI_0000"
    product = product_for(title, tmp_path)
    payload = zip_payload(
        [(METADATA_NAME, METADATA), ("product.nat", b"native data")]
    )
    supply_downloaded_zip(monkeypatch, product, payload)
    path = Path(product.download(extract=True, delete_archive=False))

    assert path.is_dir()
    assert (path.parent / f"{title}.zip").read_bytes() == payload
