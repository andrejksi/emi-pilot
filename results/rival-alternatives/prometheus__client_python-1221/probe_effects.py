import json
from prometheus_client import generate_latest
from prometheus_client.core import (
    CollectorRegistry, CounterMetricFamily, GaugeHistogramMetricFamily,
    GaugeMetricFamily, HistogramMetricFamily, InfoMetricFamily,
    StateSetMetricFamily, SummaryMetricFamily, UntypedMetricFamily,
)

class _C:
    def __init__(self, f):
        self.f = f
    def collect(self):
        yield self.f

def run_family(name, fam):
    reg = CollectorRegistry()
    reg.register(_C(fam))
    try:
        out = generate_latest(reg).decode("utf-8")
        lines = [l for l in out.splitlines() if l and not l.startswith("#")]
        return {"returned": lines}
    except Exception as exc:
        return {"raised": f"{type(exc).__name__}: {exc}"}

results = {}
u = UntypedMetricFamily("u", "h", labels=["a"]); u.add_metric([1], 2)
results["UntypedMetricFamily"] = run_family("u", u)
c = CounterMetricFamily("c", "h", labels=["a"]); c.add_metric([1], 2, created=3)
results["CounterMetricFamily"] = run_family("c", c)
g = GaugeMetricFamily("g", "h", labels=["a"]); g.add_metric([1], 2)
results["GaugeMetricFamily"] = run_family("g", g)
s = SummaryMetricFamily("s", "h", labels=["a"]); s.add_metric([1], count_value=1, sum_value=2)
results["SummaryMetricFamily"] = run_family("s", s)
h = HistogramMetricFamily("h", "h", labels=["a"]); h.add_metric([1], buckets=[("0", 1), ("+Inf", 2)], sum_value=3)
results["HistogramMetricFamily"] = run_family("h", h)
gh = GaugeHistogramMetricFamily("gh", "h", labels=["a"]); gh.add_metric([1], buckets=[("0", 1), ("+Inf", 2)], gsum_value=3)
results["GaugeHistogramMetricFamily"] = run_family("gh", gh)
im = InfoMetricFamily("i", "h", labels=["a"]); im.add_metric([1], {"c": 2})
results["InfoMetricFamily"] = run_family("i", im)
ss = StateSetMetricFamily("ss", "h", labels=["a"]); ss.add_metric([1], {3: True})
results["StateSetMetricFamily"] = run_family("ss", ss)
print(json.dumps(results, sort_keys=True))
