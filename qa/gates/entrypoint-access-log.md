# Gate: entrypoint access log (master commit 5976c832)
Opened: 2026-10-21T17:58:01+05:30
Question: KarthickCogniv's master commit 5976c832 removed `--no-access-log` from docker/entrypoint.sh. That breaks contract AU22 (qa/contracts/auth.md:230) and 2 pinned tests, and makes uvicorn log query strings and /v/<token> paths (6c verdict qa/verdicts/6c-1021c.md). int/1019 (AT-1363, AT-1368) cannot reach master without either keeping or undoing that line.
Options:
- A (recommended): revert the line on int/1019 and push; tell Karthick why (AU22, token leak in logs).
- B: keep the access log, add a log filter that scrubs query strings and /v/<token> (new unit, then amend AU22 + tests under a DECISIONS entry).
- C: accept the log as is; amend AU22 and the 2 tests under a DECISIONS entry.
Answer format: "A", "B" or "C".
Blocks: push of int/1019 (AT-1363 re-OCR masking, AT-1368 .env round-trip) to master.
