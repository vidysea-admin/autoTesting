# Manifest - t179a-lead-tester-core (T-179 slice a: the guarded stage-tool core)

## Status: ready-for-check

**OPEN QUESTION FOR THE OWNER (product decision the contract does not settle; the build below is the fail-closed answer, "refuse when in doubt"):** under `READ_ONLY`, `run_case` can today only navigate, wait, assert, hover, scroll, go back, and sign in through the declared login case. It cannot CLICK anything, type anything, or press any key, so a READ_ONLY case that needs to open a menu or follow an in-page link is refused. Where to draw the line is Umesh's call: (a) keep this (safe, narrow); (b) allow a CLICK only when the LIVE element is known to be a plain link (needs act-time enforcement in `browser/session.py` / `stages/execute.py`, which this unit does not own and which would be a second guard site); (c) point READ_ONLY runs at `TEST_ACCOUNT`, which keeps the click deny-list. Nothing is built for (b)/(c).

**Contract:** qa/contracts/agent-layer.md AL2, AL3, AL6 (the T-179 group); AL2 and AL6 in part, AL3 for the tools built (see "AL3 claim, stated exactly"); AL1, AL4, AL5, AL7 held (below)
**Goal task:** T-179, slice a only. T-180 (subagents) and T-181 (gain, budget) are not in this unit.
**Authority:** D-042 (Deep Agents adopted, `qa/gates/d042-deep-agents.md` answered 2026-09-24), D-018 (consent), D-053 (the supplied account is the scope). No new decision is needed for this slice: it adds no dependency and edits no file D-042 does not already allow.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (security class: the AL3 guards and the AL6 secret boundary decide what a model-driven tool may do to a live product; no dependency change, so not L for that reason)
Fix cycle: 1
Repair base: 638d788a
Branch: wave/t179-lead-tester, based on master 16aaa402. Master was not merged. Nothing pushed.
Code commit under check: 67a94fb1 (cycle 0 code was 9c000f1c + 90705dc0; the manifest commit changes no product file)
Executor: claude-sonnet-subagent (maker fix-cycle-1 build subagent)
Dual check: required
dual-trigger: security src/autotester/agents/guards.py:147 (`write_policy_refusal`, the write-policy decision: `execute.run_case` and `BrowserSession` have no write-policy check of their own)
dual-trigger: security src/autotester/agents/tools.py:274 (`dispatch`, the secret gate on the raw call and the only path a model reaches an acting tool)
Persona walk: skip (agent layer, no human-facing screen, route or CLI output is added; docs/plan.md:66)

## Fix cycle 1: what was repaired, in one place

Cycle 0: one blind coordinator FAILED AL3(c), the other passed. The failing observation: through `dispatch` on a READ_ONLY project, CLICK on "Save"/"Place order"/"Sign in"/a Hindi "delete" label, PRESS_KEY Enter (also the default) and Delete, NAVIGATE to `/account/delete?id=1&confirm=1`, `/logout`, an off-domain URL and a `javascript:` URL, and FILL with an empty/whitespace/None value all reached `execute.run_case`. Cause: a stored `Case` step carries no DOM facts, and `guards.py` built `ElementRef(role="button", name=step.target)` without `is_form_submit`, so the `READ_ONLY and el.is_form_submit` branch of `explore_safety.deny_reason` could never fire.

**Where the enforcement lives, and why there.** Design preference 1 (enforce at act time, where the live element is visible) was checked and does not exist in this code: `stages/execute.py::run_case` calls the `BrowserSession` handlers directly and `browser/session.py::click` / `press_key` / `fill` carry no write-policy check. The only live-element READ_ONLY guard is the crawler's (`explore_node.py:189` calling `deny_reason` on enumerated `ElementRef`s with `is_form_submit` from `enumerate.js:142`), and it is not on the `run_case` path. Building one would add a second guard site in files this unit does not own. So preference 2 is built: `agents/guards.py::write_policy_refusal`, called from `agents/tools.py::_run_case` before any session opens, decides fail-closed from what the stored step says. `explore_safety.deny_reason` stays the one name deny-function (asked a name through `_click_denied`; no second deny function). `explore_safety.py`, `execute.py` and the browser package are untouched, and their test files are green (below).

## READ_ONLY decision table (every Action in `schema/enums.py::Action`)

Result is a typed refusal from the tool's own return (`RefusalClass.WRITE_POLICY`, or `DESTINATION` where marked), zero sessions opened, zero `execute.run_case` calls. Anything not in this table (a future `Action` value) falls through to refused.

| Step | READ_ONLY | TEST_ACCOUNT | ALLOW_WRITES |
|---|---|---|---|
| WAIT, ASSERT, BACK, HOVER, SCROLL | allowed (cannot change state by construction) | allowed | allowed |
| NAVIGATE, absolute `http(s)` URL inside `allowed_domains`, no query, no placeholder, path+fragment not matching `deny_reason` | allowed | allowed | allowed |
| NAVIGATE with a query string (`?id=1&confirm=1`, `?page=2`) | refused (a GET can mutate and a stored step cannot say which query is safe) | allowed | allowed |
| NAVIGATE whose path/fragment names a deny or never-click word (`/logout`, `/account/delete`) | refused (via `deny_reason`) | allowed | allowed |
| NAVIGATE bare path (`/reports`), a description ("Admin portal URL"), or a `{{SECRET:..}}` placeholder | refused (no destination to judge) | allowed, left to `BrowserSession.goto`, which refuses what it cannot resolve | same |
| NAVIGATE `javascript:`, `data:`, `ftp:`, any non-http(s) scheme; off-domain or userinfo/backslash host; a control character | refused, `DESTINATION` | refused, `DESTINATION` | refused, `DESTINATION` (`BrowserSession.goto` -> `check_destination` refuses the same hosts at act time, so no legitimate run is narrowed) |
| CLICK, any target | refused ("click can change state"); the stored step cannot tell a link from a submit | allowed unless `deny_reason` (never-click and destructive names), unchanged from cycle 0 | allowed unless a never-click name (logout/sign-out), unchanged |
| PRESS_KEY, any key (Enter, also the default when `value` is None; Delete; Tab) | refused | allowed (unchanged) | allowed |
| FILL / SELECT / UPLOAD, any value including `""`, whitespace, None | refused | allowed (unchanged) | allowed |

**Login carve-out (the only exception, narrow).** Only the case whose id equals `Project.login_case_id` (the same declared login the crawler bootstraps with, `explore.py::_bootstrap_login`, X10/X17). In that case alone: a NAVIGATE may carry a query; a FILL is allowed only when its whole value is `{{SECRET:KEY}}` placeholders and every KEY is declared in `Project.secrets`; then exactly one submit (a CLICK that passes `deny_reason`, or PRESS_KEY Enter) is allowed per credential entry. A second submit with no new credential FILL, a literal value, an undeclared key, a placeholder with trailing text, PRESS_KEY Delete, "Delete account", or the same steps in a case that is not the declared login are all refused. There is no general "Sign in is fine".

**What READ_ONLY now treats as a read and may therefore miss (stated, not hidden).** A GET to an in-domain URL with no query and no deny/never-click word in its path or fragment is treated as a read (HTTP safe-method contract). A product whose state-changing GET endpoint has no query and a neutral name (`/api/close-account`) is not caught; neither is a `BACK` onto a page that re-posts. HOVER can in principle fire a mutating handler. These are stated limits of deciding from a stored step.

## AL3 claim, stated exactly

Cycle 0 said AL3 was met "IN FULL" while residual 1 said a submit with no tell in its name was not caught; that was inconsistent. What the code does now:
- (a) a raw secret in a call is refused (`RefusalClass.SECRET`) before any action: met.
- (b) a crawl beyond the approval is refused (`ApprovalRequired`) before any browser opens: met.
- (c) a READ_ONLY project's state-changing step is refused from the tool's own return: met for every step kind in the table above, decided fail-closed. The remaining limits are the "stated limits" paragraph above and the owner question at the top, not a pass claim for them.
- Not enforced here: the executor itself (`execute.run_case`, `BrowserSession`) still has no write-policy check, so a caller that bypasses `dispatch` is not guarded. The tool is the only entry a model reaches.

## Slice chosen, and why

The dependency question is open (no `deepagents` in `pyproject.toml` or `uv.lock`; the brief records that the PyPI package is 0.7.x and AL1's `>=1.7` resolves to nothing). So this slice contains **nothing that needs the framework**: the tool surface the framework will later be handed, with the safety checks already inside the tools. The planner, subagents, to-do middleware and `skills=` loading ARE the framework (AL1/AL4/AL7), and a hand-rolled planner behind `Provider` would be exactly what AL1 forbids, so none is built here.

In the slice: five stage tools (`crawl`, `run_case`, `get_persona`, `get_catalog`, `grade_case`), each a thin call into the existing stage function; one dispatcher a model reaches; the guards running inside the tools before any browser opens; secret gating of the call and of the result. No live model call, no browser, no network, no new dependency.

Design choices a checker should know:
- The model passes ids and requested bounds only. Project, store, secrets, judge, run id and the session factory are `AgentContext` (trusted); no args model has a field for any of them, and every args model is `extra="forbid"`.
- `crawl` calls `guards.crawl_approval` (`core.consent.require_approval`, reading existing signed rows only, so an agent can never mint one) BEFORE `ctx.open_session`.
- `run_case` runs the write-policy check, then `require_approval(kind=LIVE_CASE)`, then opens the session.
- The stage result is scrubbed (`Redactor.scrub_obj`), then passes the release gate's own detector BEFORE it is written (F3); the outcome is scrubbed again and re-gated before it returns to the model.

## What changed in cycle 1 (edited in place; no `*_v2`)

| Point | File and function | Change |
|---|---|---|
| AL3(c) | `agents/guards.py::write_policy_refusal`, new helpers `_step_refusal`, `_navigate_refusal`, `_read_only_refusal`, `_destination`, `_declared_credential`, `_click_denied`, dataclass `_Walk` | fail-closed table above; returns `(RefusalClass, why)` |
| AL3(c) | `agents/tools.py::_run_case` | raises `_Refused(*refused)` so the class is `WRITE_POLICY` or `DESTINATION` |
| AL3(c) | `schema/agent_layer.py::RefusalClass` | adds `DESTINATION`, `STAGE_ERROR` (the only schema edit) |
| F2 | `agents/tools.py::dispatch` (now a last-resort wrapper) and `_dispatch` | catches `Exception` (never `BaseException`) around the stage, `open_session` and the judge: typed `STAGE_ERROR` with `ExcType: message` scrubbed then cut to 300 chars, then released through the same gate; non-dict args, non-str/list/dict/bytes names, non-str keys and deep nesting return typed `UNKNOWN_TOOL`/`BAD_ARGUMENTS`; the returned `tool` label is a known tool name or the fixed word "unknown", never the caller's text |
| F3 | `agents/tools.py::_withhold_if_credential` (new), called from `_scrubbed` and `_grade_case` | the release gate's own detector (`guards.guard_model_bound` -> `SecretStore.guard_prompt`) runs on the result/verdict BEFORE `save_result` / `save_verdict`; a reversed, base64 or folded secret withholds the outcome and nothing is written |
| F4 | `agents/tools.py::_call_texts`, `_children`, `_scalar_text` | scans the real string values (names, keys, leaves), not `repr()`, so a tab/newline/zero-width/soft-hyphen split is caught like bare `assert_no_raw_secrets`; walked iteratively with caps of 16 KiB of text, 256 nodes, depth 6, ahead of the scan (a 2 MB arg is refused without being scanned). Larger than the one-line change allowed, kept because the size cap and real-value scan share one walk |
| F5 | `tests/test_agent_read_only.py::test_get_persona_calls_the_wrapped_reader` | a mutant that stops calling `load_portal_persona` now fails |
| Wording | this manifest | AL3 claim and AT-570 corrected (below) |

Existing tests edited: `tests/test_agent_tools.py` (`_nav()` now uses an absolute URL because a bare `/home` is correctly refused under READ_ONLY; the login test now declares `login_case_id`, since the carve-out is limited to the declared login). New: `tests/test_agent_read_only.py` (260 lines; `test_agent_tools.py` is at 283 and the 300-line cap is enforced on tests too).

## Corrections to cycle 0 wording

- AT-570: cycle 0 said "`trigger_run` (UI) checks no approval today (AT-570, open)". That is wrong at this base. `ui/routes_runs.py:85` defines `_require_live_case_approval` and `trigger_run` calls it (`routes_runs.py:205`); it accepts a covering human grant or derives one from the project's provisioned credentials (D-068) and mints a row if none covers. AT-570 is `verified` in `qa/issues.jsonl`. The accurate difference: this tool requires an existing signed `LIVE_CASE` row and never mints one, so it can be stricter than the UI when the only grant would have been credential-derived. If the owner wants parity, that is a decision to record.
- "AL3 in full" replaced by the exact statement above.

## Acceptance criteria claimed

| id | claim | where proved |
|---|---|---|
| AL2 | IN PART: 5 of the 7 named tools. Each body calls the existing function named by `ToolSpec.wraps`. `report` and `capture_network` are HELD | `test_every_tool_names_a_real_existing_function`, `test_run_case_wraps_*`, `test_crawl_wraps_*`, `test_read_tools_and_grade_wrap_*`, `test_get_persona_calls_the_wrapped_reader` |
| AL3 | (a), (b), (c) for `crawl` and `run_case`, (c) per the table; each asserts zero sessions and zero stage calls | `test_al3a_*`, `test_al3b_*`, `test_al3c_*`, `test_read_only_refuses_each_state_changing_step` (32 rows), `test_read_only_still_runs_reads` (7), `test_off_domain_and_non_http_navigation_is_refused_under_every_policy` (33), `test_allow_writes_*` (14 + 1), `test_login_carve_out_is_narrow` (8), `test_the_declared_login_case_signs_in_under_read_only` |
| AL6 | IN PART: the tool boundary only (call arguments, stage results, stored result, the grade prompt gate). Planning prompts and skill bodies HELD | `test_al6_*`, `test_a_folded_secret_in_a_stage_result_is_never_stored`, `test_a_stage_session_or_judge_failure_is_a_scrubbed_typed_refusal`, `test_malformed_calls_*` (13), `test_a_secret_split_by_whitespace_*` (4), `test_oversized_arguments_*` |

## Criteria held (verbatim ids) and why

- **AL1** (built with `create_deep_agent`, `deepagents>=1.7`): HELD. Needs the dependency, and the `>=1.7` floor resolves to nothing.
- **AL4** (skills loaded via `skills=`): HELD. A framework argument; the slice builds no agent.
- **AL5** (a T-172 trace span per agent/tool call): HELD. Needs operation/parent identifiers in `schema/trace.py` and `core/trace.py`, which D-042's `Changes-authorized` does not list.
- **AL7** (subagents only where judgement is needed): HELD. Delegation is the framework's.
- AL2 remainder (`report`, `capture_network`) and AL6 remainder (framework planning prompts, skill bodies): HELD with AL1.
- AL8-AL13 belong to T-180/T-181.

## New-module table (D-082 item 1)

| module | lines | one job | named by |
|---|---|---|---|
| `src/autotester/schema/agent_layer.py` | 96 | the tool names, effects, refusal classes, per-tool args and the outcome a model sees | brief section 4; contract AL2/AL3 |
| `src/autotester/agents/__init__.py` | 7 | package docstring | `docs/plan.md` row 16 and `qa/QUEUE.md:296` |
| `src/autotester/agents/context.py` | 39 | the trusted context a model can never choose | brief section 4 |
| `src/autotester/agents/guards.py` | 161 | the checks that run in code inside an acting tool | contract AL3 |
| `src/autotester/agents/tools.py` | 279 | the five stage tools and their one dispatcher | contract AL2 |
| `tests/test_agent_tools.py` | 283 | offline proof of AL2/AL3/AL6 for this slice (cycle 0) | brief section 6 |
| `tests/test_agent_read_only.py` | 260 | offline proof of the cycle-1 repairs | this fix cycle |

The package location follows `docs/plan.md:66` and `qa/QUEUE.md:296` (`agents/`), not the planning manifest's `stages/agent_layer.py`. The contradiction is still an owner question; this slice moves with one rename.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L. No builder full suite; file-scoped runs with `-o addopts=`, no CLI `-q` stacking; `autotester.__file__` confirmed under `D:\autoTesting\.worktrees\t179-lead-tester\src` (and under the falsification copy for those runs). TDD: `tests/test_agent_read_only.py` was written first and run RED (81 failed, 50 passed) before `guards.py`/`tools.py` were edited; it went to 131 passed after.
Pre-check[AL2]: 67a94fb1 uv run pytest tests/test_agent_tools.py -k "wraps or names_a_real or read_tools" -> 4 passed (plus F5 `test_get_persona_calls_the_wrapped_reader`, in the 131 below)
Pre-check[AL3a]: 67a94fb1 uv run pytest tests/test_agent_tools.py -k "al3a" -> 1 passed
Pre-check[AL3b]: 67a94fb1 uv run pytest tests/test_agent_tools.py -k "al3b or without_a_live_case" -> 2 passed
Pre-check[AL3c]: 67a94fb1 uv run pytest tests/test_agent_read_only.py tests/test_agent_tools.py -k "read_only or off_domain or allow_writes or carve_out" -> 119 passed, 12 deselected
Pre-check[AL6]: 67a94fb1 uv run pytest tests/test_agent_tools.py tests/test_agent_read_only.py -k "al6 or never_stored or scrubbed_typed or split_by or oversized or malformed" -> 23 passed, 108 deselected
Pre-check: 67a94fb1 uv run pytest tests/test_agent_tools.py tests/test_agent_read_only.py -> 131 passed
Pre-check: 67a94fb1 uv run pytest tests/test_explore_safety.py tests/test_execute.py tests/test_execute_new_actions.py tests/test_execute_assertions.py -> 92 passed (the crawler guard and execute stage, unchanged files)
Pre-check: 67a94fb1 uv run pytest tests/test_schema.py tests/test_doctor.py tests/test_explore_typing_guards.py tests/test_agent_loop.py -> 87 passed
Pre-check: 67a94fb1 uv run ruff check src tests scripts -> All checks passed!
Pre-check: 67a94fb1 uv run autotester doctor -> doctor: clean
Metrics: start=2026-10-12 end=2026-10-12 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=8 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9

## Falsification (throwaway copy of src, tests, scripts, docs under `scratchpad/fals-42df3e8e` on C:, outside the worktree; run with the worktree venv and `PYTHONPATH=<copy>/src`, `autotester.__file__` printed from the copy; the worktree was never edited; each file restored from the committed code and re-run green; the copy is discarded)

| Row | edit in the copy | test selection | before | after |
|---|---|---|---|---|
| AL3c | `_read_only_refusal` returns `None` first (the cycle-0 failure shape: nothing refused under READ_ONLY) | `-k "read_only_refuses_each or login_carve_out"` | 131 passed (baseline) | 31 failed, 9 passed |
| AL3c | login carve-out stops requiring the declared login case (`and walk.login` dropped) | `-k "carve_out or refuses_each"` | green | 13 failed (incl. `carve_out_is_narrow[second submit]`) |
| F2 | the two `except Exception` handlers narrowed to `ZeroDivisionError` | `test_a_stage_session_or_judge_failure_is_a_scrubbed_typed_refusal` | 1 passed | 1 failed |
| F3 | `_withhold_if_credential(ctx, clean)` removed from `_scrubbed` | `test_a_folded_secret_in_a_stage_result_is_never_stored` | 1 passed | 1 failed |
| F4 | size cap raised to 10**9 | `test_oversized_arguments_are_refused_before_any_secret_scan` | 1 passed | 1 failed |
| F4 | scan `repr(text)` instead of the real value | `-k split_by_whitespace` | 4 passed | 4 failed |
| F5 | `get_persona` stops calling the `load_portal_persona` reader | `test_get_persona_calls_the_wrapped_reader` | 1 passed | 1 failed |

The cycle-0 falsification table (8 rows, AL2/AL3a/AL3b/AL3c/AL6) still describes the unchanged parts; its AL3c row (`write_policy_refusal` returns `None`) is superseded by the two AL3c rows above.

## Open items (recorded, not built)

1. Owner question at the top (READ_ONLY CLICK / act-time enforcement / TEST_ACCOUNT).
2. Not in scope this cycle: Cyrillic homoglyph and letter-interleave secrets in a call argument; `Case.rubric_ref` path validation (`ctx.store.load_rubric(case.rubric_ref)`); a `{{SECRET:KEY}}` password placeholder typed into a non-login field in a TEST_ACCOUNT/ALLOW_WRITES run (the login carve-out covers READ_ONLY only; `BrowserSession.fill` scopes secrets to the page host); AL1/AL4/AL5/AL7; any `deepagents` dependency; module relocation (`agents/` vs `stages/agent_layer.py`).
3. Under TEST_ACCOUNT a non-Latin destructive label (a Hindi "delete") is still caught only by `DEFAULT_DENY_PATTERNS` words; that is the documented limit of `deny_patterns` (`policy_for` docstring) and D-053 makes the account's own permissions the boundary. READ_ONLY no longer depends on it because every CLICK is refused.
4. `run_case` requires an existing signed `LIVE_CASE` row (see AT-570 correction).
5. `docs/ARCHITECTURE.md` (150/150) is not edited (forbidden to this unit); its concept to file table does not yet name `agents/`. D-042 allows one line after PASS, as maker close-out.
6. `ToolOutcome.summary` of `run_case` carries `result.error` (scrubbed and gated); no length cap beyond the 300 chars of a stage error.
7. Owner questions that gate the REST of T-179, not this slice: `deepagents` version floor and dependency acceptance (needs a decision entry and a checker amendment of AL1; serialize the lock-file writer with T-167/T-202/T-174); package location; provider and trace approach for AL5; whether `tests/test_agent_layer.py` (the goal `done_check`) is checker-owned.
