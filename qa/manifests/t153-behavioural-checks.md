# Manifest — t153-behavioural-checks
**Contract:** qa/contracts/ai-target.md (AI6, AI7); also judged: core-invariants.md C1-C5, C7, C12; consent.md CN1/CN5/CN6; grade.md G1-G6
**Goal task:** T-153 (Track C3: behavioural AI capture, judge mapping, scrub boundary)
**Date:** 2026-10-11
**Fix cycle:** 0 of max 2
**Dual check:** required
**Persona walk:** skip (backend-only: no human screen; the capture, judge and consent gate are called from code and tests, no route, template, CLI command or browser step is added)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Executor rationale:** re-land of already-written, already-reviewed product code (codex/t153-completion 544b95ce + b0abd1d7) as one clean unit on a fresh branch from master; no new design.

## What changed
- src/autotester/schema/ai_check.py:1-72 — `AiReply`, `AiExchange`, `AiCapture` strict models added; `AiExchange.latency_s` is `Field(ge=0, allow_inf_nan=False)` with no default (C12(b)).
- src/autotester/stages/ai_capture.py:1-112 (new) — `capture_run` records facts only; secret admission (`assert_clean`, :92) and signed consent (`require_approval`, :95) before any send; no `grade` import, no `Verdict`/`Result` (AI6, AI7).
- src/autotester/stages/ai_judge.py:1-201 (new, un-gated module; see Gate answers) — maps a capture to `RawResult` + `Rubric`, re-scrubs and re-checks at the judge side, delegates to the real `grade()`; COMPUTED checks use a private `_ComputedJudge` so `grade()` alone creates the `Verdict`.
- src/autotester/stages/grade.py:101-113 — optional `redactor` applied to the final prompt (`_withheld`).
- tests/test_ai_capture.py (new, 300 lines), tests/test_approval_signing.py (+2 capture-bound tests), tests/test_grade_evidence.py (+AI cases) — additions only.
- docs/MAP.md — regenerated with `uv run autotester map` (last change).
- Product commit: ff901f721d17a1b2d7a109526f8444e485920965 (the two Codex product commits, cherry-picked `-n`, manifest and MAP dropped). T-154 branches from this sha.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (security: secrets are admitted or refused before any byte is sent, and the consent gate is called at the capture seam)
dual-trigger: security src/autotester/stages/ai_capture.py:92 (secret admission `assert_clean` before transport, C5); also src/autotester/stages/ai_capture.py:95 (`require_approval`, signed consent, D-018)
Base / checked state: base master 3a16616cf2c99a63c8d763150a1ca6410dfc0acc (master has since moved to 354bd31f by contract/qa-only commits; `src/`, `tests/` and `docs/MAP.md` are identical between the two); product code at ff901f72; the manifest + MAP commit sits on top and changes no product file.
Gate answers: none open for T-153. qa/gates/t151-dependency-authorization.md:20 "Answered: 2026-10-07T01:34:13Z — A — chat (Umesh): approve all three" (T-151 only; T-153 adds no dependency). qa/gates/d081-run-approvals.md "Answered: 2026-10-10 - A (full approval; maker mints per-run rows) - D-081" (T-153 sends no real request). New module `stages/ai_judge.py` is named in no D-017 line or gate; reason: AI6 forbids a Verdict in `ai_capture.py` and `grade.py` cannot map captures. Un-gated, flagged for the checker/owner.
Affected tests / full-suite trigger: tests/test_ai_capture.py, tests/test_grade_evidence.py, tests/test_approval_signing.py, plus closure tests/test_ai_catalog.py, tests/test_grade.py, tests/test_schema.py (all passed, see Actual outputs). Security-L unit: the full suite is the checker's single LAST release step, not the builder's. Safe-fallback triggers: none. `land-integrate-combined` edits `core/redact.py`; if it lands first re-run tests/test_ai_capture.py.
Pre-check[AI6]: ff901f721d17a1b2d7a109526f8444e485920965 uv run pytest tests/test_ai_capture.py tests/test_grade_evidence.py -> 112 passed (77 + 35; includes test_capturer_source_never_constructs_a_verdict_or_result, test_the_capture_is_handed_to_grade_unmodified, test_the_judged_verdict_comes_from_the_judge_not_the_capture, test_module_exposes_no_second_grading_path) and the contract grep for Result./Verdict( in ai_capture.py returns nothing (exit 1) t=35 blobs=tests/test_ai_capture.py:4fd639e,tests/test_grade_evidence.py:2af58c0
Pre-check[AI7]: ff901f721d17a1b2d7a109526f8444e485920965 uv run pytest tests/test_ai_capture.py tests/test_grade_evidence.py tests/test_approval_signing.py -> 130 passed (77 + 35 + 18; includes test_a_secret_in_the_target_response_never_reaches_the_judge_prompt, test_a_raw_secret_in_a_prompt_is_never_sent_to_the_endpoint, test_ai_computed_grade_enforces_the_final_prompt_redactor) t=47 blobs=tests/test_ai_capture.py:4fd639e,tests/test_grade_evidence.py:2af58c0,tests/test_approval_signing.py:709601f
Falsify[AI6]: tests/test_ai_capture.py::test_capturer_source_never_constructs_a_verdict_or_result — see Capability coverage (green before, red after, restored; throwaway copy)
Metrics: start=2026-10-11T00:00Z end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=60 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=4 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_ai_capture.py` → 77 passed
- `uv run pytest tests/test_grade_evidence.py` → 35 passed
- `uv run pytest tests/test_approval_signing.py` → 18 passed
- `uv run pytest tests/test_ai_catalog.py`, `tests/test_grade.py`, `tests/test_schema.py` (one process each) → 28, 13, 18 passed
- `uv run ruff check src tests scripts` → All checks passed!
- `uv run autotester doctor` → only `stale-generated: docs/SNAPSHOT.md` (pre-existing: the SNAPSHOT lags the decisions log, D-081, not touched by this unit); no design-rule violation, MAP current
- `grep -n "Result\.\|Verdict(" src/autotester/stages/ai_capture.py` → no output, exit 1

## Actual outputs (from maker's own run)
Run on product sha ff901f72, one pytest process at a time, RAM-ceiling gate (`tick.mjs --ceilings`) waited out first (cap 0 for ~60 min, then cap=2):
```
tests/test_ai_capture.py       77 passed in 2.28s
tests/test_grade_evidence.py   35 passed in 2.44s
tests/test_approval_signing.py 18 passed in 5.57s
tests/test_ai_catalog.py       28 passed in 0.84s
tests/test_grade.py            13 passed in 0.76s
tests/test_schema.py           18 passed in 0.41s
ruff: All checks passed!
```
Line counts: ai_capture.py 112, ai_judge.py 201, grade.py 216, schema/ai_check.py 72, tests at 300 (cap). Brief said grade.py 221 and test_grade_evidence ~300 → actual 216 and 300.

## Capability coverage (each new claim -> its isolating falsification)
Done in a throwaway copy (`git archive HEAD` extracted outside the worktree, PYTHONPATH pointed at the copy), anchor asserted unique, changed-bytes asserted, restored byte-exact. Script: scratchpad `falsify.py` (copied with the run).

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| AI6 | the capturer builds no Verdict/Result and never grades | tests/test_ai_capture.py::test_capturer_source_never_constructs_a_verdict_or_result | ai_capture.py: add `_X = "Verdict(" ` after the `Send = ...` line | before `1 passed`; after `1 failed` on `assert not <re.Match ... match='Verdict('>`; restored `1 passed` |
| AI7 (final grade) | the final prompt is scrubbed/refused before grade sends it | tests/test_grade_evidence.py::test_ai_computed_grade_enforces_the_final_prompt_redactor | grade.py `_withheld`: `redactor.assert_clean(prompt)` -> `pass` | before `1 passed`; after `1 failed` on `assert (Result.PASS is Result.BLOCKED)`; restored `1 passed` |
| AI7 (judge side) | a hand-built capture is re-scrubbed at the judge | tests/test_ai_capture.py::test_a_hand_built_capture_is_scrubbed_again_at_the_judge | ai_judge.py `judge_capture`: `clean = _scrubbed(cap, redactor)` -> `clean = cap` | before `3 passed`; after `3 failed` (IndexError: no judge prompt reached the stub, i.e. the red is the missing-scrub path, not a parse/import error); restored `3 passed` |
| C12(b) | an unmeasured latency has no zero default | tests/test_ai_capture.py::test_capture_carries_no_judgement_field | schema/ai_check.py: `Field(ge=0, ...)` -> `Field(0.0, ge=0, ...)` | before `1 passed`; after `1 failed` `DID NOT RAISE ValueError`; restored `1 passed` |

## Live browser evidence
Not UI-touching — no surface changed. Changed paths: src/autotester/schema/ai_check.py, src/autotester/stages/ai_capture.py, src/autotester/stages/ai_judge.py, src/autotester/stages/grade.py, tests/*, docs/MAP.md.

## Open items for the checker (honest list)
- `ApprovalKind.LIVE_CASE` for a behavioural capture (ai_capture.py:95) is an `[ASSUMPTION]`; ADVERSARIAL belongs to T-154.
- No real HTTP sender exists or is in scope; transport is an injected `send(endpoint, prompt) -> AiReply`. Nothing is persisted (T-154/T-155).
- `stages/ai_judge.py` is a new un-gated module (reason above).
- The AI7 final-grade floor and the security/full-suite integration run are the two things the previous cycle's checkers could not complete; the builder pre-check above covers the floor in a copy, the checker owns the persisted one and the single last full suite.
- Pre-check shas name the product commit ff901f72; the manifest/MAP commit on top changes no product file.

## Status: ready-for-check
