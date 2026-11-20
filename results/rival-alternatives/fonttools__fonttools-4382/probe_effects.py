import json
from fontTools.varLib.iup import iup_contour_optimize

def call(deltas, coords, tol):
    try:
        res = iup_contour_optimize(deltas, coords, tol)
        return {"returned": [list(x) if x is not None else None for x in res]}
    except Exception as exc:
        return {"raised": f"{type(exc).__name__}: {exc}"}

results = {
    "equal_rounded_deltas_tol0": call([(1.2, 0), (0.9, 0), (1.1, 0)], [(0, 0), (10, 0), (20, 5)], 0),
    "equal_rounded_deltas_tol003": call([(1.2, 0), (0.9, 0), (1.1, 0)], [(0, 0), (10, 0), (20, 5)], 0.03),
    "fractional_coords_tol0": call([(0, 0), (1, 0), (0, 0), (2, 0)], [(0.3, 2), (1.6, 0), (1.4, 1), (2, 2)], 0),
    "integer_contour": call([(0, 0), (1, 0), (2, 0)], [(0, 0), (10, 0), (20, 0)], 0),
}
print(json.dumps(results, sort_keys=True))
