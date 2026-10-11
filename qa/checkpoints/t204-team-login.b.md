# Checkpoint t204-team-login (seat B) - cycle 0, resume 1 of 2
head=aa6fec2e product=5e0c4b0b base=9c9a91f3 policy=proportional-verification/2026-10-10.9
Verdict: FAIL (qa/verdicts/t204-team-login.b.md). Blocking: F1 credential_guard slug-prefix (own/repro.py), F2 AU27 refused-attempt audit (own/repro_audit.py).

Evidence identities (all on aa6fec2e, Windows, worktree venv):
- 10 auth test files + tests/test_ui_origin_guard.py, per-criterion -k sets, one process: 249 passed (verify sub-checker, evidence verify/results.jsonl)
- tests/test_permission_coverage.py test_credential_run_approval.py test_env_loading.py: 46 passed
- AU25 five UI files: 55 passed, 1 skipped
- falsification: 38 mutant rows in copies, 34 killed, 4 survived beyond the floor (AU3 lifetime, AU5 limit literal, AU11 grant table, AU18 repeated-Origin in the host file)
- attack scripts + raw json: qa/evidence/t204-team-login-B/{unauth,session,verify,diff,own}/
- ruff clean, doctor clean, uv lock --check Resolved 89 packages
Not run by seat B: full suite, browser (seat A), AU24, AU26.
