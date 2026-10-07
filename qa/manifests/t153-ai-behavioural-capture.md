# Manifest — t153-ai-behavioural-capture
**Contract:** qa/contracts/ai-target.md (AI6, AI7 bind T-153) · core-invariants C5, C7 · D-018 (consent gate) · D-017
**Goal task:** T-153 (dep T-152, built on the previous commit of this branch; criticality high, user_value high)
**Date:** 2026-10-07
**Fix cycle:** 0
**Dual check:** required   <!-- C5 secret boundary and an outward-facing endpoint run behind the D-018 approval gate -->
**Persona walk:** skip (backend-only: no human screen)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent (maker, worktree .worktrees/t152-153, branch t152-153)
**Relitigation:** `uv run autotester ledger relitigation "T-153 ..."` → "no gate — no retired features (rule)". No HUMAN_GATE.

## What changed
- `src/autotester/schema/ai_check.py` (edited in place, 31 → 70) — adds `AiReply` (what the transport seam returns), `AiExchange` (prompt, scrubbed response, status, latency, tools, hand-offs, `is_json`, `missing_keys`, `error` type name) and `AiCapture` (Artifact; check, endpoint, exchanges, `unsent_prompts`). All `extra="forbid"`. None has a result, verdict, pass or score field (asserted).
- `src/autotester/stages/ai_capture.py` (new, 106) — `capture_run(...)`: the observer. Gates in order, all before a byte is sent: a signed matching `RunApproval` of kind `LIVE_CASE` for the exact endpoint (`core.consent.require_approval`, D-018), then no raw secret in any prompt. Then records each exchange (latency by an injected clock, JSON-parse fact, absent expected keys), stops at the wall clock and says how many prompts went unsent, records a transport failure as the exception type name only, scrubs every stored string and finally asserts the whole capture clean (`CaptureWithheld` otherwise). It contains no `Result.`/`Verdict(` and imports nothing from grade.
- `src/autotester/stages/ai_judge.py` (new, 174) — `judge_capture(...)`: the judge side of C7. Re-scrubs the capture and the reference and asserts clean before anything is built. COMPUTED checks (`ai_catalog.CHECK_METHOD`: response shape, latency) get a rule `Verdict` (`grader_provider="rule"`) from the recorded facts, no model. JUDGED checks (ground truth, tool use, hand-offs) become a `RawResult` plus a literal `Rubric` and go, unmodified, to `stages/grade.py::grade`. An empty capture is INCONCLUSIVE; an all-errored capture is an ERRORED `RawResult`, which `grade` turns into INCONCLUSIVE without calling a judge.
- `tests/test_ai_capture.py` (new, 20 cases, 274 lines).
- `docs/MAP.md` regenerated.
Reasons for the new modules: D-017 names `stages/ai_capture.py`; `ai_judge.py` is the judgement-side glue because contract AI6 forbids any Verdict in `ai_capture.py` and `grade.py` (212 lines) judges a `RawResult`, it does not map captures. The function is `capture_run`, not `capture`, because `explore_node.capture` already exists (doctor `duplicate-concept`).

Decisions the checker should look at (each is my assumption, not a gate):
1. **[ASSUMPTION] Approval kind.** A capture is an outward-facing run, so it takes the D-018 gate. I used `ApprovalKind.LIVE_CASE` with `target` = the exact endpoint, `actions` = number of prompts, `wall_clock_s` = the bound. `ADVERSARIAL` is wrong (that is T-154), `CRAWL` is wrong. `LIVE_CASE` is in `ACCOUNT_KINDS` (D-068), so an account-derived grant could cover it; whether that is intended for AI endpoints is Umesh's call.
2. **No HTTP client is shipped.** The transport is an injected `send(endpoint, prompt) -> AiReply`. How an AI endpoint authenticates (header, key, which `SecretRef`) is not decided by any contract, so a real sender would be a guess. Tests drive a fake sender. Wiring a real one is the next unit, and it needs that answer.
3. **Computed checks are decided in `ai_judge.py`, not in the capturer.** "Latency/schema computed in code, not judged" is met (no model), and C7/AI6 is met (the capturer records `latency_s`, `is_json`, `missing_keys` as observations and compares nothing against a budget).
4. **Evidence travels inline.** `grade._render_evidence` prints only `[kind] path` for non-screenshots, so the response text is carried as the literal `path` of a `NETWORK` evidence row (the schema permits a literal value). Filenames would have left the judge blind.
5. The rubric criteria are literals in `ai_judge.py` (`_CRITERIA`); the judge prompt itself is the existing `skills/grade/SKILL.md`, so no new prompt file and no new provider hunk.
6. `AiCapture` is not persisted by this unit (no store write, so no `.gitignore` change under `projects/*/ai/` yet); persistence belongs with the report unit.
7. A raw secret *in a prompt* is refused (nothing sent); a raw secret *in a response or reference* is masked, and only a surviving encoded form withholds the capture. That is the existing `scrub` then `assert_clean` contract used by `discover.py`.

## Verification scope
Policy-Version: proportional-verification/2026-10-07.7
Tier: L (outward-facing endpoint run behind a consent gate, and the C5 secret boundary on text bound for a model)
Base SHA: the T-152 commit on this branch (parent of this one); branch base 3adc00d8 (origin/master, T-125 merged)
Gate answers: none required (no dependency, prompt file or provider hunk added; `qa/gates/t151-dependency-authorization.md` is T-151's).
Affected tests: `tests/test_ai_capture.py` (20), `tests/test_ai_catalog.py` (28), `tests/test_schema.py`, `tests/test_discover.py`, `tests/test_grade.py` (the last three read modules this unit imports). No full suite (suite_runs=0).
Metrics: start=2026-10-07 end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=16 cycle=0 resumes=0 tokens=unavailable policy=2026-10-07.7

## How to verify (commands + expected)
- `uv run pytest tests/test_ai_capture.py -m "not harness"` → 20 passed
- `uv run pytest tests/test_ai_capture.py tests/test_ai_catalog.py tests/test_schema.py tests/test_discover.py tests/test_grade.py -m "not harness"` → 142 passed
- `uv run ruff check src tests scripts` → All checks passed
- `uv run autotester doctor` → one violation, `ledger-row-missing: T-125`, present on base 3adc00d8 and not in this diff; nothing else
- `grep -nE "Result\.|Verdict\(" src/autotester/stages/ai_capture.py` → no output (exit 1), the AI6 Verify

## Capability coverage and falsification
Each row: a throwaway copy outside the worktree, baseline asserted green (20 passed), one anchored single-hunk mutation (anchor counted exactly once, file changed, the copy's own `autotester` import path asserted), the run, the failing node attributed by name, then restore (20 passed). One earlier attempt (a mutation that was a syntax error) came back `UNATTRIBUTED — 1 error`; it was discarded and redone as a valid mutation, which is the row marked †.

| Criterion | claim | defending test | the falsifying edit | mutant result |
|---|---|---|---|---|
| AI6 | a JUDGED verdict comes from `grade()` | `test_the_judged_verdict_comes_from_the_judge_not_the_capture`, `test_the_capture_is_handed_to_grade_unmodified` | `return grade(...)` → `return _rule_verdict(...)` | 5 failed, both named |
| AI6 | the capture reaches `grade()` unmodified | `test_the_capture_is_handed_to_grade_unmodified` | `evidence=_evidence(cap)` → `evidence=[]` | 2 failed, named |
| AI6 | the capturer names no Verdict/Result constructor | `test_capturer_source_never_constructs_a_verdict_or_result` | `_BAD = ("Verdict(",)` added to `ai_capture.py` † | 1 failed, named (textual, as the contract's own Verify is a grep) |
| AI7 | judge side re-scrubs a hand-built capture | `test_a_hand_built_capture_is_scrubbed_again_at_the_judge`, `..._with_an_encoded_secret_never_reaches_the_judge` | `clean = _scrubbed(cap, redactor)` → `clean = cap` | 2 failed, both named |
| AI7 | judge side asserts clean (encoded form) | `test_a_hand_built_capture_with_an_encoded_secret_never_reaches_the_judge` | `redactor.assert_clean(text)` → `pass` | 1 failed, named |
| AI7 | a secret in the target response never reaches the judge prompt | `test_a_secret_in_the_target_response_never_reaches_the_judge_prompt`, `test_capture_records_facts_latency_and_scrubs_every_field` | `response=redactor.scrub(text)` → `response=text` | 2 failed, both named |
| AI7 | capture withholds an encoded secret | `test_an_encoded_secret_surviving_the_scrub_withholds_the_capture` | final `redactor.assert_clean(...)` → `pass` | 1 failed, named |
| AI7 | a transport error message is never stored | `test_a_send_failure_is_recorded_not_raised_and_names_no_value` | `type(exc).__name__` → `str(exc)` | 1 failed, named |
| D-018 | nothing is sent without a covering approval | `test_no_matching_approval_means_nothing_is_sent` | `require_approval(...)` call neutered | 1 failed, named |
| C5 | a raw secret in a prompt is never sent | `test_a_raw_secret_in_a_prompt_is_never_sent_to_the_endpoint` | `if not redactor.is_clean(prompt):` → `if False:` | 1 failed, named |
| T-153 note | computed checks never call a model | `test_response_shape_is_computed_from_recorded_facts`, `test_latency_is_computed_against_the_budget_in_code` | `if CHECK_METHOD[...] is COMPUTED:` → `if False:` | 3 failed, both named |
| T-153 note | latency is judged in code against the budget | `test_latency_is_computed_against_the_budget_in_code` | `ex.latency_s > budget` → `> budget * 100` | 1 failed, named |
| T-153 note | schema: absent expected keys fail | `test_response_shape_is_computed_from_recorded_facts` | `elif ex.missing_keys:` → `elif False:` | 1 failed, named |
| bound | the wall clock stops a capture and reports unsent prompts | `test_wall_clock_stops_the_capture_and_says_how_many_prompts_went_unsent` | `>= wall_clock_s` → `>= 10**9` | 1 failed, named |
| honesty | an all-errored capture never reaches the judge | `test_an_errored_capture_never_reaches_the_judge` | `if not cap.exchanges or len(errors) == ...` → `if not cap.exchanges` | 1 failed, named |
| honesty | an empty capture is INCONCLUSIVE, never PASS | `test_an_empty_capture_is_inconclusive_never_a_pass` | `if not cap.exchanges:` (rule verdict) → `if False:` | 1 failed, named |

## Live browser evidence
Not UI-touching: no page or route changed (`schema/ai_check.py`, `stages/ai_capture.py`, `stages/ai_judge.py`, one test file, `docs/MAP.md`). No live endpoint or model was called; the judge in tests is `MockProvider`.

## Not done / handed on
- No real HTTP sender and no endpoint-credential rule (item 2 above): open question for Umesh/checker before a live capture is wired.
- Nothing calls `capture_run` / `judge_capture` yet (CLI, UI and report belong to T-155).
- No `docs/ARCHITECTURE.md` row (file at its 150-line cap), no `.goal/goal.json` or ledger edit.

## Status: ready-for-check
