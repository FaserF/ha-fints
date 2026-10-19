"""Test helper functions in ha-fints."""

from custom_components.fints.helpers import (
    get_account_device_info,
    get_bank_device_info,
    get_integration_version,
    mask_iban,
    mask_sensitive_data,
)


def test_mask_iban():
    """Test IBAN masking logic."""
    assert mask_iban(None) == "****"
    assert mask_iban("") == "****"
    assert mask_iban("DE1234") == "****"
    masked = mask_iban("DE89370501980000012345")
    assert masked.startswith("DE89")
    assert masked.endswith("23 45")
    assert "****" in masked
    assert "0000" not in masked


def test_mask_sensitive_data():
    """Test recursive credential scrubbing."""
    data = {
        "pin": "secret_pin",
        "nested": {
            "password": "secret_password",
            "iban": "DE89370501980000012345",
            "normal_field": "public_value",
            "user_id": "sensitive_user",
        },
        "list_items": [
            {"token": "tok123"},
            {"amount": 100.5},
        ],
    }

    masked = mask_sensitive_data(data)
    assert masked["pin"] == "***REDACTED***"
    assert masked["nested"]["password"] == "***REDACTED***"
    assert masked["nested"]["user_id"] == "***REDACTED***"
    assert masked["nested"]["normal_field"] == "public_value"
    assert "****" in masked["nested"]["iban"]
    assert masked["list_items"][0]["token"] == "***REDACTED***"
    assert masked["list_items"][1]["amount"] == 100.5


def test_get_integration_version(mock_hass):
    """Test integration version caching."""
    version = get_integration_version(mock_hass)
    assert version == "1.0.0"


def test_device_info(mock_config_entry):
    """Test device info builders."""
    bank_info = get_bank_device_info(mock_config_entry, "1.0.0")
    assert (
        "fints",
        mock_config_entry.entry_id,
    ) in bank_info["identifiers"]
    assert "37050198" in bank_info["name"]

    acc_info = get_account_device_info(
        mock_config_entry,
        iban="DE89370501980000012345",
        bic="COBADEFFXXX",
        bank_code="37050198",
        version="1.0.0",
    )
    assert (
        "fints",
        f"{mock_config_entry.entry_id}_DE89370501980000012345",
    ) in acc_info["identifiers"]
    assert acc_info["via_device_id"] == mock_config_entry.entry_id
