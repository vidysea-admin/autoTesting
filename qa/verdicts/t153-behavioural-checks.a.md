# Verdict A — t153-behavioural-checks (coordinator A of a dual check)
Cycle checked: 0 · Retry: 1 · Resume: 0 of 2 · Policy-Version: proportional-verification/2026-10-10.9
Bound to D:/autoTesting; branch `wave/t153-behavioural-checks` re-verified at 2653bbcb97bd (product ff901f72), unchanged since the earlier dispatch. Date 2026-10-11. Earlier BLOCKED-PROCESS verdict archived at `qa/verdicts/t153-behavioural-checks.a.r0-1.md`.

## Check plan
Tier L (security trigger: ai_capture.py:92 `assert_clean`, :95 `require_approval`, both read in the earlier dispatch). Backend only: no UI, no walks, no browser. Retry scope: the ONE owed full suite; every other check reused by evidence identity (same sha, same test blobs, checkpoint `qa/checkpoints/t153-behavioural-checks.a.md`).

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (AI6, AI7), core invariants C5/C7/C12(b) hold on the evidence; 0/0 FAIL findings
TIER: L (security: secret admission before send, ai_capture.py:92; signed consent, :95)
FAILURES: none
CAPABILITY-COVERAGE: AI6 and AI7 rows reproduced (3 of 4 manifest rows) plus 5 own falsifications; the C12(b) row is outside AI6/AI7 and was not re-run
LIVE-BROWSER: not-applicable (changed paths: schema/ai_check.py, stages/ai_capture.py, stages/ai_judge.py, stages/grade.py, tests, docs/MAP.md)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent; self != executor)
EXPLANATION: Every criterion was evidenced in the earlier dispatch and the one owed full suite now ran: 2950 passed, 19 skipped, 2 failed, both failures are ledgered pre-existing reds with the same assertion as on the base (below). No red touches this unit's files. Two earlier attempts at the suite were blocked by the machine lock (15 min each, holders were other projects' PIDs), the third ran with the lock free.

## Full suite (checker A's one suite, sha 2653bbcb)
`python shard_suite.py --repo D:/autoTesting --ref 2653bbcb --shards 4 -- -o addopts=` (4 shards, not 6: free memory 2.7 GB), no -x, started 05:09:24, ended 05:20:02, wall 637.7 s, blocked_s 0.
Counts: passed 2950, skipped 19, failed 2, collected 2971 in 232 files; collect proof ok (baseline 2971 = union 2971 = ran 2971). Log: scratchpad `suite4.log`, `shards4/summary.json`.
- `tests/test_mc_sessionstart_loop_status.py::test_hook_prints_the_report_and_exits_zero_on_a_healthy_log` — AT-858. Failed in shard 2 with `TypeError: argument of type 'NoneType' is not iterable`; PASSED when re-run alone (load-induced). The same TypeError is recorded on the base in `qa/evidence/land-integrate-combined-A/base.out` (master 3a16616c). Not in this unit's files.
- `tests/test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen` — AT-792. Failed in shard and failed alone with `AssertionError: assert None == 'type your email here'` (Step(order=1, action=FILL, target='Email'...)). Identical assertion on the base in `qa/evidence/land-integrate-combined-A/base.out`. `git diff 3a16616c..2653bbcb --stat` touches neither this test nor reconcile code.
- AT-725 (`test_redact_wrap_perf.py`) and AT-750 (`test_crawl_inventory_live.py`) did not fail in this run. No new red. No `load-flake` row needed beyond the AT-858 ledger entry.

## Evidence (all produced by this checker)
- AI6 grep `grep -n "Result\.\|Verdict(" src/autotester/stages/ai_capture.py` -> no output, exit 1. Source read in full (112 lines): no Verdict/Result, no `grade` import; `capture_run` records reply, latency, is_json, missing_keys only.
- AI6 handoff to grade: `stages/ai_judge.py` builds a `RawResult` from the capture and calls the real `grade()`; the COMPUTED path supplies a private `_ComputedJudge` Provider, so `grade()` alone constructs the Verdict. `test_the_capture_is_handed_to_grade_unmodified` (10 params) and `test_the_judged_verdict_comes_from_the_judge_not_the_capture` pass.
- Criterion commands re-run at HEAD 2653bbcb, one process: tests/test_ai_capture.py + test_grade_evidence.py + test_approval_signing.py + test_ai_catalog.py + test_grade.py + test_schema.py -> 189 passed (77+35+18+28+13+18, the builder's counts). `ruff check src tests scripts` -> All checks passed. `git status --porcelain` clean.
- AI7 capture side (read): `assert_clean` on project/endpoint/prompts/approvals before `require_approval` and before any send (ai_capture.py:88-95); every stored string scrubbed; whole capture `assert_clean` at the end, else `CaptureWithheld` (nothing returned). Judge side: `_scrubbed` = `scrub_obj` + `assert_clean`; reference and rubric also checked; `grade(..., redactor=)` gates the final prompt (`_withheld`, grade.py:101-113). A base64-encoded secret is refused whole (test passes).
- Doctor on clean `git archive` of master 354bd31f and of 2653bbcb: both print only `stale-generated: docs/SNAPSHOT.md` (1 violation) -> the builder's "pre-existing" claim is confirmed. `src/` and `tests/` are identical between 3a16616c and 354bd31f (`git diff --stat` empty).
- Step 4c: `git diff 3a16616c..HEAD --name-status`: A ai_capture.py, ai_judge.py, test_ai_capture.py, manifest; M ai_check.py (+45), grade.py (+9/-5), MAP.md, test_approval_signing.py, test_grade_evidence.py. No deletion or rename; no test line removed (a `^-` filter on the two modified test files returns none). grade.py's removals are the old `if secrets is None` / `secrets.guard_prompt` lines, rewritten in place with the same behaviour when `redactor=None` (`test_grade_secret_store_guard_survives_optional_redactor` passes). Every changed file is listed in "What changed".

## Falsifications (reused from the earlier dispatch: same sha 2653bbcb, branch tip re-verified) (throwaway copies of `git archive 2653bbcb` under scratchpad `check-t153-a/m_*`; import path verified to be the copy; green before, red after)
| id | edit | named test | before | after |
|---|---|---|---|---|
| AI6a | ai_capture.py: add `_X = "Verdict("` | test_capturer_source_never_constructs_a_verdict_or_result | 1 passed | red on `assert not <re.Match 'Verdict('>` |
| AI6b | ai_judge.py `_evidence`: response fact -> `""` | test_the_capture_is_handed_to_grade_unmodified | 10 passed | 10 failed (evidence-path assertions) |
| AI7a | ai_judge.py `clean = _scrubbed(...)` -> `clean = cap` (the builder's judge-side edit) | test_a_hand_built_capture_is_scrubbed_again_at_the_judge | 3 passed | 3 failed, but by `IndexError: list index out of range` (confirms the builder: weak oracle) |
| AI7b | AI7a plus `grade(..., redactor=None)` in the JUDGED call (my own: removes the judge scrub AND the downstream backstop) | same test | 3 passed | 3 failed on `assert 'sk-live-1234567890abcdef' not in '# grade_v1 ...'`, the real AI7 assertion |
| AI7c | ai_capture.py pre-send `assert_clean(text)` -> `pass` (line 92) | test_a_raw_secret_in_a_prompt_is_never_sent_to_the_endpoint | 40 passed | 40 failed |
| AI7d | ai_capture.py `require_approval(` -> no-op (line 95) | test_no_matching_approval_means_nothing_is_sent | 1 passed | `DID NOT RAISE ApprovalRequired` |
| AI7e | grade.py `redactor.assert_clean(prompt)` -> `pass` | test_ai_computed_grade_enforces_the_final_prompt_redactor | 1 passed | `assert (Result.PASS is Result.BLOCKED)` |
| AI7f | ai_capture.py `_exchange` stores raw prompt/response (scrub removed) | test_a_secret_in_the_target_response_never_reaches_the_judge_prompt | 3 passed | 3 failed (`CaptureWithheld`: the end-of-capture gate caught it) |

On the weak oracle: AI7's judge-side scrub IS guarded. With only the judge scrub removed (AI7a) the grade final-prompt gate still blocks the secret (no model call), so the test goes red by IndexError; with both layers removed (AI7b) it goes red on the secret-in-prompt assertion. The layers are independent defences and each has a red test (AI7a/AI7b judge side, AI7e final gate). 8 falsifications in total (L cap 10 for mutants beyond the floor; the floor is 1 per criterion).

## New module `stages/ai_judge.py` (un-gated)
No contract line, gate or D-017 text forbids it. D-017 lists five stages but is not an allowlist; doctor and the design rules pass (201 lines, docstring states one job); it duplicates nothing (it adapts a capture to `grade()`; `test_module_exposes_no_second_grading_path`). AI6 prohibits Verdict construction in `ai_capture.py` only, and grade.py cannot map captures, so a mapper module is the minimal place. Caveat: it is absent from `docs/ARCHITECTURE.md`'s concept-to-file table and from every DECISIONS entry (permitted, not authorised in prose). `_ComputedJudge.judge` also makes a PASS/FAIL decision from recorded numbers outside grade.py, through grade's Provider seam; AI6's second clause ("judgement happens only in grade.py") is ambiguous about that. Neither is a FAIL (no criterion violated).
PROPOSED-ISSUE: {"severity":"low","feature":"ai-target","title":"stages/ai_judge.py is un-gated: no ARCHITECTURE.md row and no DECISIONS entry names it; add both (authorising entry first)","evidence":"src/autotester/stages/ai_judge.py:1; docs/ARCHITECTURE.md concept map; D-017 stage list"}
PROPOSED-ISSUE: {"severity":"low","feature":"ai-target","title":"AI6 wording: say whether a rule-based Provider supplying a Judgment to grade() (ai_judge.py _ComputedJudge) counts as judgement only in grade.py","evidence":"qa/contracts/ai-target.md:112-114; src/autotester/stages/ai_judge.py _ComputedJudge.judge"}
PROPOSED-ISSUE: {"severity":"low","feature":"ai-target","title":"weak oracle: test_a_hand_built_capture_is_scrubbed_again_at_the_judge goes red by IndexError when the judge scrub is removed; assert the blocked outcome or scrub-specific output instead","evidence":"tests/test_ai_capture.py:274 (AI7a red = IndexError)"}
Open assumption noted, not a finding: `ApprovalKind.LIVE_CASE` for a behavioural capture (ai_capture.py:95) is the builder's [ASSUMPTION]; ADVERSARIAL belongs to T-154.

## New module `stages/ai_judge.py`, proposals (unchanged from the earlier dispatch)
Un-gated but permitted: no contract line or D-017 text forbids it; doctor/design rules pass (201 lines, one-job docstring); no duplicate path. Not a FAIL.
PROPOSED-ISSUE: {"severity":"low","feature":"ai-target","title":"stages/ai_judge.py is un-gated: no ARCHITECTURE.md row and no DECISIONS entry names it; add both (authorising entry first)","evidence":"src/autotester/stages/ai_judge.py:1; docs/ARCHITECTURE.md concept map; D-017 stage list"}
PROPOSED-ISSUE: {"severity":"low","feature":"ai-target","title":"AI6 wording: say whether a rule-based Provider supplying a Judgment to grade() (ai_judge.py _ComputedJudge) counts as judgement only in grade.py","evidence":"qa/contracts/ai-target.md:112-114; src/autotester/stages/ai_judge.py _ComputedJudge.judge"}
PROPOSED-ISSUE: {"severity":"low","feature":"ai-target","title":"weak oracle: test_a_hand_built_capture_is_scrubbed_again_at_the_judge goes red by IndexError when the judge scrub is removed; assert the blocked outcome or scrub-specific output instead","evidence":"tests/test_ai_capture.py:274 (AI7a red = IndexError)"}
Open assumption noted, not a finding: `ApprovalKind.LIVE_CASE` for a behavioural capture (ai_capture.py:95) is the builder's [ASSUMPTION]; ADVERSARIAL belongs to T-154.
Metrics: start=2026-10-11T05:09:00+05:30 end=2026-10-11T05:35:00+05:30 wall_min=26 agent_min=unavailable blocked_min=15 suite_runs=1 repeat_runs=0 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1560 mutants=4 defects_unit=0 defects_6c=0
