"""Rules the task adds: a DPS interface can be the Vxlan1 source interface."""

from __future__ import annotations

from anta.result_manager.models import AntaTestStatus
from anta.tests.vxlan import VerifyVxlan1ConnSettings

from _anta_helpers import run_conn_settings


def test_dps1_is_accepted_as_the_source_interface_input():
    """New: VerifyVxlan1ConnSettings accepts Dps1 as its source_interface input."""
    assert VerifyVxlan1ConnSettings.Input(source_interface="Dps1", udp_port=4789).source_interface == "Dps1"


def test_dps1_source_interface_matching_the_device_passes():
    """New: the check succeeds when Dps1 is expected and the device's Vxlan1 source interface is Dps1."""
    result = run_conn_settings(
        {"source_interface": "Dps1", "udp_port": 4789},
        [{"interfaces": {"Vxlan1": {"srcIpIntf": "Dps1", "udpPort": 4789}}}],
    )
    assert (result.result, result.messages) == (AntaTestStatus.SUCCESS, [])


def test_dps1_expected_but_loopback_on_device_fails():
    """New: the check fails, naming both interfaces, when Dps1 is expected but the device uses Loopback1."""
    result = run_conn_settings(
        {"source_interface": "Dps1", "udp_port": 4789},
        [{"interfaces": {"Vxlan1": {"srcIpIntf": "Loopback1", "udpPort": 4789}}}],
    )
    assert result.result == AntaTestStatus.FAILURE
    assert result.messages == ["Interface: Vxlan1 - Incorrect Source interface - Expected: Dps1 Actual: Loopback1"]
