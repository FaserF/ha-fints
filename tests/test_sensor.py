"""Test sensor platform in ha-fints."""

from datetime import UTC, datetime

from custom_components.fints.const import DOMAIN
from custom_components.fints.coordinator import FinTSDataUpdateCoordinator
from custom_components.fints.sensor import (
    FinTSAccountBalanceSensor,
    FinTSActiveTanMechanismSensor,
    FinTSBankNameSensor,
    FinTSHoldingsAccountSensor,
    FinTSLastTransactionSensor,
    FinTSNetWorthSensor,
    FinTSTotalBalanceSensor,
    FinTSTotalHoldingsSensor,
    async_setup_entry,
)


def create_sample_coordinator(mock_hass, mock_config_entry):
    """Helper to create coordinator with sample multi-account and depot data."""
    coord = FinTSDataUpdateCoordinator(mock_hass, mock_config_entry)
    coord.data = {
        "bank_code": "37050198",
        "bank_name": "Commerzbank AG",
        "total_balance": 3500.50,
        "total_holdings": 12500.00,
        "net_worth": 16000.50,
        "currency": "EUR",
        "tan_required": False,
        "last_update_success": True,
        "auth": {
            "current_tan_mechanism": "901: Mobile-TAN",
            "tan_mechanisms": ["901: Mobile-TAN", "902: photoTAN"],
        },
        "accounts": {
            "DE89370501980000012345": {
                "iban": "DE89370501980000012345",
                "bic": "COBADEFFXXX",
                "account_number": "0000012345",
                "subaccount": "",
                "blz": "37050198",
                "balance": 2500.50,
                "currency": "EUR",
                "balance_date": "2026-02-01",
                "status": "ok",
                "transactions": [
                    {
                        "amount": -50.00,
                        "currency": "EUR",
                        "date": "2026-02-01",
                        "purpose": "Coffee Shop",
                        "applicant_name": "Espresso Bar",
                    }
                ],
                "last_transaction": {
                    "amount": -50.00,
                    "currency": "EUR",
                    "date": "2026-02-01",
                    "purpose": "Coffee Shop",
                    "applicant_name": "Espresso Bar",
                },
            },
            "DE89370501980000099999": {
                "iban": "DE89370501980000099999",
                "bic": "COBADEFFXXX",
                "account_number": "0000099999",
                "subaccount": "01",
                "blz": "37050198",
                "balance": 1000.00,
                "currency": "EUR",
                "balance_date": "2026-02-01",
                "status": "ok",
                "transactions": [],
                "last_transaction": None,
            },
        },
        "holdings_accounts": {
            "9876543210": {
                "account_number": "9876543210",
                "iban": "",
                "bic": "COBADEFFXXX",
                "blz": "37050198",
                "type": "holdings",
                "product_name": "DirektDepot",
                "owner_name": "Max Mustermann",
                "total_value": 12500.00,
                "currency": "EUR",
                "holdings_count": 1,
                "holdings": [
                    {
                        "isin": "IE00B4L5Y983",
                        "name": "iShares Core MSCI World",
                        "pieces": 150.0,
                        "market_value": 83.33,
                        "total_value": 12500.00,
                        "currency": "EUR",
                        "valuation_date": "2026-02-01",
                        "acquisition_price": 70.00,
                        "profit_loss": 2000.00,
                        "profit_loss_percent": 19.05,
                    }
                ],
            }
        },
    }
    coord.last_update = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)
    return coord


async def test_sensor_async_setup_entry(mock_hass, mock_config_entry):
    """Test setting up sensors from coordinator."""
    coord = create_sample_coordinator(mock_hass, mock_config_entry)
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: coord}

    added_entities = []

    def mock_add_entities(entities):
        added_entities.extend(entities)

    await async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

    # 5 integration sensors + (2 accounts * 2 = 4) + (1 depot * 1 = 1) = 10 entities
    assert len(added_entities) == 10


def test_total_balance_sensor(mock_hass, mock_config_entry):
    """Test total balance sensor properties."""
    coord = create_sample_coordinator(mock_hass, mock_config_entry)
    sensor = FinTSTotalBalanceSensor(coord, mock_config_entry, "1.0.0")

    assert sensor.native_value == 3500.50
    assert sensor.native_unit_of_measurement == "EUR"
    attrs = sensor.extra_state_attributes
    assert attrs["bank_code"] == "37050198"
    assert attrs["bank_name"] == "Commerzbank AG"
    assert attrs["account_count"] == 2
    assert "2026-02-01" in attrs["last_update"]


def test_total_holdings_sensor(mock_hass, mock_config_entry):
    """Test total holdings sensor properties."""
    coord = create_sample_coordinator(mock_hass, mock_config_entry)
    sensor = FinTSTotalHoldingsSensor(coord, mock_config_entry, "1.0.0")

    assert sensor.native_value == 12500.00
    assert sensor.native_unit_of_measurement == "EUR"
    attrs = sensor.extra_state_attributes
    assert attrs["depot_count"] == 1
    assert attrs["bank_name"] == "Commerzbank AG"


def test_net_worth_sensor(mock_hass, mock_config_entry):
    """Test combined net worth sensor properties."""
    coord = create_sample_coordinator(mock_hass, mock_config_entry)
    sensor = FinTSNetWorthSensor(coord, mock_config_entry, "1.0.0")

    assert sensor.native_value == 16000.50
    assert sensor.native_unit_of_measurement == "EUR"
    attrs = sensor.extra_state_attributes
    assert attrs["total_balance"] == 3500.50
    assert attrs["total_holdings"] == 12500.00
    assert attrs["bank_name"] == "Commerzbank AG"


def test_bank_name_and_tan_sensors(mock_hass, mock_config_entry):
    """Test bank metadata and active TAN sensors."""
    coord = create_sample_coordinator(mock_hass, mock_config_entry)
    bank_sensor = FinTSBankNameSensor(coord, mock_config_entry, "1.0.0")
    assert bank_sensor.native_value == "Commerzbank AG"
    assert bank_sensor.extra_state_attributes["bank_code"] == "37050198"

    tan_sensor = FinTSActiveTanMechanismSensor(coord, mock_config_entry, "1.0.0")
    assert tan_sensor.native_value == "901: Mobile-TAN"
    assert (
        "902: photoTAN" in tan_sensor.extra_state_attributes["available_tan_mechanisms"]
    )


def test_holdings_account_sensor(mock_hass, mock_config_entry):
    """Test official FinTsHoldingsAccount compatibility attributes."""
    coord = create_sample_coordinator(mock_hass, mock_config_entry)
    sensor = FinTSHoldingsAccountSensor(coord, mock_config_entry, "9876543210", "1.0.0")

    assert sensor.native_value == 12500.00
    assert sensor.native_unit_of_measurement == "EUR"
    attrs = sensor.extra_state_attributes
    assert attrs["account"] == "9876543210"
    assert attrs["account_type"] == "holdings"
    assert attrs["bank"] == "Commerzbank AG"
    assert attrs["owner_name"] == "Max Mustermann"
    assert attrs["product_name"] == "DirektDepot"
    assert attrs["holdings_count"] == 1

    # Official HA format check: "<name> total", "<name> pieces", "<name> price"
    assert attrs["iShares Core MSCI World total"] == 12500.00
    assert attrs["iShares Core MSCI World pieces"] == 150.0
    assert attrs["iShares Core MSCI World price"] == 83.33
    assert attrs["iShares Core MSCI World isin"] == "IE00B4L5Y983"
    assert attrs["iShares Core MSCI World profit_loss"] == 2000.00
    assert attrs["iShares Core MSCI World profit_loss_pct"] == 19.05


def test_account_balance_sensor(mock_hass, mock_config_entry):
    """Test account balance sensor properties and masking."""
    coord = create_sample_coordinator(mock_hass, mock_config_entry)
    iban = "DE89370501980000012345"
    sensor = FinTSAccountBalanceSensor(coord, mock_config_entry, iban, "1.0.0")

    assert sensor.native_value == 2500.50
    assert sensor.native_unit_of_measurement == "EUR"
    attrs = sensor.extra_state_attributes
    assert attrs["bic"] == "COBADEFFXXX"
    assert attrs["status"] == "ok"
    assert attrs["transaction_count"] == 1
    # Verify IBAN is masked
    assert "DE89" in attrs["iban"]
    assert "0000" not in attrs["iban"]


def test_last_transaction_sensor(mock_hass, mock_config_entry):
    """Test last transaction sensor with and without transactions."""
    coord = create_sample_coordinator(mock_hass, mock_config_entry)
    iban1 = "DE89370501980000012345"
    sensor1 = FinTSLastTransactionSensor(coord, mock_config_entry, iban1, "1.0.0")

    assert sensor1.native_value == -50.00
    assert sensor1.native_unit_of_measurement == "EUR"
    attrs1 = sensor1.extra_state_attributes
    assert attrs1["purpose"] == "Coffee Shop"
    assert attrs1["applicant_name"] == "Espresso Bar"

    iban2 = "DE89370501980000099999"
    sensor2 = FinTSLastTransactionSensor(coord, mock_config_entry, iban2, "1.0.0")
    assert sensor2.native_value is None
