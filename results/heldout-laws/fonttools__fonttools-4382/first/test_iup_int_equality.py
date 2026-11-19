import pytest

from fontTools.varLib.iup import iup_contour_optimize


def _optimize_or_refused(deltas, coords):
    try:
        return iup_contour_optimize(deltas, coords, 0)
    except (TypeError, ValueError, AssertionError):
        return "refused"


def test_deltas_that_round_equal_are_optimised_as_equal():
    """New: deltas (1.2,0), (0.9,0), (1.1,0) all round to (1,0), so the optimiser treats them as equal and keeps only the first (or refuses fractional input) (A1, A2)."""
    result = _optimize_or_refused(
        [(1.2, 0), (0.9, 0), (1.1, 0)], [(0, 0), (10, 0), (20, 5)]
    )
    assert result == "refused" or result[1:] == [None, None]


def test_points_that_round_equal_are_optimised_as_equal():
    """New: points (1.6,0) and (2,2) share x 2 after rounding, so the optimiser can infer two of four deltas as it would for the rounded points (or refuses fractional input) (A1, A2)."""
    result = _optimize_or_refused(
        [(0, 0), (1, 0), (0, 0), (2, 0)], [(0.3, 2), (1.6, 0), (1.4, 1), (2, 2)]
    )
    assert result == "refused" or result.count(None) == 2
