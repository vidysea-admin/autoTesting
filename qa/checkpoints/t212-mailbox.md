# Checkpoint - t212-mailbox (cycle 0, checker Mode A)
- 5 test files via worktree .venv `uv run pytest` (test_imap_mailbox, test_oracle_mailbox, test_oracle_registry, test_cross_role_runner, test_cross_role_schema), code 3b64dd3a, test blobs test_imap_mailbox 3b4132f / test_oracle_mailbox e7f52f6 (per manifest), py3.11 -> 93 passed.
- `uv run ruff check src tests scripts` -> clean.
- `git diff --name-status cff3ffe6..3b64dd3a` -> 6 additions; multi_role_enums.py absent (MPI3).
- falsification in git-archive copies outside the repo, each named node green first: MP16 readonly True->False red; BODY.PEEK->BODY red; MP17 token mask off red [numeric code]; cap removed red.
- probe: number-first OTP and all-lowercase cued password not flagged (AT-1301, low).
- Result: PASS.
