"""Custom services for the FinTS Banking integration."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, SERVICE_GET_HOLDINGS, SERVICE_GET_TRANSACTIONS, SERVICE_SYNC
from .coordinator import FinTSDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SYNC_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)

GET_TRANSACTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("iban"): cv.string,
        vol.Optional("entry_id"): cv.string,
        vol.Optional("start_date"): cv.date,
        vol.Optional("end_date"): cv.date,
        vol.Optional("limit", default=50): cv.positive_int,
    }
)

GET_HOLDINGS_SCHEMA = vol.Schema(
    {
        vol.Required("account"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register FinTS integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_SYNC):
        return

    async def async_handle_sync(call: ServiceCall) -> None:
        """Handle fints.sync service call."""
        entry_id = call.data.get("entry_id")
        coordinators: dict[str, FinTSDataUpdateCoordinator] = hass.data.get(DOMAIN, {})

        if entry_id:
            if entry_id not in coordinators:
                raise HomeAssistantError(f"Config entry '{entry_id}' not found.")
            await coordinators[entry_id].async_request_refresh()
        else:
            for coord in coordinators.values():
                await coord.async_request_refresh()

    async def async_handle_get_transactions(call: ServiceCall) -> dict[str, Any]:
        """Handle fints.get_transactions service call."""
        iban = str(call.data["iban"]).replace(" ", "").upper()
        entry_id = call.data.get("entry_id")
        start_date: date | None = call.data.get("start_date")
        end_date: date | None = call.data.get("end_date")
        limit: int = call.data.get("limit", 50)

        coordinators: dict[str, FinTSDataUpdateCoordinator] = hass.data.get(DOMAIN, {})

        target_coordinator: FinTSDataUpdateCoordinator | None = None
        if entry_id:
            target_coordinator = coordinators.get(entry_id)
            if not target_coordinator:
                raise HomeAssistantError(f"Config entry '{entry_id}' not found.")
        else:
            # Locate coordinator containing this IBAN
            for coord in coordinators.values():
                if coord.data and iban in coord.data.get("accounts", {}):
                    target_coordinator = coord
                    break

        if not target_coordinator:
            raise HomeAssistantError(
                f"No FinTS account matching IBAN '{iban}' found in active configurations."
            )

        transactions = await target_coordinator.client.async_get_transactions(
            iban=iban,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "iban": iban,
            "count": len(transactions[:limit]),
            "transactions": transactions[:limit],
        }

    async def async_handle_get_holdings(call: ServiceCall) -> dict[str, Any]:
        """Handle fints.get_holdings service call."""
        account = str(call.data["account"]).replace(" ", "").upper()
        entry_id = call.data.get("entry_id")

        coordinators: dict[str, FinTSDataUpdateCoordinator] = hass.data.get(DOMAIN, {})

        target_coordinator: FinTSDataUpdateCoordinator | None = None
        if entry_id:
            target_coordinator = coordinators.get(entry_id)
            if not target_coordinator:
                raise HomeAssistantError(f"Config entry '{entry_id}' not found.")
        else:
            for coord in coordinators.values():
                if coord.data:
                    if account in coord.data.get(
                        "holdings_accounts", {}
                    ) or account in coord.data.get("accounts", {}):
                        target_coordinator = coord
                        break

        if not target_coordinator:
            raise HomeAssistantError(
                f"No FinTS depot account matching '{account}' found in active configurations."
            )

        holdings = await target_coordinator.client.async_get_holdings(account)

        return {
            "account": account,
            "count": len(holdings),
            "holdings": holdings,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC,
        async_handle_sync,
        schema=SYNC_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_TRANSACTIONS,
        async_handle_get_transactions,
        schema=GET_TRANSACTIONS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_HOLDINGS,
        async_handle_get_holdings,
        schema=GET_HOLDINGS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload FinTS services if no entries remain."""
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SYNC)
        hass.services.async_remove(DOMAIN, SERVICE_GET_TRANSACTIONS)
        hass.services.async_remove(DOMAIN, SERVICE_GET_HOLDINGS)
