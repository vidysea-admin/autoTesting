# Verdict - ux-advisory-integration (AT-794 integration + F1)

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** 9eb23217dde2fc752e72595ab464d414f4c5f036
**Base SHA:** 766eae68d70ee0e6315cabe9d90dd0dc14e81147
**Reviewer:** independent checker (Sonnet 5.5), fresh context

## Identity
HEAD of worktree-agent-a1e28734fd48181dd = 9eb23217 (full SHA above); working tree clean before this verdict. Commits above base: merge 77ccbb7f (fd89db39 AT-794 PASS candidate 12e6cb9b) plus 9eb23217.

## 1. Merge preserved both behaviours (verified in source)
- `prepare_run` is unchanged vs base: `require_declared_values` then `require_live_case_approval` run before any run id, directory or browser. `require_live_case_approval` still passes `probes=probe_request(cases)` into `covering_approval` (the grant-budget preflight), now imported from `stages.execute` in `run_gates.py`.
- `launch_run`: gates (prepare_run) -> run_cases_traced -> save_tracked_run -> prune_old_videos -> `advise_after_run` (after the save) -> `ask_for_what_it_did_not_recognise`. Diff vs base adds only that one call line.

## 2. Split is a pure move
- Programmatic check: the base text of `LaunchRefused` and of `is_entry_case`..`require_live_case_approval` (everything up to `judge_or_refuse`) appears verbatim in `run_gates.py`; diff shows only deletions here and additions there, imports aside.
- grep: each of the 4 names is `def`/`class`-defined once (`run_gates.py` only); `run_launcher.py` imports and lists them in `__all__`. No second definition, so the one-concept rule holds. `autotester doctor` clean.
- Line counts: run_launcher 244, run_gates 83. All callers/monkeypatch targets still resolve through run_launcher (the launcher tests that patch them pass).

## 3. Security gates unchanged
`tests/test_run_approval_grant_budget.py`, `tests/test_probe_floor_matches_runtime.py` pass (below). The gate bodies are byte-identical.

## 4. Deadline (UXPolicy.deadline_s)
- Schema: `UXPolicy` still `extra="forbid"`; field default 300.0, gt 0, le 3600. Probed: default builds, 0 and 3601 rejected, unknown key rejected. Existing configs (no field) stay valid via the default.
- Default 300 s: sane for an advisory pass over <= 20 calls (max_calls default 20); a ceiling not an expected duration.
- Enforcement: `run_ux_advisory` computes `deadline` once, and before each case passes budget 0 if `monotonic() >= deadline`; eligibility gates still run first so only would-have-been-read cases become `skipped_budget`. Sabotage: in an isolated copy, replacing that expression with `cap - used` makes `test_the_pass_stops_issuing_calls_after_its_deadline_and_stays_nonfatal` FAIL (exit 1, named); green on the real candidate.
- Worst case: the bound is soft. Total <= deadline_s + one in-flight `provider.judge` (which can span fallback tiers, ~120-240 s per tier per the brief). Not hard-interrupted. Documented in the field description. Because `advise_after_run` runs synchronously inside `launch_run` after the save, the run slot/return is delayed up to that bound (and `ask_for_what_it_did_not_recognise` after it); advisory impact only, no verdict effect. Non-blocking finding F1.
- Run verdict untouched: the pass runs after `save_tracked_run`, writes only `ux_report.json`; `advise_after_run` swallows all exceptions.

## Commands (own runs, exit codes from files)
- preflight (review_budget.py): exit 0, PREFLIGHT_OK, import origin = worktree src.
- pytest (no -q) A: test_ux_advisory_wiring, test_user_persona, test_probe_floor_matches_runtime: exit 0, 32 passed (33 s).
- pytest (no -q) B: test_run_approval_grant_budget, test_run_launcher, test_run_launcher_approval, test_run_launcher_priorities_approval, test_run_launcher_retired: exit 0, 47 passed (43 s).
- ruff check stages/, schema/user_persona.py, test_ux_advisory_wiring.py: exit 0.
- `python -c "from autotester.cli import app; app()" doctor`: exit 0, "doctor: clean".
- Mutation (isolated copy of src/tests/scripts): red as above.

## Not run / limits
Full suite not run (not required by this unit's scope; belongs at the combined release gate). Maker's wider 12-file run (198 passed) is unverified-reuse and was not relied on. Maker usage unknown; BOOTSTRAP_REVIEW with standing escalation, ratio unverified; see metrics file.

## Findings
- F1 (non-blocking, advisory): the deadline bound is soft (deadline_s + one in-flight call) and delays `launch_run` return by that much when UX is enabled.
