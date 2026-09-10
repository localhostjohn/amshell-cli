from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import dataclass


class DiscoveryError(RuntimeError):
    """Raised when local Windows inventory discovery cannot complete safely."""


@dataclass(slots=True)
class WindowsDevice:
    hostname: str
    manufacturer: str
    model: str
    serial_number: str
    os_caption: str
    os_version: str
    total_memory_gb: float
    processor: str


def _powershell_executable() -> str:
    if platform.system() != "Windows":
        raise DiscoveryError("Windows discovery is only available on Windows hosts.")
    return "powershell.exe"


def discover_local_windows_device() -> WindowsDevice:
    """Collect read-only local hardware/OS inventory through CIM.

    No remote host, credentials, registry changes or administrative writes are used.
    """
    script = r"""
$computer = Get-CimInstance -ClassName Win32_ComputerSystem
$bios = Get-CimInstance -ClassName Win32_BIOS
$os = Get-CimInstance -ClassName Win32_OperatingSystem
$cpu = Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1
[pscustomobject]@{
    hostname = $env:COMPUTERNAME
    manufacturer = [string]$computer.Manufacturer
    model = [string]$computer.Model
    serial_number = [string]$bios.SerialNumber
    os_caption = [string]$os.Caption
    os_version = [string]$os.Version
    total_memory_bytes = [double]$computer.TotalPhysicalMemory
    processor = [string]$cpu.Name
} | ConvertTo-Json -Compress
""".strip()

    try:
        completed = subprocess.run(
            [
                _powershell_executable(),
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DiscoveryError(f"Unable to start PowerShell discovery: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "PowerShell returned a non-zero exit code."
        raise DiscoveryError(f"Windows discovery failed: {detail}")

    try:
        payload = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise DiscoveryError("PowerShell returned invalid discovery data.") from exc

    required = (
        "hostname",
        "manufacturer",
        "model",
        "serial_number",
        "os_caption",
        "os_version",
        "total_memory_bytes",
        "processor",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise DiscoveryError(
            f"Discovery response is missing field(s): {', '.join(missing)}"
        )

    total_memory_gb = round(float(payload["total_memory_bytes"]) / (1024**3), 1)
    return WindowsDevice(
        hostname=str(payload["hostname"]).strip().upper(),
        manufacturer=str(payload["manufacturer"]).strip(),
        model=str(payload["model"]).strip(),
        serial_number=str(payload["serial_number"]).strip().upper(),
        os_caption=str(payload["os_caption"]).strip(),
        os_version=str(payload["os_version"]).strip(),
        total_memory_gb=total_memory_gb,
        processor=str(payload["processor"]).strip(),
    )
