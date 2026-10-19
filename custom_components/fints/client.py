"""FinTS Client Wrapper for Home Assistant."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from fints.client import FinTS3PinTanClient  # type: ignore[attr-defined]
from fints.exceptions import (
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSConnectionError,
    FinTSError,
    FinTSSCARequiredError,
    FinTSUnsupportedOperation,
)

from .const import DEFAULT_PRODUCT_ID

_LOGGER = logging.getLogger(__name__)


class FinTSClient:
    """Async wrapper for the synchronous python-fints library."""

    def __init__(
        self,
        hass: HomeAssistant,
        bank_code: str,
        login: str,
        pin: str,
        server: str,
        customer_id: str | None = None,
        product_id: str = DEFAULT_PRODUCT_ID,
        tan_medium: str | None = None,
    ) -> None:
        """Initialize the FinTS client wrapper."""
        self.hass = hass
        self.bank_code = bank_code
        self.login = login
        self.pin = pin
        self.server = server
        self.customer_id = customer_id or login
        self.product_id = product_id or DEFAULT_PRODUCT_ID
        self.tan_medium = tan_medium

    def _create_raw_client(self) -> FinTS3PinTanClient:
        """Instantiate raw synchronous FinTS3PinTanClient."""
        return FinTS3PinTanClient(
            bank_identifier=self.bank_code,
            user_id=self.login,
            pin=self.pin,
            server=self.server,
            customer_id=self.customer_id,
            product_id=self.product_id,
            tan_medium=self.tan_medium,
        )

    def _sync_connect_and_test(self) -> list[Any]:
        """Test connection and credentials synchronously."""
        client = self._create_raw_client()
        return client.get_sepa_accounts()

    async def async_connect_and_test(self) -> list[Any]:
        """Test connection and verify bank credentials asynchronously."""
        try:
            return await self.hass.async_add_executor_job(self._sync_connect_and_test)
        except (FinTSClientPINError, FinTSClientTemporaryAuthError) as err:
            _LOGGER.error("FinTS authentication failed: %s", err)
            raise ConfigEntryAuthFailed(f"Invalid bank credentials: {err}") from err
        except FinTSSCARequiredError as err:
            _LOGGER.warning("FinTS SCA / TAN required: %s", err)
            raise HomeAssistantError(
                f"Two-factor TAN authentication required by bank: {err}"
            ) from err
        except FinTSConnectionError as err:
            _LOGGER.error("FinTS connection error: %s", err)
            raise UpdateFailed(f"Cannot connect to FinTS server: {err}") from err
        except FinTSError as err:
            _LOGGER.error("FinTS error during setup verification: %s", err)
            raise UpdateFailed(f"FinTS error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error during FinTS verification: %s", err)
            raise HomeAssistantError(f"Unexpected FinTS error: {err}") from err

    def _sync_fetch_all_data(self) -> dict[str, Any]:
        """Fetch accounts, balances, and recent transactions synchronously."""
        client = self._create_raw_client()
        accounts = client.get_sepa_accounts()

        accounts_data: dict[str, dict[str, Any]] = {}
        total_balance = 0.0
        primary_currency = "EUR"
        today = date.today()
        tx_start = today - timedelta(days=30)

        for acc in accounts:
            iban = acc.iban
            account_number = acc.accountnumber
            bic = acc.bic
            subaccount = getattr(acc, "subaccount", "") or ""
            blz = getattr(acc, "blz", self.bank_code)

            balance_amount = 0.0
            currency = "EUR"
            balance_date = str(today)
            balance_status = "ok"

            # 1. Fetch balance
            try:
                bal_obj = client.get_balance(acc)
                if bal_obj is not None:
                    if hasattr(bal_obj, "amount"):
                        amt = bal_obj.amount
                        if hasattr(amt, "amount"):
                            balance_amount = float(amt.amount)
                            currency = getattr(amt, "currency", "EUR") or "EUR"
                        else:
                            balance_amount = float(amt)
                    if hasattr(bal_obj, "date") and bal_obj.date:
                        balance_date = str(bal_obj.date)
                    if hasattr(bal_obj, "status") and bal_obj.status:
                        balance_status = str(bal_obj.status)
            except Exception as err:
                _LOGGER.warning("Failed to fetch balance for account %s: %s", iban, err)
                balance_status = f"error: {err}"

            # 2. Fetch recent transactions
            tx_list: list[dict[str, Any]] = []
            try:
                raw_txs = client.get_transactions(
                    acc, start_date=tx_start, end_date=today
                )
                if isinstance(raw_txs, list):
                    for tx in raw_txs:
                        data = getattr(tx, "data", {}) if hasattr(tx, "data") else {}
                        tx_amt = 0.0
                        tx_curr = currency
                        amt_obj = data.get("amount")
                        if amt_obj is not None:
                            if hasattr(amt_obj, "amount"):
                                tx_amt = float(amt_obj.amount)
                                tx_curr = (
                                    getattr(amt_obj, "currency", currency) or currency
                                )
                            elif isinstance(amt_obj, (int, float)):
                                tx_amt = float(amt_obj)

                        tx_date = str(data.get("date") or data.get("entry_date") or "")
                        tx_purpose = str(
                            data.get("purpose")
                            or data.get("remittance_information")
                            or ""
                        )
                        tx_applicant = str(
                            data.get("applicant_name") or data.get("name") or ""
                        )

                        tx_list.append(
                            {
                                "amount": tx_amt,
                                "currency": tx_curr,
                                "date": tx_date,
                                "purpose": tx_purpose,
                                "applicant_name": tx_applicant,
                            }
                        )
            except (FinTSUnsupportedOperation, Exception) as err:
                _LOGGER.debug(
                    "Transactions not available or failed for account %s: %s",
                    iban,
                    err,
                )

            # Sort transactions descending by date
            tx_list.sort(key=lambda t: t.get("date", ""), reverse=True)
            last_tx = tx_list[0] if tx_list else None

            accounts_data[iban] = {
                "iban": iban,
                "bic": bic,
                "account_number": account_number,
                "subaccount": subaccount,
                "blz": blz,
                "balance": balance_amount,
                "currency": currency,
                "balance_date": balance_date,
                "status": balance_status,
                "credit_limit": 0.0,
                "available": balance_amount,
                "transactions": tx_list,
                "last_transaction": last_tx,
            }

            total_balance += balance_amount
            primary_currency = currency

        return {
            "bank_code": self.bank_code,
            "accounts": accounts_data,
            "total_balance": round(total_balance, 2),
            "currency": primary_currency,
            "tan_required": False,
            "last_update_success": True,
        }

    async def async_fetch_all_data(self) -> dict[str, Any]:
        """Fetch all banking data asynchronously."""
        try:
            return await self.hass.async_add_executor_job(self._sync_fetch_all_data)
        except (FinTSClientPINError, FinTSClientTemporaryAuthError) as err:
            _LOGGER.error("FinTS authentication failed: %s", err)
            raise ConfigEntryAuthFailed(f"Invalid bank credentials: {err}") from err
        except FinTSSCARequiredError as err:
            _LOGGER.warning("FinTS SCA / 2FA TAN required: %s", err)
            return {
                "bank_code": self.bank_code,
                "accounts": {},
                "total_balance": 0.0,
                "currency": "EUR",
                "tan_required": True,
                "last_update_success": False,
            }
        except FinTSConnectionError as err:
            _LOGGER.error("FinTS connection error: %s", err)
            raise UpdateFailed(f"FinTS server connection error: {err}") from err
        except FinTSError as err:
            _LOGGER.error("FinTS library error: %s", err)
            raise UpdateFailed(f"FinTS library error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching FinTS data: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _sync_get_transactions(
        self,
        iban: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve transactions for a specific account synchronously."""
        client = self._create_raw_client()
        accounts = client.get_sepa_accounts()
        target_account = None
        for acc in accounts:
            if acc.iban == iban:
                target_account = acc
                break

        if target_account is None:
            raise HomeAssistantError(f"Account with IBAN {iban} not found.")

        raw_txs = client.get_transactions(
            target_account,
            start_date=start_date,
            end_date=end_date,
        )
        results = []
        if isinstance(raw_txs, list):
            for tx in raw_txs:
                data = getattr(tx, "data", {}) if hasattr(tx, "data") else {}
                amt_val = 0.0
                curr = "EUR"
                amt_obj = data.get("amount")
                if amt_obj is not None:
                    if hasattr(amt_obj, "amount"):
                        amt_val = float(amt_obj.amount)
                        curr = getattr(amt_obj, "currency", "EUR") or "EUR"
                    elif isinstance(amt_obj, (int, float)):
                        amt_val = float(amt_obj)

                results.append(
                    {
                        "iban": iban,
                        "amount": amt_val,
                        "currency": curr,
                        "date": str(data.get("date") or data.get("entry_date") or ""),
                        "purpose": str(
                            data.get("purpose")
                            or data.get("remittance_information")
                            or ""
                        ),
                        "applicant_name": str(
                            data.get("applicant_name") or data.get("name") or ""
                        ),
                    }
                )
        return results

    async def async_get_transactions(
        self,
        iban: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve transactions for a specific account asynchronously."""
        try:
            return await self.hass.async_add_executor_job(
                self._sync_get_transactions, iban, start_date, end_date
            )
        except Exception as err:
            _LOGGER.error("Failed to fetch transactions for %s: %s", iban, err)
            raise HomeAssistantError(f"Failed to fetch transactions: {err}") from err
