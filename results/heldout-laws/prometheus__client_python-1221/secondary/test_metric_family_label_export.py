from prometheus_client import generate_latest
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily


class SingleMetricCollector:
    def __init__(self, metric):
        self.metric = metric

    def collect(self):
        return [self.metric]


def test_gauge_metric_family_exports_integer_labels_as_strings():
    """New: Integer labels passed to GaugeMetricFamily.add_metric() export as strings (A1)."""
    gauge = GaugeMetricFamily("jobs_active", "Active jobs", labels=["rack", "shard"])
    gauge.add_metric([42, 3], 7)
    collector = SingleMetricCollector(gauge)

    assert b'jobs_active{rack="42",shard="3"} 7.0' in generate_latest(collector).splitlines()


def test_counter_metric_family_exports_integer_labels_as_strings():
    """New: Integer labels passed to CounterMetricFamily.add_metric() export as strings (A2)."""
    counter = CounterMetricFamily("jobs_started", "Started jobs", labels=["rack", "shard"])
    counter.add_metric([42, 3], 7)
    collector = SingleMetricCollector(counter)

    assert b'jobs_started_total{rack="42",shard="3"} 7.0' in generate_latest(collector).splitlines()


def test_gauge_metric_family_exports_label_values_already_converted_to_strings():
    """Guard: Explicitly converting label values to strings continues to allow export (A3)."""
    gauge = GaugeMetricFamily("jobs_active", "Active jobs", labels=["rack", "shard"])
    gauge.add_metric([str(42), str(3)], 7)
    collector = SingleMetricCollector(gauge)

    assert b'jobs_active{rack="42",shard="3"} 7.0' in generate_latest(collector).splitlines()
