import json
from unittest.mock import Mock, patch

import pytest

from amshell.discovery.windows import (
    DiscoveryError,
    discover_local_windows_device,
)


def test_discovery_rejects_non_windows_hosts():
    with (
        patch("amshell.discovery.windows.platform.system", return_value="Linux"),
        pytest.raises(DiscoveryError, match="only available on Windows"),
    ):
        discover_local_windows_device()


def test_discovery_parses_powershell_json():
    payload = {
        "hostname": "astra-pc01",
        "manufacturer": "Fictional Systems",
        "model": "LabBook 14",
        "serial_number": "lab-serial-001",
        "os_caption": "Microsoft Windows 11 Pro",
        "os_version": "10.0.26100",
        "total_memory_bytes": 17179869184,
        "processor": "Fictional CPU",
    }
    completed = Mock(returncode=0, stdout=json.dumps(payload), stderr="")

    with (
        patch("amshell.discovery.windows.platform.system", return_value="Windows"),
        patch("amshell.discovery.windows.subprocess.run", return_value=completed) as run,
    ):
        device = discover_local_windows_device()

    assert device.hostname == "ASTRA-PC01"
    assert device.serial_number == "LAB-SERIAL-001"
    assert device.total_memory_gb == 16.0
    assert device.os_caption == "Microsoft Windows 11 Pro"
    command = run.call_args.args[0]
    assert command[0] == "powershell.exe"
    assert "-NoProfile" in command
    assert "-NonInteractive" in command
    assert run.call_args.kwargs["timeout"] == 20


def test_discovery_reports_powershell_failure():
    completed = Mock(returncode=1, stdout="", stderr="CIM failure")
    with (
        patch("amshell.discovery.windows.platform.system", return_value="Windows"),
        patch("amshell.discovery.windows.subprocess.run", return_value=completed),
        pytest.raises(DiscoveryError, match="CIM failure"),
    ):
        discover_local_windows_device()


def test_discovery_rejects_incomplete_payload():
    completed = Mock(returncode=0, stdout='{"hostname":"ASTRA-PC01"}', stderr="")
    with (
        patch("amshell.discovery.windows.platform.system", return_value="Windows"),
        patch("amshell.discovery.windows.subprocess.run", return_value=completed),
        pytest.raises(DiscoveryError, match="missing field"),
    ):
        discover_local_windows_device()
