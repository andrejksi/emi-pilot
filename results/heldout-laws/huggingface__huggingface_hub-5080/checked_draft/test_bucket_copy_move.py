"""Rules for cp_file / mv / rename on bucket paths of HfFileSystem (offline, with an in-memory bucket store)."""

import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import pytest

from huggingface_hub._buckets import BucketFile, BucketFolder, BucketInfo
from huggingface_hub.errors import BucketNotFoundError
from huggingface_hub.hf_file_system import HfFileSystem


BUCKET = "user/ckpts"


class _FakeBucketStore:
    """In-memory buckets: {bucket_id: {path: bytes}}, with xet hash = sha256(content)."""

    def __init__(self):
        self.buckets: dict[str, dict[str, bytes]] = {}
        self.blobs: dict[str, bytes] = {}

    def put(self, bucket_id, path, content: bytes):
        h = hashlib.sha256(content).hexdigest()
        self.blobs[h] = content
        self.buckets.setdefault(bucket_id, {})[path] = content

    def _file(self, path, content):
        return BucketFile(
            type="file",
            path=path,
            size=len(content),
            xetHash=hashlib.sha256(content).hexdigest(),
            mtime="2026-01-01T00:00:00.000Z",
            uploadedAt="2026-01-01T00:00:00.000Z",
        )

    # --- HfApi methods ---
    def bucket_info(self, bucket_id, *args, **kwargs):
        if bucket_id not in self.buckets:
            raise _not_found(bucket_id)
        files = self.buckets[bucket_id]
        return BucketInfo(
            id=bucket_id,
            private=False,
            createdAt="2026-01-01T00:00:00.000Z",
            size=sum(len(c) for c in files.values()),
            totalFiles=len(files),
        )

    def list_bucket_tree(self, bucket_id, prefix=None, *args, recursive=None, **kwargs):
        files = self.buckets[bucket_id]
        prefix = (prefix or "").strip("/")
        out = []
        folders = set()
        for path, content in sorted(files.items()):
            if prefix and not path.startswith(prefix):
                continue
            if recursive or path == prefix:
                out.append(self._file(path, content))
                continue
            rest = path[len(prefix) :].lstrip("/") if prefix else path
            if prefix and path[len(prefix) : len(prefix) + 1] not in ("/",):
                # lexical match only (e.g. "dat" vs "data/..."): mimic server, return top entries of that level
                parent = str(PurePosixPath(prefix).parent)
                parent = "" if parent == "." else parent
                rest = path[len(parent) :].lstrip("/") if parent else path
                base = parent
            else:
                base = prefix
            if "/" in rest:
                folder = (base + "/" if base else "") + rest.split("/", 1)[0]
                if folder not in folders:
                    folders.add(folder)
                    out.append(BucketFolder(type="directory", path=folder, uploaded_at=None))
            else:
                out.append(self._file(path, content))
        return iter(out)

    def get_bucket_paths_info(self, bucket_id, paths, *args, **kwargs):
        files = self.buckets[bucket_id]
        return iter([self._file(p, files[p]) for p in paths if p in files])

    def get_bucket_file_metadata(self, bucket_id, path, *args, **kwargs):  # pragma: no cover - best effort
        return self._file(path, self.buckets[bucket_id][path])

    def batch_bucket_files(self, bucket_id, *, add=None, copy=None, delete=None, **kwargs):
        from huggingface_hub._buckets import _BucketAddFile, _BucketCopyFile, _BucketDeleteFile

        for item in add or []:
            if isinstance(item, _BucketAddFile):
                source, dest = item.source, item.destination
            else:
                source, dest = item
            if not isinstance(source, bytes):
                source = Path(source).read_bytes()
            self.put(bucket_id, dest, source)
        for item in copy or []:
            if isinstance(item, _BucketCopyFile):
                xet_hash, dest = item.xet_hash, item.destination
            else:
                _, _, xet_hash, dest = item
            self.put(bucket_id, dest, self.blobs[xet_hash])
        for item in delete or []:
            path = item.path if isinstance(item, _BucketDeleteFile) else item
            self.buckets[bucket_id].pop(path, None)

    def _batch_bucket_files(self, bucket_id, *, add=None, copy=None, delete=None, **kwargs):
        return self.batch_bucket_files(bucket_id, add=add, copy=copy, delete=delete)


def _not_found(bucket_id):
    try:
        return BucketNotFoundError(f"Bucket {bucket_id} not found", response=None)
    except TypeError:
        err = BucketNotFoundError.__new__(BucketNotFoundError)
        Exception.__init__(err, f"Bucket {bucket_id} not found")
        return err


@pytest.fixture
def store():
    s = _FakeBucketStore()
    s.put(BUCKET, "ckpt/__0_0.distcp", b"shard bytes")
    s.put(BUCKET, "ckpt/.metadata.tmp", b"checkpoint metadata")
    s.put(BUCKET, "data/train-00000-of-00001.parquet.tmp", b"PAR1 parquet shard")
    return s


@pytest.fixture
def fs(store, monkeypatch):
    fs = HfFileSystem(token=False, skip_instance_cache=True)
    for name in (
        "bucket_info",
        "list_bucket_tree",
        "get_bucket_paths_info",
        "get_bucket_file_metadata",
        "batch_bucket_files",
        "_batch_bucket_files",
    ):
        monkeypatch.setattr(fs._api, name, getattr(store, name))

    original_open = fs._open

    def fake_open(path, mode="rb", *args, **kwargs):
        # Reading a bucket file returns its content from the in-memory store.
        if "r" in mode:
            resolved = fs.resolve_path(path)
            content = store.buckets[resolved.bucket_id][resolved.path]
            return io.BytesIO(content)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(fs, "_open", fake_open)
    return fs


def test_cp_file_copies_a_bucket_file_within_the_same_bucket(fs, store):
    """New: fs.cp_file("hf://buckets/user/ckpts/ckpt/__0_0.distcp", ".../ckpt/copy.distcp") creates the copy with the same content instead of raising NotImplementedError, and keeps the source (A1, A4)."""
    fs.cp_file(f"hf://buckets/{BUCKET}/ckpt/__0_0.distcp", f"hf://buckets/{BUCKET}/ckpt/copy.distcp")
    assert store.buckets[BUCKET].get("ckpt/copy.distcp") == b"shard bytes"
    assert store.buckets[BUCKET].get("ckpt/__0_0.distcp") == b"shard bytes"
    assert fs.exists(f"hf://buckets/{BUCKET}/ckpt/copy.distcp") is True


def test_mv_renames_dcp_metadata_tmp_to_metadata_in_a_bucket(fs, store):
    """New: fs.mv(".../ckpt/.metadata.tmp", ".../ckpt/.metadata") on a bucket leaves ".metadata" with the written content and removes ".metadata.tmp" (A1, A2)."""
    fs.mv(f"hf://buckets/{BUCKET}/ckpt/.metadata.tmp", f"hf://buckets/{BUCKET}/ckpt/.metadata")
    assert store.buckets[BUCKET].get("ckpt/.metadata") == b"checkpoint metadata"
    assert "ckpt/.metadata.tmp" not in store.buckets[BUCKET]
    assert fs.exists(f"hf://buckets/{BUCKET}/ckpt/.metadata") is True
    assert fs.exists(f"hf://buckets/{BUCKET}/ckpt/.metadata.tmp") is False


def test_rename_of_a_temp_parquet_shard_in_a_bucket_leaves_no_temp_shard(fs, store):
    """New: fs.rename(".../data/train-00000-of-00001.parquet.tmp", ".../data/train-00000-of-00001.parquet") on a bucket succeeds and leaves no temp shard behind (A1, A3)."""
    fs.rename(
        f"hf://buckets/{BUCKET}/data/train-00000-of-00001.parquet.tmp",
        f"hf://buckets/{BUCKET}/data/train-00000-of-00001.parquet",
    )
    assert sorted(store.buckets[BUCKET]) == [
        "ckpt/.metadata.tmp",
        "ckpt/__0_0.distcp",
        "data/train-00000-of-00001.parquet",
    ]
    assert store.buckets[BUCKET]["data/train-00000-of-00001.parquet"] == b"PAR1 parquet shard"
