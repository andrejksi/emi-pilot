from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
import responses

from eodag.api.product import EOProduct
from eodag.config import load_provider_configs
from eodag.plugins.download.http import HTTPDownload


METADATA_NAME = "EOPMetadata.xml"
METADATA = b"<metadata>HRSEVIRI</metadata>"


def product_for(title, output_dir):
    config = load_provider_configs()["dedl"].download
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
    return product


def zip_payload(files):
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        for name, contents in files:
            archive.writestr(name, contents)
    return payload.getvalue()


def serve_zip(http, product, payload):
    http.get(
        product.remote_location,
        body=payload,
        content_type="application/zip",
        auto_calculate_content_length=True,
    )


def extracted_files(path):
    return {
        member.name: member.read_bytes()
        for member in Path(path).rglob("*")
        if member.is_file()
    }


def test_clean_download_extracts_both_hrseviri_files(tmp_path):
    """New: a clean DEDL HRSEVIRI download extracts both the .nat data and EOPMetadata.xml for each product (A1)."""
    first_product = product_for("MSG_HRSEVIRI_0000", tmp_path)
    second_product = product_for("MSG_HRSEVIRI_0015", tmp_path)
    first_files = [(METADATA_NAME, METADATA), ("first.nat", b"first native data")]
    second_files = [("second.nat", b"second native data"), (METADATA_NAME, METADATA)]
    with responses.RequestsMock() as http:
        serve_zip(http, first_product, zip_payload(first_files))
        serve_zip(http, second_product, zip_payload(second_files))
        downloaded = [
            product.download(extract=True, delete_archive=False)
            for product in (first_product, second_product)
        ]

    assert [extracted_files(path) for path in downloaded] == [
        dict(first_files),
        dict(second_files),
    ]


@pytest.mark.parametrize("present_file", [METADATA_NAME, "product.nat"])
def test_recorded_download_returns_complete_hrseviri_product(tmp_path, present_file):
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

    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        serve_zip(http, product, payload)
        assert extracted_files(
            product.download(extract=True, delete_archive=False)
        ) == files


def test_hrseviri_extraction_keeps_zip_when_archive_deletion_is_disabled(tmp_path):
    """Guard: a DEDL HRSEVIRI download with delete_archive=False keeps the complete ZIP beside the extracted product (A3)."""
    title = "MSG_HRSEVIRI_0000"
    product = product_for(title, tmp_path)
    payload = zip_payload(
        [(METADATA_NAME, METADATA), ("product.nat", b"native data")]
    )
    with responses.RequestsMock() as http:
        serve_zip(http, product, payload)
        path = product.download(extract=True, delete_archive=False)

    assert (Path(path).parent / f"{title}.zip").read_bytes() == payload
