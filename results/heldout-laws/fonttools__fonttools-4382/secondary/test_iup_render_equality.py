from fontTools.misc.roundTools import otRound
from fontTools.varLib.iup import iup_delta, iup_delta_optimize


def _round_pairs(pairs):
    return [None if pair is None else (otRound(pair[0]), otRound(pair[1])) for pair in pairs]


def _render_optimized(deltas, coords, ends):
    rounded_coords = _round_pairs(coords)
    try:
        optimized = iup_delta_optimize(deltas, coords, ends, tolerance=0)
    except (AssertionError, TypeError, ValueError):
        # An integer-only optimizer receives rounded inputs from its caller.
        optimized = iup_delta_optimize(
            _round_pairs(deltas), rounded_coords, ends, tolerance=0
        )
    return iup_delta(_round_pairs(optimized), rounded_coords, ends)


def test_coordinates_that_round_equal_do_not_infer_different_deltas():
    """New: distinct point positions that round equal are treated as equal when determining which deltas can be omitted (A1, A3)."""
    coords = [(0.125, 0), (0.25, 0), (0.375, 0)] + [(0, 0)] * 4
    deltas = [(2, 0), (4, 0), (6, 0)] + [(0, 0)] * 4

    assert _render_optimized(deltas, coords, [2]) == deltas


def test_deltas_that_round_equal_do_not_infer_zero_for_equal_coordinates():
    """New: distinct deltas that round equal are treated as equal when interpolating between equal point positions (A2, A3)."""
    coords = [(0, 0)] * 7
    deltas = [(2.125, 0), (0, 0), (2.375, 0)] + [(0, 0)] * 4

    assert _render_optimized(deltas, coords, [2]) == [
        (2, 0), (0, 0), (2, 0), (0, 0), (0, 0), (0, 0), (0, 0)
    ]


def test_integer_contour_can_omit_an_exactly_interpolated_delta():
    """Guard: IUP optimization can omit an exactly interpolated delta when points and deltas are already integers (A1, A2)."""
    coords = [(0, 0), (4, 0), (8, 0)] + [(0, 0)] * 4
    deltas = [(2, 0), (4, 0), (6, 0)] + [(0, 0)] * 4

    optimized = iup_delta_optimize(deltas, coords, [2], tolerance=0)

    assert optimized[1] is None
    assert iup_delta(optimized, coords, [2]) == deltas
