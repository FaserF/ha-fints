"""Button platform for the FinTS Banking integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FinTSDataUpdateCoordinator
from .helpers import get_bank_device_info, get_integration_version


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FinTS button entities."""
    coordinator: FinTSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    version = get_integration_version(hass)

    async_add_entities([FinTSSyncButton(coordinator, entry, version)])


class FinTSSyncButton(CoordinatorEntity[FinTSDataUpdateCoordinator], ButtonEntity):
    """Button to manually trigger FinTS bank synchronization."""

    _attr_device_class = ButtonDeviceClass.UPDATE
    _attr_icon = "mdi:sync"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize the sync button."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sync"
        self._attr_name = "Sync Bank Data"
        self._attr_device_info = get_bank_device_info(entry, version)

    async def async_press(self) -> None:
        """Handle button press to refresh data."""
        await self.coordinator.async_request_refresh()
