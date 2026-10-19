"""Test component setup and unload in ha-fints."""

from unittest.mock import AsyncMock, patch

from custom_components.fints import (
    async_setup_entry,
    async_unload_entry,
    async_update_listener,
)
from custom_components.fints.const import DOMAIN


async def test_setup_and_unload_entry(mock_hass, mock_config_entry):
    """Test full setup and unload cycle."""
    sample_data = {
        "bank_code": "37050198",
        "accounts": {},
        "total_balance": 100.0,
        "currency": "EUR",
        "tan_required": False,
        "last_update_success": True,
    }

    with (
        patch(
            "custom_components.fints.coordinator.FinTSClient.async_fetch_all_data",
            AsyncMock(return_value=sample_data),
        ),
        patch(
            "custom_components.fints.async_setup_services",
            AsyncMock(),
        ) as mock_setup_svc,
        patch(
            "custom_components.fints.async_unload_services",
            AsyncMock(),
        ) as mock_unload_svc,
    ):
        result = await async_setup_entry(mock_hass, mock_config_entry)
        assert result is True
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
        assert mock_setup_svc.called
        assert mock_hass.config_entries.async_forward_entry_setups.called

        unload_result = await async_unload_entry(mock_hass, mock_config_entry)
        assert unload_result is True
        assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]
        assert mock_unload_svc.called


async def test_update_listener(mock_hass, mock_config_entry):
    """Test update listener triggers reload."""
    await async_update_listener(mock_hass, mock_config_entry)
    mock_hass.config_entries.async_reload.assert_called_once_with(
        mock_config_entry.entry_id
    )
