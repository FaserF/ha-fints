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
CONF_TRANSACTION_DAYS = "transaction_days"
CONF_INCLUDE_HOLDINGS = "include_holdings"

# Defaults
DEFAULT_PRODUCT_ID = "9FA6681DEC0E304684CCAC800"
DEFAULT_SCAN_INTERVAL = 14400  # 4 hours default
MIN_SCAN_INTERVAL = 1800  # 30 minutes minimum
DEFAULT_TRANSACTION_DAYS = 30  # 30 days of transactions

# Entity attributes
ATTR_ACCOUNT = "account"
ATTR_ACCOUNT_TYPE = "account_type"
ATTR_BANK = "bank"
ATTR_BANK_NAME = "bank_name"
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
ATTR_TOTAL_HOLDINGS = "total_holdings"
ATTR_NET_WORTH = "net_worth"
ATTR_HOLDINGS = "holdings"
ATTR_HOLDINGS_COUNT = "holdings_count"
ATTR_ISIN = "isin"
ATTR_PIECES = "pieces"
ATTR_MARKET_VALUE = "market_value"
ATTR_ACQUISITION_PRICE = "acquisition_price"
ATTR_PROFIT_LOSS = "profit_loss"
ATTR_PROFIT_LOSS_PCT = "profit_loss_percent"
ATTR_VALUATION_DATE = "valuation_date"
ATTR_OWNER_NAME = "owner_name"
ATTR_PRODUCT_NAME = "product_name"
ATTR_ACTIVE_TAN_MECHANISM = "active_tan_mechanism"
ATTR_AVAILABLE_TAN_MECHANISMS = "available_tan_mechanisms"
ATTR_SCHEDULED_DEBITS = "scheduled_debits"
ATTR_SCHEDULED_DEBITS_COUNT = "scheduled_debits_count"
ATTR_STATUS = "status"

# Services
SERVICE_SYNC = "sync"
SERVICE_GET_TRANSACTIONS = "get_transactions"
SERVICE_GET_HOLDINGS = "get_holdings"
