from contextlib import nullcontext

import httpx2
import pytest

from huggingface_hub import HfFileSystem, hf_file_system


@pytest.fixture(params=["open", "filesystem"])
def streaming_filesystem(request, monkeypatch):
    if request.param == "open":
        fs = HfFileSystem(skip_instance_cache=True)
        open_options = {"block_size": 0}
    else:
        fs = HfFileSystem(block_size=0, skip_instance_cache=True)
        open_options = {}
    monkeypatch.setattr(fs._api, "repo_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(fs._api, "bucket_info", lambda *args, **kwargs: None)
    return fs, open_options


@pytest.fixture(params=["datasets/example/repo", "buckets/example/bucket"])
def marker_path(request):
    return f"hf://{request.param}/marker.txt"


@pytest.mark.parametrize("mode", ["xb", "x"])
def test_streaming_exclusive_create_raises_at_open(streaming_filesystem, marker_path, mode):
    """New: Streaming exclusive-create on a repo or bucket raises the read-only ValueError (A1, A2)."""
    fs, open_options = streaming_filesystem
    with pytest.raises(ValueError) as exc:
        fs.open(marker_path, mode, **open_options)
    assert str(exc.value) == "HfFileSystemStreamFile only supports reading but got mode='xb'"


def test_streaming_binary_write_still_raises_at_open(streaming_filesystem, marker_path):
    """Guard: Opening in mode 'wb' with block_size=0 still raises the existing read-only ValueError (A3)."""
    fs, open_options = streaming_filesystem
    with pytest.raises(ValueError) as exc:
        fs.open(marker_path, "wb", **open_options)
    assert str(exc.value) == "HfFileSystemStreamFile only supports reading but got mode='wb'"


@pytest.mark.parametrize(("mode", "expected"), [("rb", b"data"), ("r", "data"), ("rt", "data")])
def test_streaming_read_modes_still_read(streaming_filesystem, marker_path, mode, expected, monkeypatch):
    """Guard: Streaming a file in 'rb', 'r', or 'rt' still returns the data in binary or text form (A4)."""
    fs, open_options = streaming_filesystem
    monkeypatch.setattr(fs, "isdir", lambda path: False)

    def stream_response(method, url, **kwargs):
        request = httpx2.Request(method, url)
        response = httpx2.Response(200, request=request, content=b"data")
        return nullcontext(response)

    monkeypatch.setattr(hf_file_system, "http_stream_backoff", stream_response)
    with fs.open(marker_path, mode, **open_options) as stream:
        assert stream.read() == expected
