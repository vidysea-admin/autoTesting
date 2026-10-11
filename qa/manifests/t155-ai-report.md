# Manifest — t155-ai-report
**Contract:** qa/contracts/ai-target.md (AI9, AI10, AI11, AI12, AI13, AI14); also core-invariants C3/C5/C7 and report-export.md RE1/RE5 as the mechanisms AI12/AI14 cite
**Goal task:** T-155 (Track C5: unified AI test report grouped by tier with judge reason strings)
**Date:** 2026-10-11
**Fix cycle:** 0 of max 2
**Dual check:** no
**Issues addressed:** none (AT-840, AT-890, AT-892..AT-897 and AT-909..AT-918 touch inputs; none is fixed or re-statused here)
**Executor:** claude-sonnet-subagent
**Executor rationale:** single build unit with a full brief and contract criteria; fixtures only, no live call, no model call, no network.

## Base and dependencies
- Worktree `D:/autoTesting/.worktrees/t155-ai-report`, branch `wave/t155-ai-report`, cut from master `9c9a91f3`, which already contains T-153 (merged `349f3e97`) and T-154 (merged `bfec5567`). Read-only use of their models: `AiCapture`/`AiExchange` (`schema/ai_check.py`), `ProbeRun`/`ProbeRefusal` (`schema/ai_probe.py`), `AiCheckEntry`/`TIER_ORDER` (`schema/catalog.py`), `Verdict`/`Failure` (`schema/verdict.py`), `CaptureWithheld` (`stages/ai_capture.py`), `CHECK_TIER` (`stages/ai_catalog.py`). No T-153 or T-154 file is edited.
- Where the brief was stale: it was written before AI9-AI14 existed ("NOT DISPATCHABLE: no contract criterion"); the contract now has them (added 2026-10-11). It also said the t153 and t154 shapes were "not on master yet"; both are. Merged `ai_judge.judge_capture` returns an in-memory `Verdict` and persists nothing, as the brief expected.

## What changed
- src/autotester/stages/ai_report.py:1-233 (new, named by the contract as the stage file) — `export_ai_report(store, out, *, checks, redactor)`: reads stored evidence only, writes one workbook with sheets Summary, static, behavioural, adversarial (TIER_ORDER). Every cell passes `Redactor.scrub` and `clean_cell`; the joined text passes `Redactor.assert_clean` before the file is written (else `CaptureWithheld`, nothing written). It builds no verdict, calls no provider and opens no connection.
- src/autotester/core/excel.py — `clean_cell` (control-character stripping) moved here from `stages/crawl_report.py` so two exporters do not carry two copies (C3).
- src/autotester/stages/crawl_report.py — local `_ILLEGAL`/`_clean`/`import re` removed; imports `clean_cell as _clean`. Behaviour identical (`tests/test_crawl_report.py` 6 passed).
- tests/test_ai_report.py (new, 299 lines, 23 tests; the goal task's `done_check`).
- docs/MAP.md — regenerated with `uv run autotester map`.
- No schema file is added: rows are presentation (lists of strings), as in `crawl_report.py`.
- Product commit: b1ac3e409c951c0357c6b9465c1ffbe8ce260f0d. The manifest commit on top changes no product file.

## New modules (for owner/checker confirmation)
- `src/autotester/stages/ai_report.py`. Reason: the existing report homes are full (`report_export.py` is 300/300; `crawl_report.py` is the Track B5 crawl report) and AI12 names `stages/ai_report*.py`. `qa/gates/new-module-authorization.md` was answered for AT-710 only; this module needs a checker or owner acknowledgement.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: M (multi-file behaviour: a new shared report stage reading shared schemas, plus a one-hunk move of a helper into `core/excel.py` used by a second exporter)
Dual check: no. No trigger applies: the diff changes no secret handling (it only calls the existing `Redactor.scrub` and `assert_clean`), no auth, no tenancy and no production write; it reads local files and writes one named workbook.
Persona walk: skip (an exported workbook built from stored evidence; no route, template, CLI command or browser step is added or changed)
Round cap: seam = the stored-evidence layout and workbook shape of `stages/ai_report.py` (reader for `projects/<slug>/ai/{behavioural,adversarial}/`); non-security seam, the 2-PASS cap applies
Affected tests: `tests/test_ai_report.py` (new), `tests/test_crawl_report.py` (regression guard, `crawl_report.py` edited). `tests/test_cli_advice_resolves.py` was not needed: no CLI command and no advice string is added.
Pre-check[AI9]: b1ac3e409c951c0357c6b9465c1ffbe8ce260f0d uv run pytest -p no:xdist tests/test_ai_report.py -k ai9 -> 4 passed (three tier sheets in TIER_ORDER with runnable counts; empty tier present at 0; no-results statement; checks with no stored result read NOT RUN)
Pre-check[AI10]: b1ac3e409c951c0357c6b9465c1ffbe8ce260f0d uv run pytest -p no:xdist tests/test_ai_report.py -k ai10 -> 7 passed (all 6 BlockedReason values render BLOCKED with value and action; not-applicable is its own status)
Pre-check[AI11]: b1ac3e409c951c0357c6b9465c1ffbe8ce260f0d uv run pytest -p no:xdist tests/test_ai_report.py -k ai11 -> 3 passed (failure criterion, reason, fix_hint and note verbatim; rule row labelled computed, other judge labelled by provider; capture with no verdict labelled)
Pre-check[AI12]: b1ac3e409c951c0357c6b9465c1ffbe8ce260f0d uv run pytest -p no:xdist tests/test_ai_report.py -k ai12 -> 2 passed (socket connect and Provider.judge patched to raise, never hit; only out/ai.xlsx created; two builds equal; no verdict-construction text in the stage)
Pre-check[AI13]: b1ac3e409c951c0357c6b9465c1ffbe8ce260f0d uv run pytest -p no:xdist tests/test_ai_report.py -k ai13 -> 4 passed (two refusal lines give two rows and no probe text; missing, empty and malformed logs each distinct; a run record is shown NOT JUDGED)
Pre-check[AI14]: b1ac3e409c951c0357c6b9465c1ffbe8ce260f0d uv run pytest -p no:xdist tests/test_ai_report.py -k ai14 -> 3 passed (planted secret in a capture response, a judge reason and a refusal reason is masked in every cell; scripts/check_no_secrets.py exits 0 on the output with the key in .env; autosize_columns called once per sheet, 4 sheets)
Pre-check: b1ac3e409c951c0357c6b9465c1ffbe8ce260f0d uv run pytest -p no:xdist tests/test_ai_report.py tests/test_crawl_report.py -> 29 passed t=6 blobs=tests/test_ai_report.py,src/autotester/stages/ai_report.py   (aggregate line for the lint: tick.mjs CRIT_RE only recognises C<n> ids, so it cannot see the tagged AI lines above)
Falsify[AI9]: tests/test_ai_report.py::test_ai9_empty_tier_is_present_and_says_zero, test_ai9_no_results_says_so, test_ai9_checks_without_stored_results_are_not_health: see Capability coverage (green before, red after; throwaway copy)
Falsify[AI10]: tests/test_ai_report.py -k ai10: see Capability coverage
Falsify[AI11]: tests/test_ai_report.py::test_ai11_every_failure_string_verbatim: see Capability coverage
Falsify[AI12]: tests/test_ai_report.py::test_ai12_read_only_deterministic_and_no_model_or_network, test_ai12_stage_constructs_no_verdict: see Capability coverage
Falsify[AI13]: tests/test_ai_report.py::test_ai13_two_refusals_two_rows_no_probe_text, test_ai13_missing_and_empty_logs_have_distinct_statements: see Capability coverage
Falsify[AI14]: tests/test_ai_report.py::test_ai14_planted_secret_never_reaches_a_cell, test_ai14_autosize_columns_is_the_shared_helper: see Capability coverage
Metrics: start=2026-10-11T00:00Z end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=10 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=10 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest -p no:xdist tests/test_ai_report.py` -> 23 passed
- `uv run pytest -p no:xdist tests/test_crawl_report.py` -> 6 passed (regression guard)
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> doctor: clean (this worktree; MAP regenerated)
- `grep -nE "Verdict\(" src/autotester/stages/ai_report.py` -> no output

## Capability coverage (each criterion -> its isolating falsification)
Throwaway copy of `src/ tests/ scripts/ pyproject.toml` under the scratchpad (outside the worktree), `PYTHONPATH` pointed at the copy, one fresh copy per mutation, anchor asserted unique, source asserted changed. Script (scratchpad `t155/fals.py`) and copy are discarded.

| Criterion | falsifying edit in `stages/ai_report.py` | observed |
|---|---|---|
| AI9 (empty tier) | the behavioural sheet is skipped when no behavioural check exists | `test_ai9_empty_tier...`: 1 passed before, 1 failed after |
| AI9 (no results) | the "No AI results are stored" statement replaced by "All clear" | 2 passed before, 2 failed after |
| AI10 | blocked row status `BLOCKED` -> `PASS` | `-k ai10`: 7 passed before, 6 failed after (all 6 BlockedReason cases) |
| AI11 | failure reason truncated to 8 characters | `-k ai11`: 3 passed before, 1 failed after on the verbatim test |
| AI12 (read-only) | a second file written beside the workbook | 1 passed before, 1 failed after |
| AI12 (no verdict) | the text of a verdict construction added to the module | 1 passed before, 1 failed after |
| AI13 (rows) | refusal reason cell emptied | 1 passed before, 1 failed after |
| AI13 (statements) | the empty-log statement changed to the missing-log text | 1 passed before, 1 failed after |
| AI14 (secret) | `redactor.scrub` removed from the cell path and the `assert_clean` gate removed | 1 passed before, 1 failed after on the planted secret |
| AI14 (helper) | `autosize_columns(ws)` replaced by `pass` | 1 passed before, 1 failed after |

All reds are assertion failures. 10 mutations, 10 red.

## Held on an owner answer (built what does not depend on it; nothing guessed)
- Open product choice (1) in `ai-target.md`: where behavioural captures and their verdicts are stored, and which unit writes them. AI9-AI14 hold wherever they are stored; the reader assumes `projects/<slug>/ai/behavioural/<id>/capture.json` (`AiCapture`) and `verdict.json` (`Verdict`) beside the T-154 layout `ai/adversarial/<run_id>/run.json` and `ai/adversarial/refusals.jsonl`. **Nothing writes the behavioural layout today** (T-153's capturer and judge persist nothing), so a real project's report shows NOT RUN until a writer exists. Answer needed: confirm that layout and name the unit that writes it.
- Open product choice (2): no HTML, CLI command or UI page is built; only the workbook the contract requires. A caller must today pass the `AiCheckEntry` list (from `ai_catalog.match`), because the catalog is not persisted.
- The adversarial tier shows stored runs as NOT JUDGED: no adversarial judge exists, so the report invents no verdict (AI12).

## Open items for the checker (honest list)
- New module `stages/ai_report.py` needs acknowledgement (see New modules).
- `core/excel.py::clean_cell` is a shared-file change (moved from `crawl_report.py`); `tests/test_crawl_report.py` is the guard.
- Unreadable `capture.json` or `run.json` render as UNREADABLE rows and a malformed refusal line is named by number, never dropped; raw file content is never echoed.
- AT-840 and AT-890 (PII masking toward a model) are out of scope: this stage calls no model, and only `Redactor` secret masking applies to cells.

Status: ready-for-check
