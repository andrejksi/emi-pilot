import json
from mpmath import fp

def call(fn, *args):
    try:
        v = fn(*args)
        return {"returned": round(float(v), 11)}
    except Exception as exc:
        return {"raised": f"{type(exc).__name__}: {exc}"}

results = {
    "fp_besselyzero_2_1": call(fp.besselyzero, 2, 1),
    "fp_besselyzero_0_1": call(fp.besselyzero, 0, 1),
    "fp_besselyzero_3_2": call(fp.besselyzero, 3, 2),
    "fp_bessely_2_3": call(fp.bessely, 2, 3),
}
print(json.dumps(results, sort_keys=True))
