"""Helper functions for the FinTS Banking integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_BANK_CODE, CONF_LOGIN, CONF_PIN, DOMAIN

_LOGGER = logging.getLogger(__name__)

_CACHED_VERSION: str | None = None


def get_integration_version(hass: HomeAssistant) -> str:
    """Return the integration version, caching it in memory to avoid event-loop blocking disk I/O."""
    global _CACHED_VERSION
    if _CACHED_VERSION is not None:
        return _CACHED_VERSION

    try:
        manifest_path = Path(__file__).parent / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)
                _CACHED_VERSION = manifest_data.get("version", "1.0.0")
                return _CACHED_VERSION
    except Exception as err:
        _LOGGER.debug("Could not read manifest version: %s", err)

    _CACHED_VERSION = "1.0.0"
    return _CACHED_VERSION


def mask_iban(iban: str | None) -> str:
    """Mask an IBAN for secure display, keeping only the country/checksum prefix and last 4 digits."""
    if not iban or len(iban) < 8:
        return "****"
    country_prefix = iban[:4]
    suffix = iban[-4:]
    masked_middle = "*" * (len(iban) - 8)
    # Format with spaces every 4 characters
    full = country_prefix + masked_middle + suffix
    return " ".join(full[i : i + 4] for i in range(0, len(full), 4))


def mask_sensitive_data(data: Any) -> Any:
    """Recursively scrub sensitive credentials (PIN, passwords, logins, IBANs) from data structures."""
    sensitive_keys = {
        CONF_PIN,
        "pin",
        "password",
        "passwd",
        "token",
        "secret",
        "access_token",
        "refresh_token",
        CONF_LOGIN,
        "login",
        "username",
        "user_id",
        "customer_id",
    }

    if isinstance(data, dict):
        masked_dict = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if key_lower in sensitive_keys:
                masked_dict[key] = "***REDACTED***"
            elif key_lower in ("iban", "accountnumber", "account_number"):
                masked_dict[key] = mask_iban(str(value)) if value else value
            else:
                masked_dict[key] = mask_sensitive_data(value)
        return masked_dict
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(mask_sensitive_data(item) for item in data)
    return data


def get_bank_device_info(entry: ConfigEntry, version: str) -> DeviceInfo:
    """Return DeviceInfo for the bank institution / gateway."""
    bank_code = entry.data.get(CONF_BANK_CODE, "Unknown")
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"FinTS Bank ({bank_code})",
        manufacturer="FinTS / HBCI",
        model="Banking Gateway",
        sw_version=version,
    )


def get_account_device_info(
    entry: ConfigEntry,
    iban: str,
    bic: str | None,
    bank_code: str | None,
    version: str,
) -> DeviceInfo:
    """Return DeviceInfo for a specific bank account."""
    masked = mask_iban(iban)
    manufacturer = bic or f"BLZ {bank_code}" if bank_code else "FinTS Banking"
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{iban}")},
        name=f"Account {masked}",
        manufacturer=manufacturer,
        model="Bank Account",
        sw_version=version,
        via_device=(DOMAIN, entry.entry_id),
    )
