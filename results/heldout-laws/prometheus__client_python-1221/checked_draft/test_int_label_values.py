from prometheus_client import generate_latest
from prometheus_client.core import CollectorRegistry, CounterMetricFamily, GaugeMetricFamily


class _Collector:
    def __init__(self, family):
        self._family = family

    def collect(self):
        yield self._family


def _export(family):
    registry = CollectorRegistry()
    registry.register(_Collector(family))
    return generate_latest(registry).decode()


def test_gauge_family_int_label_value_exports_as_string():
    """New: a GaugeMetricFamily metric added with the int label value 1 exports as port="1", like str(1) (A1)."""
    g = GaugeMetricFamily("g", "help", labels=["port"])
    g.add_metric([1], 2.0)
    assert 'g{port="1"} 2.0' in _export(g)


def test_counter_family_int_label_value_exports_as_string():
    """New: a CounterMetricFamily metric added with the int label value 8080 exports as port="8080", like str(8080) (A1)."""
    c = CounterMetricFamily("c", "help", labels=["port"])
    c.add_metric([8080], 3.0)
    assert 'c_total{port="8080"} 3.0' in _export(c)


def test_gauge_family_str_label_value_still_exports():
    """Guard: a GaugeMetricFamily metric added with the str label value "1" still exports as port="1" (A2)."""
    g = GaugeMetricFamily("g", "help", labels=["port"])
    g.add_metric(["1"], 2.0)
    assert 'g{port="1"} 2.0' in _export(g)


def test_counter_family_str_label_value_still_exports():
    """Guard: a CounterMetricFamily metric added with the str label value "8080" still exports as port="8080" (A2)."""
    c = CounterMetricFamily("c", "help", labels=["port"])
    c.add_metric(["8080"], 3.0)
    assert 'c_total{port="8080"} 3.0' in _export(c)
