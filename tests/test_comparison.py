from amshell.comparison import compare_asset_to_windows_device
from amshell.discovery.windows import WindowsDevice


def stored_asset(**overrides):
    asset = {
        "asset_tag": "AST001",
        "hostname": "ASTRA-PC01",
        "manufacturer": "ExampleCorp",
        "model": "LabBook 14",
        "serial_number": "SERIAL001",
    }
    asset.update(overrides)
    return asset


def discovered_device(**overrides):
    values = {
        "hostname": "ASTRA-PC01",
        "manufacturer": "ExampleCorp",
        "model": "LabBook 14",
        "serial_number": "SERIAL001",
        "os_caption": "Windows 11 Pro",
        "os_version": "10.0.26100",
        "total_memory_gb": 16.0,
        "processor": "Example CPU",
    }
    values.update(overrides)
    return WindowsDevice(**values)


def test_matching_device_has_no_drift():
    comparison = compare_asset_to_windows_device(stored_asset(), discovered_device())

    assert comparison.identity_match is True
    assert comparison.has_drift is False
    assert comparison.drifted_fields == ()
    assert comparison.safe_updates() == {}


def test_non_identity_fields_can_be_reconciled_when_serial_matches():
    comparison = compare_asset_to_windows_device(
        stored_asset(hostname="ASTRA-OLD", model="LabBook 13"),
        discovered_device(hostname="ASTRA-PC01", model="LabBook 14"),
    )

    assert comparison.identity_match is True
    assert comparison.has_drift is True
    assert comparison.safe_updates() == {
        "hostname": "ASTRA-PC01",
        "model": "LabBook 14",
    }


def test_serial_mismatch_blocks_automatic_updates():
    comparison = compare_asset_to_windows_device(
        stored_asset(hostname="ASTRA-OLD"),
        discovered_device(hostname="ASTRA-PC01", serial_number="DIFFERENT001"),
    )

    assert comparison.identity_match is False
    assert comparison.has_drift is True
    assert comparison.safe_updates() == {}


def test_comparison_is_case_insensitive_for_descriptive_fields():
    comparison = compare_asset_to_windows_device(
        stored_asset(manufacturer="EXAMPLECORP", model="labbook 14"),
        discovered_device(manufacturer="ExampleCorp", model="LabBook 14"),
    )

    assert comparison.has_drift is False
