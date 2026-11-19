"""Shared helper for the laws: run VerifyVxlan1ConnSettings on canned EOS output."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

from anta.device import AntaDevice
from anta.tests.vxlan import VerifyVxlan1ConnSettings


def run_conn_settings(inputs: dict[str, Any], eos_data: list[dict[str, Any]]):
    """Run the check on a mocked device and return its result object."""
    with patch.object(AntaDevice, "__abstractmethods__", set()):
        dev = AntaDevice(name="laws-device")  # type: ignore[abstract]
        dev.hw_model = "cEOSLab"
        instance = VerifyVxlan1ConnSettings(dev, inputs=inputs, eos_data=eos_data)
        asyncio.run(instance.test())
    return instance.result
