"""Test button platform in ha-fints."""

from unittest.mock import AsyncMock

from custom_components.fints.button import FinTSSyncButton, async_setup_entry
from custom_components.fints.const import DOMAIN
from custom_components.fints.coordinator import FinTSDataUpdateCoordinator


async def test_button_setup_and_press(mock_hass, mock_config_entry):
    """Test button platform setup and press action."""
    coord = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    coord.async_request_refresh = AsyncMock()
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: coord}

    added = []
    await async_setup_entry(
        mock_hass, mock_config_entry, lambda entities: added.extend(entities)
    )
    assert len(added) == 1

    button = added[0]
    assert isinstance(button, FinTSSyncButton)
    assert button.name == "Sync Bank Data"

    await button.async_press()
    assert coord.async_request_refresh.called
