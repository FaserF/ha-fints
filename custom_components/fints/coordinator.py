"""Data update coordinator for FinTS."""
from __future__ import annotations
import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

class FinTSDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.entry = entry
        interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=max(interval, 3600)),
        )

    async def _async_update_data(self):
        try:
            # FinTS bank polling logic here
            return {
                "accounts": [],
                "balance": 0.0,
                "status": "connected"
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching FinTS data: {err}") from err
