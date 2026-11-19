from unittest.mock import MagicMock, patch

import pytest

from huggingface_hub import HfFileSystem
from huggingface_hub.hf_file_system import HfFileSystemStreamFile

REPO_PATH = "hf://datasets/user/repo/marker.txt"
BUCKET_PATH = "hf://buckets/user/bucket/marker.txt"


def _fake_resolve(path):
    resolved = MagicMock()
    resolved.unresolve.return_value = path.replace("hf://", "")
    return resolved


def _fs(**kwargs):
    fs = HfFileSystem(**kwargs)
    return fs


def _open_and_write(fs, path, mode, **open_kwargs):
    with patch.object(fs, "resolve_path", side_effect=lambda p, revision=None, **kw: _fake_resolve(path)):
        with fs.open(path, mode, **open_kwargs) as f:
            f.write(b"data" if "b" in mode else "data")


def test_xb_with_block_size_zero_on_repo_path_is_refused():
    """New: opening a repo path with mode "xb" and block_size=0 is refused with the same ValueError as "wb" instead of silently dropping writes (A1, A3, A4)."""
    fs = _fs()
    with pytest.raises(ValueError, match="only supports reading but got mode='xb'"):
        _open_and_write(fs, REPO_PATH, "xb", block_size=0)


def test_xb_with_block_size_zero_on_bucket_path_is_refused():
    """New: opening a bucket path with mode "xb" and block_size=0 is refused with ValueError (A1, A3, A4)."""
    fs = _fs()
    with pytest.raises(ValueError, match="only supports reading"):
        _open_and_write(fs, BUCKET_PATH, "xb", block_size=0)


def test_text_x_with_block_size_zero_is_refused():
    """New: opening with text mode "x" and block_size=0 is refused with ValueError (A2, A4)."""
    fs = _fs()
    with pytest.raises(ValueError, match="only supports reading"):
        _open_and_write(fs, REPO_PATH, "x", block_size=0)


def test_xb_with_instance_block_size_zero_is_refused():
    """New: opening with "xb" on HfFileSystem(block_size=0) without overriding block_size is refused with ValueError (A2, A4)."""
    fs = _fs(block_size=0)
    with pytest.raises(ValueError, match="only supports reading"):
        _open_and_write(fs, REPO_PATH, "xb")


def test_stream_file_constructor_refuses_xb():
    """New: constructing HfFileSystemStreamFile directly with mode "xb" raises ValueError (A1, A4)."""
    fs = _fs()
    with patch.object(fs, "resolve_path", side_effect=lambda p, revision=None, **kw: _fake_resolve(REPO_PATH)):
        with pytest.raises(ValueError, match="only supports reading but got mode='xb'"):
            HfFileSystemStreamFile(fs, REPO_PATH, mode="xb")


def test_wb_with_block_size_zero_is_still_refused():
    """Guard: opening with "wb" and block_size=0 still raises the same ValueError (A4)."""
    fs = _fs()
    with pytest.raises(ValueError, match="only supports reading but got mode='wb'"):
        _open_and_write(fs, REPO_PATH, "wb", block_size=0)


@pytest.mark.parametrize("mode", ["rb", "r", "rt"])
@pytest.mark.parametrize("path", [REPO_PATH, BUCKET_PATH])
def test_read_modes_with_block_size_zero_still_open_a_stream_file(mode, path):
    """Guard: opening a repo or bucket path for reading ("rb", "r", "rt") with block_size=0 still gives a streaming file without error (A5)."""
    fs = _fs()
    with patch.object(fs, "resolve_path", side_effect=lambda p, revision=None, **kw: _fake_resolve(path)):
        f = fs.open(path, mode, block_size=0)
        raw = f if "b" in mode else f.buffer
        assert isinstance(raw, HfFileSystemStreamFile)
        assert raw.mode == "rb"
