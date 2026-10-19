"""Pytest configuration and mocks for the FinTS Banking integration tests."""

import sys
import types
from dataclasses import dataclass
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Windows compatibility stubs
if sys.platform == "win32":
    if "fcntl" not in sys.modules:
        fcntl_mock = types.ModuleType("fcntl")
        fcntl_mock.LOCK_EX = 2
        fcntl_mock.LOCK_NB = 4
        fcntl_mock.LOCK_SH = 1
        fcntl_mock.LOCK_UN = 8
        fcntl_mock.flock = MagicMock()
        sys.modules["fcntl"] = fcntl_mock

    if "resource" not in sys.modules:
        resource_mock = types.ModuleType("resource")
        resource_mock.RLIMIT_NOFILE = 7
        resource_mock.getrlimit = MagicMock(return_value=(1024, 2048))
        resource_mock.setrlimit = MagicMock()
        sys.modules["resource"] = resource_mock

if "voluptuous" not in sys.modules:
    vol_mock = MagicMock()
    vol_mock.Schema = lambda schema, *args, **kwargs: schema
    vol_mock.Required = lambda key, *args, **kwargs: key
    vol_mock.Optional = lambda key, *args, **kwargs: key
    vol_mock.Coerce = lambda typ: typ
    vol_mock.In = lambda items: items
    vol_mock.All = lambda *validators: validators[0]
    vol_mock.Range = lambda **kwargs: kwargs
    sys.modules["voluptuous"] = vol_mock


def mock_submodule(name: str) -> None:
    """Recursively mock submodules to ensure they are available in sys.modules."""
    parts = name.split(".")
    for i in range(1, len(parts) + 1):
        full_name = ".".join(parts[:i])
        if full_name not in sys.modules:
            mock = MagicMock()
            mock.__path__ = []
            sys.modules[full_name] = mock
            if i > 1:
                parent_name = ".".join(parts[: i - 1])
                setattr(sys.modules[parent_name], parts[i - 1], mock)
        else:
            if not hasattr(sys.modules[full_name], "__path__"):
                sys.modules[full_name].__path__ = []


@dataclass(frozen=True, kw_only=True)
class MockEntityDescription:
    """Base class for mocked entity descriptions."""

    key: str
    name: str | None = None
    icon: str | None = None
    entity_registry_enabled_default: bool = True
    entity_category: Any = None
    translation_key: str | None = None
    has_entity_name: bool = False
    device_class: Any = None
    native_unit_of_measurement: str | None = None
    state_class: Any = None


class MockEntity:
    """Base class for mocked Home Assistant entities."""

    _attr_has_entity_name: bool = False
    _attr_name: str | None = None
    _attr_unique_id: str | None = None
    _attr_device_info: dict[str, Any] | None = None
    _attr_extra_state_attributes: dict[str, Any] | None = None
    _attr_icon: str | None = None
    entity_description: Any = None
    hass: Any = None

    @property
    def name(self) -> str | None:
        if self._attr_name is not None:
            return self._attr_name
        if hasattr(self, "entity_description") and self.entity_description:
            return getattr(self.entity_description, "name", None)
        return None

    @property
    def unique_id(self) -> str | None:
        return self._attr_unique_id

    @property
    def device_info(self) -> dict[str, Any] | None:
        return self._attr_device_info

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return self._attr_extra_state_attributes

    def async_write_ha_state(self) -> None:
        pass


class MockCoordinatorEntity(MockEntity):
    """Base class for coordinator entities."""

    @classmethod
    def __class_getitem__(cls, _):
        return cls

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator
        self.hass = getattr(coordinator, "hass", None)

    @property
    def available(self) -> bool:
        if self.coordinator and hasattr(self.coordinator, "last_update_success"):
            return self.coordinator.last_update_success
        return True


class MockDataUpdateCoordinator:
    """Mock DataUpdateCoordinator."""

    @classmethod
    def __class_getitem__(cls, _):
        return cls

    def __init__(
        self,
        hass: Any,
        logger: Any,
        *,
        name: str,
        update_interval: Any = None,
        update_method: Any = None,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.update_method = update_method
        self.data: Any = None
        self.last_update_success = True
        self._listeners: list[Any] = []

    def async_add_listener(self, update_callback: Any, context: Any = None) -> Any:
        self._listeners.append(update_callback)
        return lambda: self._listeners.remove(update_callback)

    async def async_refresh(self) -> None:
        if hasattr(self, "_async_update_data"):
            self.data = await self._async_update_data()

    async def async_request_refresh(self) -> None:
        await self.async_refresh()

    async def async_config_entry_first_refresh(self) -> None:
        await self.async_refresh()


class MockConfigFlow:
    """Mock ConfigFlow."""

    def __init_subclass__(cls, domain: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._domain = domain

    def __init__(self) -> None:
        self.hass: Any = None
        self._unique_id: str | None = None
        self.context: dict[str, Any] = {}

    async def async_set_unique_id(self, unique_id: str) -> None:
        self._unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        pass

    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any = None,
        errors: dict[str, str] | None = None,
        description_placeholders: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
            "description_placeholders": description_placeholders or {},
        }

    def async_create_entry(
        self,
        *,
        title: str,
        data: dict[str, Any],
        description: str | None = None,
        description_placeholders: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {
            "type": "create_entry",
            "title": title,
            "data": data,
            "description": description,
            "description_placeholders": description_placeholders,
        }

    def async_abort(self, *, reason: str) -> dict[str, Any]:
        return {"type": "abort", "reason": reason}


class MockOptionsFlow:
    """Mock OptionsFlow."""

    def __init__(self, config_entry: Any = None) -> None:
        self.config_entry = config_entry
        self.hass: Any = None

    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any = None,
        errors: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
        }

    def async_create_entry(
        self, *, title: str = "", data: dict[str, Any]
    ) -> dict[str, Any]:
        return {"type": "create_entry", "title": title, "data": data}


# Setup homeassistant mocks
mock_submodule("homeassistant.const")
mock_submodule("homeassistant.core")
mock_submodule("homeassistant.exceptions")
mock_submodule("homeassistant.config_entries")
mock_submodule("homeassistant.helpers.update_coordinator")
mock_submodule("homeassistant.helpers.entity")
mock_submodule("homeassistant.helpers.entity_platform")
mock_submodule("homeassistant.helpers.config_validation")
mock_submodule("homeassistant.helpers.device_registry")
mock_submodule("homeassistant.helpers.typing")
mock_submodule("homeassistant.components.sensor")
mock_submodule("homeassistant.components.binary_sensor")
mock_submodule("homeassistant.components.button")

ha_typing = sys.modules["homeassistant.helpers.typing"]
ha_typing.ConfigType = dict[str, Any]
ha_typing.DiscoveryInfoType = dict[str, Any]

ha_const = sys.modules["homeassistant.const"]
ha_const.Platform = types.SimpleNamespace(
    SENSOR="sensor",
    BINARY_SENSOR="binary_sensor",
    BUTTON="button",
)

ha_core = sys.modules["homeassistant.core"]
ha_core.HomeAssistant = MagicMock
ha_core.ServiceCall = MagicMock
ha_core.SupportsResponse = types.SimpleNamespace(
    NONE="none",
    OPTIONAL="optional",
    ONLY="only",
)
ha_core.callback = lambda fn: fn

ha_exc = sys.modules["homeassistant.exceptions"]


class MockHomeAssistantError(Exception):
    pass


class MockConfigEntryAuthFailed(MockHomeAssistantError):
    pass


ha_exc.HomeAssistantError = MockHomeAssistantError
ha_exc.ConfigEntryAuthFailed = MockConfigEntryAuthFailed


class MockUpdateFailed(MockHomeAssistantError):
    pass


coord_module = sys.modules["homeassistant.helpers.update_coordinator"]
coord_module.DataUpdateCoordinator = MockDataUpdateCoordinator
coord_module.CoordinatorEntity = MockCoordinatorEntity
coord_module.UpdateFailed = MockUpdateFailed

entity_module = sys.modules["homeassistant.helpers.entity"]
entity_module.Entity = MockEntity

dev_reg = sys.modules["homeassistant.helpers.device_registry"]
dev_reg.DeviceInfo = dict

config_val = sys.modules["homeassistant.helpers.config_validation"]
config_val.string = str
config_val.date = lambda val: val
config_val.positive_int = int
config_val.PLATFORM_SCHEMA = MagicMock()
config_val.PLATFORM_SCHEMA.extend = lambda schema, *args, **kwargs: schema
config_val.ensure_list = lambda x: [x] if not isinstance(x, list) else x

sensor_module = sys.modules["homeassistant.components.sensor"]


class MockSensorEntity(MockEntity):
    _attr_native_value: Any = None
    _attr_native_unit_of_measurement: str | None = None
    _attr_state_class: Any = None
    _attr_device_class: Any = None

    @property
    def native_value(self) -> Any:
        return self._attr_native_value

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._attr_native_unit_of_measurement


sensor_module.SensorEntity = MockSensorEntity
sensor_module.SensorEntityDescription = MockEntityDescription
sensor_module.SensorStateClass = types.SimpleNamespace(
    TOTAL="total",
    MEASUREMENT="measurement",
)
sensor_module.SensorDeviceClass = types.SimpleNamespace(
    MONETARY="monetary",
)

bs_module = sys.modules["homeassistant.components.binary_sensor"]


class MockBinarySensorEntity(MockEntity):
    _attr_is_on: bool = False

    @property
    def is_on(self) -> bool:
        return self._attr_is_on


bs_module.BinarySensorEntity = MockBinarySensorEntity
bs_module.BinarySensorEntityDescription = MockEntityDescription
bs_module.BinarySensorDeviceClass = types.SimpleNamespace(
    CONNECTIVITY="connectivity",
    PROBLEM="problem",
)

btn_module = sys.modules["homeassistant.components.button"]


class MockButtonEntity(MockEntity):
    async def async_press(self) -> None:
        pass


btn_module.ButtonEntity = MockButtonEntity
btn_module.ButtonEntityDescription = MockEntityDescription
btn_module.ButtonDeviceClass = types.SimpleNamespace(
    UPDATE="update",
)

cfg_module = sys.modules["homeassistant.config_entries"]
cfg_module.ConfigFlow = MockConfigFlow
cfg_module.OptionsFlow = MockOptionsFlow
cfg_module.ConfigEntry = MagicMock
cfg_module.ConfigFlowResult = dict
cfg_module.SOURCE_IMPORT = "import"


@dataclass
class MockSEPAAccount:
    """Mock SEPA Account for tests."""

    iban: str = "DE89370501980000012345"
    bic: str = "COBADEFFXXX"
    accountnumber: str = "0000012345"
    subaccount: str = ""
    blz: str = "37050198"


@dataclass
class MockBalanceAmount:
    """Mock Amount for tests."""

    amount: float = 1250.75
    currency: str = "EUR"


@dataclass
class MockBalance:
    """Mock Balance for tests."""

    amount: Any = None
    date: Any = date(2026, 1, 15)
    status: str = "C"

    def __post_init__(self):
        if self.amount is None:
            self.amount = MockBalanceAmount()


@dataclass
class MockTransaction:
    """Mock Transaction for tests."""

    data: dict[str, Any]


@dataclass
class MockHolding:
    """Mock Holding for depot tests."""

    ISIN: str = "IE00B4L5Y983"
    name: str = "iShares Core MSCI World"
    pieces: float = 100.0
    market_value: float = 85.50
    total_value: float = 8550.0
    value_symbol: str = "EUR"
    valuation_date: Any = date(2026, 2, 1)
    acquisitionprice: float = 75.00


@pytest.fixture
def mock_hass() -> MagicMock:
    """Fixture providing a mocked Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.services = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock(return_value=True)
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_get_entry = MagicMock()

    async def async_add_executor_job(target, *args, **kwargs):
        return target(*args, **kwargs)

    hass.async_add_executor_job = AsyncMock(side_effect=async_add_executor_job)
    return hass


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Fixture providing a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_fints_123"
    entry.data = {
        "bank_code": "37050198",
        "login": "testuser",
        "pin": "secret123",
        "server": "https://fints.bank.de/fints",
        "customer_id": "testuser",
        "product_id": "9FA6681DEC0E304684CCAC800",
    }
    entry.options = {
        "scan_interval": 14400,
    }
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock()
    return entry


@pytest.fixture
def mock_fints_client() -> MagicMock:
    """Fixture providing a mocked raw FinTS3PinTanClient."""
    raw = MagicMock()
    raw.get_sepa_accounts.return_value = [
        MockSEPAAccount(
            iban="DE89370501980000012345",
            bic="COBADEFFXXX",
            accountnumber="0000012345",
            subaccount="",
            blz="37050198",
        ),
        MockSEPAAccount(
            iban="DE89370501980000099999",
            bic="COBADEFFXXX",
            accountnumber="0000099999",
            subaccount="01",
            blz="37050198",
        ),
    ]

    def mock_get_balance(acc):
        if acc.iban == "DE89370501980000012345":
            return MockBalance(
                amount=MockBalanceAmount(amount=2500.50, currency="EUR"),
                date=date(2026, 2, 1),
                status="C",
            )
        return MockBalance(
            amount=MockBalanceAmount(amount=500.00, currency="EUR"),
            date=date(2026, 2, 1),
            status="C",
        )

    raw.get_balance.side_effect = mock_get_balance

    raw.get_transactions.return_value = [
        MockTransaction(
            data={
                "amount": MockBalanceAmount(amount=-49.99, currency="EUR"),
                "date": "2026-02-01",
                "purpose": "Supermarket Groceries",
                "applicant_name": "REWE Market",
            }
        ),
        MockTransaction(
            data={
                "amount": MockBalanceAmount(amount=2000.00, currency="EUR"),
                "date": "2026-01-28",
                "purpose": "Monthly Salary",
                "applicant_name": "Acme Corp",
            }
        ),
    ]

    return raw
