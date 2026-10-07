# Manifest — t176-script-replay (persist + replay the generated script, locate by meaning)

Contract: qa/contracts/script-replay.md SR1-SR5 (DRAFT, authored under D-041; goes ACTIVE on this unit's first checker PASS)
Goal task: T-176 (D-041; depends on T-165, done)
Policy-Version: proportional-verification/2026-10-06.6
Fix cycle: 0 of 2
Phase: READY
Tier: M — new behaviour across existing execute/pipeline/schema seams; no auth, tenancy, production-data write or protected-test edit. The contract names no tier.
Dual check: no — single checker.
Persona walk: skip (no UI surface changed)
Executor: claude-sonnet-subagent (maker build)
Base: fe6eb98ac640999b4ecdaa1b14bc7c8356ea753f
Branch: wave/t176-script-replay, code commit 677bfbe4 plus this manifest

## Contract rows (verbatim)

## Criteria

### SR1 — A stored script is replayed with zero provider calls

`Case.script_ref` resolves to a persisted, versioned `Script`. A second run of an unchanged case
replays it and makes **no provider call**. The run records that it was a replay.

**Verify:** run a fixture case twice against a local fixture page with a counting fake provider —
first run: N calls and a stored script; second run: **0** calls, same outcome, the trace/run record
says `replay`. Sabotage: make the loader ignore `script_ref` — the second run's call count goes
non-zero and the named test is red.

### SR2 — A stale script is invalidated, never trusted

A stored script carries a content hash over everything that determines it (the case's steps, the
FlowSpec version, the locator-priority setting). If any input changed, the script is **not replayed**;
the run says why. Same fail-closed instinct as `grade`'s stale-rubric invalidation.

**Verify:** change one step of the fixture case → replay refuses the old script and reports the
reason. Sabotage: remove the hash comparison — the changed-step test turns red on the "old script was
used" assertion, not on a parse error.

### SR3 — Locators are semantic first, and a brittle one is named

Replayed steps locate by **role + accessible name** or **label** before falling back to CSS, and a
step whose only locator is a CSS path or a generated id is **flagged** (named in the report), not
silent. This makes the `flowspec.py:78` promise true.

**Verify:** a fixture page where the CSS class is renamed but role and name are intact — replay
passes. A fixture where the accessible name changes — replay **fails honestly** (`ERRORED`, naming
the step); it does not pass. The second half matters: a locator that "heals" onto the wrong element is
worse than one that fails.

### SR4 — A declared test-id attribute priority is honoured, in order, and nothing else is used

The project declares an ordered list of test-id attributes (research names
`project update --test-id-attributes <list>`; the flag name is the build's to confirm). It lives in
`schema/project.py` (`extra="forbid"`, a default stated), and the locator picks the first declared
attribute present. An attribute not on the list is never used. An empty list means role/label only.

**Verify:** a fixture element carrying two candidate attributes — the chosen one follows the declared
order, and **reversing the list flips it**. A project written before this unit still loads (default).

### SR5 — A failed replay reports; it never regenerates or overwrites

When a replay step cannot find its target, the outcome is `ERRORED` with the failing step named. The
stored script is **byte-identical** afterwards. Repairing a script is an explicit, recorded act (the
T-177 fallback or a human), never a side effect of running. Replay never grades (C7).

**Verify:** replay a fixture script against a page missing the target; assert outcome `ERRORED`,
the stored script's bytes unchanged, and zero provider calls. Sabotage: let a failed replay call the
generator and overwrite — the unchanged-bytes assertion goes red.

## What changed

- `src/autotester/browser/locators.py` (new, in the owned `browser/` package) — the target grammar (`role=button[name="Save"]`, `label="Email"`, `testid[data-qa]="x"`, anything else = plain selector, unchanged), exact-match resolution via `get_by_role`/`get_by_label`, `LocatorNotFound`, and `LocatorMixin.locate()` (a semantic locator must match exactly one element or the step raises).
- `src/autotester/browser/locator_derive.py` (new) — derives the best locator for a live element: declared test-id attribute in declared order, then role + accessible name (Playwright aria snapshot), then label, else the original selector flagged `brittle`. Every rung is verified unique and same-element.
- `src/autotester/browser/session.py` — the seven action methods that took `self.page.locator(locator)` now call `self.locate(locator)`; `LocatorMixin` joins the bases. File stays at the 300 cap (one docstring condensed to pay for the import). `first_option` and the `body` poll keep `page.locator` (explorer/internal).
- `src/autotester/schema/project.py` — `Project.test_id_attributes: list[str]`, default `[]` (role/label only), validated to distinct plain attribute names (they land in a selector). Old project files load unchanged.
- `src/autotester/schema/case.py` — `Script` gains `version`, `inputs: ScriptInputs` (steps hash, FlowSpec version, test-id priority) and `steps: list[ScriptStep]`; new `ScriptStep`, `ScriptInputs.differences()`. `Case.script_ref` is now read.
- `src/autotester/stages/script_replay.py` (new stage module, a small split from execute.py/pipeline rather than growing them) — `run_scripted(case, session, store, execute=run_case)`: replay a valid script, else run live and record `projects/<slug>/scripts/<case_id>.v<N>.json` (only on COMPLETED, only for a case on file) and point `case.script_ref` at it. `load_script` returns `(script, None)`, `(None, why)` for stale/missing, `(None, None)` for none. No Provider appears anywhere in this module.
- `src/autotester/stages/execute.py` — `_run_steps` calls `session.recorder.capture` before each step when recording; `_error_text` names the failing step in a replay or locator miss. Non-replay, non-semantic errors are byte-identical to before.
- `src/autotester/stages/run_case_pipeline.py` — both `run_and_grade_case` and `_resilient` execute through `run_scripted(..., run_case)` (it passes its own `run_case` reference, so the existing monkeypatch seam in tests still works). New keyword `judge_replays: bool = True`; `False` returns a finished replay unjudged (INCONCLUSIVE by rule, never PASS) with zero provider calls.
- `tests/test_script_replay.py` (new, 15 tests, real Chromium over a local fixture page) · `docs/MAP.md` regenerated by `autotester map` (the new modules).

INTERPRETATION TO CONFIRM (SR1): this repo's executor makes no provider call on a live run either (`run_case` has none); the only per-run model spend is the judge. So "first run: N calls, second run: 0" is measured on the judge: run 1 = 1 call plus a stored script; run 2 replays, and with `judge_replays=False` makes 0 calls. By default a replayed run is STILL graded (judge call kept), because grading is a separate stage (C7) and a regression suite needs verdicts; the default-grading behaviour is pinned by `test_sr1_a_replayed_run_is_still_graded_by_default`. If the checker reads SR1 as "replay must never reach the judge even by default", that is a one-line default flip, not a redesign.

Not done, by ownership: the `project update --test-id-attributes` CLI flag (cli.py is another build's) and any UI field (ui/ files are others'). The schema field is the whole contract (SR4) and is settable by editing project.json. `docs/ARCHITECTURE.md`'s "Not yet built (D-031)" paragraph is now stale; it needs a DECISIONS entry first, so it is untouched. `.goal/goal.json`, `docs/DECISIONS.md`, `docs/FEATURES.jsonl` untouched.

## Verification scope

Policy-Version: proportional-verification/2026-10-06.6
Tier: M, single checker.
Base / checked state: fe6eb98a + 677bfbe4 (+ this manifest).
Affected tests / full-suite trigger: tests/test_script_replay.py; regression set run: test_execute*.py (4 files), test_network_assertions.py, test_viewport_locale_enact.py, test_run_case_pipeline.py, test_run_case_pipeline_resilient.py, test_schema.py, test_browser.py, test_browser_actions.py, test_browser_settle.py, test_parallel_run.py, test_ui_runs_serial_entry_order.py, test_ui_runs_serial_resilience.py, test_ui_runs.py, test_ui_project_edit.py, test_doctor.py, test_product_map.py. The builder ran no full suite.
Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=2 mutations=9 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6

## How to verify (commands + expected)

- `uv run pytest tests/test_script_replay.py` -> 15 passed (about 5 minutes on this loaded machine: browser start and close dominate)
- regression set above -> 165 passed
- `uv run ruff check src tests scripts` -> All checks passed
- `uv run autotester doctor` -> 1 violation, present at the base: stale-generated docs/SNAPSHOT.md (the base also had docs/MAP.md stale; this unit regenerated it)

## Capability coverage (each criterion -> its defender test and isolating falsification)

Throwaway copy outside the worktree (`D:/t176-sr-fals-run2`, `D:/t176-sr-fals-run3`, `PYTHONPATH` pointing at the copy, import path asserted); the original was never edited; each mutation restored byte-identical and re-run green. Runner: `scratchpad/t176-script-replay/t176_falsify.py` (before / after / restored per mutation).

| Criterion | defender test (tests/test_script_replay.py) | falsifying edit | observed |
|---|---|---|---|
| SR1 replay, 0 provider calls | test_sr1_second_run_replays_the_stored_script_with_zero_provider_calls (+ test_sr1_a_replayed_run_is_still_graded_by_default) | script_replay.py::load_script `ref = None` (loader ignores script_ref) | before `1 passed in 20.44s`; after `FAILED ...sr1_second_run_replays...`, `1 failed in 69.28s`; restored `1 passed in 43.59s` |
| SR2 stale script refused | test_sr2_a_changed_step_refuses_the_old_script_and_says_why, test_sr2_a_changed_flowspec_version_or_locator_priority_is_stale | script_replay.py::load_script `changed = []` (hash comparison removed) | before `2 passed`; after `2 failed in 157.98s` (both named); restored `2 passed in 13.62s` |
| SR3 semantic first | test_sr3_replay_survives_a_css_class_rename | locator_derive.py: role and label rungs deleted (css only) | before `1 passed`; after `FAILED ...css_class_rename`, `1 failed in 50.16s`; restored `1 passed in 14.77s` |
| SR3 no healing onto a wrong element | test_sr3_a_changed_accessible_name_fails_honestly_and_names_the_step | locators.py::resolve `exact=True` removed from get_by_role | before `1 passed`; after `FAILED ...changed_accessible_name...`, `1 failed in 25.13s`; restored `1 passed in 14.18s` |
| SR3 brittle named | test_sr3_a_css_only_step_is_flagged_not_silent | locator_derive.py fallback `brittle` True -> False | before `1 passed`; after `FAILED ...css_only_step...`, `1 failed in 24.80s`; restored `1 passed in 15.73s` |
| SR4 declared order | test_sr4_the_first_declared_attribute_present_wins (4 params; reversing flips it) | locator_derive.py `for attr in sorted(attrs)` | before `4 passed in 54.47s`; after `1 failed, 3 passed` (the reversed-list param); restored `4 passed in 70.73s` |
| SR4 nothing off the list | test_sr4_an_attribute_not_on_the_list_is_never_used | locator_derive.py `for attr in (*attrs, "data-testid")` | before `1 passed`; after `FAILED ...never_used`, `1 failed in 38.21s`; restored `1 passed in 40.36s` |
| SR4 old project loads, default stated | test_sr4_a_project_written_before_this_unit_still_loads | project.py field made required (`Field(...)`) | before `1 passed in 0.44s`; after `FAILED ...before_this_unit_still_loads`, `1 failed in 2.73s`; restored `1 passed in 1.87s` |
| SR5 failed replay reports, never overwrites | test_sr5_a_failed_replay_is_errored_with_the_script_byte_identical | script_replay.py::_replay rewrites the script as version+1 when the replay is ERRORED | before `1 passed in 22.05s`; after `FAILED ...byte_identical`, `1 failed in 31.44s`; restored `1 passed in 38.03s` |

Note: the first SR4 "never used" test did not catch its mutation (the declared attribute was present, so the injected one was never reached); the test was tightened (declare an absent attribute, assert no `data-` in any locator) and the mutation then went red. Replay-never-grades (C7) is held structurally (`run_scripted` has no Provider parameter; the pipeline's unjudged replay verdict is INCONCLUSIVE/rule) and asserted in test_sr1 (`verdict.grader_provider == "rule"`).

## Live browser evidence

No UI surface changed. The tests drive real Chromium (headless) against a local HTTP fixture page; no live site was touched.

## Status: checked-PASS

Checker verdict: `qa/verdicts/t176-script-replay.md` (cycle 0, PASS, Tier M, single checker, commit 5383a559). HUMAN_GATE-REQUEST for the new modules `browser/locators.py`, `browser/locator_derive.py`, `stages/script_replay.py` answered by D-072 item 2 (approved, origin/master 642ab4bd). Verdict P1 (SR1 default grades a replay) resolved as "keep the default" by D-072 item 11 (`judge_replays=True` stays). P2/P3/P4 filed as AT issues at merge.
