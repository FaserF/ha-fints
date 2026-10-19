# Security Policy for FinTS Banking Integration

Because this integration interacts directly with financial institutions via the FinTS / HBCI protocol, security and privacy are top priorities.

---

## 🔒 Security Architecture

1. **Direct TLS Endpoints (No Cloud Intermediaries)**
   - All network traffic connects directly from your local Home Assistant instance to the bank's official HTTPS FinTS server.
   - No external proxy, third-party server, or commercial data aggregator (such as Tink, Plaid, or Klarna) is involved.

2. **Encrypted Credential Storage**
   - Online banking PINs and login IDs are stored using Home Assistant's internal encrypted configuration entry storage.
   - Credentials are never exposed in Home Assistant frontend states, event buses, or entity attributes.

3. **Automatic Data Redaction**
   - All diagnostic exports automatically scrub passwords, PINs, usernames, customer IDs, and tokens.
   - All account IBANs are masked (`DE89 **** **** **** **12 34`), retaining only the country code, bank checksum, and last 4 digits for identification.

4. **PSD2 SCA Compliance**
   - The integration fully respects Strong Customer Authentication (SCA) challenges. If the bank requires an interactive two-factor TAN (PushTAN, photoTAN, ChipTAN), the integration halts automated polling and turns on `binary_sensor.tan_challenge_required`.

---

## 🛡️ Recommended User Practices

- **Dedicated Banking Sub-User**: Many banks (e.g. Sparkasse, Volksbank) allow creating secondary online banking users with read-only view permissions. We strongly recommend using a read-only banking profile if your bank supports it.
- **Reasonable Polling Intervals**: Do not poll your bank faster than every 30 minutes (default is 4 hours). High-frequency polling can trigger the bank's automated fraud detection filters and lock your online access.
- **Log Sanitation**: When opening a public issue on GitHub, always ensure you do not inadvertently paste personal financial numbers or passwords.

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability in this integration:

1. **Do NOT open a public issue.**
2. Report the vulnerability privately via [GitHub Security Advisories](https://github.com/FaserF/ha-fints/security/advisories/new) or email `github@fabiseitz.de`.
3. Provide a detailed summary of the vulnerability, reproduction steps, and impact.
4. We aim to acknowledge reports within 48 hours and release fixes promptly.
