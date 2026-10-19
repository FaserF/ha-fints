<p align="center">
  <img src="https://raw.githubusercontent.com/FaserF/ha-fints/main/custom_components/fints/brand/logo.png" alt="FinTS Banking Logo" width="360">
</p>

# FinTS Banking (Enhanced) for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-fints.svg?style=flat-square)](https://github.com/FaserF/ha-fints/releases)
[![Downloads (Current release)](https://img.shields.io/github/downloads/FaserF/ha-fints/latest/fints.zip?label=Downloads%20(Current%20release)&style=flat-square)](https://github.com/FaserF/ha-fints/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-fints.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![CI Orchestrator](https://github.com/FaserF/ha-fints/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-fints/actions/workflows/ci-orchestrator.yml)

A secure, privacy-focused Home Assistant integration for German and Austrian online banking using the native **FinTS 3.0 / HBCI** standard. Connect directly to your bank without intermediaries or cloud aggregators.

---

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [🏦 Supported Banks](#-supported-banks) | [📦 Installation](#-installation) | [⚙️ Configuration](#️-configuration) |
| [🛡️ Security](SECURITY.md) | [📊 Entities](#-entities) | [🧱 Services](#-services) | [🤖 Automations](#-automation-examples) |
| [❓ Troubleshooting](#️-troubleshooting) | [🧑‍💻 Development](AGENTS.md) | [💖 Sponsors](.github/FUNDING.yml) | [📄 License](LICENSE) |

---

## ✨ Features

- **Direct Bank Connection**: Communicates directly via HTTPS FinTS/HBCI endpoints. No third-party data aggregators (Plaid, Tink, Klarna) and no recurring fees.
- **Multi-Account Support**: Automatically detects and creates sensors for all SEPA accounts associated with your login (checking, savings, money market).
- **Accurate Balances**: Real-time monetary sensors with currency support (`EUR`) and `total` state class for long-term statistics and Energy/Finance dashboards.
- **Aggregated Total Balance**: Automatically tracks the cumulative balance across all accounts at a financial institution.
- **Transaction Tracking**: Dedicated sensors for recent booking activity, transaction amounts, applicant names, and purpose strings.
- **Connectivity & TAN Status**: Binary sensors indicate gateway health and alert when PSD2 Two-Factor (SCA / TAN) challenges arise.
- **On-Demand Synchronization**: Button entity and `fints.sync` service to refresh data outside scheduled intervals.
- **Privacy Masking**: IBANs are masked (`DE89 **** **** **** **12 34`) and credentials (PIN, login) are scrubbed from diagnostics and logs.
- **Asynchronous Architecture**: Fully non-blocking execution using Home Assistant's executor pool to safeguard the event loop.

---

## 🏦 Supported Banks

The integration supports all financial institutions offering standard FinTS 3.0 PIN/TAN access, including:

| Institution | BLZ Example | FinTS Server URL |
|---|---|---|
| **Sparkasse** | *Varies by city* | `https://banking-*.s-fints-pt-*.de/fints30` |
| **Deutsche Bank** | `10070000` | `https://fints.deutsche-bank.de/fints` |
| **Commerzbank** | `10040000` | `https://fints1.commerzbank.de/fints` |
| **DKB (Deutsche Kreditbank)** | `12030000` | `https://banking-dkb.s-fints-pt-dkb.de/fints30` |
| **ING-DiBa** | `50010517` | `https://fints.ing-diba.de/fints/` |
| **Volksbanken / Raiffeisenbanken** | *Varies by city* | `https://fints1.atruvia.de/cgi-bin/hbciservlet` |
| **GLS Bank** | `43060967` | `https://fints1.atruvia.de/cgi-bin/hbciservlet` |
| **Postbank** | `10010010` | `https://fints.postbank.de/fints/` |

---

## 📦 Installation

### Via HACS (Recommended)

1. Open **HACS** in your Home Assistant dashboard.
2. Select **Integrations** > **Custom Repositories**.
3. Add `https://github.com/FaserF/ha-fints` with category **Integration**.
4. Click **Download**, then restart Home Assistant.

### Manual Installation

1. Download `fints.zip` from the [Latest Release](https://github.com/FaserF/ha-fints/releases).
2. Extract the archive into your `custom_components/fints` directory:
   ```text
   config/
   └── custom_components/
       └── fints/
           ├── __init__.py
           ├── manifest.json
           └── ...
   ```
3. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, navigate to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for **FinTS Banking (Enhanced)**.
3. Fill in your bank details:
   - **Bank Code (BLZ)**: 8-digit German bank code.
   - **Login / Username**: Online banking username or Legitimations-ID.
   - **PIN**: Online banking password / PIN.
   - **FinTS Server URL**: HTTPS URL for your bank's FinTS endpoint.
   - **Customer ID**: Optional (leave blank unless your bank requires a separate customer ID).
   - **Product ID**: Optional (defaults to registered open-source identifier).

### Options Flow

Select **Configure** on the integration card to adjust:
- **Update Interval**: Polling frequency in seconds (default: `14400` / 4 hours, minimum `1800` / 30 minutes). *Note: Banks enforce strict rate limits to prevent automated credential abuse.*
- **TAN Medium**: Mobile device name for multi-device push TAN setups.

---

## 📊 Entities

### Sensors

| Entity ID | Name | Description | Attributes |
|---|---|---|---|
| `sensor.total_bank_balance` | Total Bank Balance | Aggregated funds across all accounts | `account_count`, `bank_code`, `last_update` |
| `sensor.balance_<masked_iban>` | Balance `<masked_iban>` | Account balance | `iban`, `bic`, `account_number`, `status`, `transaction_count` |
| `sensor.last_transaction_<masked_iban>` | Last Transaction `<masked_iban>` | Value of last booking | `iban`, `date`, `purpose`, `applicant_name` |

### Binary Sensors

| Entity ID | Name | Device Class | Description |
|---|---|---|---|
| `binary_sensor.bank_connection` | Bank Connection | `connectivity` | `on` if FinTS connection is healthy. |
| `binary_sensor.tan_challenge_required` | TAN Challenge Required | `problem` | `on` when bank requires manual 2FA TAN confirmation. |

### Button

| Entity ID | Name | Description |
|---|---|---|
| `button.sync_bank_data` | Sync Bank Data | Triggers immediate synchronization with the bank. |

---

## 🧱 Services

### `fints.sync`

Triggers an immediate data refresh.

```yaml
action: fints.sync
data:
  entry_id: "01JABCDEF1234567" # Optional: omit to sync all accounts
```

### `fints.get_transactions`

Retrieves a structured list of bank transactions. Supports returning response data for automations and scripts.

```yaml
action: fints.get_transactions
data:
  iban: "DE89370501980000012345"
  start_date: "2026-01-01"
  end_date: "2026-01-31"
  limit: 20
response_variable: recent_bookings
```

---

## 🔒 Security & Privacy

- **Zero Cloud Intermediaries**: All TLS sessions terminate directly between your local Home Assistant instance and your financial institution.
- **Credentials Protection**: Passwords and PINs are encrypted using Home Assistant's secure storage and are never exposed in state attributes or frontend interfaces.
- **Masked Diagnostics**: Integration diagnostic dumps automatically redact PINs, passwords, logins, and middle IBAN segments.

---

## 🤖 Automation Examples

### Alert on Large Expense

```yaml
alias: "FinTS: Alert on Large Outgoing Transaction"
trigger:
  - platform: numeric_state
    entity_id: sensor.last_transaction_de89_1234
    below: -200
action:
  - action: notify.persistent_notification
    data:
      title: "Bank Alert: Large Expense"
      message: >
        An expense of {{ states('sensor.last_transaction_de89_1234') }} EUR was booked.
        Applicant: {{ state_attr('sensor.last_transaction_de89_1234', 'applicant_name') }}
        Purpose: {{ state_attr('sensor.last_transaction_de89_1234', 'purpose') }}
```

### Alert when Two-Step TAN Confirmation is Required

```yaml
alias: "FinTS: TAN Challenge Pending"
trigger:
  - platform: state
    entity_id: binary_sensor.tan_challenge_required
    to: "on"
action:
  - action: notify.mobile_app_phone
    data:
      title: "Bank Approval Needed"
      message: "Your bank has requested two-factor TAN approval. Please open your banking app to authenticate."
```

---

## 🛠️ Troubleshooting

- **Rate Limiting / Account Lockout**: FinTS queries should not be run too frequently (never below 30 minutes). Banks automatically lock online access if polled too often.
- **SCA / 90-Day PSD2 Reauthorization**: Under European PSD2 regulations, banks require strong customer authentication (TAN challenge) at least once every 90 days. When this occurs, `binary_sensor.tan_challenge_required` turns `on`.
- **Diagnostics**: Export diagnostic logs via **Settings** > **Devices** > **FinTS** > **Download Diagnostics**. All sensitive credentials are automatically redacted.