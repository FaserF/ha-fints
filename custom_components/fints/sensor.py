"""Sensor platform for the FinTS Banking integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ACCOUNT_NUMBER,
    ATTR_APPLICANT_NAME,
    ATTR_BALANCE_DATE,
    ATTR_BANK_CODE,
    ATTR_BIC,
    ATTR_CURRENCY,
    ATTR_DATE,
    ATTR_IBAN,
    ATTR_LAST_UPDATE,
    ATTR_PURPOSE,
    ATTR_STATUS,
    ATTR_SUBACCOUNT,
    ATTR_TRANSACTION_COUNT,
    DOMAIN,
)
from .coordinator import FinTSDataUpdateCoordinator
from .helpers import (
    get_account_device_info,
    get_bank_device_info,
    get_integration_version,
    mask_iban,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FinTS banking sensors from config entry."""
    coordinator: FinTSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    version = get_integration_version(hass)

    entities: list[SensorEntity] = [
        FinTSTotalBalanceSensor(coordinator, entry, version)
    ]

    accounts = coordinator.data.get("accounts", {}) if coordinator.data else {}
    for iban in accounts:
        entities.append(FinTSAccountBalanceSensor(coordinator, entry, iban, version))
        entities.append(FinTSLastTransactionSensor(coordinator, entry, iban, version))

    async_add_entities(entities)


class FinTSTotalBalanceSensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity
):
    """Sensor tracking total balance across all accounts at the bank."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:bank"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize the total balance sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_total_balance"
        self._attr_name = "Total Bank Balance"
        self._attr_device_info = get_bank_device_info(entry, version)

    @property
    def native_value(self) -> float:
        """Return the total balance."""
        if not self.coordinator.data:
            return 0.0
        return float(self.coordinator.data.get("total_balance", 0.0))

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the primary currency."""
        if not self.coordinator.data:
            return "EUR"
        return str(self.coordinator.data.get("currency", "EUR"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        accounts = self.coordinator.data.get("accounts", {})
        return {
            ATTR_BANK_CODE: self.coordinator.data.get("bank_code"),
            "account_count": len(accounts),
            ATTR_LAST_UPDATE: (
                self.coordinator.last_update.isoformat()
                if self.coordinator.last_update
                else None
            ),
        }


class FinTSAccountBalanceSensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity
):
    """Sensor tracking balance of an individual bank account."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash-multiple"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        iban: str,
        version: str,
    ) -> None:
        """Initialize the account balance sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.iban = iban
        self._attr_unique_id = f"{entry.entry_id}_{iban}_balance"
        masked = mask_iban(iban)
        self._attr_name = f"Balance {masked}"

        account = (
            coordinator.data.get("accounts", {}).get(iban, {})
            if coordinator.data
            else {}
        )
        self._attr_device_info = get_account_device_info(
            entry,
            iban=iban,
            bic=account.get("bic"),
            bank_code=account.get("blz"),
            version=version,
        )

    @property
    def _account_data(self) -> dict[str, Any]:
        """Get account dictionary from coordinator data."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get("accounts", {}).get(self.iban, {})

    @property
    def native_value(self) -> float:
        """Return the current balance amount."""
        return float(self._account_data.get("balance", 0.0))

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the account currency."""
        return str(self._account_data.get("currency", "EUR"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        acc = self._account_data
        txs = acc.get("transactions", [])
        return {
            ATTR_IBAN: mask_iban(self.iban),
            ATTR_BIC: acc.get("bic"),
            ATTR_ACCOUNT_NUMBER: acc.get("account_number"),
            ATTR_SUBACCOUNT: acc.get("subaccount"),
            ATTR_BANK_CODE: acc.get("blz"),
            ATTR_CURRENCY: acc.get("currency"),
            ATTR_BALANCE_DATE: acc.get("balance_date"),
            ATTR_STATUS: acc.get("status"),
            ATTR_TRANSACTION_COUNT: len(txs),
        }


class FinTSLastTransactionSensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity
):
    """Sensor tracking the last transaction of an account."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:swap-horizontal"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        iban: str,
        version: str,
    ) -> None:
        """Initialize the last transaction sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.iban = iban
        self._attr_unique_id = f"{entry.entry_id}_{iban}_last_transaction"
        masked = mask_iban(iban)
        self._attr_name = f"Last Transaction {masked}"

        account = (
            coordinator.data.get("accounts", {}).get(iban, {})
            if coordinator.data
            else {}
        )
        self._attr_device_info = get_account_device_info(
            entry,
            iban=iban,
            bic=account.get("bic"),
            bank_code=account.get("blz"),
            version=version,
        )

    @property
    def _account_data(self) -> dict[str, Any]:
        """Get account dictionary from coordinator data."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get("accounts", {}).get(self.iban, {})

    @property
    def _last_tx(self) -> dict[str, Any] | None:
        """Get last transaction dictionary."""
        return self._account_data.get("last_transaction")

    @property
    def native_value(self) -> float | None:
        """Return the transaction amount."""
        tx = self._last_tx
        if not tx:
            return None
        return float(tx.get("amount", 0.0))

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the transaction currency."""
        tx = self._last_tx
        if not tx:
            return self._account_data.get("currency", "EUR")
        return str(tx.get("currency", "EUR"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return transaction details."""
        tx = self._last_tx or {}
        return {
            ATTR_IBAN: mask_iban(self.iban),
            ATTR_DATE: tx.get("date"),
            ATTR_PURPOSE: tx.get("purpose"),
            ATTR_APPLICANT_NAME: tx.get("applicant_name"),
        }
