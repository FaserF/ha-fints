"""Test binary sensor platform in ha-fints."""

from datetime import UTC, datetime

from custom_components.fints.binary_sensor import (
    FinTSConnectionBinarySensor,
    FinTSTanRequiredBinarySensor,
    async_setup_entry,
)
from custom_components.fints.const import DOMAIN
from custom_components.fints.coordinator import FinTSDataUpdateCoordinator


async def test_binary_sensor_setup(mock_hass, mock_config_entry):
    """Test setting up binary sensors."""
    coord = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    coord.data = {"tan_required": False}
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: coord}

    added = []
    await async_setup_entry(
        mock_hass, mock_config_entry, lambda entities: added.extend(entities)
    )
    assert len(added) == 2


def test_connection_binary_sensor(mock_hass, mock_config_entry):
    """Test connection binary sensor state logic."""
    coord = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    sensor = FinTSConnectionBinarySensor(coord, mock_config_entry, "1.0.0")

    coord.last_update_success = True
    coord.data = {"tan_required": False, "bank_code": "37050198"}
    coord.last_update = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)

    assert sensor.is_on is True
    assert sensor.extra_state_attributes["bank_code"] == "37050198"

    # When update failed
    coord.last_update_success = False
    assert sensor.is_on is False

    # When TAN is required
    coord.last_update_success = True
    coord.data = {"tan_required": True}
    assert sensor.is_on is False


def test_tan_required_binary_sensor(mock_hass, mock_config_entry):
    """Test TAN challenge binary sensor."""
    coord = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    sensor = FinTSTanRequiredBinarySensor(coord, mock_config_entry, "1.0.0")

    coord.data = {"tan_required": False}
    assert sensor.is_on is False
    assert sensor.extra_state_attributes["action_required"] == "None"

    coord.data = {"tan_required": True}
    assert sensor.is_on is True
    assert "push app" in sensor.extra_state_attributes["action_required"]
