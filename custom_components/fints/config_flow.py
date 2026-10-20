"""Config flow and Options flow for FinTS Banking."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

from .client import FinTSClient
from .const import (
    CONF_BANK_CODE,
    CONF_BLZ,
    CONF_CUSTOMER_ID,
    CONF_LOGIN,
    CONF_PIN,
    CONF_PRODUCT_ID,
    CONF_SCAN_INTERVAL,
    CONF_SERVER,
    CONF_TAN_MEDIUM,
    CONF_TRANSACTION_DAYS,
    DEFAULT_PRODUCT_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRANSACTION_DAYS,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class FinTSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FinTS Banking."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            bank_code = str(user_input[CONF_BANK_CODE]).strip()
            login = str(user_input[CONF_LOGIN]).strip()
            pin = str(user_input[CONF_PIN]).strip()
            server = str(user_input[CONF_SERVER]).strip()
            customer_id = user_input.get(CONF_CUSTOMER_ID)
            if customer_id:
                customer_id = str(customer_id).strip()
            product_id = str(
                user_input.get(CONF_PRODUCT_ID) or DEFAULT_PRODUCT_ID
            ).strip()

            unique_id = f"{bank_code}_{login}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            client = FinTSClient(
                hass=self.hass,
                bank_code=bank_code,
                login=login,
                pin=pin,
                server=server,
                customer_id=customer_id,
                product_id=product_id,
            )

            try:
                await client.async_connect_and_test()
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except (UpdateFailed, HomeAssistantError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating FinTS credentials")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"FinTS {bank_code} ({login})",
                    data={
                        CONF_BANK_CODE: bank_code,
                        CONF_LOGIN: login,
                        CONF_PIN: pin,
                        CONF_SERVER: server,
                        CONF_CUSTOMER_ID: customer_id,
                        CONF_PRODUCT_ID: product_id,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_BANK_CODE): str,
                vol.Required(CONF_LOGIN): str,
                vol.Required(CONF_PIN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_SERVER): str,
                vol.Optional(CONF_CUSTOMER_ID): str,
                vol.Optional(CONF_PRODUCT_ID, default=DEFAULT_PRODUCT_ID): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Import legacy configuration from YAML (including official HA fints schema)."""
        bank_code = str(
            import_data.get("bank_identification_number")
            or import_data.get(CONF_BANK_CODE)
            or import_data.get(CONF_BLZ)
            or ""
        ).strip()
        login = str(
            import_data.get("username") or import_data.get(CONF_LOGIN) or ""
        ).strip()
        pin = str(import_data.get(CONF_PIN) or "").strip()
        server = str(
            import_data.get("url") or import_data.get(CONF_SERVER) or ""
        ).strip()
        customer_id = import_data.get(CONF_CUSTOMER_ID)
        if customer_id:
            customer_id = str(customer_id).strip()
        else:
            customer_id = ""
        product_id = str(import_data.get(CONF_PRODUCT_ID) or DEFAULT_PRODUCT_ID).strip()

        if not bank_code or not login or not pin or not server:
            _LOGGER.error(
                "Cannot import FinTS from YAML: missing required connection parameter(s)"
            )
            return self.async_abort(reason="missing_parameters")

        unique_id = f"{bank_code}_{login}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        account_names: dict[str, str] = {}
        for acc in import_data.get("accounts", []):
            if isinstance(acc, dict) and "account" in acc:
                acc_key = str(acc["account"]).replace(" ", "").upper()
                acc_name = acc.get("name")
                if acc_name:
                    account_names[acc_key] = str(acc_name)

        entry_data: dict[str, Any] = {
            CONF_BANK_CODE: bank_code,
            CONF_LOGIN: login,
            CONF_PIN: pin,
            CONF_SERVER: server,
            CONF_CUSTOMER_ID: customer_id,
            CONF_PRODUCT_ID: product_id,
            "account_names": account_names,
        }

        client = FinTSClient(
            hass=self.hass,
            bank_code=bank_code,
            login=login,
            pin=pin,
            server=server,
            customer_id=customer_id,
            product_id=product_id,
        )

        try:
            await client.async_connect_and_test()
        except ConfigEntryAuthFailed:
            _LOGGER.error(
                "FinTS YAML import failed: Invalid PIN / authentication rejected by bank %s for user %s",
                bank_code,
                login,
            )
            return self.async_abort(reason="invalid_auth")
        except Exception as err:
            _LOGGER.warning(
                "FinTS YAML import could not verify connection immediately (%s); proceeding with entry creation so coordinator can manage authentication",
                err,
            )

        return self.async_create_entry(
            title=f"FinTS {bank_code} ({login})",
            data=entry_data,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthentication upon expired or invalid credentials."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm reauthentication with updated PIN."""
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None

        if user_input is not None:
            new_pin = str(user_input[CONF_PIN]).strip()
            data = dict(self._reauth_entry.data)
            data[CONF_PIN] = new_pin

            client = FinTSClient(
                hass=self.hass,
                bank_code=data[CONF_BANK_CODE],
                login=data[CONF_LOGIN],
                pin=new_pin,
                server=data[CONF_SERVER],
                customer_id=data.get(CONF_CUSTOMER_ID),
                product_id=data.get(CONF_PRODUCT_ID, DEFAULT_PRODUCT_ID),
            )

            try:
                await client.async_connect_and_test()
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except (UpdateFailed, HomeAssistantError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during FinTS reauthentication")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry, data=data
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        schema = vol.Schema(
            {
                vol.Required(CONF_PIN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                CONF_LOGIN: self._reauth_entry.data.get(CONF_LOGIN, ""),
                CONF_BANK_CODE: self._reauth_entry.data.get(CONF_BANK_CODE, ""),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> FinTSOptionsFlowHandler:
        """Get the options flow for this handler."""
        return FinTSOptionsFlowHandler(config_entry)


class FinTSOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for FinTS Banking."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the FinTS options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_product_id = self.config_entry.options.get(
            CONF_PRODUCT_ID,
            self.config_entry.data.get(CONF_PRODUCT_ID, DEFAULT_PRODUCT_ID),
        )
        current_tan_medium = self.config_entry.options.get(
            CONF_TAN_MEDIUM,
            self.config_entry.data.get(CONF_TAN_MEDIUM, ""),
        )

        current_days = self.config_entry.options.get(
            CONF_TRANSACTION_DAYS,
            self.config_entry.data.get(CONF_TRANSACTION_DAYS, DEFAULT_TRANSACTION_DAYS),
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=max(current_interval, MIN_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                vol.Optional(
                    CONF_TRANSACTION_DAYS,
                    default=max(current_days, 1),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
                vol.Optional(
                    CONF_PRODUCT_ID,
                    default=current_product_id,
                ): str,
                vol.Optional(
                    CONF_TAN_MEDIUM,
                    default=current_tan_medium,
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
