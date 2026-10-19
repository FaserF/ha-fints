#!/usr/bin/env python3
"""FinTS Connection Test Tool.

Validates connectivity and credentials against a live FinTS/HBCI banking server.
"""

from __future__ import annotations

import argparse
import getpass
import sys

try:
    from fints.client import FinTS3PinTanClient
    from fints.exceptions import (
        FinTSClientPINError,
        FinTSClientTemporaryAuthError,
        FinTSConnectionError,
        FinTSError,
        FinTSSCARequiredError,
    )
except ImportError:
    print(
        "Error: 'fints' library not installed. Install requirements with: pip install fints mt-940"
    )
    sys.exit(1)

DEFAULT_PRODUCT_ID = "9FA6681DEC0E304684CCAC800"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test FinTS/HBCI connection and credentials."
    )
    parser.add_argument(
        "--blz",
        required=True,
        help="Bankleitzahl (BLZ) / Bank Identifier (e.g. 12030000 for DKB, 43060967 for GLS)",
    )
    parser.add_argument(
        "--login",
        required=True,
        help="Login / Username / Legitimations-ID",
    )
    parser.add_argument(
        "--pin",
        help="Online banking PIN / Password (interactive prompt if omitted)",
    )
    parser.add_argument(
        "--server",
        required=True,
        help="FinTS Server URL (e.g. https://banking-dkb.s-fints-pt-dkb.de/fints30)",
    )
    parser.add_argument(
        "--customer-id",
        help="Optional Customer ID (defaults to login)",
    )
    parser.add_argument(
        "--product-id",
        default=DEFAULT_PRODUCT_ID,
        help=f"FinTS product ID (default: {DEFAULT_PRODUCT_ID})",
    )

    args = parser.parse_args()

    pin = args.pin
    if not pin:
        pin = getpass.getpass(f"Enter PIN for {args.login} @ BLZ {args.blz}: ")

    print(f"\nConnecting to {args.server} for BLZ {args.blz}...")

    client = FinTS3PinTanClient(
        bank_identifier=args.blz,
        user_id=args.login,
        pin=pin,
        server=args.server,
        customer_id=args.customer_id or args.login,
        product_id=args.product_id,
    )

    try:
        accounts = client.get_sepa_accounts()
        print(f"Successfully connected! Found {len(accounts)} SEPA account(s):")
        for idx, acc in enumerate(accounts, 1):
            masked_iban = (
                acc.iban[:4] + " **** " + acc.iban[-4:]
                if acc.iban and len(acc.iban) >= 8
                else "****"
            )
            print(f"  [{idx}] IBAN: {masked_iban} | BIC: {acc.bic} | BLZ: {acc.blz}")

            try:
                bal = client.get_balance(acc)
                if bal and hasattr(bal, "amount"):
                    amt = (
                        bal.amount.amount
                        if hasattr(bal.amount, "amount")
                        else bal.amount
                    )
                    curr = getattr(bal.amount, "currency", "EUR")
                    print(f"       Balance: {amt} {curr}")
            except Exception as b_err:
                print(f"       Balance could not be fetched: {b_err}")

    except (FinTSClientPINError, FinTSClientTemporaryAuthError) as err:
        print(f"[AUTH ERROR] Invalid credentials or PIN: {err}")
        sys.exit(2)
    except FinTSSCARequiredError as err:
        print(f"[SCA REQUIRED] Two-step TAN authentication required: {err}")
        sys.exit(3)
    except FinTSConnectionError as err:
        print(f"[CONNECTION ERROR] Failed to connect to server: {err}")
        sys.exit(4)
    except FinTSError as err:
        print(f"[FINTS ERROR] {err}")
        sys.exit(5)
    except Exception as err:
        print(f"[UNEXPECTED ERROR] {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
