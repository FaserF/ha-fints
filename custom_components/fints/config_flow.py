"""Config flow for FinTS Banking."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_BANK_CODE, CONF_LOGIN, CONF_PIN, CONF_SERVER

class FinTSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=f"FinTS {user_input[CONF_BANK_CODE]}", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_BANK_CODE): str,
            vol.Required(CONF_LOGIN): str,
            vol.Required(CONF_PIN): str,
            vol.Required(CONF_SERVER): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FinTSOptionsFlowHandler(config_entry)

class FinTSOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("scan_interval", default=3600): int
            })
        )
