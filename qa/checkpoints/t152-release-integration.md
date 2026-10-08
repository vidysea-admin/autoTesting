# T152 merged release integration checkpoint

Checker: `/root/t152_release_integration`; root `D:/autoTesting/.worktrees/codex-t152-release`; branch `codex/t152-release`. Policy-Version: proportional-verification/2026-10-07.7. Cycle 0.

Checked code head: `cc4743e6435e6c0f811dbb1d17bbf99866fb34b1`, origin base `167f7576`; only T152 source commit `4375739b` is cherry-picked. T153 source/tests are absent. No live browser/deployment or external target is claimed.

## Original acceptance attribution and applicable reuse

Original independent checker `/root/check_t152`, cycle 0 PASS at `D:/autoTesting/.worktrees/codex-t152-check/qa/verdicts/t152-ai-check-registry.md`; original checkpoint at the matching `qa/checkpoints/t152-ai-check-registry.md`. Exact copies are now retained at those same repository-relative paths in this release root. Copy SHA256: verdict `c660726f473946f2660cc0932a417a02eb644e639ab3f9f0fef27adbd7fa4a2e`; checkpoint `be6c5515282a964b8afb9fd5d5ae769e8e3b0690959045183d1ddeead06e7a58e`.

The original whole `ai_check.py` hash does NOT match the release: the original checkout included unjudged T153 reply/exchange/capture types and imports. The `AiCheckKind` and `AiCheckMethod` ASTs match exactly. `git diff 97103cf3 HEAD --` over catalog.py, ai_catalog.py, test_ai_catalog.py, tests/conftest.py, test_catalog.py, test_catalog_packs.py, test_ui_catalog.py, test_schema.py, pyproject.toml, uv.lock, ai_target.py, base.py, enums.py, discover.py, catalog.py, regression_proof.py and tests_mutation_fixtures.py is empty. Applicable original falsification inputs/config/fixtures/runtime are therefore unchanged; seven original independent falsifications are reused with their original attribution, not described as new mutations.

Explicit release SHA256 values match the original checkpoint:

- catalog.py `49e4bc5172fa9f508c052c9cc60dee084918c56d7d23957b205e9685c6be6904`
- ai_catalog.py `7478a9eedd548b9d20d1347c1f32163d7313e33fc904cee016198a69053f4785`
- test_ai_catalog.py `5f611e1848e1dfae0d1525d2f393aa7d35d5b9707460f35b63a7832cef141a15`
- tests/conftest.py `9bbb6a4bc2be7eb9adfb1b6adfdfcc8da4708287349ecb108a0c66c99ff4652a`
- pyproject.toml `4b56e19c01e8bcc00450b51a32360ce8466bd3090bb9f548f20a8a7e05f2b0f0`
- uv.lock `0f25d574ae096863a23b6f6e1b03e3d797e1bdec10341c5316a848aea937f41d`

Native runtime probe: Python 3.11.15, Windows-10-10.0.26300-SP0, pydantic 2.13.5, pytest 9.1.1; ai_catalog/catalog import paths point to this release checkout's `src`. No dependency installation. API-only registry: no UI change, no service/data snapshot applies.

## Own scoped verification

Environment: `PYTHONPATH=D:/autoTesting/.worktrees/codex-t152-release/src`; TEMP/TMP own `.work/temp`; native execution approved for synthetic TestClient/temp operations.

`D:/autoTesting/.venv/Scripts/python.exe -m pytest tests/test_ai_catalog.py tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py tests/test_schema.py tests/test_ui_runs_serial_entry_order.py -m 'not harness' --basetemp D:/autoTesting/.worktrees/codex-t152-release/.work/temp/affected-native -o faulthandler_timeout=30`

Exit 0: `114 passed, 1 warning in 9.78s`. Additional 21 run-dispatch importer checks complement the original 93. Starlette BlockingPortal deprecation warning only. Sandbox attempt had TEMP setup errors and socketpair stall, was interrupted and excluded from product evidence.

`D:/autoTesting/.venv/Scripts/python.exe -m ruff check src tests scripts` -> exit 0, `All checks passed!`.

`D:/autoTesting/.venv/Scripts/python.exe -c 'from autotester.cli import main; main()' doctor` -> exit 0, `doctor: clean`. The original verdict's T125 ledger gap is resolved on the current origin base.

`node C:/Users/Lenovo/.agents/skills/maker/tools/tick.mjs --policy-check` -> `proportional-verification/2026-10-07.7 targets=2 drift=0 mode=--policy-check`.

## Full integration run: completed (initial RED)

Owned wrapper `.work/t152-integration-run.py` invokes `D:/ai_os/.claude/skills/checker/tools/shard_suite.py` SHA256 `59fc0cca9dfe6f504eefa3ca8d8b151416ed4dce6a122d402dacfdc044b5e2fa`. Read full runner/suite_lock before execution. Native machine lock `C:/Users/Lenovo/AppData/Local/aios/suite.lock`; RAM measurement approximately 4.9 GB free, so resource bound two shards, no pins. No real .env/venv/runtime copied. `PYTHONPATH=src` resolves per archive-copy cwd. `core.autocrlf=false` is set before Git init/read-tree. Batched `git cat-file --batch` proves all 1,988 archived files exactly match Git blobs; scratch Git diff is empty. Identity JSON is `.work/t152-integration-suite/archive-identity.json`.

Exact runner arguments: `--repo D:/autoTesting/.worktrees/codex-t152-release --ref cc4743e6 --python D:/autoTesting/.venv/Scripts/python.exe --shards 2 --out .work/t152-integration-suite --durations .work/t152-integration-suite/durations.json --keep --shard-timeout 3600 --lock-timeout 900 -- -o addopts=`. No `-m` filter, fail-fast or harness exclusion. The addopts override removes the repo's extra `-q`; the runner itself supplies one `-q`, preserving node IDs and summaries.

Preparations: first own runner (PID 43924) interrupted before collection due slow per-file proof; subsequent preparation/collection exited runner 2 with pytest collect 0 because duplicate `-q` printed file counts rather than node IDs. Neither attempt ran test shards or counts as a full-suite result. Both excluded from product failures. Current invocation began 2026-10-08 13:58:14 IST, collection completed 13:59:08: 2,835 tests, 231 files; shard PIDs 19792 and 39940, 1,418/1,417 tests. Session ID 91370. Full-suite completion/proof remains mandatory; no PASS, task close, release commit or push yet. Kill only these owned PIDs if needed, never peers.

Metrics: start=2026-10-08T08:28:14Z end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=0 mutations=0 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7

14:03 IST progress: runner PID 10880 holds the real machine lock; owned shard PIDs 19792/39940. Shard 0 has reported one `F` around 45% and shard 1 progressed around 35%; full run continues with no fail-fast. Failure attribution and isolated rerun are mandatory before any PASS or push.

Landplane applicability: read full landplane/pack-up skill. This is a subtask of root's enclosing session; root explicitly owns the final coordinated append-only session decision and has a separate unpushed D080 foundation entry. No competing DECISIONS entry is appended in this release root. T152 uses existing D017 authorization and changes no ARCHITECTURE prose, contract or enforcement path. Root-coordinated session logging/handoff remains separate; release closeout, if green, is confined to T152 QA, goal, normal updated ledger and generated docs.

Completion 14:33:51 IST: session91370 exit1, counts2813 passed/19 skipped/3 failed. All2835 nodes ran exactly once, full collect proof true, no duplicates/missing/unexpected. Overall2137.4s; extract31.4, collect22.1, run2076.4, rerun6.9s; lock blocked0. Shard0 rc1 wall1664.2s (3failed1412passed3skipped); shard1 rc0 wall2075.4s. Native owned runner/shard PIDs10880/19792/39940/29080/25504 exited. Actual machine lock subsequently belongs to unrelated HEI PID44320 and is preserved, not removed. No owned service was started outside the suite's fixtures.

Exact failures and isolated repeats: RC2 ingest narration None at test_reconcile_schema.py:125 (still failed); healthy hook missing ticks:1 at test_mc_sessionstart_loop_status.py:164 with exit0 (passed alone); goal dashboard facts at test_goal_contract_registration.py:90 (still failed). These are not T152 source files. Native unchanged-origin167 probe session17113, UV_OFFLINE1, exact3nodes, returned pytest1/3failed54.90s with the same named assertions. Eighteen applicable inputs match exact base/release blobs and archive bytes; baseline.json/log persist identities/command/results. Hook raw follow-up session59952 passed1/8.56s, rawhook exit0 ticks:1/loop-status:no gaps/stderr empty; raw output saved hook-subprocess.json. Cold/warm/load inference is not an established root cause.

Correction to preparation safety scope: no real env/runtime was copied into archive inputs, but the existing native hook harness subsequently created scratch shard0/.venv via uv. No claim of no dependency installation/network across the full run; baseline probe explicitly offline. No approved provider/model/live target call or deployment was performed by this checker.

At14:38:30 IST source/test/config diff empty and public master readback remains167f75761cb47f4839ca9d998b3da9d21ac536e5. Scoped PASS integration verdict now records full RED honestly and failure ownership. .7 unit-ownership rule applied, not a blanket waiver. Normal closeout verification still required. Protocol hashes remain maker11E05EC50948AFF374EB95925C98EFF7344E819501C285B6538C77B9C9A6CFB0 and checker4C153467FC9F826601F67A8DD66E233402AA9F26B4FC65AEBFFD2FA96F5ACC90.

Normal closeout complete locally: goal_cli.py done --root ownrelease --task-id T-152 returnedok/73percent. Only T152 task differs from UTF-8-decoded origin Git blob (git cat-file blob), all91others identical; local92total67done25pending. Dashboard generated with render_dashboard.write_dashboard(current goal), not a stale copy. Ledger exact CLI appended F075 updated ai-check-registry --value normal --unit T-152 --verdict qa/verdicts/t152-release-integration.md, automatic reason:update. map regenerated with no diff; snapshot regenerated. Post-closeout native session36058: pytest tests/test_goal_contract_registration.py tests/test_goal_done_checks.py --basetemp own.work/temp/closeout -o addopts= ->8passed0.29s; doctor:clean; ruff:All checks passed. Source/test/config/DECISIONS diff empty. Public still167beforecommit; narrowcommit/push not yet claimed. No additional full suite or broad fix.
