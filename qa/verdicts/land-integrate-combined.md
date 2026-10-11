# Verdict — land-integrate-combined — Coordinator: A (blind dual check)

Date: 2026-10-11 · Cycle checked: 0 · Policy-Version: proportional-verification/2026-10-10.9 · Resume: 0 of 2 · Retry: 0
Checked: worktree `.worktrees/land-integrate-combined`, HEAD 23e694a9 (code f210ddc2), base master 3a16616c (merge-base verified). Tree e7093149.
Evidence: `qa/evidence/land-integrate-combined-A/` (falsify.out, falsify2.out, base.out, summary.json, A-shard.log).

## Plan
Tier L (security: dual-trigger lines verified, redact.py:173 `def mask_pii`, reconcile.py:92 `def build_judge_prompt`). No UI surface (diff touches no ui/, template or static file) so no browser walk. Checks: step 4c diff scope; criteria RC11, RC12, RC14 and C1, C2, C3 re-run by me; one falsification per criterion in throwaway copies of HEAD outside the worktree; own PII probes; the one owed checker full suite.

VERDICT: PASS
SCOREBOARD: 6/6 criteria met (RC11 RC12 RC14 C1 C2 C3), invariants touched by the diff hold
TIER: L (security: PII masking in core/redact.py:173 and the judge prompt path stages/reconcile.py:92)
FAILURES: none
CAPABILITY-COVERAGE: 6/6 rows reproduced (green in copy, red after, assertion named); see below
LIVE-BROWSER: not-applicable (no ui/template/static path changed)
ISSUES-WRITTEN: none (dual check; PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Step 4c diff scope (git diff 3a16616c...HEAD, 13 files)
Only: redact.py (+101, additions only), reconcile.py (import, mask in build_judge_prompt, docstring 3 -> 1 line, 300 lines), 2 new test files, 2 at780 manifests + 4 verdicts + this manifest (merge), issues.jsonl (+11 rows AT-830..AT-840; AT-780 line untouched vs master, status open), SNAPSHOT.md (1 line). Removed lines in code: only the old docstring and the old `actions` comprehension. No test deleted or edited (0 `-` lines under tests/). No stages/review.py, test_review*, ui/ file (grep count 0). Every file is in the manifest.

## Criteria (my own runs)
- RC11: `test_rc11_same_inputs_give_byte_identical_output_in_any_input_order` green in copy, RED after `videos = list(videos)` + unsorted `new_s.values()` (byte inequality at index 143). Full-suite run also green for it. Probe: mask_pii idempotent on 12 inputs, mask_pii_obj deterministic.
- RC12: tests/test_reconcile_pii.py 42 passed in copy; deleting `video, other = mask_pii_obj(video), mask_pii_obj(other)` -> 16 failed (`test_hardened_pii_shapes_never_reach_the_prompt[*]`, `test_nested_strings_in_every_part_of_the_prompt_are_masked`). Probe: email, +91, 10-digit, US, STD, IDN emails masked; `User name`/`studentId` not masked, `First Name`/`student_name` masked.
- RC14: doctor in copy green, then RED after one added line: `file-too-long: reconcile.py 302 lines > 300`. In the worktree: `autotester doctor` -> "doctor: clean", reconcile.py 300 lines; review/ui diff count 0.
- C1: no new model; `test_schema.py::test_unknown_field_is_rejected_loudly` green, RED when `extra="forbid"` -> `"ignore"` (14 occurrences): DID NOT RAISE.
- C2: doctor clean + `ruff check src tests scripts` -> All checks passed; reconcile.py 300 lines; same RC14 mutant red.
- C3: doctor clean; copy with a second `def mask_pii` in stages/ingest.py -> RED `duplicate-concept: ingest.py:303 'mask_pii' also defined in core/redact.py`. No *_v2/_new files in diff.

## Full suite (checker-owned, one per tier L security trigger), run in the worktree at 23e694a9
Attempt 1 serial `pytest -p no:xdist` aborted by me (PIDs I started) at about 37% after 40 min (host CPU ~90% from other sessions, projected 2+ h); log kept, not counted as a result. Attempt 2 `shard_suite.py --shards 6 -- -o addopts=`: collect proof ok 3035 = 3035, 3013 passed, 19 skipped, 3 failed, 0 error, wall 1168 s, blocked_s 54.
Reds, each checked on master 3a16616c in a git-archive copy, same message:
1. test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus (AT-725): master FAILS 3.54 s > 3 s; head passes alone 2.44 s. Timing-bound under load, not this unit's.
2. test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen (AT-792): identical assertion `None == 'type your email here'` on master and head.
3. test_mc_sessionstart_loop_status.py healthy-log (AT-858): master FAILS `TypeError: argument of type 'NoneType'`; head passes alone and in the shard rerun (flaky). Not this unit's.
No red is new. test_crawl_inventory_live (AT-750) did not fail. Doctor and ruff were re-run by me on the worktree after that (both clean; SNAPSHOT.md not stale at this HEAD).

PROPOSED-ISSUE: {"severity":"low","type":"process","feature":"land-integrate-combined","title":"checker A exceeded the L 45 min wall (about 67 min): serial full suite is about 2 h on a loaded host; use shard_suite first","evidence":"qa/evidence/land-integrate-combined-A/A-shard.log"}
PROPOSED-ISSUE: {"severity":"low","type":"pii-leak","feature":"redact","title":"mask_pii leaves `a@@b.com` unmasked (probe)","evidence":"probe output, redact.py _mask_emails"}
(Both are lows; AT-830..AT-840 already track the known hardening gaps. AT-840 grade.py unmasked stays out of scope.)

EXPLANATION: Every criterion is evidenced by my own run and a named red-after falsification; the diff adds PII masking without deleting or touching anything outside scope; the full suite shows only three reds, each reproduced on master. I slipped the L wall (67 min) after the serial suite proved too slow; slow: full suite 63 min.
Metrics: start=2026-10-11T01:03:33+05:30 end=2026-10-11T02:12:00+05:30 wall_min=68 agent_min=unavailable blocked_min=1 suite_runs=2 repeat_runs=0 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=4100 mutants=0 defects_unit=0 defects_6c=0
