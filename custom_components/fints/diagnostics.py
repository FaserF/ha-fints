"""Diagnostics support for FinTS Banking."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import FinTSDataUpdateCoordinator
from .helpers import get_integration_version, mask_sensitive_data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry with sensitive credentials redacted."""
    coordinator: FinTSDataUpdateCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )

    coordinator_data = coordinator.data if coordinator else None

    return {
        "integration_version": get_integration_version(hass),
        "entry_data": mask_sensitive_data(dict(entry.data)),
        "entry_options": mask_sensitive_data(dict(entry.options)),
        "coordinator_data": mask_sensitive_data(coordinator_data)
        if coordinator_data
        else None,
        "last_update": (
            coordinator.last_update.isoformat()
            if coordinator and coordinator.last_update
            else None
        ),
        "last_update_success": coordinator.last_update_success
        if coordinator
        else False,
    }
