# GATE ANSWERED - Google identity for Drive links

**Opened:** 2026-10-07 (`plan-approved-g10.md`, still-open item 2). **Decider:** Umesh. **Status:** ANSWERED.
**Blocks:** only the live Drive fetch in T-198 (`ingest fetch-drive`, `sources/drive.py`).

Question: which Google account does the system use to fetch Drive links? Options: (A) the existing gws CLI login (the one the /doc-polisher skill uses); (B) a new service account.

Answer (D-081 item 6): the existing gws CLI login. The live Drive fetch shells out to gws; no token is copied into this repo.

Answered: 2026-10-10 - A (existing gws CLI login) - D-081
