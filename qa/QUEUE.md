# qa/QUEUE.md — checker sweep queue (top-3 recommended next units)

## Human-asked, above the TODO rows (2026-10-07 sweep consolidation)

| Row | State |
|---|---|
| Group 10: T-197, T-198, T-199, T-200, T-201 | human-asked D-067 (Umesh, chat 2026-10-07, top priority); blocked on PLAN gate (intent -> grill -> spec -> plan) before any build. Not sweep findings. They have no contract, spec or intent coverage yet (expected: the PLAN gate authorizes it), and the pending tasks lack done_checks (AT-744, maker-owned, red suite test). Also absent from target.md and docs/plan.md (AT-729/AT-738 family). No code before `qa/gates/plan-approved.md` covers them. |

No `HOLD:` line this sweep: no failure is traced, with evidence, to a checked-PASS feature's changed files.

2026-10-01 bounded Mode B full-goal triage — EXHAUSTED (partial seven-check sweep, not CLEAN).
Report: `qa/verdicts/sweep-2026-10-01-bounded-goal-triage.md`. Preserve all older queue history below.

## Current independent next units (supersedes obsolete recommendations below)

| Priority | Unit | State and evidence |
|---|---|---|
| 1 | TODO: AT-733 logged-out entry-profile cleanup honesty | Existing `ui/run_execution.py:55::_run_entry_case`, suppressed wipe error at67 then browser startup at70; canonical open/high AT-733; C12/RU1/RU3. Existing-file red-first plan, no T-165/live-account dependency. |
| 2 | TODO: T-125 catalog scoped cycle4 resume | D-051 answered; CT9 written; CT6 order-only stands under D-058 point2. Recover/identify existing branch artifact before fresh plan/checker; no discard/recreate/merge authorization. |
| 3 | TODO: T-151 deterministic discovery/context | T-150 done; ai-target AI1/AI8 and D-017 named stages. Synthetic in-root fixtures first, ordinary independent plan/new-file scope validation; no real-target firing authorization. |

AT-113 cycle3 STALLED + FAIL remains held on `qa/gates/at113-cycle3-recovery.md` (Decision pending). No additional cycle, contract weakening or release. T-165 pending makes T-176/T-166/T-168 dependent, not free. T-171 is already done with checked-PASS cycle2; missing done_check/ledger metadata is separate debt, NOT a task-resume instruction. Other independent work continues; the whole reusable platform/two-target acceptance objective is unchanged. Uncovered sweep dimensions are listed in the report.

## Candidates (human picks) — 2026-10-07 sweep, report `qa/sweeps/2026-10-07-sweep.md`

Candidates are never built until a human moves one out of this section with `approved: <date>`. Source: sharded Mode B (3 shards + consolidation), window 2aed300e..72fafe7c, working tree dirty.

| Priority | Candidate | Ref |
|---|---|---|
| priority: S1/S2 | Pending goal tasks T-197..T-201 have no done_check; `test_every_pending_task_actually_has_a_done_check` fails deterministically and keeps the suite red. Maker-owned and in progress; listed so it is not lost. | AT-744 (high) |
| priority: S1/S2 | `data_boundary.py` exits 1 (adapter.json declares no `data_class`). Standing, accepted posture, wontfix, exemption recorded in `qa/contracts/core-invariants.md` (AT-365 list entry). NOT refiled. | AT-365 (wontfix) |
| medium | AT-113 cycle 3 STALLED, gate answered 2026-10-05, no maker action since 2026-10-06 and no `qa/debug/at113-cycle3.md`. Reread the gate file before reopening. | AT-745 |
| medium | One solo re-run on an idle tree for the 4 load-or-regression suite failures: `test_crawl_inventory_live` STOPPED_BOUND (possible AT-113-era regression), mc_sessionstart 60 s timeouts, redact_wrap_perf 3.83 s, `video_parallel_sweep` 'A never finished closing' (possible ISS-t191-run-video-1 regression). Not a HOLD. | AT-750, ISS-t151-target-discovery-6, AT-725 |
| medium | RULING (checker, 2026-10-07): the AT-750 solo re-run found 4 load flakes, no regression. Loosen via ONE env-scaled helper `timing_scale()` (AUTOTESTER_TIMING_SCALE, default 1.0, clamp [1.0, 4.0], can only loosen): crawl_inventory_live:103 wall_clock_s 240, mc_sessionstart:142 timeout 60, redact_wrap_perf:192 bound 3.0 (the :209 scaling guard stays untouched), video_parallel_sweep:42 `_WAIT_S` 30; sweeps run with scale 2. Tier L protected change, one checker; load marker and keep-as-is rejected. Exact change and checker tests are in the ledger row. Not built until a human approves. | AT-757, AT-750, AT-725 |
| medium | Gates showing ANSWERED without an `Answered:` line (at638, t125-stalled, pathlynks-user-account-first); t192 narrowed-command ratification is genuinely OPEN and Umesh's. | AT-746, AT-285 |
| medium | `qa/feedback-inbox.md` is 5802 lines; about 20 sections from 2026-10-05/06 unfolded. Fold or archive. | AT-747 |
| medium | T-136 truth sheet `ERP_Issues_Trainers.xlsx` missing on disk. | AT-752 |
| medium | Roadmap and plan text stale against goal.json (target.md T-165 marked done while pending; T-120/T-150/T-171/T-185 unchecked; T-196..T-201 missing; plan.md 'draft', '26 remaining', 8 done tasks listed as remaining, T-165 shown buildable). Already filed, carried. | AT-729, AT-738, AT-642, AT-731 |
| medium | Ledger debt carried: 459 of 508 fixed rows lack `regression_check`; 11 duplicate ids (AT-288..291, AT-547..552) unreconciled. | AT-634, AT-656, AT-676 |
| low | `ui/routes_video.py` added after plan approval with no feature trio or Persona walk line (arguably T-191's fix cycle). | AT-748 |
| low | Delegation ledger has no record rows since 2026-09-27 (~15 Claude-built units). | AT-749 |
| low | Two `test_cli_harness_safety` failures were contamination by a concurrent `ingest prep`, not a CLI bug. | AT-751 |
| low | CLAUDE.md 'Credentials' (AT-570 open, pre-D-068) and `explore.md:614` 'explicit per-run' need a D-entry before the edit. | AT-753 |
| low | doctor not clean: root-clutter `at113-fixture-wn6g4n_e`, `pytest-of-unknown`; stale `docs/MAP.md`. | AT-756 |
| low | `qa/loop.md` HUMAN_GATE example stale; three EXHAUSTED sweeps with the same top-3 and no unit closed (loop-spin). | AT-754, AT-755 |
| low | `explore_node.py` sits at exactly 300 lines (cap), carried. | AT-567 |

GRILL candidates (not rows to build): the three intent questions Q1/Q3/Q4 in `docs/intent.md` have been open over 7 days (Q1 row already below; Q3/Q4 listed with it); D-067 moved the goal, so either one GRILL for group-10 scope or accept the PLAN gate's own grill as that grill (Umesh decides).

`ISS-ingest-fields-1` (high) was fixed and merged in 72fafe7c with checked-PASS cycle 0; it is in the ledger as `fixed`, nothing to do.

---

2026-09-30 bounded crawl-recovery sweep addendum (preserves previous queue):
1. AT-113 / T-165 reopen: independently reproduced completed/0 actions/one aborted_error;
   fix new and legacy completion truth, frontier exhaustion and persona deletion honesty first.
2. Generic authenticated recovery using existing return_to/replay seams; truthful failure alone
   does not satisfy authenticated end-to-end crawling.
3. T-171 permission-surface coverage (carry the prior work/recovery priority).
Report and proposed existing-file plan: `qa/verdicts/sweep-2026-09-30-crawl-recovery.md`.
at673 cycle 3 is checked-PASS with matching verdict; ISS-at673-1 already owns detector debt.

Refreshed by `/checker sweep` **2026-09-29T12:28Z** (system clock, `date -u`, not typed — AT-399), HEAD
`ade87168` (D-057). Bound strictly to `D:/autoTesting`. **Single-agent sweep** — measured ceiling this tick
2.81 GB free RAM, the same constraint the 2026-09-28T12:35 sweep stated, so the 3-shard split was not
available. Full report: `qa/verdicts/sweep-2026-09-29.md`. Supersedes the 2026-09-28T12:32Z queue. **D-057 (Umesh, 2026-09-29) is folded in:** the CT6 gate and the AT-710 new-module gate are both ANSWERED.

**What changed since that queue:** D-057 answered both open gates (below); the four D-054 contract files exist (so the ISS-at638-remainder-1
HUMAN_GATE line is gone — it was answered 2026-09-27 and fixed 2026-09-28); D-041's four unwritten
contracts now exist too (AT-726); `at710` was built, falsified and **held** at a new-module gate
(`qa/gates/new-module-authorization.md`, unanswered); the approval-surface cluster stands as re-triaged.

## TOP-3 BUILDABLE NEXT UNITS

| # | Unit | Why |
|---|---|---|
| 1 | **T-171 permission-surface — RESUME, do not restart.** `.claude/worktrees/agent-a34c44eb5901959f8` holds 10 files (+249/-19) of **uncommitted** crawl-coverage and explore-safety work from 2026-09-28 18:12, tied to a manifest that exists only inside that worktree, untracked, with `tests/test_permission_coverage.py` (AT-728, corrected). Criteria exist and are ungated: `qa/contracts/permission-surface.md` PS1-PS4 (DRAFT, D-054) plus `coverage.md` V9 (AT-663). Commit that work and its manifest to a wave branch so master can see them, then build. | Serves O4 directly and Umesh's verbatim 2026-09-23 ask ("jo account mai dunga usme jitni permission hogi uthi tho testing ho hi jaani chaiyee"). It is also the one item where finished-looking work is one `worktree remove` from being lost. RAM-bound: one build at a time at 2.81 GB. |
| 2 | **T-176 script-replay.** Criteria written today: `qa/contracts/script-replay.md` SR1-SR5. Free behind T-165 (done). `Case.script_ref` and `Script` already exist and are unwired, so this is wiring, not invention. **It was never gated** — the maker's 2026-09-29 tick listed "T-176: no authorizing contract", but D-041 authorized the file on 2026-09-24 (AT-726). T-177 (`agent-fallback.md` AF1-AF6) follows it. | Highest-value ungated unit: it turns every regression run from N provider calls into zero, and SR5 encodes D-041's refusal of "regenerate instead of maintain". |
| 3 | **T-125 cycle 4 -- submit it for check, and judge it against CT6 (narrowed) and CT9 (new).** Build to recover: `worktree-agent-aca539b488be4c248`, 12 ahead (manifest `t125-test-catalog.md`, `ready-for-check`, uncommitted edit, no verdict; master carries neither, so the hook cannot see it). **D-057 makes CT6 PASSable:** it is now 'dispatch in tier order, report each tier's runnable count, never skip' and no longer conflicts with RU3/F-058; the build must wire `tiers_to_run()` (not yet in `src/` on master) into `routes_runs.py::trigger_run` as ordering only. **New precondition met this sweep:** D-051 asked for a written relevance rule before cycle 4 and none existed (AT-732); CT9 now states it. Expect the check to open on CT9(b) (`4636e832`) and CT6(2) (executed set == `list_cases()`). | T-125 gates T-152, T-166, T-174 and T-178; `cli-mcp.md` and `failure-bundle.md` wait behind it. Merge note: `wave/t125-catalog` holds a 2026-09-27 catalog.md amendment master lacks; the two log tails will conflict and both entries stay. |

## HELD on a human — one line each, not build rows

- **AT-710 is OFF the human list (D-057, Umesh 2026-09-29):** `src/autotester/ledger/citations.py` and its own test module are authorized for AT-710 ONLY. AT-697 and AT-727 meet the new-module gate again on their own merits (the standing-rule variant was not chosen). The build is held in `.work/at710/` and resumes under the maker. **AT-718 has happened AGAIN (AT-740):** the seven write-policy citations were re-pointed to `D-057 (NOT YET WRITTEN)`, and D-057 was then appended on 2026-09-29 for a different subject (the three answers). They resolve to the wrong entry a second time; the write-policy entry, once written, is `D-058` or later. This is the exact case `check_decision_citations` exists to catch, and its fixture (c) in `living-ledger.md` names the now-spent id.
- **HUMAN (classifier-blocked): the approval-derivation unit** — AT-674 (`core/env.py::ensure_approval_key`) + AT-683 (`cli_crawl.py::approve_cmd` real min=1 defaults). Fully authorized by Umesh's 2026-09-28 answer; both halves were reported blocked by the harness classifier. Blocks T-122.
- **HUMAN_GATE (AT-668/AT-669):** the guard-the-guards protection does not cover `qa/hooks/*` — needs an `Approved-by` DECISIONS entry before the wiring fix lands.
- **Umesh's, still open:** `qa/gates/t192-narrowed-command-ratification.md`. (`t125-ct6-tiered-dispatch-vs-ru3.md` is ANSWERED, D-057; the maker records its `Answered:` line.)

## Also real, not in the top 3 only for space

AT-733 (high: `ui/run_execution.py:67` wipes the logged-out profile with `ignore_errors=True`, so a locked profile lets a logged-out case PASS logged in); AT-734/735/736 (video, post-save prune and session-start failure paths); AT-727 (nothing checks that an authorized contract file exists — twice now misread as a human gate);
AT-731 (T-185 still `pending` after its PASS, merge and green done_check — one `goal_cli done`);
AT-729/AT-730 (target.md, plan.md and the at638-remainder manifest still say things that stopped being
true on 2026-09-27); AT-645/AT-656/AT-676 (recurring `qa/issues.jsonl` duplicate-id debt — 10 ids still
carry two rows); AT-711; AT-644; AT-634 (rows fixed without a `regression_check`, now 69, was 31).

## GRILL — human decision, not a build row (carried)

- GRILL: recurring vacuous-guard prevention policy (AT-218). Unanswered, carried.
- GRILL: real two-mode acceptance thresholds for D-023/T-169 (AT-281). Carried.
- GRILL (AT-402): structure-before-code review of `visual_order.js`. Carried.
- GRILL: intent Q1 audience internal-tool vs external-ui (`docs/intent.md:82`) -- unanswered, not PARKED. It sets how expensive every persona walk is.

**Explicitly NOT judged this sweep:** `at673` (`qa/manifests/at673-sessionstart-unclosed-detector.md`,
`qa/hooks/mc-sessionstart.ps1`, `tests/test_mc_sessionstart_unclosed.py`) and rows AT-713/714/715 and
AT-722..725 — a concurrent Mode A checker owns it. Commit `8ea308ee` (its cycle-2 build) is the only
in-window commit that touched `src`/`tests`/`scripts`/`qa/hooks`, and it belongs to that check.
