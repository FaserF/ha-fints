"""Test config flow and options flow in ha-fints."""

from unittest.mock import AsyncMock, patch

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.fints.config_flow import FinTSConfigFlow, FinTSOptionsFlowHandler
from custom_components.fints.const import (
    CONF_BANK_CODE,
    CONF_LOGIN,
    CONF_PIN,
    CONF_PRODUCT_ID,
    CONF_SCAN_INTERVAL,
    CONF_SERVER,
    CONF_TRANSACTION_DAYS,
)


async def test_config_flow_user_form(mock_hass):
    """Test user step shows schema form initially."""
    flow = FinTSConfigFlow()
    flow.hass = mock_hass

    result = await flow.async_step_user(None)
    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_config_flow_user_success(mock_hass):
    """Test user step creates entry on valid credentials."""
    flow = FinTSConfigFlow()
    flow.hass = mock_hass

    user_input = {
        CONF_BANK_CODE: "37050198",
        CONF_LOGIN: "testuser",
        CONF_PIN: "secret123",
        CONF_SERVER: "https://fints.bank.de/fints",
    }

    with patch(
        "custom_components.fints.config_flow.FinTSClient.async_connect_and_test",
        AsyncMock(return_value=[]),
    ):
        result = await flow.async_step_user(user_input)
        assert result["type"] == "create_entry"
        assert result["title"] == "FinTS 37050198 (testuser)"
        assert result["data"][CONF_BANK_CODE] == "37050198"


async def test_config_flow_user_invalid_auth(mock_hass):
    """Test user step returns invalid_auth on bad credentials."""
    flow = FinTSConfigFlow()
    flow.hass = mock_hass

    user_input = {
        CONF_BANK_CODE: "37050198",
        CONF_LOGIN: "testuser",
        CONF_PIN: "wrong_pin",
        CONF_SERVER: "https://fints.bank.de/fints",
    }

    with patch(
        "custom_components.fints.config_flow.FinTSClient.async_connect_and_test",
        AsyncMock(side_effect=ConfigEntryAuthFailed("Invalid PIN")),
    ):
        result = await flow.async_step_user(user_input)
        assert result["type"] == "form"
        assert result["errors"]["base"] == "invalid_auth"


async def test_config_flow_user_cannot_connect(mock_hass):
    """Test user step returns cannot_connect on server error."""
    flow = FinTSConfigFlow()
    flow.hass = mock_hass

    user_input = {
        CONF_BANK_CODE: "37050198",
        CONF_LOGIN: "testuser",
        CONF_PIN: "secret123",
        CONF_SERVER: "https://offline.bank.de/fints",
    }

    with patch(
        "custom_components.fints.config_flow.FinTSClient.async_connect_and_test",
        AsyncMock(side_effect=UpdateFailed("Timeout")),
    ):
        result = await flow.async_step_user(user_input)
        assert result["type"] == "form"
        assert result["errors"]["base"] == "cannot_connect"


async def test_config_flow_reauth(mock_hass, mock_config_entry):
    """Test reauth flow."""
    mock_hass.config_entries.async_get_entry.return_value = mock_config_entry

    flow = FinTSConfigFlow()
    flow.hass = mock_hass
    flow.context = {"entry_id": mock_config_entry.entry_id}

    result = await flow.async_step_reauth(mock_config_entry.data)
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.fints.config_flow.FinTSClient.async_connect_and_test",
        AsyncMock(return_value=[]),
    ):
        confirm_result = await flow.async_step_reauth_confirm({CONF_PIN: "new_secret"})
        assert confirm_result["type"] == "abort"
        assert confirm_result["reason"] == "reauth_successful"


async def test_options_flow(mock_config_entry):
    """Test options flow form and submission."""
    flow = FinTSOptionsFlowHandler(mock_config_entry)

    form_result = await flow.async_step_init(None)
    assert form_result["type"] == "form"
    assert form_result["step_id"] == "init"

    user_input = {
        CONF_SCAN_INTERVAL: 7200,
        CONF_TRANSACTION_DAYS: 60,
        CONF_PRODUCT_ID: "CUSTOM_PRODUCT_ID",
    }
    submit_result = await flow.async_step_init(user_input)
    assert submit_result["type"] == "create_entry"
    assert submit_result["data"][CONF_SCAN_INTERVAL] == 7200
    assert submit_result["data"][CONF_TRANSACTION_DAYS] == 60
