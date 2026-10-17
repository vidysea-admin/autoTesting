# Verdict - at650-typing-input-type (dual check, coordinator A)
Cycle checked: 0
Policy-Version: proportional-verification/2026-10-15.12
Bound to: D:/autoTesting/.worktrees/at650-typing-input-type · Base 69ebfae7 (git merge-base HEAD master) · Judged head bb79ddb6 (no src/tests change since)

## Check plan
Logic + schema + security gate changed (enumerate.js, ElementRef, typing_target_allowed). Plan: re-run the manifest's verify commands; read the full unit diff (4c); one falsification per changed behaviour in isolated copies, green-before/red-after; downstream consumers of ElementRef/enumerate; ruff + doctor. No UI surface changed (no Mode D); no persona walk (backend-only gate); no full suite (policy .7, left to 6c).

## Result
VERDICT: PASS
SCOREBOARD: 1/1 criteria met (AT-650 / X10-b condition 4), invariants: none touched
TIER: L (security: explore_safety.py:58 typing gate, dual-trigger line present and matches the diff)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (guard deleted -> 5 failed; `type` line deleted in enumerate.js -> 1 failed)
LIVE-BROWSER: not-applicable (no screen changed; the browser test drives real headless Chromium through page_factory and ran green in my own runs)
ISSUES-WRITTEN: none (dual coordinator PASS has no side effects)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (all produced by me in this check)
- Verify command: `uv run pytest tests/test_explore_typing_input_type.py tests/test_explore_typing.py tests/test_explore_typing_guards.py tests/test_explore_safety.py` -> 104 passed, 1 warning in 137.20s (own run, exit 0).
- Downstream consumers of enumerate_elements/ElementRef: `pytest tests/test_observe.py tests/test_explore_replay.py tests/test_explore_merge.py tests/test_crawl_coverage.py` -> 50 passed. Affected-set tool (`shard_suite.py --affected 69ebfae7..bb79ddb6 --list`) returned integration-required (exit 2, dynamic glob tests in repo): recorded as `full-suite trigger: repo has dynamic-glob tests` for 6c, not run here.
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean.
- Falsification (copies outside the worktree, PYTHONPATH pinned to the copy, `autotester.__file__` confirmed inside the copy), named file tests/test_explore_typing_input_type.py:
  - green in both copies before any edit: `8 passed` (A), `8 passed` (B).
  - A: delete `if el.type.lower() in _UNTYPEABLE_INPUT_TYPES: return False` (explore_safety.py:58-59) -> `5 failed, 3 passed`, `AssertionError: assert not True` x5 on the 4 gate parametrizations + the browser test's gate assertion (the named assertion, not an import error).
  - B: delete `type:` emit in enumerate.js:147 -> `1 failed, 7 passed`, `AssertionError: assert ('', '', '', '') == ('password', ...)` in test_enumerate_reports_the_real_type_of_a_password_input_named_pin.
  - Mutations=2 (the floor); no extra mutants.
- Step 4c diff read (src fully read, `git diff 69ebfae7..bb79ddb6 -- src`): +1 line enumerate.js:147, +6 screen_graph.py:46-51 (`type: str = ""` defaulted, extra="forbid" kept), explore_safety.py:39,58-59 (`_UNTYPEABLE_INPUT_TYPES`, guard before the name heuristic, which is kept as a widening). Nothing deleted or renamed; every file touched is in the manifest's What changed; the only other diff vs base is the manifest and the new 64-line test file.
- Issue text check (AT-650 `expected`): enumerate emits `type` (met), ElementRef carries it defaulted so old graphs validate (met; test_a_stored_element_without_type_still_loads... passed), gate refuses password/file outright with the name heuristic retained (met; docstring now true). Contract X10-b condition 4 (explore.md:128) holds. Case-folding (`PassWord`) covered in both JS (lowercased) and Python (`.lower()`).
- Security read of changed lines: the gate only gets stricter (adds a refusal, removes none); a legacy element with type "" is still gated by role + the name substring exactly as before, so no widening of what is typed. explore_replay re-evaluates the same gate on the recorded ElementRef (explore_replay.py:82), so recorded old actions keep the old behaviour and new recordings carry type.

## Notes (non-blocking, questions only)
- agent_actuator.py:163 builds an ElementRef without `type` for deny_reason; that path is a click/deny guard, does not call typing_target_allowed, and is out of this criterion.
- Manifest and builder Pre-check line match what I reproduced (104 passed).

PROPOSED-ISSUE: none

Metrics: start=2026-10-17T14:25:00Z end=2026-10-17T16:38:00Z wall_min=45 agent_min=unavailable blocked_min=95 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
slow: affected-set pytest run 2.3 min (pytest startup + chromium); rate-limit wait counted as blocked_min
