"""Test FinTS client wrapper in ha-fints."""

from unittest.mock import MagicMock, patch

import pytest
from fints.exceptions import (
    FinTSClientPINError,
    FinTSConnectionError,
    FinTSSCARequiredError,
)
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.fints.client import FinTSClient


@pytest.fixture
def fints_client(mock_hass) -> FinTSClient:
    """Create a FinTSClient instance for tests."""
    return FinTSClient(
        hass=mock_hass,
        bank_code="37050198",
        login="testuser",
        pin="secret123",
        server="https://fints.bank.de/fints",
    )


async def test_connect_and_test_success(fints_client, mock_fints_client):
    """Test successful connection test."""
    with patch.object(
        fints_client, "_create_raw_client", return_value=mock_fints_client
    ):
        accounts = await fints_client.async_connect_and_test()
        assert len(accounts) == 2
        assert accounts[0].iban == "DE89370501980000012345"


async def test_connect_and_test_invalid_pin(fints_client):
    """Test invalid credentials error mapping."""
    mock_raw = MagicMock()
    mock_raw.get_sepa_accounts.side_effect = FinTSClientPINError("Bad PIN")

    with patch.object(fints_client, "_create_raw_client", return_value=mock_raw):
        with pytest.raises(ConfigEntryAuthFailed):
            await fints_client.async_connect_and_test()


async def test_connect_and_test_connection_error(fints_client):
    """Test server connection error mapping."""
    mock_raw = MagicMock()
    mock_raw.get_sepa_accounts.side_effect = FinTSConnectionError("Network timeout")

    with patch.object(fints_client, "_create_raw_client", return_value=mock_raw):
        with pytest.raises(UpdateFailed):
            await fints_client.async_connect_and_test()


async def test_connect_and_test_sca_required(fints_client):
    """Test SCA required error mapping."""
    mock_raw = MagicMock()
    mock_raw.get_sepa_accounts.side_effect = FinTSSCARequiredError("Need TAN")

    with patch.object(fints_client, "_create_raw_client", return_value=mock_raw):
        with pytest.raises(HomeAssistantError):
            await fints_client.async_connect_and_test()


async def test_fetch_all_data_success(fints_client, mock_fints_client):
    """Test fetching all banking accounts, balances, and transactions."""
    with patch.object(
        fints_client, "_create_raw_client", return_value=mock_fints_client
    ):
        data = await fints_client.async_fetch_all_data()

        assert data["bank_code"] == "37050198"
        assert data["total_balance"] == 3000.50
        assert data["currency"] == "EUR"
        assert not data["tan_required"]
        assert data["last_update_success"]

        accounts = data["accounts"]
        assert len(accounts) == 2
        acc1 = accounts["DE89370501980000012345"]
        assert acc1["balance"] == 2500.50
        assert acc1["currency"] == "EUR"
        assert acc1["last_transaction"]["amount"] == -49.99
        assert acc1["last_transaction"]["applicant_name"] == "REWE Market"


async def test_fetch_all_data_sca_handling(fints_client):
    """Test handling of 2FA TAN challenges during polling."""
    mock_raw = MagicMock()
    mock_raw.get_sepa_accounts.side_effect = FinTSSCARequiredError("TAN required")

    with patch.object(fints_client, "_create_raw_client", return_value=mock_raw):
        data = await fints_client.async_fetch_all_data()
        assert data["tan_required"] is True
        assert data["last_update_success"] is False


async def test_get_transactions_success(fints_client, mock_fints_client):
    """Test fetching transactions for a specific account."""
    with patch.object(
        fints_client, "_create_raw_client", return_value=mock_fints_client
    ):
        txs = await fints_client.async_get_transactions("DE89370501980000012345")
        assert len(txs) == 2
        assert txs[0]["iban"] == "DE89370501980000012345"
        assert txs[0]["amount"] == -49.99


async def test_get_transactions_account_not_found(fints_client, mock_fints_client):
    """Test error when account does not exist."""
    with patch.object(
        fints_client, "_create_raw_client", return_value=mock_fints_client
    ):
        with pytest.raises(HomeAssistantError):
            await fints_client.async_get_transactions("DE99999999999999999999")


async def test_get_holdings_success(fints_client, mock_fints_client):
    """Test fetching depot securities holdings."""
    from tests.conftest import MockHolding, MockSEPAAccount

    mock_fints_client.get_sepa_accounts.return_value.append(
        MockSEPAAccount(
            iban="",
            bic="COBADEFFXXX",
            accountnumber="9876543210",
            subaccount="",
            blz="37050198",
        )
    )
    mock_fints_client.get_holdings.return_value = [MockHolding()]

    with patch.object(
        fints_client, "_create_raw_client", return_value=mock_fints_client
    ):
        holdings = await fints_client.async_get_holdings("9876543210")
        assert len(holdings) == 1
        assert holdings[0]["isin"] == "IE00B4L5Y983"
        assert holdings[0]["pieces"] == 100.0
        assert holdings[0]["total_value"] == 8550.0


async def test_get_holdings_account_not_found(fints_client, mock_fints_client):
    """Test error when depot account does not exist."""
    with patch.object(
        fints_client, "_create_raw_client", return_value=mock_fints_client
    ):
        with pytest.raises(HomeAssistantError):
            await fints_client.async_get_holdings("NONEXISTENT_DEPOT")


async def test_fetch_all_data_with_holdings_and_metadata(
    fints_client, mock_fints_client
):
    """Test full fetch cycle including depot accounts, profit/loss, and metadata."""
    from tests.conftest import MockHolding, MockSEPAAccount

    depot_acc = MockSEPAAccount(
        iban="DE89370501980000055555",
        bic="COBADEFFXXX",
        accountnumber="0000055555",
        subaccount="",
        blz="37050198",
    )
    mock_fints_client.get_sepa_accounts.return_value = [depot_acc]
    mock_fints_client.get_information.return_value = {
        "bank_name": "Deutsche Bank AG",
        "accounts": [
            {
                "iban": "DE89370501980000055555",
                "accountnumber": "0000055555",
                "type": 30,  # Depot account
                "product_name": "Top-Depot",
                "owner_name": ["Erika Mustermann"],
            }
        ],
        "auth": {
            "current_tan_mechanism": "902: pushTAN",
            "tan_mechanisms": ["902: pushTAN"],
        },
    }
    mock_fints_client.get_holdings.return_value = [
        MockHolding(
            ISIN="US0378331005",
            name="Apple Inc.",
            pieces=50.0,
            market_value=200.0,
            total_value=10000.0,
            value_symbol="EUR",
            acquisitionprice=150.0,
        )
    ]

    with patch.object(
        fints_client, "_create_raw_client", return_value=mock_fints_client
    ):
        data = await fints_client.async_fetch_all_data()

        assert data["bank_name"] == "Deutsche Bank AG"
        assert data["total_balance"] == 0.0
        assert data["total_holdings"] == 10000.0
        assert data["net_worth"] == 10000.0
        assert len(data["holdings_accounts"]) == 1
        assert len(data["accounts"]) == 0

        depot = data["holdings_accounts"]["DE89370501980000055555"]
        assert depot["product_name"] == "Top-Depot"
        assert depot["owner_name"] == "Erika Mustermann"
        assert len(depot["holdings"]) == 1
        h = depot["holdings"][0]
        assert h["isin"] == "US0378331005"
        # profit_loss = 10000 - (50 * 150 = 7500) = 2500
        assert h["profit_loss"] == 2500.0
        assert h["profit_loss_percent"] == 33.33
