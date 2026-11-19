import pickle
import tempfile

import pytest

from dill import temp


class CannotSerialize:
    def __reduce__(self):
        raise RuntimeError("cannot serialize")


def test_failed_temp_dump_closes_and_removes_its_default_temporary_file(monkeypatch, tmp_path):
    """New: A failed temp.dump closes any file it opened and leaves no partial file while the error is retained (A1)."""
    create_temporary_file = tempfile.NamedTemporaryFile
    opened_files = []

    def track_temporary_file(*args, **kwargs):
        opened_file = create_temporary_file(*args, **kwargs)
        opened_files.append(opened_file)
        return opened_file

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", track_temporary_file)
    try:
        with pytest.raises(RuntimeError, match="^cannot serialize$") as retained_error:
            temp.dump(CannotSerialize(), dir=tmp_path)

        assert retained_error.value.__traceback__ is not None
        assert all(opened_file.closed for opened_file in opened_files)
        assert list(tmp_path.iterdir()) == []
    finally:
        for opened_file in opened_files:
            opened_file.close()


def test_successful_temp_dump_returns_an_open_file(tmp_path):
    """Guard: A successful temp.dump still returns an open temporary file (A2)."""
    returned_file = temp.dump([1, 2, 3], dir=tmp_path)
    try:
        assert not returned_file.closed
        returned_file.seek(0)
        assert pickle.load(returned_file) == [1, 2, 3]
    finally:
        returned_file.close()
