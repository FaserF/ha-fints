"""Binary sensor platform for the FinTS Banking integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_BANK_CODE, ATTR_LAST_UPDATE, DOMAIN
from .coordinator import FinTSDataUpdateCoordinator
from .helpers import get_bank_device_info, get_integration_version


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FinTS binary sensor entities."""
    coordinator: FinTSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    version = get_integration_version(hass)

    async_add_entities(
        [
            FinTSConnectionBinarySensor(coordinator, entry, version),
            FinTSTanRequiredBinarySensor(coordinator, entry, version),
        ]
    )


class FinTSConnectionBinarySensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor representing overall bank connectivity."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:bank-check"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize the connection status sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_connection"
        self._attr_name = "Bank Connection"
        self._attr_device_info = get_bank_device_info(entry, version)

    @property
    def is_on(self) -> bool:
        """Return True if connection is healthy and last update succeeded."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data:
            return False
        return not bool(self.coordinator.data.get("tan_required", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        return {
            ATTR_BANK_CODE: self.coordinator.data.get("bank_code"),
            ATTR_LAST_UPDATE: (
                self.coordinator.last_update.isoformat()
                if self.coordinator.last_update
                else None
            ),
        }


class FinTSTanRequiredBinarySensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor indicating whether 2FA / SCA TAN approval is pending."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:security"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize the TAN required sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_tan_required"
        self._attr_name = "TAN Challenge Required"
        self._attr_device_info = get_bank_device_info(entry, version)

    @property
    def is_on(self) -> bool:
        """Return True if bank requested a two-step TAN authentication."""
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.get("tan_required", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "action_required": "Authenticate via your bank's push app or generate TAN to resume automatic updates"
            if self.is_on
            else "None"
        }
