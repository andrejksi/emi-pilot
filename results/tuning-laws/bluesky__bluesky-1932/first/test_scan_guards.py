"""Behaviour of bluesky.plans.scan that already holds and must keep holding."""

from __future__ import annotations

from ophyd import Signal
from ophyd.sim import SynAxis

from bluesky import RunEngine
from bluesky.plans import scan


def test_scan_completes_after_num_steps():
    """Guard: a scan with num=5 emits exactly 5 primary events, each recording every detector and the motor."""
    detectors = [Signal(name=f"g_det{i}", value=i) for i in range(3)]
    motor = SynAxis(name="g_motor")
    docs = []
    RE = RunEngine({})
    RE(scan(detectors, motor, -1, 11, 5), lambda name, doc: docs.append((name, doc)))
    events = [d for n, d in docs if n == "event"]
    assert len(events) == 5
    assert all({"g_det0", "g_det1", "g_det2", "g_motor"} <= set(e["data"]) for e in events)
    assert [e["data"]["g_motor"] for e in events] == [-1.0, 2.0, 5.0, 8.0, 11.0]
