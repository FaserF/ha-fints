"""Test services in ha-fints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.fints.const import DOMAIN, SERVICE_GET_TRANSACTIONS, SERVICE_SYNC
from custom_components.fints.coordinator import FinTSDataUpdateCoordinator
from custom_components.fints.services import async_setup_services, async_unload_services


async def test_services_setup_and_sync(mock_hass, mock_config_entry):
    """Test fints.sync service handling."""
    coord = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    coord.async_request_refresh = AsyncMock()
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: coord}

    handlers = {}

    def mock_register(domain, service, handler, **kwargs):
        handlers[f"{domain}.{service}"] = handler

    mock_hass.services.async_register.side_effect = mock_register

    await async_setup_services(mock_hass)
    assert f"{DOMAIN}.{SERVICE_SYNC}" in handlers
    assert f"{DOMAIN}.{SERVICE_GET_TRANSACTIONS}" in handlers

    # Test sync all
    call = MagicMock()
    call.data = {}
    await handlers[f"{DOMAIN}.{SERVICE_SYNC}"](call)
    assert coord.async_request_refresh.called

    # Test sync invalid entry
    call.data = {"entry_id": "invalid_id"}
    with pytest.raises(HomeAssistantError):
        await handlers[f"{DOMAIN}.{SERVICE_SYNC}"](call)


async def test_services_get_transactions(mock_hass, mock_config_entry):
    """Test fints.get_transactions service handling."""
    coord = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    iban = "DE89370501980000012345"
    coord.data = {"accounts": {iban: {"iban": iban, "balance": 1000.0}}}
    sample_txs = [
        {
            "iban": iban,
            "amount": -25.0,
            "purpose": "Pharmacy",
            "applicant_name": "Apotheke",
        }
    ]
    coord.client.async_get_transactions = AsyncMock(return_value=sample_txs)
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: coord}

    handlers = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h, **kw: (
        handlers.update({f"{d}.{s}": h})
    )

    await async_setup_services(mock_hass)

    call = MagicMock()
    call.data = {"iban": iban, "limit": 10}
    res = await handlers[f"{DOMAIN}.{SERVICE_GET_TRANSACTIONS}"](call)
    assert res["count"] == 1
    assert res["transactions"][0]["purpose"] == "Pharmacy"

    # Test unknown IBAN
    call.data = {"iban": "DE00000000000000000000"}
    with pytest.raises(HomeAssistantError):
        await handlers[f"{DOMAIN}.{SERVICE_GET_TRANSACTIONS}"](call)


async def test_services_unload(mock_hass):
    """Test unloading services."""
    mock_hass.data[DOMAIN] = {}
    await async_unload_services(mock_hass)
    assert mock_hass.services.async_remove.call_count == 2
