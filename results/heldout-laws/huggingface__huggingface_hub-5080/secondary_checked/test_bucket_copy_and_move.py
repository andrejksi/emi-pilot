import json

import httpx2
import pytest

from huggingface_hub import HfFileSystem, constants
from huggingface_hub.utils import _http


BUCKET_ID = "trainer/outputs"
BUCKET_URL = f"hf://buckets/{BUCKET_ID}"
BUCKET_API = f"/api/buckets/{BUCKET_ID}"
SOURCE_HASH = "18" * 32


@pytest.fixture
def bucket_filesystem(monkeypatch):
    files = {}

    def file_info(path):
        return {"type": "file", "path": path, "size": 32, "xetHash": files[path]}

    def serve(request):
        path = request.url.path
        if request.method == "GET" and path == BUCKET_API:
            return httpx2.Response(
                200,
                json={
                    "id": BUCKET_ID,
                    "private": True,
                    "createdAt": "2026-01-01T00:00:00Z",
                    "size": 32 * len(files),
                    "totalFiles": len(files),
                },
            )
        if request.method == "GET" and path.startswith(f"{BUCKET_API}/tree"):
            prefix = path.removeprefix(f"{BUCKET_API}/tree").lstrip("/")
            entries = {}
            for name in files:
                if not prefix or name.startswith(f"{prefix}/"):
                    local_name = name.removeprefix(f"{prefix}/") if prefix else name
                    child, separator, _ = local_name.partition("/")
                    if separator and request.url.params.get("recursive") != "true":
                        child_path = f"{prefix}/{child}" if prefix else child
                        entries[child_path] = {"type": "directory", "path": child_path}
                    else:
                        entries[name] = file_info(name)
                elif name == prefix:
                    entries[name] = file_info(name)
            return httpx2.Response(200, json=list(entries.values()))
        if request.method == "POST" and path == f"{BUCKET_API}/paths-info":
            paths = json.loads(request.content)["paths"]
            return httpx2.Response(200, json=[file_info(name) for name in paths if name in files])
        if request.method == "POST" and path == f"{BUCKET_API}/batch":
            for line in request.content.splitlines():
                operation = json.loads(line)
                if operation["type"] == "copyFile":
                    assert operation["sourceRepoType"] == "bucket"
                    assert operation["sourceRepoId"] == BUCKET_ID
                    assert operation["xetHash"] in files.values()
                    files[operation["path"]] = operation["xetHash"]
                else:
                    assert operation["type"] == "deleteFile"
                    del files[operation["path"]]
            return httpx2.Response(200, json={"failed": []})
        pytest.fail(f"Unexpected bucket request: {request.method} {request.url}")

    monkeypatch.setattr(constants, "HF_HUB_DISABLE_TELEMETRY", True)
    with httpx2.Client(transport=httpx2.MockTransport(serve)) as client:
        monkeypatch.setattr(_http, "_GLOBAL_CLIENT", client)
        fs = HfFileSystem(endpoint="https://bucket.example", token=False, skip_instance_cache=True)
        yield fs, files


def test_cp_file_copies_by_xet_hash_within_bucket(bucket_filesystem):
    """New: copying a file within its bucket creates the destination from its Xet hash and keeps the source (A1)."""
    fs, files = bucket_filesystem
    files["outputs/run.log"] = SOURCE_HASH
    source = f"{BUCKET_URL}/outputs/run.log"
    destination = f"{BUCKET_URL}/outputs/run-copy.log"

    fs.cp_file(source, destination)

    assert fs.info(destination)["xet_hash"] == SOURCE_HASH
    assert fs.info(source)["xet_hash"] == SOURCE_HASH


def test_rename_publishes_checkpoint_metadata(bucket_filesystem):
    """New: renaming .metadata.tmp on an hf:// bucket publishes the checkpoint as .metadata (A2)."""
    fs, files = bucket_filesystem
    files["ckpt/.metadata.tmp"] = SOURCE_HASH
    source = f"{BUCKET_URL}/ckpt/.metadata.tmp"
    destination = f"{BUCKET_URL}/ckpt/.metadata"

    fs.rename(source, destination)

    assert fs.info(destination)["xet_hash"] == SOURCE_HASH
    assert not fs.exists(source)


def test_mv_publishes_a_dataset_parquet_shard(bucket_filesystem):
    """New: moving a temporary Parquet shard on an hf:// bucket publishes the shard and removes the temporary file (A3)."""
    fs, files = bucket_filesystem
    files["dataset/train-00000.parquet.tmp"] = SOURCE_HASH
    source = f"{BUCKET_URL}/dataset/train-00000.parquet.tmp"
    destination = f"{BUCKET_URL}/dataset/train-00000.parquet"

    fs.mv(source, destination)

    assert fs.info(destination)["xet_hash"] == SOURCE_HASH
    assert not fs.exists(source)
