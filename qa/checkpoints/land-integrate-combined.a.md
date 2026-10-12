# Checkpoint: land-integrate-combined (cycle 0, dual coordinator A)
Attribution: claude-sonnet-subagent checker A; verdict qa/verdicts/land-integrate-combined.md.
Identity: HEAD 23e694a9, tree e7093149; blobs redact.py 368cd7ac, reconcile.py 55efeb89, test_reconcile_pii.py d1bbee28, test_redact_pii.py 0d985c00; uv.lock e9bfb886. Env: Windows 11, worktree .venv (cpython 3.11), host CPU ~70-90% from other sessions. No UI/deploy/data snapshot.

| Check | Scope | Result |
|---|---|---|
| diff scope 4c | git diff 3a16616c...HEAD, 13 files | clean |
| doctor + ruff | worktree | clean / All checks passed |
| falsify RC12 | tests/test_reconcile_pii.py (42) in copy | green -> 16 red |
| falsify RC11 | test_rc11_... in copy | green -> red |
| falsify C1 | test_unknown_field_is_rejected_loudly in copy | green -> red |
| falsify RC14/C2, C3 | doctor in copy | clean -> file-too-long / duplicate-concept |
| full suite | shard_suite 6 shards, collect proof 3035 | 3013 passed, 19 skipped, 3 failed (all fail on master 3a16616c too, or flake) |
| PII probes | mask_pii / mask_name_value / mask_pii_obj | idempotent, perf ok |
Result: PASS. Remaining: none.
