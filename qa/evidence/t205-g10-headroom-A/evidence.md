# t205-g10-headroom seat A evidence (head 0b8325b6, base 09828f2d, cycle 0)

Produced by seat A's own sub-checkers (read-only, scratch copies under the session scratchpad) and the coordinator's own runs.
Sub-checker reports are text the coordinator saved here; they ran commands themselves and printed `autotester.__file__` to prove which tree was under test.

## 1. Criteria commands (coordinator ran each once on the bound worktree, `-p no:xdist -o addopts=`)
- tests/test_run_launcher.py 4 passed · test_run_launcher_approval.py 8 passed · test_routers_list.py 4 (all in the run, tail shows pass) · test_policy_merge.py 8 passed ·
  test_cli_subapp_hook.py 4 passed · test_project_schema_team.py 6 passed · test_team_store.py 50 passed · test_team_enums_home.py 3 passed.
- tests/test_ui_runs.py + live_case_approval + parallel_crash_recovery + parallel_trace + queue + serial_entry_mix_live + test_cli_surface + test_cli_advice_resolves + test_cli_issues + test_schedule_model:
  176 passed, 1 skipped (the skip is `test_ui_runs_serial_entry_mix_live.py`, `pytest.skip`/`importorskip("playwright")` at :45/:59, an environment skip), 151 s.
  Builder said 177 passed; the one-test difference is that skip.
- `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> clean. `wc -l ui/app.py cli.py` -> 271, 297.
- `git diff 09828f2d..0b8325b6 --stat -- tests/` shows only added files (builder claim, reproduced by the stat list: 8 test files + 5 goldens, all new).

## 2. Behaviour preservation of trigger_run (old routes_runs.py 263 lines at 09828f2d vs new routes_runs.py 74 + stages/run_launcher.py 285)
Coordinator also read run_launcher.py in full (:1-285). Sub-checker table, every item opened at file:line:

| Old (09828f2d routes_runs.py) | New | Result |
|---|---|---|
| `_is_entry_case` 51-61 | run_launcher.py:105-111 `is_entry_case`, alias routes_runs.py:22/27 | IDENTICAL body |
| `_require_declared_values` 64-81 | run_launcher.py:114-131 | same sorted-missing logic and both message strings; raises `LaunchRefused(400)` instead of `HTTPException(400)`, mapped back |
| `_require_live_case_approval` 84-104 | run_launcher.py:134-154 | same CrawlBounds, same project-mismatch ApprovalRequired text, same `covering_approval(kind=LIVE_CASE, secrets, account_keys or None)`; `LaunchRefused(403, str(exc))`, mapped back |
| `_plan_under_shared_budget` 107-117 | run_launcher.py:185-198 + route wrapper | same planning/grant sequence; new branch `ledger is None` -> plain planner (route path always passes the queue ledger) |
| `_execute_with_trace` 120-158 | run_launcher.py:201-238 `run_cases_traced` | same order, kwargs, EXECUTE span and error text |
| `_Prepared` 161-170 | `Prepared` 93-102 | IDENTICAL fields and order |
| `_prepare_run` 175-198 | `prepare_run` 157-182 | slug 400 -> 404 -> no cases 400 -> no provider 400 -> SecretStore(strict=False) -> declared values -> approval gate -> catalog snapshot: same order and texts |
| `trigger_run` 201-212 | routes_runs.py:48-62 | prepare_run (gate-only seams, ledger=None) -> `get_queue().submit` with a run id minted after the gates -> QueueFull 429 -> 303 to `/projects/{slug}/report` |
| `_run_queued` 215-221 | routes_runs.py:65-71 | `launch_run(...)` re-runs `prepare_run` first (HO19), LaunchRefused -> RunRefused(reason) |
| `_execute_and_record` 227-246 | `launch_run` 241-271 | same Run fields, then save_run, prune_old_videos, ask_for_what_it_did_not_recognise |
| `_ask_for_what_it_did_not_recognise` 249- | 274-285 | IDENTICAL logic |
| `set_runner(_run_queued)` 224 | routes_runs.py:74 | IDENTICAL |
| HTTP mapping | routes_runs.py:56-57 `HTTPException(exc.status, exc.reason)` | 400/403/404 + detail text byte-identical |

CHANGED, none user-visible: `__all__` added; private helper names moved to non-underscore names in the launcher (no in-repo consumer of the old names);
exception type `LaunchRefused` mapped back; new `launch_run` kwargs trigger/requested_by/slot_key/via default to today's behaviour (Run default trigger MANUAL, others None).
Gate position: the approval call (run_launcher.py:179) is inside `prepare_run`, which runs before any run id, run dir or BrowserSession (first `run_dir` use is `launch_run` :254, after `prepare_run` returns).
Monkeypatch seams: tests patch `routes_runs.LangChainFallbackProvider`, `plan_parallel_run`, `_free_ram_mb`; `_seams()` (routes_runs.py:35-36) reads them per call, so each patch is still honoured. No test patches a removed helper.
Run serialisation: `write_json` = `model_dump_json(indent=2, exclude_none=True)` (filestore.py:39-41), so a Run/Project without team keys writes byte-identical (see section 4).

## 3. Route list and CLI tree (master 09828f2d extracted by git archive, same venv, PYTHONPATH switched, `__file__` printed)
- Routes: master and new both 56 routes (52 `autotester.*` + 4 FastAPI own); equal row for row (methods, path, endpoint qualname, route class, order).
  `tests/golden/ui_routes.json` (52 rows) equals master's 52 rows exactly, in order: generated from master, not from the new code.
  Test compares with `is_ordered_subsequence(golden, live)`, so it tolerates added or shadowing routes (TF3 weakness, see falsifications).
  One hidden difference: OpenAPI `description` of the run-trigger operation changed (docstring of `trigger_run` reworded); paths, params, schemas unchanged.
- CLI: master and new both 38 nodes (17 top-level + sub-commands), 101 parameters; names, help, options, defaults identical (md5 equal after normalising a `0x` repr address).
  `tests/golden/cli_commands.json` (17 `[name, short help]`) equals master's top-level listing in order. It does not capture sub-commands, options or exit codes (checked options by hand: equal).
- Schema: all 9 committed `projects/*/project.json` load; all 81 `projects/*/runs/*/run.json` in the root checkout load; `diff -r` of store-written output for a fixed Project and Run plus 90 real files, master code vs new code, is empty (92 files each).
  Run written without team keys has no `requested_by`/`slot_key`/`via`; Project has no `schedule`/`tracker` key. Relocated enums (ScheduleMode, ScheduleZone, SlotOutcome, SchedulerHealth): same names, values, order; only `__module__` changed, old import path still works.
  schedule.py: 35 lines removed = `from enum import StrEnum`, 32 enum lines, 2 docstring lines; 8 added = docstring + re-export import.

## 4. Falsifications (coordinator-chosen edits differing from the builder's; each in its own copy; green before, assertion red after)
| Crit | Edit | Result |
|---|---|---|
| TF1 | `from fastapi import HTTPException` into run_launcher.py | KILLED (`test_the_launcher_imports_nothing_from_fastapi`, `assert not ['fastapi']`) |
| TF1 | `_shadow_launch` calling `_execute_with_trace` appended to ui/helpers.py | KILLED (site list `['stages/run_launcher.py:253','ui/helpers.py:296']`) |
| TF1 | `trigger_run` also calls `launch_run(slug, seams=_seams())` | SURVIVED in TF1 file (4 passed); killed by test_ui_runs_live_case_approval (2 failed) |
| TF2 | `run_dir('premade').mkdir` before `prepare_run` in launch_run | KILLED 3 rows (`assert not store.paths.runs_dir.exists()`); the byte-identical listing check alone would miss an empty dir |
| TF2 | `sum(action_cost(c) for c in cases[:1])` in the gate bounds | SURVIVED (42 passed): single-case world never exercises the sum; RunBudget still stops the run at execution |
| TF2 | extra unwired parameter `check_consent: bool = True` on launch_run | SURVIVED (8 passed): `test_the_gate_is_not_a_parameter` is a name blocklist |
| TF3 | route added to the `inbox` stub | KILLED (`stubs ... add zero routes`) |
| TF3 | shadow `POST /projects/{slug}/run` router registered first in include_all | SURVIVED (subsequence golden) |
| TF3 | every router registered twice | SURVIVED (subsequence golden) |
| TF4 | public-set check compares wrong collection | KILLED (`DID NOT RAISE PolicyError`) |
| TF4 | `for unit in units` (unsorted) | KILLED (order-independence test) |
| TF4 | existence check compares path only, ignores method | SURVIVED (only `GET /nowhere` case) |
| TF5 | `SUBAPPS[:-1]` | KILLED (3 failed) |
| TF5 | register ingest under name `intake` | KILLED (2 failed) |
| TF6 | `extra="ignore"` on Project | KILLED (`DID NOT RAISE ValidationError`) |
| TF6 | TrackerConfig `extra="ignore"` | KILLED |
| TF6 | swap url/text priority in `Source` id derivation | SURVIVED (6 passed): one text-only pin |
| TF7 | marker open(path,"w") instead of O_EXCL | KILLED (`create_marker(...) is False`) |
| TF7 | reserved device-name check off / trailing dot-space check off | KILLED (14 / 3 failed) |
| TF7 | guarded `import fcntl` in team_store.py | KILLED (AST test names store/team_store.py) |
| TF7 | `.work/` removed from .gitignore / from .dockerignore | KILLED (real `git check-ignore` / list assert) |
| TF7 | `import fcntl` in core/paths.py or filestore.py, `import os as _o; _o.fork()`, `importlib.import_module("fcntl")` | SURVIVED: grep covers only safe_names.py and team_store.py and literal names |
| TF8 | `_OUTCOME = "skipped_overlap"` in stages/issues.py | KILLED |
| TF8 | `SourceKind` class defined in team_enums.py | KILLED |
| TF8 | `SlotOutcome.APPROVED = "approved"` (value also in enums.py) | SURVIVED: only whole-class/whole-set duplicates tested |
| TF8 | plain-word literals `"missed"`, `"refused"` in a stage | SURVIVED: test only checks values containing `_`; scans stages/ only |
All kills were assertion failures on the named property, none an import or setup error.

## 5. HELD audit (stated reason vs contract text vs master)
- TF6 Source provenance (`uploaded_by`, `uploaded_at`, `origin`): not built. Master 09828f2d Source (project.py:105) has none; worktree has none (`grep uploaded_by|uploaded_at|origin src/autotester/schema/project.py` -> exit 1).
  Contract TF6 states the fields as part of the criterion and allows "minimal typed placeholders" for models G5/G6 build, not a deferral to T-198. wave/t198a-zip-drive-intake defines `origin` as a discriminated union in schema/intake.py:83, which differs from the contract's closed enum, so the conflict is real but the contract is unamended. Reason PARTLY valid; criterion PARTLY MET.
- TF4 catalogue / central table / catalogue golden / empty dicts for stubs: master has no `src/autotester/auth/`; T-204 (wave/t204-team-login 6ea9b688) has `schema/auth.py` CATALOGUE and keys `(method, path)` tuples. Contract allows: "If T-204 has not landed, G1 adds only the merge function and its tests". Valid for the table and catalogue golden. Not allowed by that sentence and not built: "The stubs of TF3 contribute empty dicts" (no `ROUTE_POLICY` anywhere in src except a docstring), and nothing calls the merge at import. PARTLY MET.
- TF8 delivery-status and source-origin enums: owners G6/T-198; `team_enums.py:7` says so honestly. The location rule (one home, no duplicates) is met; the vocabularies themselves are undefined. Also `QueueStatus` (schema/run_queue.py:17) stays where T-203 put it.
- TF8 ARCHITECTURE rows: contract says "under a DECISIONS entry that names the section"; D-072 has no section-naming Changes-authorized; no rows in the worktree. Builder may not write DECISIONS. Valid; needs the Approver. docs/MAP.md regenerated (met).
- TF2 stale AT-570 note: only in `.goal/goal.json` (T-201 note); `docs/plan.md:117` already reads "closed in code". Builder is told not to edit root state; the manifest's mention of docs/plan.md is inaccurate (low).
The manifest claims nothing as done for any of these.

## 6. New modules
Nine, all <= 300 lines: run_launcher.py 285 (TF1 names; cannot fold, it is the extracted 265-line routes_runs body), ui/routers.py 67 (TF3 names; app.py was at 300), cli_subapps.py 24 (TF5 requires a small module, name builder's; cli.py was 299),
auth/__init__.py 1 + auth/policy.py 63 (TF4 names policy.py; add/add with T-204's 107-line file, manifest has the reconcile plan), schema/team_enums.py 51 (TF8 names; enums.py at 300), store/team_store.py 50 (TF7 names),
core/safe_names.py 66 (TF7 requires one validator, names no file; could fold into team_store.py -> 116 lines; builder's choice; SLUG_PATTERN is shared by schema, ui/helpers and the launcher, so a pure module avoids cycles),
core/repo_docs.py 78 (not named by contract, plan or D-072 except the blanket "yes to all"; split out of core/paths.py, 294 lines on master, to make room for `team_path`; costs a lazy import and re-export; the one module needing explicit human confirmation).
Measured master line counts: app.py 300, cli.py 299, paths.py 294, enums.py 300 (the contract's 295/287 understate).

## 7. Layering and shims
- run_launcher.py:58 `from autotester.ui.run_execution import _run_cases_in_parallel, _run_cases_serially` (top-level, two private names). ARCHITECTURE.md has no layering rule; doctor (doctor.py checks: file size, function size, file name, root clean, duplicate definition, deps declared, ledger, pytest -q, stale evidence, generated fresh, architecture budget, docs routed, decision citation) has no import-direction check. No stage imported `autotester.ui` on master; upward-import precedent exists elsewhere (core/ids.py:62 lazy ui import, cli_issues.py:36). run_execution.py imports no fastapi/starlette, so the launcher stays framework-free transitively in source, but `import autotester.stages.run_launcher` does put `fastapi`/`starlette` in `sys.modules` in practice (via `autotester.ui` package import chain, per falsification sub-checker); the TF1 test is lexical. Ruling: accept, follow-up issue to move run_execution.py under stages/.
- Shims: routes_runs.py:44-45 `_execute_with_trace = _with_seams(run_launcher.run_cases_traced)`, `_plan_under_shared_budget = _with_seams(...)`; `_is_entry_case` alias. Required so tests/test_ui_runs_serial_entry_order.py:227,237, test_ui_runs_queue.py:160, test_ui_runs.py:154 keep unedited. Not literally "two-line" (a `_with_seams` lambda helper). Production never uses them (`_run_queued` calls `launch_run`). The single-call-site test is name-based and does not count them (they are assignments, not Call nodes of those names). Ruling: accept; owner rules open item 2, then move tests and delete shims.

## 8. Browser smoke (Playwright MCP, new code port 8811 vs master 09828f2d port 8812, temp data roots, no .env, empty provider keys)
GET /, /projects/regression-demo: 200, identical titles, headings, button `Run tests`, form `post /projects/regression-demo/run`, identical link list, 0 console errors on both.
Run click -> `/projects/regression-demo/run` 400 page "no AI provider is configured (set an API key in .env) -- cannot grade a run", identical on both (1 console error = the browser's own line for the 400, both servers).
13 HTTP probes per server (redirects not followed): outputs identical apart from /healthz timestamps. POST run on a project with no cases -> 400 "project 'saucedemo' has no cases to run"; unknown project -> 404 `no project 'nope'`.
Not exercised: the 303 success redirect (needs a provider key). No `runs/` directory created on either server. New server PID 41712 and master PID 29300 stopped by PID; netstat shows no listener on 8811/8812.
Playwright MCP left `D:/autoTesting/.playwright-mcp/` (tool side effect; not shown in git status).
