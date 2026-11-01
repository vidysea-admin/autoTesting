# Verdict - e2e-fixes-e9 (checker, independent)

**Verdict:** PASS
**Status:** PASS (E9.1, E9.2, E9.3(a) met; E9.3(b) held via the contract's HUMAN_GATE option (ii), 2 non-blocking warnings W1-W2)
**Cycle checked:** 0
**Reviewed SHA:** 914ea655 (base master 6eb21a54), worktree `D:/autoTesting/.claude/worktrees/e2e-e9`.
**Scope:** `qa/contracts/e2e-fixes.md` E9.1-E9.3. I did not read any other checker's verdict on this unit.

## Commands re-run (`env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts=`)

| Command | Result |
|---|---|
| `tests/test_credential_store_u11.py tests/test_cli_advice_resolves.py` | 63 passed |
| `tests/test_schedule_tick.py tests/test_mongo_backend_layout.py -rxX` | 84 passed, 1 xfailed (the TS6 guard, reason E9.3(b)) |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor` (to file) | 2 violations only: `docs/SNAPSHOT.md` stale-generated and stale-committed (pre-existing drift; no size, duplicate or docstring finding) |
| `git diff 6eb21a54 -- tests/advice_scan.py tests/test_cli_advice_resolves.py` | empty (0 lines) |

## Findings per criterion

**E9.1 PASS.** `tests/test_credential_store_u11.py:70-74`: the assertion stays an equality, `== {"core/env.py", "ui/env_editor.py", "store/migrate_creds.py"}`, with an M46 comment. I grepped `credential_collection(` in `src/`: exactly those three files call it (`core/env.py:257,274`, `store/migrate_creds.py:78`, `ui/env_editor.py:119,235,...`), so the set equals reality. Other assertions of the test are untouched (diff is +4/-1 in that file, all in that one assert). Mutations (each reverted, `git status` clean): rename the call in `migrate_creds.py` (`credential_collectionX()`) -> `test_only_the_door_writes_secrets_and_no_crypto_exists` FAILED; add `# credential_collection(` to a fourth file (`store/mongo_routes.py`) -> same test FAILED. Not a subset check.

**E9.2 PASS.** `src/autotester/store/mongo_backend.py:73` edited in place: `f"{key!r} is {size} bytes; limit {int(MAX_DOC_BYTES)}"`. The message still carries key, size and limit; wording changed from "the limit is" to "limit" (`grep "the limit is" src tests` finds no pin on the old wording; `tests/test_mongo_backend_layout.py:62` matches `limit` and passes). `wc -l` = 300 (at the cap, not over; doctor reports no size finding). `MAX_DOC_BYTES` is bound by a tuple assignment at `:34`, which is why the collector could not fold the bare name; wrapping in `int()` is a call the collector reports as resolvable. Mutation: restore `the limit is {MAX_DOC_BYTES}` -> `test_the_collector_reports_what_it_could_not_resolve` FAILED with `(store/mongo_backend.py, 73)`; reverted. `tests/advice_scan.py` and `tests/test_cli_advice_resolves.py` unmodified.

**E9.3(a) PASS.** `tests/test_schedule_tick.py` `ALLOWED_OUTSIDE` gained exactly `autotester.auth.store_mongo`, `autotester.auth.store_mongo_tx`, `autotester.auth.store_mongo_video`, `autotester.auth.store_mongo_fence`, with a U6a-precedent comment; no `autotester.browser.*` entry anywhere in the diff. The modules are still walked: mutation appending `from autotester.browser.session import BrowserSession` to `auth/store_mongo_tx.py` -> the pin test FAILED listing `autotester.auth.store_mongo_tx -> autotester.browser.session` (and the transitive consequences, "17 more items"); reverted. The `LEAKS` self-tests (`:233`) pass unmodified (84 passed).

**E9.3(b) held, accepted under HUMAN_GATE option (ii).** The guard test carries `@pytest.mark.xfail(strict=True, reason="E9.3(b) HUMAN_GATE: repo_redactor -> browser.profiles edge")`; it XFAILed in my run. A companion `test_the_only_scheduler_side_violation_is_the_known_redactor_edge` asserts `scheduler_side_violations() == ["autotester.store.mongo_routes -> autotester.browser.profiles"]` (an equality). It passed on the clean tree and failed under the BrowserSession mutation above, so a NEW violation is not hidden by the xfail; and if the edge is removed, the strict xfail turns XPASS-fail and the pin fails too, forcing both to be cleaned up together. This is not a widened set and not a catch-all, which is what the contract forbids. I verified the manifest's reasons for not taking option (i): `browser/profiles.py:216` `stored_session_values` depends on `_collection` (`:62`) and `session_values` (`:199`), which `capture_session` also uses; `store/mongo_routes.py` is 292 lines and `mongo_backend.py` 300. `repo_redactor` still imports the function lazily at `store/mongo_routes.py:195`. The equivalence test is correctly not applicable (no `repo_redactor` change; `git diff --stat` shows neither `mongo_routes.py` nor `profiles.py` touched).

## Does the hold satisfy the contract's HUMAN_GATE path? Yes, with two caveats

The contract text for (ii): "files a HUMAN_GATE with the evidence, leaves the edge, and the guard test stays red under an `xfail(strict=True)` carrying the issue id, not a widened set." Met: evidence is in the manifest and in the comment above `KNOWN_BROWSER_EDGE`, the edge is left, the strict xfail is in place, `browser.profiles` is not allow-listed. Not yet met: "carrying the issue id". The E9 table says ids are assigned at filing, and the issues ledger (`qa/issues.jsonl`, no E9 row; `qa/issues.jsonl` and `qa/gates/` are unchanged by this branch) is the checker's to maintain, so the maker could not supply one. That is the owed follow-up, not a defect of the diff.

## Warnings (non-blocking)

- **W1 (owed, orchestrator/checker):** file the issue row and the HUMAN_GATE (with the manifest's two options: (a) a new `store/` module, e.g. `store/session_values.py`, holding the redaction half with `browser/profiles.py` importing it, or (b) accept the xfail), then amend the xfail `reason=` and the `KNOWN_BROWSER_EDGE` comment to cite the AT id. Until then the xfail cites only "E9.3(b) HUMAN_GATE".
- **W2:** the manifest says a new module "needs a D-entry (not allowed to me)". I could not confirm that from `CLAUDE.md` (it requires only a module docstring, the 300-line cap and no duplicates; D-entries gate `ARCHITECTURE.md` prose and enforcement paths). Option (i) may be cheaper than the manifest states; the human should weigh it on that basis when ruling on the gate, rather than on the "needs a D-entry" premise.

## Notes

- `autotester doctor` crashed once with `MemoryError` (machine low on memory) and passed on the retry as described above; not a code finding.
- A second TS6 mutation (a pipeline import in `store/mongo_routes.py`) hit an unrelated circular import at collection time, so it proved nothing; the BrowserSession mutation in `store_mongo_tx.py` is the evidence for "new violation still fails".
- Nothing was merged or pushed; src/tests are unmodified in my worktree (all mutations reverted, `git status` clean before this file).
