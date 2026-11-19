import os
import pickle
from pathlib import Path

import dill
import dill.temp


def _open_fds():
    return len(os.listdir("/proc/self/fd"))


def test_failed_loads_keep_no_descriptors(tmp_path):
    """New: 20 failed dill.temp.load calls on b"not a pickle", with every exception kept, leave no extra open descriptors (A1)."""
    path = tmp_path / "invalid.pkl"
    path.write_bytes(b"not a pickle")
    errors = []
    before = _open_fds()
    for _ in range(20):
        try:
            dill.temp.load(str(path))
        except Exception as error:
            errors.append(error)
    assert (len(errors), _open_fds() - before) == (20, 0)


def test_failed_load_leaves_no_open_file_in_traceback(tmp_path):
    """New: after a failed dill.temp.load whose exception is kept, no file object reachable from its traceback is still open (A1)."""
    path = tmp_path / "invalid.pkl"
    path.write_bytes(b"not a pickle")
    try:
        dill.temp.load(str(path))
    except Exception as error:
        kept = error
    tb = kept.__traceback__
    open_files = []
    while tb is not None:
        for value in tb.tb_frame.f_locals.values():
            if hasattr(value, "closed") and hasattr(value, "read") and not value.closed:
                open_files.append(value)
        tb = tb.tb_next
    assert open_files == []


def test_failed_load_keeps_original_exception(tmp_path):
    """Guard: dill.temp.load on b"not a pickle" still raises pickle.UnpicklingError "invalid load key, 'n'." (A3)."""
    path = tmp_path / "invalid.pkl"
    path.write_bytes(b"not a pickle")
    try:
        dill.temp.load(str(path))
    except Exception as error:
        assert (type(error), str(error)) == (pickle.UnpicklingError, "invalid load key, 'n'.")
    else:
        raise AssertionError("no exception raised")


def test_successful_load_returns_object_and_closes_file():
    """Guard: dill.temp.load of a dill.temp.dump of [1, 2, 3, 4, 5] returns [1, 2, 3, 4, 5] and leaves no extra open descriptors (A2)."""
    dumpfile = dill.temp.dump([1, 2, 3, 4, 5])
    before = _open_fds()
    results = [dill.temp.load(dumpfile) for _ in range(5)]
    assert (results[-1], _open_fds() - before) == ([1, 2, 3, 4, 5], 0)
