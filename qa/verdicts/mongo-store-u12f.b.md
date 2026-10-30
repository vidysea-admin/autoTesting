# Verdict (checker B) - mongo-store-u12f

**Cycle checked:** 0
**Verdict:** PASS (with warnings, none blocking)
**Unit:** mongo-store U12f, branch `feat/mongo-store-u12f`, implementation head `609e2349`, cut from master `54db88c6`.
**Contract:** `qa/contracts/mongo-store.md` M38, M39, M40, M34, M8 and the U12 row, plus the U12 dual-PASS warnings (A-W1, B-W1, W2, W3, W4). W5 and W6 stay open by design and are not judged here.
**Method:** fresh independent check; every claim below re-run by me. I did not read any other checker's verdict. No `.env` value printed. `src/` and `tests/` were only mutated by the mutation harness, which restores them; a temporary probe test was deleted; `git status` was clean of changes afterwards.

## Commands run and results

| Command | Result |
|---|---|
| `env -u ANTHROPIC_BASE_URL uv run pytest tests/test_session_store_u12f.py tests/test_session_store_u12.py -o addopts= -q` | 28 passed |
| same, `tests/test_session_store_u12_redaction.py tests/test_manual_login.py` | 11 passed |
| same, `tests/test_multi_role_session.py tests/test_role_session_port_login.py` | 13 passed |
| same, `tests/test_role_session_port.py tests/test_credential_store_u11f.py` | 44 passed |
| same, `tests/test_entry_browser_reuse_lent.py tests/test_ui_project_edit.py` | 22 passed |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor > .work/doctor-u12f-b.txt` | exit 0, `doctor: clean` |
| `scripts/mutation_check.py qa/evidence/mongo-store-u12f/mutations.json --repo .` (maker's 18) | 18/18 killed |
| `scripts/mutation_check.py <my own spec, 21 mutants>` | 19/21 killed; 2 survivors judged equivalent (finding 7) |
| File sizes | profiles.py 263, multi_role_session.py 211, role_session_port.py 233, routes_project_edit.py 276, test_session_store_u12f.py 229; all <= 300; doctor enforces function <= 50 |

## Per-item judgement

1. **A-W1 rearm, one client (PASS).** `profiles.py:72-77` `_put_session` calls `default_backend().rearm()`; `mongo_backend.py:246` sets `_redactor = None`, rebuilt lazily at `:63`. Test `test_session_saves_reuse_one_client_and_the_gate_still_rebuilds` counts client factory calls (1 across three saves) and then proves a put carrying the newly saved value is refused. My mutants: rearm removed (A1) killed; rearm replaced by `reset_default_backend()` (A2) killed. Both halves are live.
2. **B-W1 call-site tests (PASS).** My mutants against `stages/manual_login.py:48`: capture deleted (B1) killed, wrong account `t1` (B2) killed. Against `ui/run_execution.py:178`: restore deleted (B4) killed, wrong account `t1` (B5) killed, nonexistent account (B6) killed. The run test seeds both `_project` and `t1` sessions, so the wrong-account kill is real. B3 (an extra early capture before the human prompt) survived, but my mutant left the later capture in place, so it is equivalent in outcome, not a test hole.
3. **W2 save only after proof (PASS).** `role_session_port.py:113-114` saves only `if proven`, inside the same `try`, so a store outage during the save still fails closed as `RoleLoginFailed`. `multi_role_session.py:206` `save_login` captures on the account's own thread. The only caller of `RoleSessions.sign_in` in `src/` is `role_session_port.py:108` (grep), so no proven login lost its save. Mutants killed: save regardless of proof (W2a), never save (W2b), wrong role (W2c), `save_login` a no-op (W2d). The edit to `test_session_store_u12_redaction.py` only adds an assertion (`docs(rig) == []` after `sign_in`) and then calls `save_login`; it strengthens the test and keeps its name.
4. **W3 malformed state, age cap, redactor (PASS, with findings 1 and 2).** `_readable` (`profiles.py:138-150`) rejects non-numeric times, bool, non-dict state, non-list parts, and re-applies `min(expires, saved + MAX_AGE_S)`. `load_session:164-166` deletes such a document and returns `None`. `session_values` goes through `_dicts` (`:84`, `:194-196`), and the mutant that removes the guard (W3e) is killed. Mutants killed: skew rule off (W3a), skew widened (W3b), cap dropped (W3c). Survivor W3d (bool accepted) is equivalent in effect: `True` is 1, and `min(1, ...) <= now` fails the age test anyway. The 300 s skew rule is acceptable today (finding 2).
5. **W4 undeclare forgets sessions (PASS, with finding 3).** `routes_project_edit.py:268-270` calls `forget_session` for each role account whose `username_key` or `password_key` equals the key, beside `drop_credentials`. Mutants killed: forget removed (W4a), username-only (W4b), also forgetting `_project` (W4c), wrong account (W4d). Judgement: restoring the credential but not the session after a failed project save is benign (the account is only logged out and re-logs in). Leaving the `_project` login alone is correct, since it is not tied to one key. Neither is a defect.

## Findings (numbered)

1. **WARNING - NaN/inf defeats the age cap on load.** `profiles.py:143,147`. A stored document with `saved_at` NaN and `expires_at` inf (or both NaN) passes `_readable`: `min(inf, nan)` is inf and `nan <= at` is False. My probe: both forms were still loaded 10 years later. The maker's tamper test (`test_a_tampered_far_future_expiry_is_not_trusted_on_load`) covers only finite numbers. Exploiting it needs a write to `browser_sessions`, so it is defense in depth only, but the stated purpose of the re-applied cap is to resist tampering. Fix: reject non-finite values with `math.isfinite` in `_readable`.
2. **WARNING (low) - skew rule deletes a valid document when the reader clock is behind.** `profiles.py:145,164-165`. Probe: a session saved by a clock 400 s ahead is deleted by a reader at the true time (loaded False, document gone). With `--max-instances 1` (M28) this cannot happen today. If CAS and more instances come, a lagging instance would destroy another instance's fresh login, forcing a re-login. Safer: return `None` without deleting for the future-dated case (or widen `SKEW_S`). The 300 s boundary itself has no test on either side.
3. **WARNING - `forget_session` sits outside the restore `try`, so a mid-sequence outage orphans the credential.** `routes_project_edit.py:266-275`. The manifest says "a store outage still raises before anything changed". That holds only for an outage at `snapshot_credentials`/`drop_credentials`. Probe: with `forget_session` raising after `drop_credentials` succeeded, the route raised, `drop` ran, `restore_credentials` never ran, and the declaration stayed: the credential value was deleted while the key remained declared. This is the exact state the U11f order was built to prevent (M37). Fix: move the `forget_session` loop inside the `try` so `restore_credentials(held)` runs, or run it after the project save. The window is narrow (two consecutive store calls), hence a warning.
4. **INFO - no test for the `saved_at` skew boundary or for the forget-then-save-fail path.** Findings 2 and 3 describe the behaviour a test would pin.
5. **INFO - W5 (a restore may overwrite fresher cookies) and W6 (the `orchestrate_execute` path does not restore) remain open**, as the manifest states. Live Chromium with the store on is still untested.
6. **INFO - `LiveRolePort.login` marks the role failed if `save_login` raises**, even though the browser is signed in. This matches the previous fail-closed behaviour on an outage and is acceptable.
7. **INFO - survivors in my own spec:** B3 and W3d, both equivalent as explained above; no test gap.

## Result

All five claimed fixes work and are guarded by tests that kill both the maker's mutants and my 21 independent ones (19 killed, 2 equivalent survivors). The three warnings are real but none breaks M38-M40, M34 or M8 as shipped; they are listed for the next unit or a small fix-up. Verdict: **PASS, cycle 0.**
