"""ArrowSeries.scatter behaviour that already holds and must keep holding."""

from __future__ import annotations

import pyarrow as pa
import pytest

import narwhals as nw


def _series(values):
    return nw.from_native(pa.table({"a": values}), eager_only=True)["a"]


def test_scatter_every_index_still_works():
    """Guard: on a pyarrow series [1, 2, 3], scatter([0, 2, 1], [7, 8, 9]) returns [7, 9, 8]."""
    assert _series([1, 2, 3]).scatter([0, 2, 1], [7, 8, 9]).to_list() == [7, 9, 8]


def test_scatter_index_zero_still_works():
    """Guard: on a pyarrow series [1, 2, 3], scatter(0, 999) returns [999, 2, 3]."""
    assert _series([1, 2, 3]).scatter(0, 999).to_list() == [999, 2, 3]


def test_scatter_with_series_values():
    """Guard: scattering a pyarrow series [142, 124, 132] into itself at [0, 2, 1] returns [142, 132, 124]."""
    s = _series([142, 124, 132])
    assert s.scatter([0, 2, 1], s).to_list() == [142, 132, 124]


def test_scatter_returns_a_new_series():
    """Guard: scatter leaves the original pyarrow series unchanged and returns a series of the same kind."""
    s = _series([1, 2, 3])
    result = s.scatter([0, 1], [999, 888])
    assert (s.to_list(), result.to_list(), type(result)) == ([1, 2, 3], [999, 888, 3], type(s))


def test_an_index_past_the_end_is_refused():
    """Guard: on a pyarrow series [1, 2, 3], scatter(3, 999) raises an out-of-bounds error."""
    with pytest.raises(Exception):
        _series([1, 2, 3]).scatter(3, 999)


def test_a_negative_index_is_refused():
    """Guard: on a pyarrow series [1, 2, 3], scatter(-1, 999) raises an out-of-bounds error."""
    with pytest.raises(Exception):
        _series([1, 2, 3]).scatter(-1, 999)
