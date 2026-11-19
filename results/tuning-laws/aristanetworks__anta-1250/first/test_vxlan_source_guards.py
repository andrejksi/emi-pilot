"""Behaviour that already holds and must keep holding."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anta.result_manager.models import AntaTestStatus
from anta.tests.vxlan import VerifyVxlan1ConnSettings

from _anta_helpers import run_conn_settings


def test_loopback_source_interface_still_passes():
    """Guard: the check still succeeds when Loopback1 is expected and the device's Vxlan1 source interface is Loopback1."""
    result = run_conn_settings(
        {"source_interface": "Loopback1", "udp_port": 4789},
        [{"interfaces": {"Vxlan1": {"srcIpIntf": "Loopback1", "udpPort": 4789}}}],
    )
    assert (result.result, result.messages) == (AntaTestStatus.SUCCESS, [])


def test_a_non_dps_non_loopback_source_interface_is_refused():
    """Guard: an interface that is neither Dps nor Loopback, like Ethernet1, is refused as the source interface with a ValidationError."""
    with pytest.raises(ValidationError):
        VerifyVxlan1ConnSettings.Input(source_interface="Ethernet1", udp_port=4789)
