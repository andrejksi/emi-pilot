import json
from mpmath import gammainc

def call(*args):
    try:
        return {"returned": round(float(gammainc(*args)), 11)}
    except Exception as exc:
        return {"raised": f"{type(exc).__name__}: {exc}"}

results = {
    "gammainc_neg_01": call(3, 0, -0.1),
    "gammainc_neg_02": call(3, 0, -0.2),
    "gammainc_pos_1": call(3, 0, 1),
}
print(json.dumps(results, sort_keys=True))
