# Verdict -- ingest-fields (Mode A, cycle 0, single checker)
Cycle checked: 0
Date: 2026-10-07 · Bound root: D:/autoTesting/.worktrees/ingest-fields · Base fe6eb98a · Checked HEAD a902bc8d
Policy-Version: proportional-verification/2026-10-06.6

## Check plan (step 0)
- Diff: src/autotester/stages/ingest.py (`_to_screen`), tests/test_ingest.py, qa/manifests/ingest-fields.md. Backend only, no UI, no data artifact, no model call. Signal "logic changed" -> affected tests + falsification floor (one row per criterion).
- TIER: S (one product function in one file plus its test; no L trigger: no security/auth/data write/concurrency/config/dependency change in the diff).
- No dual check, no persona walk (api/backend, no human screen), no Mode D. Fan-out not needed (one check type).
- Contract: none names this bug; judged against manifest C1-C3 and ingest.md I1 (observed-only, deterministic content-addressed ids) and I7 (SourceRef on every screen, url_pattern via the shared templater).

## Re-run by the checker (own output)
- `uv run pytest tests/test_ingest.py tests/test_ingest_persist.py tests/test_ingest_real_cli.py` -> 39 passed in 5.67s (matches manifest count).
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> 2 violations (stale-generated docs/MAP.md, docs/SNAPSHOT.md). Claim "pre-existing on base" VERIFIED: ran doctor on a `git archive fe6eb98a` copy outside the bound root -> same 2 violations. Diff touches neither doc.
- No full suite (tier S, no safe-fallback trigger; conftest/fixtures/config/deps untouched).

## Falsification (copy outside root: scratchpad/fals = git archive HEAD, PYTHONPATH pinned to the copy's src; import path confirmed as the copy)
| Crit | named check | green before (in copy) | edit (single hunk, single file named in What changed) | red after | assertion that fired |
|---|---|---|---|---|---|
| C1 | tests/test_ingest.py::test_ingest_video_wraps_observed_field_labels_as_inputfields | 1 passed | `_to_screen`: `fields=observed.fields` restored (src/autotester/stages/ingest.py:142) | 1 failed | pydantic ValidationError `fields.0 Input should be a valid dictionary or instance of InputField ... input_value='Email', input_type=str` raised inside `ingest_video` = the named bug, not an import/setup failure |
| C2 | git diff scope (schema/ untouched) | n/a | the same red proves `Screen` still rejects raw str (no loosening validator) | n/a | `git diff fe6eb98a --name-only` = ingest.py, test_ingest.py, qa/manifests/ingest-fields.md only |
| C3 | the 3 ingest test files | 39 passed (bound tree, re-run) | regression criterion, n/a | n/a | n/a |
Copy was discarded unrestored-by-design (throwaway); the bound tree was never edited.

## Criteria
- C1 MET: labels become `InputField(name=label, label=label)` (ingest.py:142); `InputField` schema (schema/flowspec.py:41) accepts name+label with defaults; ingest_video no longer raises (test green, red when edit applied).
- C2 MET: `ObservedScreen.fields` untouched, no change under schema/, conversion lives only in `_to_screen`.
- C3 MET: 39 passed, existing ingest tests unchanged (diff of tests/test_ingest.py is purely additive: +1 import, +1 test).
- Invariants not broken: I1 (screen id still `content_id("scr", {name, signals})`, fields not in the id, so determinism and no invention are unchanged; conversion is 1:1 with observed labels, none added); I7 (`source_ref` and `url_pattern` lines untouched).
- 4c diff scope: one line replaced, docstring extended, one import extended; no function/class/test/config key deleted or renamed; all 3 changed files are listed in the manifest "What changed" (plus the manifest itself).

## Non-blocking notes (not FAIL)
- Wording: manifest line "(~L133-146)" is approximate; immaterial.
- Observation (suspicion, below 80 percent, not filed against this unit): src/autotester/ui/routes_product_map.py:38 and stages/product_map.py:41 treat `screen.fields` as strings/lists for a product-map screen type; I did not open or trace which Screen type they use, so it is not claimed as a defect.

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 2/2 relevant invariants (I1, I7) hold
TIER: S (one product function in one file plus its test; no L trigger in the diff)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 falsification rows reproduced (C1); C2/C3 are diff-scope and regression criteria with no edit row
LIVE-BROWSER: not-applicable (src/autotester/stages/ingest.py, tests/test_ingest.py; no UI path)
ISSUES-WRITTEN: ISS-ingest-fields-1 (fixed, regression_check = the new test node)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The one-line conversion in `_to_screen` fixes the real-video ValidationError; the new test is green on the fix and red with the exact pydantic type error when the line is reverted in an isolated copy. Lint and the 39 affected tests re-ran green, and doctor's 2 stale-generated violations reproduce identically on the base commit.
Metrics: start=2026-10-07T05:01:00Z end=2026-10-07T05:12:00Z wall_min=11 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
