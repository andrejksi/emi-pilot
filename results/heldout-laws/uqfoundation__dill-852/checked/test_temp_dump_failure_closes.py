import os

import pytest

import dill
import dill.temp


class CannotSerialize:
    def __reduce__(self):
        raise RuntimeError("cannot serialize")


def _open_fds():
    return len(os.listdir("/proc/self/fd"))


def test_failed_dump_removes_partial_file(tmp_path):
    """New: dill.temp.dump(CannotSerialize(), dir=tmp_path) that fails with the exception kept leaves no temporary file in tmp_path (A1)."""
    errors = []
    try:
        dill.temp.dump(CannotSerialize(), dir=str(tmp_path))
    except RuntimeError as error:
        errors.append(error)
    assert (len(errors), os.listdir(tmp_path)) == (1, [])


def test_repeated_failed_dumps_keep_no_descriptors(tmp_path):
    """New: 20 failed dill.temp.dump(CannotSerialize()) calls, with every exception kept, leave no extra open descriptors (A1)."""
    errors = []
    before = _open_fds()
    for _ in range(20):
        try:
            dill.temp.dump(CannotSerialize(), dir=str(tmp_path))
        except RuntimeError as error:
            errors.append(error)
    assert (len(errors), _open_fds() - before) == (20, 0)


def test_failed_dump_raises_original_error():
    """Guard: dill.temp.dump(CannotSerialize()) still raises RuntimeError('cannot serialize') (A2)."""
    with pytest.raises(RuntimeError, match="cannot serialize"):
        dill.temp.dump(CannotSerialize())


def test_successful_dump_returns_open_file():
    """Guard: dill.temp.dump([1, 2, 3, 4, 5]) still returns an open file that dill.temp.load reads back as [1, 2, 3, 4, 5] (A3)."""
    f = dill.temp.dump([1, 2, 3, 4, 5])
    assert (f.closed, os.path.exists(f.name), dill.temp.load(f)) == (False, True, [1, 2, 3, 4, 5])
