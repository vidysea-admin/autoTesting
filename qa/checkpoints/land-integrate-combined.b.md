# Checkpoint (coordinator B) — land-integrate-combined

Checker: claude-sonnet-subagent coordinator B · verdict qa/verdicts/land-integrate-combined.b.md · result PASS at 23e694a9 (tree e7093149)
Environment: Windows 11, worktree venv python 3.11 with PYTHONPATH to a `git archive 23e694a9` copy; host CPU load 100%, free RAM about 7 GB.
Code hashes (blob, 10 chars): core/redact.py 368cd7ac38 · stages/reconcile.py 55efeb89e2 · tests/test_reconcile_pii.py d1bbee281b · tests/test_redact_pii.py 0d985c0023. Lock file: unchanged by this unit.

| Check | Command and scope | Result |
|---|---|---|
| scoped tests | pytest tests/test_redact_pii.py test_reconcile_pii.py test_reconcile.py test_redact_encoding_coverage.py test_redact_ignorable_perf.py test_redact_obfuscation.py test_redact_wrap_perf.py test_timing_scale.py test_schema.py -p no:xdist (359 collected) | 358 passed, 1 timing-bound load flake (test_redact_wrap_perf 500 KB, 3.57 s vs 3 s); that file alone: 18 passed |
| doctor + ruff | autotester doctor; ruff check src tests scripts (copy) | clean; All checks passed |
| scope | git diff --name-only master...wave/land-integrate-combined grep review/ui/grade/contracts | 0 |
| falsification RC12 x2, RC11a, RC14, C1, C2, C3 | each in its own copy, green before, red after | all red on the named check |
| mutant RC11b | drop screen output sort | survived (input sort covers it) |
| bypass probes | mask_pii shape table; end-to-end build_judge_prompt via reconcile_fakes | see verdict |
