"""Test coordinator in ha-fints."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from custom_components.fints.coordinator import FinTSDataUpdateCoordinator


async def test_coordinator_init_and_update(mock_hass, mock_config_entry):
    """Test coordinator initialization and data update cycle."""
    coordinator = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    assert coordinator.update_interval == timedelta(seconds=14400)

    sample_data = {
        "bank_code": "37050198",
        "accounts": {},
        "total_balance": 1500.0,
        "currency": "EUR",
        "tan_required": False,
        "last_update_success": True,
    }

    with patch.object(
        coordinator.client, "async_fetch_all_data", AsyncMock(return_value=sample_data)
    ):
        data = await coordinator._async_update_data()
        assert data["total_balance"] == 1500.0
        assert coordinator.last_update is not None


async def test_coordinator_min_scan_interval(mock_hass, mock_config_entry):
    """Test that scan interval cannot be set below minimum."""
    mock_config_entry.options = {"scan_interval": 60}  # Try 1 minute
    coordinator = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    assert coordinator.update_interval == timedelta(seconds=1800)
