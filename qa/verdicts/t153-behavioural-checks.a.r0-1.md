# Verdict A — t153-behavioural-checks (coordinator A of a dual check)
Cycle checked: 0 · Retry: 0 · Resume: 0 of 2 · Policy-Version: proportional-verification/2026-10-10.9
Bound to D:/autoTesting; checked worktree `.worktrees/t153-behavioural-checks` HEAD 2653bbcb (product ff901f72). Date 2026-10-11.

## Check plan
Tier L (security trigger cited: ai_capture.py:92 `assert_clean`, :95 `require_approval`, both read). Backend only: no UI, no walks, no browser.
Steps: contract AI6/AI7 + C5/C7/C12(b); re-run criterion commands (pre-check sha ff901f72 != HEAD, so .9-5 reuse not allowed); falsifications in copies; step 4c diff scope; doctor on a clean archive of master; ONE full suite (owed to A).

VERDICT: BLOCKED-PROCESS
CAUSE (cited): the machine-wide suite lock `%LOCALAPPDATA%/aios/suite.lock` was held by PIDs that are not ours for the whole 15 min wait.
- Holder 1: pid 20200, `uv --directory D:/autoTesting/.worktrees/land-integrate-combined run pytest ...`, started 01:04:09.
- Holder 2 (took over at 01:44:54): pid 38884, repo `.worktrees/land-integrate-combined`, a shard_suite run.
- `shard_suite.py --repo D:/autoTesting --ref 2653bbcb --shards 1 --lock-timeout 900 -- -o addopts=` logged `[01:45:08] BLOCKED: suite lock busy after 900s ... (exit 3)`. Log: scratchpad `check-t153-a/suite.log`, summary `suite/summary.json`.
- The lock holder was not touched. blocked_min=15.
SCOREBOARD: 2/2 criteria evidenced (AI6, AI7); core invariants C5/C7/C12(b) hold on the evidence; the single owed full suite did NOT run, so no PASS.
TIER: L (security: secret admission before send, ai_capture.py:92; signed consent, :95)
FAILURES: none
REMAINING (for the retry): the one checker full suite only: `python ~/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting --ref 2653bbcb --shards 1 --out <scratch> -- -o addopts=` once the lock is free (code cap is 1). Everything below is reusable by evidence identity (same sha 2653bbcb, same test blobs).

## Evidence (all produced by this checker)
- AI6 grep `grep -n "Result\.\|Verdict(" src/autotester/stages/ai_capture.py` -> no output, exit 1. Source read in full (112 lines): no Verdict/Result, no `grade` import; `capture_run` records reply, latency, is_json, missing_keys only.
- AI6 handoff to grade: `stages/ai_judge.py` builds a `RawResult` from the capture and calls the real `grade()`; the COMPUTED path supplies a private `_ComputedJudge` Provider, so `grade()` alone constructs the Verdict. `test_the_capture_is_handed_to_grade_unmodified` (10 params) and `test_the_judged_verdict_comes_from_the_judge_not_the_capture` pass.
- Criterion commands re-run at HEAD 2653bbcb, one process: tests/test_ai_capture.py + test_grade_evidence.py + test_approval_signing.py + test_ai_catalog.py + test_grade.py + test_schema.py -> 189 passed (77+35+18+28+13+18, the builder's counts). `ruff check src tests scripts` -> All checks passed. `git status --porcelain` clean.
- AI7 capture side (read): `assert_clean` on project/endpoint/prompts/approvals before `require_approval` and before any send (ai_capture.py:88-95); every stored string scrubbed; whole capture `assert_clean` at the end, else `CaptureWithheld` (nothing returned). Judge side: `_scrubbed` = `scrub_obj` + `assert_clean`; reference and rubric also checked; `grade(..., redactor=)` gates the final prompt (`_withheld`, grade.py:101-113). A base64-encoded secret is refused whole (test passes).
- Doctor on clean `git archive` of master 354bd31f and of 2653bbcb: both print only `stale-generated: docs/SNAPSHOT.md` (1 violation) -> the builder's "pre-existing" claim is confirmed. `src/` and `tests/` are identical between 3a16616c and 354bd31f (`git diff --stat` empty).
- Step 4c: `git diff 3a16616c..HEAD --name-status`: A ai_capture.py, ai_judge.py, test_ai_capture.py, manifest; M ai_check.py (+45), grade.py (+9/-5), MAP.md, test_approval_signing.py, test_grade_evidence.py. No deletion or rename; no test line removed (a `^-` filter on the two modified test files returns none). grade.py's removals are the old `if secrets is None` / `secrets.guard_prompt` lines, rewritten in place with the same behaviour when `redactor=None` (`test_grade_secret_store_guard_survives_optional_redactor` passes). Every changed file is listed in "What changed".

## Falsifications (throwaway copies of `git archive 2653bbcb` under scratchpad `check-t153-a/m_*`; import path verified to be the copy; green before, red after)
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

## Full suite
Owed to coordinator A and NOT run: the suite lock was busy for 15 min (cited above). suite_runs=0. No ledgered red can be classified because no suite ran.

LIVE-BROWSER: not-applicable (changed paths: schema/ai_check.py, stages/ai_capture.py, stages/ai_judge.py, stages/grade.py, tests, docs/MAP.md)
CAPABILITY-COVERAGE: manifest rows for AI6, AI7 final-grade and AI7 judge-side reproduced (3 of 4; the C12(b) row is outside AI6/AI7 and was not re-run); plus 5 own falsifications
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent; self != executor)
EXPLANATION: Both criteria hold on evidence I produced and the floor is met, but the single full suite owed to this coordinator could not run because the machine suite lock stayed with another project's PIDs for 15 minutes; per policy that is BLOCKED-PROCESS (burns no fix cycle), not a PASS. A retry needs only the full suite.
Metrics: start=2026-10-11T01:14:00+05:30 end=2026-10-11T01:48:00+05:30 wall_min=19 agent_min=unavailable blocked_min=15 suite_runs=0 repeat_runs=0 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2040 mutants=4 defects_unit=0 defects_6c=0
