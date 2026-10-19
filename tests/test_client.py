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
