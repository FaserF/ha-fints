"""Data update coordinator for the FinTS Banking integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import FinTSClient
from .const import (
    CONF_BANK_CODE,
    CONF_CUSTOMER_ID,
    CONF_LOGIN,
    CONF_PIN,
    CONF_PRODUCT_ID,
    CONF_SCAN_INTERVAL,
    CONF_SERVER,
    CONF_TAN_MEDIUM,
    DEFAULT_PRODUCT_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class FinTSDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage polling FinTS banking accounts and balances."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the FinTS coordinator."""
        self.entry = entry
        interval_seconds = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        scan_interval = timedelta(seconds=max(interval_seconds, MIN_SCAN_INTERVAL))

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=scan_interval,
        )

        self.client = FinTSClient(
            hass=hass,
            bank_code=entry.data[CONF_BANK_CODE],
            login=entry.data[CONF_LOGIN],
            pin=entry.data[CONF_PIN],
            server=entry.data[CONF_SERVER],
            customer_id=entry.data.get(CONF_CUSTOMER_ID),
            product_id=entry.options.get(
                CONF_PRODUCT_ID,
                entry.data.get(CONF_PRODUCT_ID, DEFAULT_PRODUCT_ID),
            ),
            tan_medium=entry.options.get(
                CONF_TAN_MEDIUM,
                entry.data.get(CONF_TAN_MEDIUM),
            ),
        )
        self.last_update: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest banking data from FinTS."""
        data = await self.client.async_fetch_all_data()
        self.last_update = datetime.now(UTC)
        return data
