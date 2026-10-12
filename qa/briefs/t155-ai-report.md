# Brief — t155-ai-report (T-155, Track C5)

Written 2026-10-11 by a readiness pass (read-only; no build, no test, no browser). Measured against `master` 3a16616cf2c99a63c8d763150a1ca6410dfc0acc. Re-read `git -C D:/autoTesting rev-parse master` before use.

# NOT DISPATCHABLE: no contract criterion exists for T-155

I searched every file in `qa/contracts/` for T-155, a Track C report, an AI-test report or a tier-grouped AI report. None defines acceptance criteria for it:
- `qa/contracts/ai-target.md` states "Covers: goal tasks T-151 (AI1-AI3...), T-152 (AI4...), T-153 (AI5-AI6...), and AI7"; AI1-AI8 stop at the capture and judge boundary. It has no report criterion.
- `qa/contracts/adversarial.md` header says it covers "T-154 ... and T-155 (its report — AD7's audit trail feeds it)", but AD1-AD7 constrain the adversarial runner only. AD7 is the only line that mentions the report, as a data source. Its no-fire list also records that `docs/spec.md` R30 stops at T-153 and T-155 has no requirement row (`ISS-t150-1`).
- `qa/contracts/report-export.md` (RE1-RE6) governs the run reports (`stages/report_export.py`); it does not mention Track C.
- `qa/contracts/catalog.md` CT6/CT8 bind the web catalog page and run trigger (`ui/routes_runs.py`), not an AI report.
- `qa/feedback-inbox.md` holds no T-155 criteria (the only T-155 mentions are the 2026-09-27 AD1-AD7 filing's scope note and the T-168 dependency-drop note).

The only acceptance text is the goal task (`.goal/goal.json` T-155): title "Track C5: unified AI test report grouped by tier with judge reason strings"; `done_check` `uv run pytest tests/test_ai_report.py`; note "Reuses core/excel.py autosize_columns. Blocked checks appear as blocked with a reason, never as passes." A goal note is not a checker-owned criterion, and the maker never writes a contract. Per the dispatch rule, a builder must not be sent until the checker files criteria (maker feedback goes verbatim to `qa/feedback-inbox.md`; the checker folds it into `ai-target.md` or `adversarial.md`).

Everything below is the rest of the brief, written so it can be dispatched the moment criteria exist. Section 3 carries the criteria the checker is asked to consider; they are proposals, not contract text.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier M.** Trigger: multi-file behaviour that reads shared schemas (`AiCapture`, `Verdict`, `AiCheckEntry`, the adversarial run record) and adds a shared report module. No security, auth, tenancy, write, migration, concurrency, config or dependency trigger (it only reads stored evidence; no network, no model call).
- **Dual check: no.** A secret-leak risk exists in any report (C5/RE5), but there is no `security|auth|tenancy|prod-write <path:line>` trigger in code this unit adds; the leak property is covered by a normal C5 test plus `scripts/check_no_secrets.py`.
- goal.json criticality: `low`, `user_value: normal`.

## 2. Root and base

- Root `D:/autoTesting`. Base = current `master`.
- Branch: a fresh `wave/t155-ai-report`, cut after `wave/t154-adversarial-pass` has a stable run-record schema (the report reads it). No existing branch or worktree carries any T-155 work (searched `git branch -a` and `git worktree list`).
- goal.json dependency is T-154 (which depends on T-153). T-155 could start earlier for the static and behavioural tiers on top of t153, but the third tier (adversarial) and the refusal rows need t154's record shape, so keep the stated order.

## 3. Acceptance criteria

**None exist (see top).** Proposed for the checker to adopt, amend or reject; each is grounded in text already on disk:

- P1, tier grouping: the report groups results by `Tier` in `TIER_ORDER` (static, behavioural, adversarial; `src/autotester/schema/catalog.py:43`) and shows each tier's runnable count including zero, in the spirit of `catalog.md` CT6 (cheap tiers first, empty tier shown as 0, never omitted). Source: goal title.
- P2, blocked honesty: a blocked check renders as BLOCKED with its reason and the one action that clears it, never as a pass or a blank (`AiCheckEntry.blocked_reason` and `unblock_action`, `schema/catalog.py:120-141`; `ai-target.md` AI5; `catalog.md` CT8's "reason and action, not merely the enum value"). Source: goal note.
- P3, judge reason strings: every judged row carries the judge's own `Failure.reason` (and `fix_hint` when present) and `Verdict.note`, verbatim (`schema/verdict.py:54-62`, `:79-91`), plus `grader_provider` so a computed rule verdict (`"rule"`) is distinguishable from a model-judged one. Source: goal title; `report-export.md` RE6 as precedent.
- P4, no recomputation: the report is read-only presentation over stored evidence and invents no result (`report-export.md` RE1).
- P5, adversarial audit trail: refused adversarial attempts from `projects/<slug>/ai/adversarial/refusals.jsonl` appear in the report (AD7's stated purpose: "T-155 ... needs a record of refused attempts to be a unified report"), with no probe content.
- P6, no secret reaches the file: `report-export.md` RE5 applied to the new exporter (`scripts/check_no_secrets.py` passes on the output; `Redactor.scrub` on every cell).
- P7, reuse: column sizing through `core/excel.py::autosize_columns` (`src/autotester/core/excel.py:15`), not a second implementation (goal note; C3).

## 4. What exists and what is missing

Exists on master:
- `src/autotester/core/excel.py:15` `autosize_columns`, used by `stages/crawl_report.py` (8 call sites) and `stages/issues.py:28`.
- `src/autotester/stages/report_export.py` (300 lines, at the cap): the run Excel/HTML exporter, `valid_runs_newest_first:38`, imports `autosize_columns`, `Redactor`, `Verdict`.
- `src/autotester/stages/crawl_report.py` (243 lines): the precedent for a sibling exporter (Excel, multi-sheet, `export_crawl_excel`), CLI `report crawl` in `src/autotester/cli_crawl.py:287` (that file is 300 lines, at the cap).
- `src/autotester/schema/catalog.py:120` `AiCheckEntry` (kind, tier, method, applicable, runnable, blocked_reason, unblock_action) and `Catalog.ai_checks`; `stages/ai_catalog.py` `match()`, `CHECK_TIER`, `CHECK_METHOD`.
- `src/autotester/schema/verdict.py` `Verdict`, `Failure(criterion_id, reason, evidence_refs, fix_hint)`.

From t153/t154 (not on master yet): `AiCapture`/`AiExchange` (`schema/ai_check.py`), `judge_capture` returning grade-owned `Verdict`s (`stages/ai_judge.py`), and the adversarial run record and `refusals.jsonl` (t154).

Missing: any module that assembles these into a report; a persisted store for captures and verdicts (neither t153 nor t154 persists behavioural results: t153's manifest says "persistence belongs with the report unit"; t154 persists only adversarial runs). Decision needed (open question below): where behavioural captures and verdicts are stored (`projects/<slug>/ai/...` is the layout t154 starts) and who writes them. The report format (Excel only, HTML, or both) is also undecided: the goal note names only the Excel helper.

## 5. Files the builder will touch

Names are proposals; the repo does not fix them.

| File | New or existing | Lines |
|---|---|---|
| `src/autotester/stages/ai_report.py` | new (a split module is required: `report_export.py` is 300/300 and `crawl_report.py` is the sibling precedent) | n/a, <= 300 |
| `tests/test_ai_report.py` | new (named by the done_check) | n/a, <= 300 |
| `src/autotester/schema/ai_report.py` | new, only if typed row models are needed (`extra="forbid"`); otherwise keep rows internal to the stage | n/a |
| `docs/MAP.md` | existing, generated | regenerate |
| `qa/manifests/t155-ai-report.md` | new | the maker's evidence |

Not touched: `stages/report_export.py` (at cap), `cli.py` (295), `cli_crawl.py` (300), `core/paths.py` (300), `store/project_store.py` (299), `schema/ai_check.py` (t153-owned), `.gitignore` (t154 owns `projects/*/ai/`). A CLI command to run the report would need a new CLI module (no existing CLI file has room); whether it is in scope is unknown. `docs/ARCHITECTURE.md` is at its 150-line cap.

New module note: `ai_report.py` is not named in D-017, and `qa/gates/new-module-authorization.md` was answered for AT-710 only (`:77`, "standing-rule variant not chosen"). The existing homes are full, which is the condition that gate describes. Treat the new module as needing the checker or owner to acknowledge, and say so in the manifest.

## 6. Test scope (exact files)

- `tests/test_ai_report.py` (new; whole file)
- Regression guards only if their code is touched: none expected (`tests/test_report_export.py` 187 lines and `tests/test_crawl_report.py` 107 lines stay untouched)
- Then `uv run ruff check src tests scripts` and `uv run autotester doctor`; no `-q`, no pipes, no full suite.

## 7. Reachable test cases (per proposed criterion, happy path first)

- P1: a fixture with results in all three tiers renders three sections in static, behavioural, adversarial order, each with its runnable count; an empty tier shows 0 and is present; a failing static row sorts above a passing adversarial row.
- P2: for each `BlockedReason` value that an `AiCheckEntry` can carry, a fixture row renders its reason text plus action, distinct from the bare enum name, and the status cell reads BLOCKED, never PASS.
- P3: a judged FAIL shows each `Failure.criterion_id`, `reason` and `fix_hint` verbatim; an INCONCLUSIVE with `note` shows the note; `grader_provider == "rule"` rows are labelled as computed.
- P4: building the report twice from the same stored files gives identical output and writes nothing else.
- P5: a `refusals.jsonl` with two lines renders two rows of target, time, requested probes and reason, and no probe text.
- P6: a planted synthetic secret in a response and in a judge reason never appears in any cell; `scripts/check_no_secrets.py` passes on the output.
- P7: column widths come from `autosize_columns` (a test patches or inspects the call).
- Edge: no stored AI results at all produces a report that says so, not an empty or crashing file.

## 8. Gate answers (verbatim)

No gate is specific to T-155. Applicable on disk:
- `docs/plan.md:91` (Held / blocked): "**T-154 and T-155** are no longer held for a separate approval (D-081 item 3 supersedes the 2026-09-27 hold). T-154 builds after T-153 and each adversarial run still writes its own signed row naming target and scope; T-155 follows T-154."
- `qa/gates/d081-run-approvals.md`: "Answered: 2026-10-10 - A (full approval; maker mints per-run rows) - D-081". The report fires nothing; this is context only.
- `qa/gates/write-policy-tier.md:88-92` still reads "HELD ... Track C builds through C3 only" with no `Answered:` line superseding it (see the t154 brief's owner questions). The report is read-only, so this does not block the build, but the stale text should be reconciled.
- `qa/gates/new-module-authorization.md:77`: "Answered: 2026-09-29 — A — 'A: new ledger/citations.py (Recommended)', AT-710 only (standing-rule variant not chosen)".

## 9. UI surface and persona walk

`Persona walk: skip (an exported report file built from stored evidence; no route, template, CLI command or browser step is in scope)`. If the checker's criteria add a UI page or a CLI command, change this to `required (tester)` and add the route file to section 5.

## 10. Dependencies and conflicts

- Must land first: `t153-behavioural-checks`, then `t154-adversarial-pass` (goal.json deps; the run-record and refusal-log shapes come from t154).
- Shared files (owner in bold): `src/autotester/schema/ai_check.py` — **t153**, read only here; `projects/<slug>/ai/` layout and `.gitignore` — **t154**; `src/autotester/stages/ai_judge.py` — **t153**, imported only; `docs/MAP.md` — generated, integrator regenerates last; `src/autotester/core/excel.py` — unchanged, shared with `crawl_report.py` and `issues.py`.
- Other pending units that report: `t168-damage-control-report` (`qa/QUEUE.md`, "report layer; stages/report_export.py is 299 lines, so a split module is likely") will also want a split module next to `report_export.py`. goal.json dropped its dependency on T-155 (D-059), but both could add `stages/*_report.py`; names must differ and neither edits `report_export.py` (single owner of that file: whichever unit first needs to; none today).

## 11. Budget and process rules

- Check budget: **M = 10 minutes** active wall. No full suite by the builder; falsification only in a throwaway copy (AT-693); kill only PIDs it started; no network, no model call, no browser.
- The report is read-only over stored evidence. It writes only the output file the caller names, under `.work/` in tests.

## Decisions this unit needs before it can be dispatched

1. The checker files T-155 criteria (see section 3 proposals) in the contract, and `docs/spec.md` gets a requirement row (`ISS-t150-1`).
2. Where behavioural captures and their verdicts are persisted, and whether the T-153 or T-155 unit writes them.
3. Report format: Excel only (the goal note's only hint), HTML, or both; and whether a CLI command or UI page is in scope.
