# Verdict (checker B) - mongo-store-u12f

**Cycle checked:** 1
**Verdict:** PASS (with warnings, none blocking)
**Unit:** mongo-store U12f, fix cycle 1, branch `feat/mongo-store-u12f`, implementation head `dee5bb71` (cycle 0 head `609e2349`; the cycle 0 B verdict `4ade61de` is in git history).
**Contract:** `qa/contracts/mongo-store.md` M38, M39, M40, M34, M8; scope: the three cycle-0 warnings (NaN/inf defeats the age cap; `forget_session` outside the restore `try`; skew boundary and non-dict state untested, and a lagging reader deleting a valid document).
**Method:** fresh independent narrow re-check. Every claim below was re-run by me. I did not read any other checker's verdict on this unit. No `.env` value printed. Another checker was running pytest and a mutation harness in the same worktree at the same time (I saw `profiles.py` mutated by a process that was not mine), so all my mutation runs and one test run were done in a throwaway detached worktree of `dee5bb71` (`uv sync`, removed afterwards). `src/` and `tests/` in the unit worktree were never edited by me (a temporary probe test was written and deleted).

## Commands run and results

| Command | Result |
|---|---|
| `env -u ANTHROPIC_BASE_URL uv run pytest tests/test_session_store_u12f.py tests/test_session_store_u12.py -o addopts= -q` | 39 passed |
| same, `tests/test_session_store_u12_redaction.py tests/test_manual_login.py` | 11 passed |
| same, `tests/test_multi_role_session.py tests/test_role_session_port_login.py` | 13 passed |
| same, `tests/test_role_session_port.py tests/test_credential_store_u11f.py` | 44 passed |
| same, `tests/test_entry_browser_reuse_lent.py tests/test_ui_project_edit.py` | 22 passed |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor > .work/doctor-u12f-b1.txt` | exit 0, last line `doctor: clean` |
| `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u12f/mutations.json --repo .` (the maker's) | 25/25 mutations killed |
| `scripts/mutation_check.py .work/mut-b1-spec.json` (my 13 mutants, scratch worktree) | 9/13 killed; my B13 was malformed and was re-written (try/except around the forget) and then killed; survivors B9, B10, B12 (finding 2 and item 2) |
| B10 by hand: remove `restore_credentials(held)` from the `except`, run `test_credential_store_u11f.py` + `test_ui_project_edit.py` | `test_a_failed_project_save_on_undeclare_puts_the_stored_value_back` FAILED: killed by the U11f suite, not by the U12f file |
| File sizes | `profiles.py` 272, `routes_project_edit.py` 278, `test_session_store_u12f.py` 287; all <= 300; doctor enforces function <= 50 |

## Per-item judgement

1. **Non-finite times (PASS).** `profiles.py:151-153` `_readable` rejects any `expires_at` / `saved_at` that is not an int/float, is a bool, or fails `math.isfinite`; `load_session:171-173` deletes such a document. My probe: `saved_at` -inf, None, True and "x" all return `None` and the document is deleted; `saved_at` NaN is also rejected and deleted. The one exception is `saved_at` = +inf (and absurdly large values), which `_ahead` handles first (finding 1). Other paths: `grep -rn "saved_at\|expires_at\|browser_sessions" src` shows no reader outside `profiles.py`; `scope_state` and `session_values` never read a time, so `repo_redactor` / `stored_session_values` cannot be fooled by one. A cookie-level `expires` of NaN is not a session time: `_expired` keeps it (`0 < nan` is False) but `save_session` leaves it out of `live` (`> 0` is False), so `expires_at` stays capped at `saved_at + MAX_AGE_S` (probe: saved and loaded, bounded by the 24 h cap; finding 5). Mutants: B1 (inf passes), B2 (finite check on expires only), B3 (on saved only) all killed by the parametrised NaN/inf test; B8 (cap not re-applied) killed.
2. **`undeclare_secret` order (PASS).** `routes_project_edit.py:266-275`: forget loop, then `snapshot_credentials`, `drop_credentials`, then `try: save_project / except: restore_credentials; raise`. I injected an outage (fake server down) at each store call, through a wrapper on the route module's names, then read the state back with the server up:

   | Failure injected | Response | Declaration | Credential `T1_P` | Sessions left |
   |---|---|---|---|---|
   | `forget_session` | 503 | kept | kept | `pl\|t1`, `pl\|t2` (all untouched) |
   | `snapshot_credentials` | 503 | kept | kept | `pl\|t2` (t1 forgotten) |
   | `drop_credentials` | 503 | kept | kept | `pl\|t2` |
   | `save_project` raises OSError | raised | kept | restored | `pl\|t2` |
   | `save_project` raises AND `restore_credentials` hits an outage | 503 | kept | **gone** | `pl\|t2` |

   No orphaned credential and no declared key without its credential in the first four rows. The manifest claim ("a forget failure raises with the credential, the declaration and the other sessions untouched; a drop or save failure after it restores the credential; sessions already forgotten stay forgotten") matches what I observed. The fifth row is a double fault (the restore itself fails), unrecoverable without the store and unchanged from the U11f design (finding 3). Mutants: B11 (forget after the save, outside the `try`) killed; B13 (forget failure swallowed) killed; B10 (restore removed) killed by the U11f test, not by the U12f file; B12 (forget between snapshot and drop) survives and is equivalent (an outage there happens before the drop, so nothing has changed either way); B9 (password key only) survives, finding 2.
3. **Skew and non-dict state (PASS).** `profiles.py:139-144` `_ahead`, called at `:168` before `_readable`: +300 s loads, +301 s returns `None` and keeps the document (`test_the_skew_boundary_is_exactly_five_minutes`; B5 `>=`, B4 `_ahead` off and B6 ahead-deletes all killed). A non-dict `state` (str, list, int, None) returns `None` and the document is deleted (`:154`, `:171-173`; B7 killed, all four cases fail under it). `_ahead` is not a way to keep a malformed or expired document alive in any practical sense: it applies only when `saved_at` is a real, non-bool number more than 300 s ahead of the reader, which a genuine save never produces, and such a document is never loadable. It can only keep a tampered document (finding 1).
4. **No regression of the cycle-0 checks (PASS).** One client across saves (`test_session_saves_reuse_one_client_and_the_gate_still_rebuilds`), the two call-site tests, save only after proof (`test_a_failed_login_never_replaces_a_good_stored_session`, `test_a_proven_login_is_saved`), malformed state deleted and the forget wiring all pass; the maker's 25 mutants, which still include the cycle-0 ones, are all killed.

## Findings (numbered)

1. **INFO / LOW - a tampered `saved_at` far ahead of the reader is kept.** `profiles.py:139-144,168`. Probe: `saved_at` = +inf with a malformed `state`, or with `expires_at` NaN, returns `None` and the document is still there after a load at `now` and again at `now + 1e19`. `saved_at` = 1e18 is deleted only when a reader's clock passes it. Such a document never loads, so no login is replayed; it is cleared by the next `save_session` for that account (replace by `_id`), by `forget_session`, or by a project delete (`delete_many {"p": slug}`), and its cookie values still feed the redactor (the safe direction). Exploiting it needs a write to `browser_sessions`, the same capability that could plant any document. Not a defect of the stated fix; bounding it (delete when ahead by more than `MAX_AGE_S`) would close it if wanted.
2. **WARNING (test gap, low) - undeclaring a role account's USERNAME key is untested.** `routes_project_edit.py:268`. My mutant B9 (`key in (acct.password_key,)`) survives the whole U12f file: the only undeclare test uses `T1_P`, the password key. The cycle-0 mutant "username-only" is killed, but its mirror image is not. Add the same test for `T1_U`.
3. **INFO - double fault leaves a declared key with no credential.** Save fails and then the restore hits an outage: the route answers 503, the declaration stays and the stored value is gone (table row 5). Unchanged from U11f; the manifest does not claim to cover it. The claim "no declared key without its credential" holds for any single failure.
4. **INFO - my survivors.** B10 is killed by `test_credential_store_u11f.py`, so the restore-on-failed-save path is guarded elsewhere; B12 is equivalent; B9 is finding 2. My first B13 was malformed (`__enter__` does not suppress) and was replaced by a proper try/except, which was killed.
5. **INFO - a cookie `expires` of NaN is kept on a session** (`_expired`, `profiles.py:104`); bounded by the 24 h cap and not producible by Playwright's own `storage_state`. Not a session time; no action.
6. **INFO - W5 and W6 remain open** as the manifest states; live Chromium with the store on is still untested.

## Result

All three cycle-0 warnings are fixed and guarded: finite times (item 1), forget-before-drop with no orphan under a failure at any single store call (item 2), and the 300 s boundary and non-dict state pinned and behaving as claimed (item 3). My independent mutants for each fix are killed (10 in the U12f file, B10 in the U11f suite), except the equivalent B12 and the one real gap, the username-key test (finding 2, warning only). Verdict: **PASS, cycle 1.**
