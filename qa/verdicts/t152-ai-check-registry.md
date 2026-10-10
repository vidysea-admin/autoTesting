# T-152 — independent checker verdict

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-07.7
VERDICT: PASS

## CHECK-PLAN

Original checker: `/root/check_t152`; isolated root `D:/autoTesting/.worktrees/codex-t152-check`. Tier M: multi-file behavior and shared schema. SERIAL: instruments run without extra checker agents; no per-unit full suite under .7. AI2: actual literal table/no-provider inspection, exact-kind acceptance tests, membership sabotage. AI3: classifier/adversarial-kind acceptance tests, lying-string-subclass sabotage. AI4/CT7: one-model definition check and existing web-row preservation, duplication/preservation sabotages. AI5: endpoint and ground-truth blockers plus schema refusal tests, three independent sabotages. C1/C2/C3: schema tests, lint, actual doctor. API-only registry has no changed UI flow; browser not applicable. Read applicable architecture/invariants, ai-target AI2-AI5, catalog CT7/CT8, D-017 and native checker protocol.

## SCOREBOARD

AI2–AI5: 4/4 evidenced. CT7 evidenced. Per-criterion falsification floor met by seven successful isolated mutations, each with asserted green baseline, applied single-hunk change, named assertion red, exact byte restoration and restored green. C1 and applicable C2/C3 source checks satisfied; doctor's one T125 bookkeeping condition is independently traced outside this unit. No concrete correctness contradiction found.

## CHECKED-STATE

HEAD `97103cf3e98e5fc774cfeddaea4bd7820f2c8c02`; T152 commit `4375739b`; base `3adc00d8`. T153 sibling is present and not judged by this verdict. T152 scope is ai_check.py enum portion, catalog.py, ai_catalog.py, test_ai_catalog.py and generated MAP. Native checker SHA256 `4C153467FC9F826601F67A8DD66E233402AA9F26B4FC65AEBFFD2FA96F5ACC90`; manifest maker pin `11E05EC50948AFF374EB95925C98EFF7344E819501C285B6538C77B9C9A6CFB0`.

Original execution fingerprint: Python 3.11.15, Windows 10.0.26300, pydantic 2.13.5, pytest 9.1.1. The actual import-path probe returned ai_catalog and catalog from this isolated root's src. Before persistence on 2026-10-08 07:40:11 UTC, HEAD remains identical, all seven previously captured source/test/config hashes match, and `git diff --exit-code -- src tests scripts pyproject.toml uv.lock` exits 0. Tracked fixtures/downstream tests are still the same committed identities; current additional downstream hashes are recorded in the checkpoint. Only QA feedback and maker-owned manifest were dirty. No acceptance rerun required by unchanged inputs.

## RESULTS

Environment: `PYTHONPATH=D:/autoTesting/.worktrees/codex-t152-check/src`; TEMP/TMP `D:/autoTesting/.worktrees/codex-t152-check/.work/temp`; cwd own checkout. Exact acceptance command:

`D:/autoTesting/.venv/Scripts/python.exe -m pytest tests/test_ai_catalog.py tests/test_catalog.py tests/test_catalog_packs.py tests/test_ui_catalog.py tests/test_schema.py -m 'not harness' --basetemp D:/autoTesting/.worktrees/codex-t152-check/.work/temp/affected-elevated -o faulthandler_timeout=30`

Exit 0: `93 passed, 1 warning in 0.96s`. Warning: Starlette BlockingPortal deprecation. No skips. Approved native execution resolved default sandbox TEMP denial and local TestClient stalling; interrupted sandbox runs are not product-failure or mutation evidence. No external targets, models, installs or browser calls.

`D:/autoTesting/.venv/Scripts/python.exe -m ruff check src tests scripts` -> `All checks passed!`; touched-path lint independently exits 0 with the same result.

`D:/autoTesting/.venv/Scripts/python.exe -c 'from autotester.cli import main; main()' doctor` -> exit 1, exactly `ledger-row-missing: T-125 — closed high-value task has no live/updated row`, `1 violation(s)`. Base proof: `git show 3adc00d8:.goal/goal.json` has T125 status done/user_value high; `git show 3adc00d8:docs/FEATURES.jsonl` searched for T125 has no rows; neither file is in the T152 diff. This condition is pre-existing and not attributed to T152. An initial module-mode CLI invocation was a no-op and was not counted as a doctor pass; standalone actual CLI execution supplied the exit above.

Seven named mutant results are persisted in this verdict's checkpoint and the checker-authored T152 section of `qa/feedback-inbox.md`. All mutated copies excluded __pycache__; baseline exit 0, exact anchor count 1/changed bytes, mutant exit 1 plus intended FAILED node, no collection error, original-byte restoration and restored exit 0 were asserted. One failed multiline anchor was rejected before application and not counted.

FAILURES: none attributable to T152.
Persistence runtime recheck: the original Python/OS/pydantic/pytest fingerprint matches; post-write product/config/test diff remains empty. Exact command is recorded in the checkpoint.
REMAINING: none for this scoped unit check. Maker owns closeout and merged pre-push integration; this verdict makes no task-close, commit, push or deployment claim.
LIVE-BROWSER: not applicable; no changed UI surface.
ISSUES-WRITTEN: none; no obligation to invent issues.

Metrics: start=unavailable end=2026-10-08T07:02:17Z wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=7 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7

Measured interval: first own clock 06:56:02 UTC to evidence-completion clock 07:02:17 UTC = 6.25 minutes; initial reads preceded that first sample. Dispatch timestamp and exact active/blocked split were not recorded and are not invented. Evidence persistence awaited file authority; human's relayed instruction “jo jo chaiye vo bnaao, baar baar approval mat loo” now authorizes these normal checker files. This is persistence of this checker's own evidence, not a fresh check or reuse of another checker's findings.
