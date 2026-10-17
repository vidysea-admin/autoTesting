# Verdict - at650-typing-input-type (coordinator B, blind dual check)
Verdict: PASS
Cycle checked: 0
Policy-Version: proportional-verification/2026-10-15.12
Bound to: D:/autoTesting/.worktrees/at650-typing-input-type  Base: 69ebfae7 (git merge-base HEAD master)  Head: 0d0a98ee (code bb79ddb6)
TIER: L (security trigger quoted: src/autotester/stages/explore_safety.py:58 typing gate) - dual-trigger line present and real. LANE: normal (lane off for dual).

## Check plan
Logic + security gate changed -> affected tests, 1 falsification per criterion, security read of changed lines (4c). No UI surface, no persona walk (backend-only), no data collection.

## Criterion AT-650 (issue text: enumerate.js emits `type`; ElementRef carries it, defaulted; typing_target_allowed refuses password/file outright, name heuristic stays as widening)
- Diff read in full (git diff 69ebfae7..HEAD -- src): enumerate.js:147 emits type (lowercased el.type for input, "" otherwise); screen_graph.py:46-51 `type: str = ""` (old graphs validate under extra=forbid); explore_safety.py:39,58-59 frozenset{password,file}, check `el.type.lower()` placed BEFORE the name heuristic, which is retained. Docstring now matches behaviour.
- Re-ran affected tests myself: `uv run pytest tests/test_explore_typing_input_type.py tests/test_explore_typing.py tests/test_explore_typing_guards.py tests/test_explore_safety.py` -> 104 passed (139.7s). ruff src tests scripts -> All checks passed. `autotester doctor` -> clean.
- Falsification (throwaway copies outside worktree, scratchpad fz-A/B, green-before from unedited copy fz-C):
  green: 8 passed (new test file).
  A: delete the `el.type.lower() in _UNTYPEABLE_INPUT_TYPES` guard -> 5 failed, 3 passed; `AssertionError: assert not True` in test_a_password_or_file_input_is_refused_even_when_its_name_looks_harmless[PIN/Passcode/Avatar/PASSWORD] and the browser test's gate assertion.
  B: delete the `type:` emit in enumerate.js -> 1 failed, 7 passed; `assert ('', '', '', '') == ('password', ...)` in test_enumerate_reports_the_real_type_of_a_password_input_named_pin (real Chromium).
- Security read: gate is strictly narrowing (adds refusals only); a missing type ("" from legacy graphs / non-input) falls through to the old name heuristic, so no widening. Replay path (explore_replay.py:82) and both typing call sites (explore_typing.py:104,147; explore_node.py:240) all use typing_target_allowed, so the fix covers fresh and replayed typing. structural_signature (screen_identity.py:42) keys only role|name, so screen identity is unchanged by the new field.
- 4c: only the 5 files named in What changed (+ manifest); nothing deleted or renamed.

## Findings
none blocking. PROPOSED-ISSUE: none.

Metrics: start=2026-10-17T14:25:00Z end=2026-10-17T15:05:00Z wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=2400 mutants=0 defects_unit=0 defects_6c=0
