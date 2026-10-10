# GATE ANSWERED - email sender and credentials for report delivery

**Opened:** 2026-10-07 (`plan-approved-g10.md`, still-open item 1). **Decider:** Umesh. **Status:** ANSWERED.
**Blocks:** only `delivery/email.py` (G4 / T-201).

Question: which sender and credentials does the email adapter use? Options: (A) reuse the AWS SES SMTP values from d:/erp; (B) a new sender.

Answer (D-081 item 5): take the credentials from d:/erp. The AWS SES SMTP values and sender identity used by d:/erp are copied into the gitignored repo-root `.env` under AutoTester-prefixed keys, never printed, never committed, and declared as SecretRef keys. This file holds key names only, never values.

Answered: 2026-10-10 - A (credentials from d:/erp, AutoTester-prefixed keys) - D-081
