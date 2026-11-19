import pickle
from io import BytesIO
from unittest.mock import Mock

import pytest

import dill
from dill import temp


def test_temp_load_closes_its_file_and_preserves_the_original_error(monkeypatch):
    """New: A failed temp.load closes the file it opened while preserving the original exception (A1)."""
    loading_error = pickle.UnpicklingError("invalid pickle")
    with BytesIO(b"not a pickle") as owned_file:
        monkeypatch.setattr(temp, "open", Mock(return_value=owned_file), raising=False)
        monkeypatch.setattr(dill, "load", Mock(side_effect=loading_error))

        with pytest.raises(pickle.UnpicklingError) as retained_error:
            temp.load("invalid.pkl")

        assert retained_error.value is loading_error
        assert owned_file.closed


def test_temp_load_closes_its_file_after_a_successful_load(monkeypatch):
    """New: A successful temp.load returns the deserialized value and closes the file it opened (A2)."""
    with BytesIO(pickle.dumps([1, 2, 3])) as owned_file:
        monkeypatch.setattr(temp, "open", Mock(return_value=owned_file), raising=False)

        assert temp.load("valid.pkl") == [1, 2, 3]
        assert owned_file.closed


def test_direct_dill_load_keeps_the_callers_file_open():
    """Guard: Passing a file directly to dill.load leaves the caller's file open (A3)."""
    with BytesIO(pickle.dumps([1, 2, 3])) as caller_file:
        assert dill.load(caller_file) == [1, 2, 3]
        assert not caller_file.closed
