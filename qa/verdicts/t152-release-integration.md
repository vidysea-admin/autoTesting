# T152 - independent merged release integration

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-07.7
VERDICT: PASS

## CHECK-PLAN

Checker `/root/t152_release_integration`, own root `D:/autoTesting/.worktrees/codex-t152-release`, Tier M. SERIAL: native machine lock and resource-bound two shards. This judges T152 only, not T153, the foundation or T174. Re-derive AI2 literal kind/check table and no-provider selection; AI3 exact-kind refusal; AI4/CT7 single Catalog with web rows preserved; AI5 endpoint/ground-truth blockers and schema consistency. Verify affected imports, configuration/runtime identity, original independent falsification applicability, lint and doctor. Run one complete sharded suite including harness at the merged pre-push source head, with complete node union proof. Attribute each initial red against unchanged origin, never claim a clean suite. No changed UI surface, live browser or deployment claim.

## SCOREBOARD AND IDENTITY

AI2-AI5 and CT7 acceptance remain satisfied. Own run: 114 passed, one warning in 9.78s; full lint passed; actual doctor clean. Exact commands and applicable hashes are in `qa/checkpoints/t152-release-integration.md`. Seven original independent green/red/restored per-criterion falsifications by `/root/check_t152` are reused with attribution from the preserved cycle-0 PASS/checkpoint, not claimed as new mutations. Their applicable source/test/fixture/config/runtime identities are unchanged. Original whole ai_check.py is NOT byte-identical: unjudged T153 types/imports were removed; the two judged enum ASTs are identical. No T153 acceptance is inherited.

Checked source HEAD `cc4743e6435e6c0f811dbb1d17bbf99866fb34b1`, public base `167f75761cb47f4839ca9d998b3da9d21ac536e5`, original T152 source commit `4375739b`. Source/test/config diff remained empty before closeout. Python 3.11.15, Windows 10.0.26300, pydantic 2.13.5, pytest 9.1.1; own release imports verified. Native maker/checker protocol hashes match the original pins; tick policy check: .7, targets=2, drift=0.

## COMPLETE INTEGRATION RESULT - INITIAL RED RETAINED

One full suite: 2,813 passed, 19 skipped, 3 failed; exit 1. All 2,835 tests in 231 files collected and ran exactly once; baseline=unique=shard union=ran=2,835, no duplicates, missing or unexpected nodes. No harness exclusion, fail-fast or pins. Source archive proof: all 1,988 files match exact Git blobs, core.autocrlf=false before snapshots. Runner overall 2,137.4s (35.62 min), run 2,076.4s; two shard walls 1,664.2s and 2,075.4s, lock wait 0. This is a completed RED integration instrument, not a green full-suite claim.

| Exact initial failure | Release isolated repeat | Unchanged origin targeted result | Ownership / disposition |
|---|---|---|---|
| test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen | failed | same assertion failed at line125: narration None vs phrase | Existing ingest/reconcile criterion, outside T152. Source drops narration without transcript verification. Owner of that criterion must reconcile this contract/test; not fixed or waived here. |
| test_mc_sessionstart_loop_status.py::test_hook_prints_the_report_and_exits_zero_on_a_healthy_log | passed | first fresh-baseline run failed at line164, missing ticks:1, hook exit0; subsequent traced run passed in8.56s | Existing native hook/harness, outside T152. Cold/warm/load cause is an inference, not established root cause. Keep native-harness reliability concern; no enforcement edit here. |
| test_goal_contract_registration.py::test_revised_goal_contract_is_registered | failed | same dashboard-facts assertion failed at line90 | Already stale origin dashboard. T152 normal task closeout regenerates it; post-closeout check required. |

Exact baseline command: `D:/autoTesting/.venv/Scripts/python.exe .work/t152-baseline-probe.py`; isolated origin167, UV_OFFLINE=1, own src imports, no real .env/runtime copied. Pytest returned 1: three exact failures in54.90s, not setup errors. Eighteen applicable source/test/fixture/config/goal blobs are identical origin/release and baseline copy. Raw follow-up hook capture: `.work/t152-baseline-results/hook-subprocess.json`, exit0, ticks:1 and loop-status:no gaps, stderr empty. Initial red remains recorded despite passing rerun. Raw runner summary/logs and baseline evidence remain in `.work/t152-integration-suite/` and `.work/t152-baseline-results/`.

Policy .7's pre-push ownership rule reopens the unit owning a failed file, not every independent unit. Completed instrument plus unchanged-origin exact assertion proof establishes these failures predate T152. No affected T152 failure or concrete security contradiction was found. PASS is scoped T152 acceptance/integration attribution, not approval of the unrelated red criteria. Their holds remain with their existing owners; no other goal is closed or source repaired here.

Safety caveat: snapshot inputs contain no real .env/venv/runtime and own scoped acceptance uses synthetic fixtures. Existing full-suite hook harness creates its own scratch .venv through uv. Dependency-network activity was not independently monitored, so no blanket no-network assertion is made for the full suite; baseline follow-up was explicitly offline. No approved external model/live product run or deployment was performed.

## NORMAL CLOSEOUT VERIFICATION

Only T152 task data changed, asserted against UTF-8-decoded origin Git blob; other91 task objects identical. Goal CLI done output ok:true/task:T-152/percent:73; local92total67done25pending. Dashboard regenerated from this current-origin goal, never copied from the old checker tree. Ledger CLI appended F075 updated/normal/reason:update with this verdict ref, no live claim. map regenerated with no byte diff; snapshot regenerated normally. Post-closeout command `python -m pytest tests/test_goal_contract_registration.py tests/test_goal_done_checks.py --basetemp .work/temp/closeout -o addopts=` returned8passed0.29s; actual doctor clean and ruff All checks passed. The dashboard failure is thereby repaired through required bookkeeping; the initial full-suite red and unrelated reconcile/hook concerns remain intact. Source/test/config/DECISIONS diff is empty.

REMAINING: narrow commit and nonforce public push; no deployment claim. Root owns enclosing landplane entry; existing D017 authorizes this registry, with no new architecture/contract/enforcement change and no competing D080.

Metrics: start=2026-10-08T08:28:14Z end=2026-10-08T09:08:30Z wall_min=40.27 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=3 mutations=0 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7

The metric interval is the measured full integration plus attribution, separately from the proportional scoped review; initial dispatch/scoped wall split was not recorded and is unavailable, not asserted within10min. Repeat_runs=3 means the runner's three-node isolation, unchanged-origin three-node probe and one-node raw hook trace. Seven reused original mutations remain attributed to the original checker, not this metric.
