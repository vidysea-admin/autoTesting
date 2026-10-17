# Manifest — at650-typing-input-type
**Contract:** qa/contracts/explore.md (X10-b condition 4, line 128: password-named fields never typed, an upload never performed)
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** required
dual-trigger: security src/autotester/stages/explore_safety.py:58
**Persona walk:** skip (backend-only: the typing gate and the element observer, no screen)
**Issues addressed:** AT-650 (medium, open -> fixed)
**Executor:** claude-sonnet-subagent
**Executor rationale:** one gate, one schema field, one emitted key; nothing external was worthy.

## What changed
- src/autotester/browser/enumerate.js:147 — the out.push object now emits `type` (the input's real, lowercased `el.type`; "" for any non-input). It was computed for `is_form_submit` and dropped.
- src/autotester/schema/screen_graph.py:46-51 — `ElementRef.type: str = ""` (default, so graphs stored before AT-650 still validate under `extra="forbid"`).
- src/autotester/stages/explore_safety.py:39,58-59 — `_UNTYPEABLE_INPUT_TYPES = {"password","file"}`; `typing_target_allowed` refuses on `el.type.lower()` BEFORE the name heuristic, which stays as a widening. Docstring now true.
- tests/test_explore_typing_input_type.py (new test file, 64 lines) — gate (PIN/#pin password, Passcode/#otp password, Avatar/#avatar file, upper-case PASSWORD), legacy element without type stays typeable and name heuristic still widens, stored element without `type` loads and unknown key still refused, and a real-Chromium enumeration of `<input type=password aria-label=PIN>` etc.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: L (security: what explore types into which input; schema read/write) — dual check required
Base / checked state: 69ebfae7 / bb79ddb6 (clean tree)
Gate answers: none (no human gate; no new src module, qa/gates/new-module-authorization.md not needed)
Affected tests / full-suite trigger: tests/test_explore_typing_input_type.py, tests/test_explore_typing.py, tests/test_explore_typing_guards.py, tests/test_explore_safety.py; no full-suite trigger; builder ran no full suite.
Pre-check[C1]: bb79ddb6 uv run pytest tests/test_explore_typing_input_type.py tests/test_explore_typing.py tests/test_explore_typing_guards.py tests/test_explore_safety.py -> 104 passed t=129 blobs=tests/test_explore_typing_input_type.py:0b10027,tests/test_explore_typing.py:0c2240c,tests/test_explore_typing_guards.py:6afc7af,tests/test_explore_safety.py:7d1f5fd
Metrics: start=2026-10-17T13:40:00Z end=2026-10-17T14:20:00Z wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=129 mutants=2 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_explore_typing_input_type.py tests/test_explore_typing.py tests/test_explore_typing_guards.py tests/test_explore_safety.py` → expected: 104 passed
- `uv run ruff check src tests scripts` → expected: All checks passed!
- `uv run autotester doctor` → expected: `doctor: clean`

## Actual outputs (from maker's own run)
- pytest: `104 passed, 1 warning in 128.95s (0:02:08)`
- ruff: `All checks passed!`
- doctor: `doctor: clean`

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | a real password/file input is never typed regardless of its name; enumerate emits `type`; old graphs load | tests/test_explore_typing_input_type.py::test_a_password_or_file_input_is_refused_even_when_its_name_looks_harmless, ::test_enumerate_reports_the_real_type_of_a_password_input_named_pin, ::test_a_stored_element_without_type_still_loads_and_unknown_keys_are_still_refused | throwaway copy outside the worktree (scratchpad fz/): (A) delete the `el.type.lower() in _UNTYPEABLE_INPUT_TYPES` guard (explore_safety.py:58-59); (B) delete the `type:` line in enumerate.js:147 | green: `8 passed`. Red A: `AssertionError: assert not True` x5, `5 failed, 3 passed` (the 4 gate parametrizations + the browser test's gate assertion). Red B: `AssertionError: assert ('', '', '', '') == ('password', ...', 'password')`, `1 failed, 7 passed` (browser test only). Green again after restore: `8 passed`. The schema hunk alone was red pre-fix as a pydantic ValidationError on `type` (7 failed, 1 passed before any fix hunk existed) |

## Live browser evidence
Real headless Chromium via the `page_factory` fixture: tests/test_explore_typing_input_type.py::test_enumerate_reports_the_real_type_of_a_password_input_named_pin set a page with `type=password` (PIN), `type=file` (Avatar), no type (Plain), `type="PassWord"` (Upper) and ran `enumerate_elements`; reported types ('password','file','text','password'), the gate refused the three and allowed Plain. No screen changed, so no screenshots; no qa/evidence dir.

## Status: checked-PASS (qa/verdicts/at650-typing-input-type.md + at650-typing-input-type.b.md, cycle 0, dual)
