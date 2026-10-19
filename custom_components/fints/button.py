"""Button platform for FinTS sync."""
from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FinTSSyncButton(coordinator, entry)])

class FinTSSyncButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_sync"
        self._attr_name = "FinTS Sync Now"

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
