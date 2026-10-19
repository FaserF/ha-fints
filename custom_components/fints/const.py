"""Constants for the FinTS Banking integration."""

from __future__ import annotations

DOMAIN = "fints"

# Configuration keys
CONF_BANK_CODE = "bank_code"
CONF_BLZ = "blz"
CONF_LOGIN = "login"
CONF_PIN = "pin"
CONF_SERVER = "server"
CONF_CUSTOMER_ID = "customer_id"
CONF_PRODUCT_ID = "product_id"
CONF_TAN_MEDIUM = "tan_medium"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_PRODUCT_ID = "9FA6681DEC0E304684CCAC800"
DEFAULT_SCAN_INTERVAL = 14400  # 4 hours default
MIN_SCAN_INTERVAL = 1800  # 30 minutes minimum

# Entity attributes
ATTR_IBAN = "iban"
ATTR_BIC = "bic"
ATTR_ACCOUNT_NUMBER = "account_number"
ATTR_SUBACCOUNT = "subaccount"
ATTR_BANK_CODE = "bank_code"
ATTR_CURRENCY = "currency"
ATTR_BALANCE_DATE = "balance_date"
ATTR_CREDIT_LIMIT = "credit_limit"
ATTR_AVAILABLE_AMOUNT = "available_amount"
ATTR_TRANSACTIONS = "transactions"
ATTR_TRANSACTION_COUNT = "transaction_count"
ATTR_AMOUNT = "amount"
ATTR_DATE = "date"
ATTR_PURPOSE = "purpose"
ATTR_APPLICANT_NAME = "applicant_name"
ATTR_LAST_UPDATE = "last_update"
ATTR_ACCOUNTS = "accounts"
ATTR_TOTAL_BALANCE = "total_balance"
ATTR_STATUS = "status"

# Services
SERVICE_SYNC = "sync"
SERVICE_GET_TRANSACTIONS = "get_transactions"
