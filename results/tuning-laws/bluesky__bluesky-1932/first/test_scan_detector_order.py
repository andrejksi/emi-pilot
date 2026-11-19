"""Rules for bluesky.plans.scan: detector keys keep the order the detectors were given in."""

from __future__ import annotations

import string

from hypothesis import given, settings
from hypothesis import strategies as st
from ophyd import Signal
from ophyd.sim import SynAxis

from bluesky import RunEngine
from bluesky.plans import scan


def _run_scan(detector_names, num=3):
    """Run scan over fresh signals named as given; return (descriptor data_keys order, event data key orders, event count)."""
    detectors = [Signal(name=n, value=i) for i, n in enumerate(detector_names)]
    motor = SynAxis(name="laws_motor")
    docs = []
    RE = RunEngine({})
    RE(scan(detectors, motor, -1, 1, num), lambda name, doc: docs.append((name, doc)))
    primary = [d for n, d in docs if n == "descriptor" and d["name"] == "primary"]
    uid = primary[0]["uid"]
    events = [d for n, d in docs if n == "event" and d["descriptor"] == uid]
    wanted = set(detector_names)
    desc_order = [k for k in primary[0]["data_keys"] if k in wanted]
    event_orders = [[k for k in e["data"] if k in wanted] for e in events]
    return desc_order, event_orders, len(events)


NAMES = ["det_gamma", "det_gamscrew", "det_h", "det_k", "det_l", "det_m", "det_n", "det_o"]


def test_descriptor_data_keys_follow_the_detectors_order():
    """New: the primary descriptor's detector data_keys come in the order the detectors were passed to scan."""
    desc_order, _, _ = _run_scan(NAMES)
    assert desc_order == NAMES


def test_event_data_keys_follow_the_detectors_order():
    """Guard: every primary event's detector data keys come in the order the detectors were passed to scan."""
    _, event_orders, _ = _run_scan(NAMES)
    assert event_orders == [NAMES, NAMES, NAMES]


def test_reversed_detectors_give_reversed_keys():
    """New: passing the same detectors in reverse order gives the descriptor data_keys in reverse order."""
    desc_order, _, _ = _run_scan(NAMES[::-1])
    assert desc_order == NAMES[::-1]


@settings(max_examples=25, deadline=None)
@given(
    st.lists(
        st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=6),
        min_size=2,
        max_size=8,
        unique=True,
    )
)
def test_any_detector_order_is_kept(raw_names):
    """New: for any list of distinct detectors, the descriptor and every event list their keys in the order given to scan."""
    names = [f"d_{n}" for n in raw_names]
    desc_order, event_orders, _ = _run_scan(names, num=2)
    assert desc_order == names
    assert all(order == names for order in event_orders)
