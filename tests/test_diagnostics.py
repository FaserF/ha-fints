"""Test diagnostics platform in ha-fints."""

from datetime import UTC, datetime

from custom_components.fints.const import DOMAIN
from custom_components.fints.coordinator import FinTSDataUpdateCoordinator
from custom_components.fints.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redaction(mock_hass, mock_config_entry):
    """Test that sensitive credentials are redacted in diagnostics export."""
    coord = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    coord.data = {
        "bank_code": "37050198",
        "accounts": {
            "DE89370501980000012345": {
                "iban": "DE89370501980000012345",
                "balance": 5000.0,
            }
        },
    }
    coord.last_update = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: coord}

    diag = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

    assert diag["integration_version"] == "1.0.0"
    assert diag["last_update_success"] is True

    # Check that PIN was redacted
    assert diag["entry_data"]["pin"] == "***REDACTED***"
    assert diag["entry_data"]["login"] == "***REDACTED***"

    # Check IBAN masking in coordinator data
    acc_diag = diag["coordinator_data"]["accounts"]["DE89370501980000012345"]
    assert "0000" not in acc_diag["iban"]
    assert "****" in acc_diag["iban"]
