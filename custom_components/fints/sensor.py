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
    ATTR_ACCOUNT,
    ATTR_ACCOUNT_NUMBER,
    ATTR_ACCOUNT_TYPE,
    ATTR_ACTIVE_TAN_MECHANISM,
    ATTR_APPLICANT_NAME,
    ATTR_AVAILABLE_TAN_MECHANISMS,
    ATTR_BALANCE_DATE,
    ATTR_BANK,
    ATTR_BANK_CODE,
    ATTR_BANK_NAME,
    ATTR_BIC,
    ATTR_CURRENCY,
    ATTR_DATE,
    ATTR_HOLDINGS,
    ATTR_HOLDINGS_COUNT,
    ATTR_IBAN,
    ATTR_LAST_UPDATE,
    ATTR_OWNER_NAME,
    ATTR_PRODUCT_NAME,
    ATTR_PURPOSE,
    ATTR_SCHEDULED_DEBITS_COUNT,
    ATTR_STATUS,
    ATTR_SUBACCOUNT,
    ATTR_TOTAL_BALANCE,
    ATTR_TOTAL_HOLDINGS,
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
        FinTSTotalBalanceSensor(coordinator, entry, version),
        FinTSTotalHoldingsSensor(coordinator, entry, version),
        FinTSNetWorthSensor(coordinator, entry, version),
        FinTSBankNameSensor(coordinator, entry, version),
        FinTSActiveTanMechanismSensor(coordinator, entry, version),
    ]

    # Add balance account sensors
    accounts = coordinator.data.get("accounts", {}) if coordinator.data else {}
    for key in accounts:
        entities.append(FinTSAccountBalanceSensor(coordinator, entry, key, version))
        entities.append(FinTSLastTransactionSensor(coordinator, entry, key, version))

    # Add holdings / depot account sensors
    holdings_accounts = (
        coordinator.data.get("holdings_accounts", {}) if coordinator.data else {}
    )
    for key in holdings_accounts:
        entities.append(FinTSHoldingsAccountSensor(coordinator, entry, key, version))

    async_add_entities(entities)


class FinTSTotalBalanceSensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity
):
    """Sensor tracking total liquid balance across checking and savings accounts."""

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
            ATTR_BANK_NAME: self.coordinator.data.get("bank_name"),
            "account_count": len(accounts),
            ATTR_LAST_UPDATE: (
                self.coordinator.last_update.isoformat()
                if self.coordinator.last_update
                else None
            ),
        }


class FinTSTotalHoldingsSensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity
):
    """Sensor tracking cumulative investment portfolio / depot value."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:chart-line"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize the total holdings sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_total_holdings"
        self._attr_name = "Total Depot Value"
        self._attr_device_info = get_bank_device_info(entry, version)

    @property
    def native_value(self) -> float:
        """Return cumulative depot valuation."""
        if not self.coordinator.data:
            return 0.0
        return float(self.coordinator.data.get("total_holdings", 0.0))

    @property
    def native_unit_of_measurement(self) -> str:
        """Return currency."""
        return "EUR"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        holdings_accs = self.coordinator.data.get("holdings_accounts", {})
        return {
            ATTR_BANK_NAME: self.coordinator.data.get("bank_name"),
            "depot_count": len(holdings_accs),
            ATTR_LAST_UPDATE: (
                self.coordinator.last_update.isoformat()
                if self.coordinator.last_update
                else None
            ),
        }


class FinTSNetWorthSensor(CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity):
    """Sensor tracking total net worth (cash balances + investment holdings)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:scale-balance"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize net worth sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_net_worth"
        self._attr_name = "Bank Net Worth"
        self._attr_device_info = get_bank_device_info(entry, version)

    @property
    def native_value(self) -> float:
        """Return combined net worth."""
        if not self.coordinator.data:
            return 0.0
        return float(self.coordinator.data.get("net_worth", 0.0))

    @property
    def native_unit_of_measurement(self) -> str:
        """Return currency."""
        return "EUR"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return breakdown attributes."""
        if not self.coordinator.data:
            return {}
        return {
            ATTR_TOTAL_BALANCE: self.coordinator.data.get("total_balance", 0.0),
            ATTR_TOTAL_HOLDINGS: self.coordinator.data.get("total_holdings", 0.0),
            ATTR_BANK_NAME: self.coordinator.data.get("bank_name"),
        }


class FinTSBankNameSensor(CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity):
    """Sensor displaying the official bank name and routing identifier."""

    _attr_icon = "mdi:bank-outline"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize bank name sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_bank_name"
        self._attr_name = "Bank Name"
        self._attr_device_info = get_bank_device_info(entry, version)

    @property
    def native_value(self) -> str:
        """Return bank name."""
        if not self.coordinator.data:
            return "Unknown"
        return str(self.coordinator.data.get("bank_name", "Unknown"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return routing parameters."""
        if not self.coordinator.data:
            return {}
        return {
            ATTR_BANK_CODE: self.coordinator.data.get("bank_code"),
            ATTR_ACTIVE_TAN_MECHANISM: (
                self.coordinator.data.get("auth", {}).get("current_tan_mechanism")
            ),
        }


class FinTSActiveTanMechanismSensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity
):
    """Sensor tracking the currently active 2FA / TAN mechanism."""

    _attr_icon = "mdi:shield-key"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize active TAN sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_active_tan"
        self._attr_name = "Active TAN Method"
        self._attr_device_info = get_bank_device_info(entry, version)

    @property
    def native_value(self) -> str:
        """Return current TAN mechanism."""
        if not self.coordinator.data:
            return "None"
        auth = self.coordinator.data.get("auth", {})
        return str(auth.get("current_tan_mechanism", "None"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return available mechanisms list."""
        if not self.coordinator.data:
            return {}
        auth = self.coordinator.data.get("auth", {})
        return {
            ATTR_AVAILABLE_TAN_MECHANISMS: auth.get("tan_mechanisms", []),
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
        account_key: str,
        version: str,
    ) -> None:
        """Initialize the account balance sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.account_key = account_key
        self._attr_unique_id = f"{entry.entry_id}_{account_key}_balance"

        account = (
            coordinator.data.get("accounts", {}).get(account_key, {})
            if coordinator.data
            else {}
        )
        iban = account.get("iban", account_key)
        masked = mask_iban(iban)
        product_name = account.get("product_name") or "Account"
        self._attr_name = f"{product_name} {masked}"

        self._attr_device_info = get_account_device_info(
            entry,
            iban=iban or account_key,
            bic=account.get("bic"),
            bank_code=account.get("blz"),
            version=version,
        )

    @property
    def _account_data(self) -> dict[str, Any]:
        """Get account dictionary from coordinator data."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get("accounts", {}).get(self.account_key, {})

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
        """Return comprehensive attributes matching official HA integration + extended fields."""
        acc = self._account_data
        txs = acc.get("transactions", [])
        bank_name = (
            self.coordinator.data.get("bank_name") if self.coordinator.data else None
        )

        attrs = {
            ATTR_ACCOUNT: acc.get("iban") or acc.get("account_number"),
            ATTR_ACCOUNT_TYPE: "balance",
            ATTR_BANK: bank_name,
            ATTR_IBAN: mask_iban(acc.get("iban")),
            ATTR_BIC: acc.get("bic"),
            ATTR_ACCOUNT_NUMBER: acc.get("account_number"),
            ATTR_SUBACCOUNT: acc.get("subaccount"),
            ATTR_BANK_CODE: acc.get("blz"),
            ATTR_PRODUCT_NAME: acc.get("product_name"),
            ATTR_OWNER_NAME: acc.get("owner_name"),
            ATTR_CURRENCY: acc.get("currency"),
            ATTR_BALANCE_DATE: acc.get("balance_date"),
            ATTR_STATUS: acc.get("status"),
            ATTR_TRANSACTION_COUNT: len(txs),
            ATTR_SCHEDULED_DEBITS_COUNT: acc.get("scheduled_debits_count", 0),
        }
        return attrs


class FinTSHoldingsAccountSensor(
    CoordinatorEntity[FinTSDataUpdateCoordinator], SensorEntity
):
    """Sensor tracking an investment portfolio / depot account with individual holdings."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:finance"

    def __init__(
        self,
        coordinator: FinTSDataUpdateCoordinator,
        entry: ConfigEntry,
        depot_key: str,
        version: str,
    ) -> None:
        """Initialize depot holdings sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.depot_key = depot_key
        self._attr_unique_id = f"{entry.entry_id}_{depot_key}_holdings"

        account = (
            coordinator.data.get("holdings_accounts", {}).get(depot_key, {})
            if coordinator.data
            else {}
        )
        acc_num = account.get("account_number") or depot_key
        prod = account.get("product_name") or "Depot"
        self._attr_name = f"{prod} {acc_num}"

        self._attr_device_info = get_account_device_info(
            entry,
            iban=account.get("iban") or depot_key,
            bic=account.get("bic"),
            bank_code=account.get("blz"),
            version=version,
        )

    @property
    def _depot_data(self) -> dict[str, Any]:
        """Return depot dictionary."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get("holdings_accounts", {}).get(
            self.depot_key, {}
        )

    @property
    def native_value(self) -> float:
        """Return total portfolio value."""
        return float(self._depot_data.get("total_value", 0.0))

    @property
    def native_unit_of_measurement(self) -> str:
        """Return currency."""
        return str(self._depot_data.get("currency", "EUR"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes matching official FinTsHoldingsAccount + modern additions."""
        depot = self._depot_data
        holdings = depot.get("holdings", [])
        bank_name = (
            self.coordinator.data.get("bank_name") if self.coordinator.data else None
        )

        attributes: dict[str, Any] = {
            ATTR_ACCOUNT: depot.get("account_number") or self.depot_key,
            ATTR_ACCOUNT_TYPE: "holdings",
            ATTR_BANK: bank_name,
            ATTR_OWNER_NAME: depot.get("owner_name"),
            ATTR_PRODUCT_NAME: depot.get("product_name"),
            ATTR_HOLDINGS_COUNT: len(holdings),
            ATTR_HOLDINGS: holdings,
        }

        # 100% compatibility with official Home Assistant FinTsHoldingsAccount attributes format:
        # "<name> total", "<name> pieces", "<name> price"
        for h in holdings:
            name = h.get("name", "Holding")
            attributes[f"{name} total"] = h.get("total_value")
            attributes[f"{name} pieces"] = h.get("pieces")
            attributes[f"{name} price"] = h.get("market_value")
            if h.get("isin"):
                attributes[f"{name} isin"] = h.get("isin")
            if h.get("profit_loss") is not None:
                attributes[f"{name} profit_loss"] = h.get("profit_loss")
                attributes[f"{name} profit_loss_pct"] = h.get("profit_loss_percent")

        return attributes


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
        account_key: str,
        version: str,
    ) -> None:
        """Initialize the last transaction sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.account_key = account_key
        self._attr_unique_id = f"{entry.entry_id}_{account_key}_last_transaction"

        account = (
            coordinator.data.get("accounts", {}).get(account_key, {})
            if coordinator.data
            else {}
        )
        iban = account.get("iban", account_key)
        masked = mask_iban(iban)
        self._attr_name = f"Last Transaction {masked}"

        self._attr_device_info = get_account_device_info(
            entry,
            iban=iban or account_key,
            bic=account.get("bic"),
            bank_code=account.get("blz"),
            version=version,
        )

    @property
    def _account_data(self) -> dict[str, Any]:
        """Get account dictionary from coordinator data."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get("accounts", {}).get(self.account_key, {})

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
            ATTR_IBAN: mask_iban(self._account_data.get("iban", self.account_key)),
            ATTR_DATE: tx.get("date"),
            ATTR_PURPOSE: tx.get("purpose"),
            ATTR_APPLICANT_NAME: tx.get("applicant_name"),
        }
