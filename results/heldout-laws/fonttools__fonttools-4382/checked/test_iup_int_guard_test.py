from fontTools.varLib.iup import iup_contour_optimize, iup_delta_optimize


def test_integer_input_optimises_as_before():
    """Guard: optimising integer deltas (1,0),(1,0),(1,0) keeps only the first, as before (A3)."""
    assert iup_contour_optimize([(1, 0), (1, 0), (1, 0)], [(0, 0), (10, 0), (20, 5)], 0) == [(1, 0), None, None]


def test_integer_points_with_shared_x_optimise_as_before():
    """Guard: integer points (0,2),(2,0),(1,1),(2,2) with deltas (0,0),(1,0),(0,0),(2,0) still encode only the second and fourth delta (A3)."""
    coords = [(0, 2), (2, 0), (1, 1), (2, 2)] + [(0, 0)] * 4
    deltas = [(0, 0), (1, 0), (0, 0), (2, 0)] + [(0, 0)] * 4
    assert iup_delta_optimize(deltas, coords, [3])[:4] == [None, (1, 0), None, (2, 0)]
