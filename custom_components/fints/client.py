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

from .const import DEFAULT_PRODUCT_ID, DEFAULT_TRANSACTION_DAYS

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
        transaction_days: int = DEFAULT_TRANSACTION_DAYS,
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
        self.transaction_days = max(transaction_days, 1)

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
        """Fetch all accounts, balances, holdings, and transactions synchronously."""
        client = self._create_raw_client()
        sepa_accounts = client.get_sepa_accounts()

        # Retrieve comprehensive bank and account info from BPD/UPD
        bank_info: dict[str, Any] = {}
        account_metadata_map: dict[str, dict[str, Any]] = {}
        auth_info: dict[str, Any] = {}

        try:
            info = client.get_information()
            bank_info = info.get("bank", {})
            auth_info = info.get("auth", {})
            for acc_meta in info.get("accounts", []):
                key = acc_meta.get("iban") or acc_meta.get("account_number")
                if key:
                    account_metadata_map[key] = acc_meta
        except Exception as err:
            _LOGGER.debug("Could not retrieve extended get_information(): %s", err)

        bank_name = (
            bank_info.get("name")
            or (info.get("bank_name") if isinstance(info, dict) else None)
            or (
                client.bpa.bank_name
                if hasattr(client, "bpa")
                and hasattr(client.bpa, "bank_name")
                and isinstance(client.bpa.bank_name, str)
                else None
            )
            or f"Bank {self.bank_code}"
        )

        accounts_data: dict[str, dict[str, Any]] = {}
        holdings_accounts_data: dict[str, dict[str, Any]] = {}
        total_balance = 0.0
        total_holdings = 0.0
        primary_currency = "EUR"

        today = date.today()
        tx_start = today - timedelta(days=self.transaction_days)

        for acc in sepa_accounts:
            iban = acc.iban or ""
            account_number = acc.accountnumber or ""
            bic = acc.bic or ""
            subaccount = getattr(acc, "subaccount", "") or ""
            blz = getattr(acc, "blz", self.bank_code)

            # Metadata from get_information()
            meta = (
                account_metadata_map.get(iban)
                or account_metadata_map.get(account_number)
                or {}
            )
            acc_type = meta.get("type")
            product_name = meta.get("product_name") or "Bank Account"
            owner_names = meta.get("owner_name") or []
            owner_name = (
                ", ".join(owner_names)
                if isinstance(owner_names, list)
                else str(owner_names)
            )

            is_holding = False
            supported_ops = meta.get("supported_operations", {})
            has_get_holdings = any(getattr(op, "name", str(op)) == "GET_HOLDINGS" and supp for op, supp in supported_ops.items())
            if (isinstance(acc_type, int) and 30 <= acc_type <= 39) or has_get_holdings or "depot" in product_name.lower():
                is_holding = True

            # If it's a holdings / investment portfolio account
            if is_holding:
                depot_holdings: list[dict[str, Any]] = []
                depot_value = 0.0
                depot_currency = "EUR"

                try:
                    raw_holdings = client.get_holdings(acc)
                    if isinstance(raw_holdings, list):
                        for h in raw_holdings:
                            isin = getattr(h, "ISIN", "") or ""
                            h_name = getattr(h, "name", "") or "Securities"
                            pieces = float(getattr(h, "pieces", 0.0) or 0.0)
                            m_val = float(getattr(h, "market_value", 0.0) or 0.0)
                            t_val = float(
                                getattr(h, "total_value", 0.0) or (pieces * m_val)
                            )
                            curr = getattr(h, "value_symbol", "EUR") or "EUR"
                            val_date = str(getattr(h, "valuation_date", "") or today)

                            acq_price = getattr(h, "acquisitionprice", None)
                            acq_float = (
                                float(acq_price) if acq_price is not None else None
                            )
                            profit_loss = None
                            profit_loss_pct = None
                            if acq_float and acq_float > 0 and pieces > 0:
                                cost_basis = pieces * acq_float
                                profit_loss = round(t_val - cost_basis, 2)
                                profit_loss_pct = round(
                                    ((t_val / cost_basis) - 1.0) * 100, 2
                                )

                            depot_holdings.append(
                                {
                                    "isin": isin,
                                    "name": h_name,
                                    "pieces": pieces,
                                    "market_value": m_val,
                                    "total_value": t_val,
                                    "currency": curr,
                                    "valuation_date": val_date,
                                    "acquisition_price": acq_float,
                                    "profit_loss": profit_loss,
                                    "profit_loss_percent": profit_loss_pct,
                                }
                            )
                            depot_value += t_val
                            depot_currency = curr
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to fetch holdings for depot %s: %s",
                        iban or account_number,
                        err,
                    )

                key = iban or account_number
                holdings_accounts_data[key] = {
                    "account_number": account_number,
                    "iban": iban,
                    "bic": bic,
                    "blz": blz,
                    "type": acc_type or "holdings",
                    "product_name": product_name or "Depot",
                    "owner_name": owner_name,
                    "total_value": round(depot_value, 2),
                    "currency": depot_currency,
                    "holdings": depot_holdings,
                    "holdings_count": len(depot_holdings),
                }
                total_holdings += depot_value
                continue

            # Otherwise, balance account (checking, savings, credit)
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

            # 3. Scheduled debits / standing orders if supported
            debits_list: list[dict[str, Any]] = []
            try:
                raw_debits = client.get_scheduled_debits(acc)
                if isinstance(raw_debits, list):
                    for d in raw_debits:
                        debits_list.append(
                            {
                                "description": str(d),
                            }
                        )
            except (FinTSUnsupportedOperation, Exception):
                pass

            account_key = iban or account_number
            accounts_data[account_key] = {
                "iban": iban,
                "bic": bic,
                "account_number": account_number,
                "subaccount": subaccount,
                "blz": blz,
                "type": acc_type or "balance",
                "product_name": product_name,
                "owner_name": owner_name,
                "balance": balance_amount,
                "currency": currency,
                "balance_date": balance_date,
                "status": balance_status,
                "credit_limit": 0.0,
                "available": balance_amount,
                "transactions": tx_list,
                "last_transaction": last_tx,
                "scheduled_debits": debits_list,
                "scheduled_debits_count": len(debits_list),
            }

            total_balance += balance_amount
            primary_currency = currency

        current_tan = auth_info.get("current_tan_mechanism")
        current_tan_str = (
            getattr(current_tan, "name", None)
            or getattr(current_tan, "description", None)
            or str(current_tan)
            if current_tan
            else "Standard PIN/TAN"
        )

        tan_mechanisms = auth_info.get("tan_mechanisms") or {}
        tan_mechanisms_list = (
            [
                f"{sec_func}: {getattr(mech, 'name', mech)}"
                for sec_func, mech in tan_mechanisms.items()
            ]
            if isinstance(tan_mechanisms, dict)
            else []
        )

        return {
            "bank_code": self.bank_code,
            "bank_name": bank_name,
            "accounts": accounts_data,
            "holdings_accounts": holdings_accounts_data,
            "total_balance": round(total_balance, 2),
            "total_holdings": round(total_holdings, 2),
            "net_worth": round(total_balance + total_holdings, 2),
            "currency": primary_currency,
            "auth": {
                "current_tan_mechanism": current_tan_str,
                "tan_mechanisms": tan_mechanisms_list,
            },
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
                "bank_name": f"Bank {self.bank_code}",
                "accounts": {},
                "holdings_accounts": {},
                "total_balance": 0.0,
                "total_holdings": 0.0,
                "net_worth": 0.0,
                "currency": "EUR",
                "auth": {
                    "current_tan_mechanism": "SCA Challenge Pending",
                    "tan_mechanisms": [],
                },
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
            if acc.iban == iban or acc.accountnumber == iban:
                target_account = acc
                break

        if target_account is None:
            raise HomeAssistantError(f"Account with IBAN/Number {iban} not found.")

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

    def _sync_get_holdings(self, account_identifier: str) -> list[dict[str, Any]]:
        """Retrieve depot securities holdings synchronously."""
        client = self._create_raw_client()
        accounts = client.get_sepa_accounts()
        target_account = None
        for acc in accounts:
            if (
                acc.iban == account_identifier
                or acc.accountnumber == account_identifier
            ):
                target_account = acc
                break

        if target_account is None:
            raise HomeAssistantError(
                f"Depot / Holdings account '{account_identifier}' not found."
            )

        raw_holdings = client.get_holdings(target_account)
        results = []
        if isinstance(raw_holdings, list):
            for h in raw_holdings:
                isin = getattr(h, "ISIN", "") or ""
                name = getattr(h, "name", "") or "Securities"
                pieces = float(getattr(h, "pieces", 0.0) or 0.0)
                m_val = float(getattr(h, "market_value", 0.0) or 0.0)
                t_val = float(getattr(h, "total_value", 0.0) or (pieces * m_val))
                curr = getattr(h, "value_symbol", "EUR") or "EUR"
                val_date = str(getattr(h, "valuation_date", "") or date.today())
                acq_price = getattr(h, "acquisitionprice", None)
                acq_float = float(acq_price) if acq_price is not None else None

                results.append(
                    {
                        "isin": isin,
                        "name": name,
                        "pieces": pieces,
                        "market_value": m_val,
                        "total_value": t_val,
                        "currency": curr,
                        "valuation_date": val_date,
                        "acquisition_price": acq_float,
                    }
                )
        return results

    async def async_get_holdings(self, account_identifier: str) -> list[dict[str, Any]]:
        """Retrieve depot securities holdings asynchronously."""
        try:
            return await self.hass.async_add_executor_job(
                self._sync_get_holdings, account_identifier
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to fetch holdings for %s: %s", account_identifier, err
            )
            raise HomeAssistantError(f"Failed to fetch holdings: {err}") from err
