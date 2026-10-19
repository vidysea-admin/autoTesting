# Manifest - crawl-redact-timestamp (T-136 live r5: a short numeric .env secret corrupted crawl timestamps and the crawl stayed running)

**Status:** ready-for-check
**Fix cycle:** 1 of max 2
**Repair base:** 6e94d128
**Contract:** qa/contracts/explore.md (X11), qa/contracts/core-invariants.md (redaction: no raw secret reaches disk); no contract edited
**Goal task:** T-136 (live run r5, `.work/t136-live-report-r5.md`)
**Dual check:** no
dual-waiver: small-security 0 lines; prior-dual qa/verdicts/crawl-redact-timestamp-A.md
Dual-check note (maker): cycle 0 was dual-checked (A and B PASS). The cycle-1 repair changes only tests/test_explore_replay.py (+4 lines, a test double); no product line in the security-triggered files changes, so security behaviour is unchanged.
**Persona walk:** skip (no UI surface)
**Issues addressed:** none (T-136 live defect)
**Executor:** claude-sonnet-subagent
**Base SHA:** ec151a35 (worktree .worktrees/crawl-redact-timestamp, branch wave/crawl-redact-timestamp)

## What changed
- `src/autotester/stages/explore_summary.py:34-66` - `scrubbed` (the one place a crawl model is masked for disk) used to run `Redactor.scrub_obj` over `model_dump(mode="json")`, so the digits `587` inside `created_at` (`...07.587000Z`) became `[REDACTED]:AUTOTESTER_SMTP_PORT` and `model_validate` raised (live crash at the old line 54, called from explore_node.py:85). Now `_scrub_text` (new) walks `model_dump(mode="python")` and runs `Redactor.scrub` on STRING values only: datetimes, numbers and Enum members are typed, not text (same rule as `core/trace.py::TraceWriter._scrub_value`, AT-1304). Strings under the minted keys `_MINTED` (ids, `crawl_id`/`node_id`/`from_node`/`to_node`/`discovered_by`/`approval_id`, and the str timestamps `started_at`/`finished_at`/`heartbeat_at`) are kept, because a digit run inside a system-minted id would split edge<->node joins. Every other string (names, selectors, reasons, urls, details) is still scrubbed.
- `src/autotester/stages/explore_summary.py:28` - new stop-reason code `crawl_error` (first in `_STOP_CODES`) for the tracked CrawlSummary.
- `src/autotester/stages/explore.py:279-290` - `run_crawl` wraps the walk: the old login/seed/bfs/terminal body moved unchanged into `_walk`; `except Exception` sets `rt.stop_reason = crash_reason(exc)` and `_finish(rt, ABORTED)`, so the stored crawl and its summary are terminal with the error recorded, never `running` (C3).
- `src/autotester/stages/explore_status.py` - new `crash_reason(exc)`; `_login_failed_reason` moved here verbatim as `login_failed_reason` (explore.py sat at the 300-line cap; now 295). Only caller updated (explore.py `_walk`).
- Redaction set NOT narrowed: `SecretStore.redactor()` still masks every .env value (AT-004) including `AUTOTESTER_SMTP_PORT`; no key was removed.
- Tests: `tests/test_crawl_redact_timestamp.py` (new, 5 tests).

## Fix cycle 1 (6c red)
Cause: the pre-push full suite (qa/verdicts/integration-6c-int1019-redact.md, int/1019 @ 0e0999a4) failed 4 nodes of tests/test_explore_replay.py with `AttributeError: '_Redactor' object has no attribute 'scrub'` at src/autotester/stages/explore_summary.py:69. The product call is right (core/redact.py `Redactor.scrub` :125 exists); the test double `_Redactor` (tests/test_explore_replay.py:84) implemented only `scrub_obj`. Fix: the double gains a pass-through `scrub(text) -> text` (tests/test_explore_replay.py:85-87). `grep "def scrub_obj" tests/` found no other double; the other `scrub_optional` fakes expose no `redactor()` and never reach `scrubbed`.
Round: 1 files, 1 criteria, est 5 min - one test-double method, 4 failing nodes plus the touched file
Repaired criterion: C1 (typed timestamps and minted ids survive a numeric secret end to end; the replay path runs `scrubbed` through the session Redactor)
Tests[C1-fix]: tests/test_explore_replay.py::test_a_replay_that_lands_off_domain_is_refused_and_recorded, ::test_the_off_domain_replay_refusal_is_recorded_as_an_edge_a_surface_can_show, ::test_a_refill_that_leaves_the_domain_is_caught_before_the_submit_is_clicked (whole file, 11 tests) + tests/test_crawl_redact_timestamp.py - the 4 reported red nodes and the file whose double was touched
Pre-check[C1-fix]: 74120f36 uv run pytest tests/test_explore_replay.py tests/test_crawl_redact_timestamp.py -> 16 passed t=39 blobs=tests/test_explore_replay.py (committed 74120f36)
Falsify[C1]: red@6e94d128 green@74120f36 - the 4 nodes (test_a_replay_that_lands_off_domain_is_refused_and_recorded[click], [fill], test_the_off_domain_replay_refusal_is_recorded_as_an_edge_a_surface_can_show, test_a_refill_that_leaves_the_domain_is_caught_before_the_submit_is_clicked) failed with the AttributeError on the unchanged head, pass after the fix
Metrics-cycle1: defects_6c=1

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L (security-adjacent: the redaction call site for everything a crawl persists changed)
Round: 4 files, 3 criteria, est 25 min - one scrub helper, one wrapper, one moved function
Owners: OG-EXPLORE
Base / checked state: ec151a35 / 0a6e02c2, clean tree
Gate answers: none apply (no gate touches crawl persistence redaction; no new src module)
Affected tests / full-suite trigger: no conftest or shared schema file changed; `explore_summary.scrubbed` callers are explore.py, explore_node.py, explore_incremental.py; `login_failed_reason` caller is explore.py. Builder ran no full suite; a wider explore/redaction set also ran green (215 passed incl. login-wall, coverage-bounds, login-bypass, test_core).
Tests[C1]: tests/test_crawl_redact_timestamp.py::test_smtp_port_587_in_env_appears_inside_a_crawl_timestamp, ::test_ids_that_contain_the_secret_digits_still_join, ::test_a_crawl_with_a_numeric_secret_in_every_timestamp_finishes; regression tests/test_approval_prod_gate.py::test_crawl_artifacts_mask_the_test_account_email - typed timestamps and minted ids survive a numeric secret, end to end through run_crawl
Tests[C2]: tests/test_crawl_redact_timestamp.py::test_free_text_still_masks_the_same_numeric_secret; regression tests/test_trace_numeric_secret.py, tests/test_approval_prod_gate.py, tests/test_approval_prod_gate_paths.py - free-text strings are still masked with the same numeric secret and the existing secret tests are unchanged and green
Tests[C3]: tests/test_crawl_redact_timestamp.py::test_a_crawl_that_raises_mid_run_ends_terminal_with_the_error_recorded; regression tests/test_explore_error_causes.py, tests/test_explore_node_recovery.py, tests/test_explore_blocked.py, tests/test_explore.py - an exception mid-walk leaves ABORTED with the error recorded and the existing crash/recovery paths still behave
Pre-check[C1]: 0a6e02c2 uv run pytest tests/test_crawl_redact_timestamp.py tests/test_trace_numeric_secret.py tests/test_approval_prod_gate.py tests/test_approval_prod_gate_paths.py -> 68 passed t=40 blobs=tests/test_crawl_redact_timestamp.py:ec28a09,tests/test_trace_numeric_secret.py:fbe03fd,tests/test_approval_prod_gate.py:9fb80d0,tests/test_approval_prod_gate_paths.py:59d7d83
Pre-check[C2]: 0a6e02c2 uv run pytest tests/test_crawl_redact_timestamp.py tests/test_trace_numeric_secret.py tests/test_approval_prod_gate.py tests/test_approval_prod_gate_paths.py -> 68 passed t=40 blobs=tests/test_crawl_redact_timestamp.py:ec28a09,tests/test_trace_numeric_secret.py:fbe03fd,tests/test_approval_prod_gate.py:9fb80d0,tests/test_approval_prod_gate_paths.py:59d7d83
Pre-check[C3]: 0a6e02c2 uv run pytest tests/test_crawl_redact_timestamp.py tests/test_explore_error_causes.py tests/test_explore_node_recovery.py tests/test_explore_blocked.py tests/test_explore.py -> 74 passed t=122 blobs=tests/test_crawl_redact_timestamp.py:ec28a09,tests/test_explore_error_causes.py:c22049f,tests/test_explore_node_recovery.py:fd148cd,tests/test_explore_blocked.py:8917304
Falsification[C1]: golden ::test_smtp_port_587_in_env_appears_inside_a_crawl_timestamp red@ec151a35 (pydantic ValidationError on ScreenEdge.created_at, input `2026-10-19T05:58:07.[RED...UTOTESTER_SMTP_PORT000Z`), green@0a6e02c2; copy-mutant in scratchpad crawl-redact-timestamp restoring the old `scrub_obj(model_dump(mode="json"))` body -> 5 failed (ValidationError at explore_summary.py:80 of the copy), restored control -> 5 passed
Falsification[C2]: copy-mutant in scratchpad crawl-redact-timestamp replacing `return value if key in _MINTED else redactor.scrub(value)` with `return value` (scrub nothing) -> 1 failed (::test_free_text_still_masks_the_same_numeric_secret), other 4 passed; restored control -> 5 passed
Falsification[C3]: copy-mutant in scratchpad crawl-redact-timestamp narrowing the guard `except Exception` to `except ZeroDivisionError` -> 1 failed (::test_a_crawl_that_raises_mid_run_ends_terminal_with_the_error_recorded, ValueError propagates), 4 passed; restored control -> 5 passed
Lint: 0a6e02c2 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> doctor: clean; explore.py 295 lines, explore_summary.py 103, explore_status.py 281 (all <= 300)
Metrics: start=2026-10-19T12:35Z end=2026-10-19T13:50Z wall_min=75 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 lane=normal check_s=162 mutants=3 defects_unit=0 defects_6c=1 tests=5 tests_min=1

## Residual risk and boundaries
- The `_MINTED` exemption means a secret equal to (or embedded in) an id or an ISO timestamp string would not be masked in those fields; ids are content hashes or ULIDs and timestamps are generated, never user text. `project` (slug) is deliberately NOT exempt.
- Enum members are not scrubbed (fixed vocabulary), as in `TraceWriter._scrub_value`; before this change a str-enum value was scrubbed after a JSON dump.
- Other persistence paths that scrub encoded JSON text (outside `explore_summary.scrubbed`) were not audited.
- The crash guard catches `Exception`, not `BaseException`; a KeyboardInterrupt still leaves a `running` crawl (the AT-483 heartbeat-stale display path covers that case). If `_finish` itself raises inside the guard, the exception propagates after the first `save_crawl`.
- AT-1304's numeric-secret rule for real secret text is unchanged: a short numeric secret still masks digit runs inside free-text strings (names, reasons, selectors).

## Live browser evidence
Not UI-touching - no surface changed (changed paths: src/autotester/stages/explore.py, explore_status.py, explore_summary.py, tests/test_crawl_redact_timestamp.py).

## Status: ready-for-check
