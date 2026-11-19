"""Rules the task adds: ArrowSeries.scatter accepts any in-range indices."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pyarrow as pa
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.configuration import set_hypothesis_home_dir

import narwhals as nw

# Keep Hypothesis' storage out of the repository.
set_hypothesis_home_dir(Path(tempfile.gettempdir()) / "emi-laws-hypothesis")


def _series(values):
    return nw.from_native(pa.table({"a": values}), eager_only=True)["a"]


def test_scatter_a_single_non_zero_index():
    """New: on a pyarrow series [1, 2, 3], scatter(1, 999) returns [1, 999, 3]."""
    assert _series([1, 2, 3]).scatter(1, 999).to_list() == [1, 999, 3]


def test_scatter_indices_that_do_not_cover_the_series():
    """New: on a pyarrow series [1, 2, 3], scatter([0, 2], [999, 888]) returns [999, 2, 888]."""
    assert _series([1, 2, 3]).scatter([0, 2], [999, 888]).to_list() == [999, 2, 888]


def test_scatter_the_last_index_alone():
    """New: on a pyarrow series [1, 2, 3], scatter(2, 7) returns [1, 2, 7]."""
    assert _series([1, 2, 3]).scatter(2, 7).to_list() == [1, 2, 7]


@settings(database=None, deadline=None)
@given(
    st.lists(st.integers(-1000, 1000), min_size=1, max_size=12).flatmap(
        lambda base: st.tuples(
            st.just(base),
            st.lists(st.integers(0, len(base) - 1), min_size=1, max_size=len(base), unique=True).flatmap(
                lambda idx: st.tuples(st.just(idx), st.lists(st.integers(-1000, 1000), min_size=len(idx), max_size=len(idx)))
            ),
        )
    )
)
def test_scatter_replaces_exactly_the_given_positions(case):
    """New: for any pyarrow series and any distinct in-range indices with as many values, scatter puts each value at its index and leaves every other position unchanged."""
    base, (indices, values) = case
    expected = list(base)
    for i, v in zip(indices, values):
        expected[i] = v
    assert _series(base).scatter(indices, values).to_list() == expected
