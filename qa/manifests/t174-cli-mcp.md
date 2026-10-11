# Manifest — t174-cli-mcp
**Contract:** qa/contracts/cli-mcp.md (CM1-CM5, DRAFT; goes ACTIVE on this unit's first checker PASS); also consent.md CN1/CN9 and core-invariants.md (secret scrub, one concept one place, dependency declaration)
**Goal task:** T-174 (CLI contract and MCP surface; D-041, D-071)
**Date:** 2026-10-12
**Fix cycle:** 0 (fresh branch from master; see "Lineage" for the earlier candidate's cycles 0-2, which are history and not reset)
**Base:** 822dca2bbeb3 (master with merge 09fc65a8 of t205-g10-headroom). Master has since moved to d867024f (t197 merged); `git merge-tree HEAD master` reports no conflict.
Policy-Version: proportional-verification/2026-10-10.9
**Tier:** L. Triggers: a new third-party dependency (`mcp`), and a new machine surface (CLI JSON + MCP) over the secret scrub and the `RunApproval` gate.
**Dual check:** required. The builder adds no approval or secret logic of its own, but an MCP tool that can launch a run and one that returns stored run evidence are a security surface, so the honest answer is yes.
dual-trigger: security src/autotester/run_ops.py:154 (the one `launch_run` call both CLI and MCP reach; the approval gate is `run_launcher.require_live_case_approval`, unchanged)
dual-trigger: security src/autotester/run_ops.py:67 (`_scrubbed`, the last stop before any stdout / MCP output; C5)
**Persona walk:** skip (no screen, route or template; API-only operator / CI / MCP surface; no `ui/` file touched)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Executor rationale:** one build unit with a full brief; fakes only, no real browser, model call, network or `.env` value read or printed.

## Status table: what master already had, what this unit builds, what is HELD
Master (822dca2b) had nothing for CM1-CM5: `grep -rniE "mcp|ExitCode|--output|dry.run" src` found no CLI exit-code table, no JSON mode, no dry run, no `mcp` module or dependency. `doctor` exits 0/1 only.

| Criterion | On master | Built here | Held |
|---|---|---|---|
| CM1 one exit-code table, every code provoked | no | yes: `schema/cli_output.py::ExitCode` (OK 0, TEST_FAILED 1, USAGE 2, RUN_REFUSED 3, INFRASTRUCTURE 4, INTERNAL 5), rendered into `run --help`; per-code provoking tests; `doctor` 0/1 untouched | nothing, except that Click's own parser errors exit 2 outside this table (see CM2 hold) |
| CM2 `--output json` typed, scrubbed | no | yes: `RunReport`/`CaseOutcome` (`extra="forbid"`), one JSON document on stdout, progress to stderr, `Redactor` over every string, fail-closed when the `.env` is unreadable | **the parser-refusal clause**: a bad `run <project> <extra-arg> --output json` is refused by Typer/Click before any of our code runs, and the usage text echoes the offending token (exit 2, empty stdout). Held on `qa/gates/t174-parser-recovery.md` (State OPEN, `Answered: pending`). Not decided here |
| CM3 `--dry-run` sends nothing | no | yes: `run_ops.plan_run` reads only; strict fakes + tree hash identical; same command without the flag and without approval exits 3 | nothing |
| CM4 MCP thin adapter, approval stands | no | yes: three tools `run_tests`, `get_report`, `get_catalog`; each calls the `run_ops` function the CLI calls; a run is `stages.run_launcher.launch_run`; no approval parameter anywhere | nothing |
| CM5 dependency declared here, no raw secret | no | yes: `mcp>=2.3.0` in `pyproject.toml` (this commit only), `check_dependencies_declared` clean; planted secret through a real stdio child | nothing |

### Owner question (the held criterion): parser recovery
When the CLI is called with malformed or partial input in machine mode (`--output json`), what must it do? Facts: today Typer prints its own usage error to stderr, echoing the offending argv token verbatim (which may be a secret pasted by mistake), exit 2, empty stdout. Options:
- **A. Wrap the parser.** In machine mode the CLI emits exactly one scrubbed `RunReport` (status `usage_error`, exit 2) for every Click usage error (extra or missing argument, unknown option, bad `--output` value) and no raw token on either stream. Cost: a custom Click group/command class at the Typer app construction (`cli.py:31`, at the 300-line cap) or an invocation wrapper; touches existing parser plumbing; needs the independent plan review the gate asks for.
- **B. Accept Click's default, scrub only what we render.** Parser errors stay Click's (exit 2, text on stderr, no JSON), documented as such in `--help`; CM2 is then amended by the checker to say "once arguments parse". Cheapest; leaves the echo of a mistaken secret.
- **C. A + redact the echo only** (keep Click's text format but replace the offending token with `<arg>`); no JSON document on parser errors.
Recommended by the gate itself: authorize one bounded recovery of the existing parser output boundary (option A), existing files only, independent plan approval first. This unit does not touch `cli.py`'s Typer construction.

## Other open questions for the owner (none blocks the built slice)
1. **New-module authorization.** `qa/gates/new-module-authorization.md` names no T-174 modules (D-072 item 2 lists other units). New files: `src/autotester/run_ops.py`, `cli_run.py`, `mcp_server.py`, `schema/cli_output.py`; tests `tests/cli_mcp_fixture.py`, `tests/test_cli_mcp.py`, `tests/test_cli_mcp_boundary.py`. Cited basis: D-041 (names the MCP server and CLI contract) and D-071 (authorizes the SDK). Please confirm or amend.
2. **MCP SDK choice** (contract no-fire list leaves it open). Chosen: PyPI `mcp` (the official SDK, named in D-071), licence MIT (PyPI metadata, checked 2026-10-12), version 2.3.0 uploaded 2026-10-02, declared `mcp>=2.3.0` and pinned to 2.3.0 by `uv.lock` (101 added lock lines, no existing package moved; `uv lock --check` passes). New transitive packages: `mcp-types 2.3.0`, `opentelemetry-api 1.45.1`, `pyjwt 2.15.1`, `pywin32 312` (Windows marker), `sse-starlette 3.5.0`. Local stdio transport only; nothing listens on a socket.
3. **"No AI provider configured" is exit 3? 2? 4?** It arrives as `LaunchRefused(400)` from the launcher, the same status as "no cases" and "credential has no value", and the launcher carries no machine kind for it (changing `LaunchRefused` would grow `run_launcher.py`, at 299 lines, owned by others). So every 400 maps to USAGE (2) and only a failure during execution (`ProviderError`, `TimeoutError`, `OSError`, `PlaywrightError`) maps to INFRASTRUCTURE (4). Operators may prefer a missing provider to be 4.
4. **`ValueError` maps to USAGE** (a corrupt stored file or a pydantic error raised mid-run reads as "bad arguments", not 5). Review finding (low), kept because a corrupt `project.json` at load time is the case the tests pin. A narrower mapping is a small follow-up if wanted.
5. **Run attribution.** CLI and MCP runs are saved with `trigger=ci`, `requested_by="cli"` or `"mcp"`, `via=None`. No new `RunVia` member was added (`schema/team_enums.py` is T-200's neighbour). Confirm that is the label you want.
6. **`docs/ARCHITECTURE.md`** does not yet document the CLI contract or the MCP tools; the maker does not edit it (Lab Protocol). The checker/owner should authorize the section.
7. **Master has since moved** (d867024f); this branch is based on 822dca2b. No conflict in a trial merge.

## Lineage
Earlier candidate (branch `t174` at 7af87feb plus the uncommitted cycle-2 repair in `.worktrees/codex-t174-repair`) failed the cycle-2 check on exactly the parser-refusal clause and stalled at the fix-cycle cap. That work predated T-205 (`run_launcher`) and edited `ui/routes_runs.py`. This branch re-lands it as INPUT on current master: the schema, `run_ops`, `cli_run`, `mcp_server` and the cycle-2 SDK-boundary tests were ported, and the run path was rebuilt on `launch_run` so **`ui/routes_runs.py`, `stages/run_launcher.py` and `cli.py` are not touched** (T-200 and AT-774 own neighbouring files). The cycle counter is not claimed as reset; whether this fresh re-landing counts as the named human recovery attempt is the gate's question, and the built slice here does not depend on it.

## What changed
- `src/autotester/schema/cli_output.py` (new, 71): `ExitCode`, `EXIT_CODE_MEANING`, `CaseOutcome`, `RunReport`, all `extra="forbid"`.
- `src/autotester/run_ops.py` (new, 182): `perform_run` (a run is `launch_run(..., trigger=CI)`; dry run is `plan_run`, reads only), `get_report`, `get_catalog`, `stored_run_report`, `exit_code_for` (the one exception-to-code table), `_scrubbed`/`error_report` (C5, fail closed), `_open` (slug check), `RUN_SEAMS` (test seam, looked up at call time). `run_id` is a path segment: `[A-Za-z0-9][A-Za-z0-9_-]*`, and a loaded run must carry that id and the project's slug (reviewer finding, fixed, see below).
- `src/autotester/cli_run.py` (new, 122): `run`, `catalog`, `report show`, `mcp`; `--output text|json`, `--dry-run`; the exit-code table rendered from the enum into `run --help`; `attach_commands(app)` joins the existing `report` group (or creates one on an app that has none).
- `src/autotester/mcp_server.py` (new, 109): stdio `MCPServer` with exactly `run_tests`, `get_report`, `get_catalog`; SDK-error middleware and log sanitizer from the earlier cycle-2 repair; imports only `run_ops`, `schema`, `core.env`.
- `src/autotester/cli_subapps.py` (25, was 24): `register_subapps` also calls `cli_run.attach_commands(app)`. `cli.py` is unchanged (293).
- `pyproject.toml`: `mcp>=2.3.0` and a `B008` per-file ignore for `cli_run.py` (same idiom as `cli.py`/`cli_issues.py`). `uv.lock`: +101 lines.
- `tests/cli_walk.py` (+3): the `mcp` command is walked with an extra argument so the smoke matrix cannot start the server. `tests/test_cli_harness_safety.py` (+13): proves that.
- `tests/golden/cli_commands.json` (74 -> 86 lines): regenerated from the live listing in the file's own format (CRLF); the diff is exactly three added rows at the head (`run`, `catalog`, `mcp`).
- New tests: `tests/test_cli_mcp.py` (299), `tests/test_cli_mcp_boundary.py` (280), fixture `tests/cli_mcp_fixture.py` (103).
- `docs/MAP.md` regenerated (`autotester map`). `qa/briefs/t174-cli-mcp.md` copied from the main checkout.

## Advice-scan impact
`tests/advice_scan.py` / `tests/test_cli_advice_resolves.py`: no command here prints an operator instruction naming an `autotester <cmd>`; the refusals are the launcher's and `core/consent.py`'s existing wording. So `EXPECTED_SITES` and `EXPECTED_SITE_COUNT` are unchanged: **24 before, 24 after** (21 distinct sites before and after). That file passes (run in the affected set below).

## Review
`senior-software-engineer` agent (sonnet, read-only) on 4421e98b: Block, one high finding, plus three low. High: `run_id` unvalidated, so `report show demo ../../other/secretdir` resolved outside the project's runs directory and quoted a foreign file's content in the error text. Fixed in e5e7696f (`stored_run_report`: id pattern plus `run.id == run_id and run.project == slug`), test `test_an_unsafe_run_id_is_usage_and_reads_nothing` (5 cases, CLI + `get_report` + MCP tool), falsified below. Low findings: `ValueError` to USAGE (kept, owner question 4); `_open` repeats the launcher's slug check (kept: a dry run needs the check before any read, and `prepare_run` does not run on that path); direct `playwright` import in `run_ops` (kept for `PlaywrightError` classification, doctor clean). Reviewer's test gap "MCP `run_tests dry_run=true` over the real transport" is not covered (the in-process call is); recorded here, not closed.

## Verification scope
Test files run, one pytest process at a time with `-p no:xdist -o addopts=`: `tests/test_cli_*.py` (all), `tests/test_doctor.py`, `tests/test_hosting_deploy.py`, `tests/test_run_launcher.py`, `tests/test_run_launcher_approval.py` -> 277 passed. Repo-wide scanner tests among them: `tests/test_cli_advice_resolves.py` (site count 24 -> 24), `tests/test_cli_subapp_hook.py` (golden listing, `cli.py` <= 300 lines, throwaway sub-app), `tests/test_doctor.py`, `tests/test_cli_surface.py` + `tests/test_cli_harness_safety.py` (walk every shipped command), `tests/test_run_launcher.py` (one `Run(` / executor call site: still `stages/run_launcher.py` only). Importers of the touched modules (`cli_subapps`: `cli.py`, tests above) are covered. No full suite run (builder rule). Not run: `tests/test_ui_runs*.py` (no `ui/` file touched; the launcher is unedited). Affected-test list / full-suite trigger: `full-suite trigger: dependency manifest (pyproject.toml/uv.lock) + new third-party SDK`.
Code SHA: e5e7696f87894f07cf3600397426595edc9da6b3 (HEAD of `wave/t174-cli-mcp` before this manifest commit; the manifest commit changes no product file).
`uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean. `autotester map` run (docs/MAP.md), `autotester snapshot` run (no tracked change).

Pre-check[CM1]: e5e7696f87894f07cf3600397426595edc9da6b3 uv run pytest -p no:xdist -o addopts= tests/test_cli_mcp.py -k "every_code or each_code or timeout or help_documents or doctors_own" -> 10 passed (table test pins `ExitCode.__members__` so a collapsed alias is caught; one provoking test per code: OK 0, TEST_FAILED 1, USAGE 2, RUN_REFUSED 3, INFRASTRUCTURE 4, INTERNAL 5; a timeout is 4 not 5; `--help` shows the table)
Pre-check[CM2]: e5e7696f87894f07cf3600397426595edc9da6b3 uv run pytest -p no:xdist -o addopts= tests/test_cli_mcp.py tests/test_cli_mcp_boundary.py -k "json_stdout or printed_human or planted_secret or text_output or report_show or catalog_json or machine_error or unreadable_masking or text_catalog or credential_matching or unsafe_slug or unsafe_run_id" -> 31 passed (stdout parses as one document with no ANSI; planted secret absent from stdout and stderr and present as `[REDACTED]`; errors on an unknown or corrupt project are scrubbed on 6 surfaces; unreadable `.env` withholds all strings). EXCLUDES the held parser-refusal clause
Pre-check[CM3]: e5e7696f87894f07cf3600397426595edc9da6b3 uv run pytest -p no:xdist -o addopts= tests/test_cli_mcp.py -k dry_run -> 3 passed (strict fakes raise on browser, grader, socket; tree hash identical before and after, with and without a declared credential; the same command without the flag and without approval exits 3)
Pre-check[CM4]: e5e7696f87894f07cf3600397426595edc9da6b3 uv run pytest -p no:xdist -o addopts= tests/test_cli_mcp.py tests/test_cli_mcp_boundary.py -k "exactly_three or run_tool or server_calls or only_ever_started or attributed or sdk or rpc" -> 23 passed (tool set is exactly three; `run_tests` without approval starts nothing and returns code 3, no runs directory; with approval it runs and `get_report`/`get_catalog` return the schema; `run_ops` has one `launch_run(` call and no approval/skip/force parameter, `mcp_server` imports only `run_ops`/schema/`core.env`; SDK errors are typed and echo nothing)
Pre-check[CM5]: e5e7696f87894f07cf3600397426595edc9da6b3 uv run pytest -p no:xdist -o addopts= tests/test_cli_mcp.py -k "stdio or declared_dependency" -> 2 passed (real stdio child process, planted secret in the stored report and in malformed tool inputs absent from every response and from the child's stderr; `mcp` is in `pyproject.toml` dependencies and doctor reports no `undeclared-dependency`). `git diff 822dca2b HEAD -- pyproject.toml` shows the line arriving in this unit's commit only
Pre-check: e5e7696f87894f07cf3600397426595edc9da6b3 uv run pytest -p no:xdist -o addopts= tests/test_cli_*.py tests/test_doctor.py tests/test_hosting_deploy.py tests/test_run_launcher.py tests/test_run_launcher_approval.py ; uv run ruff check src tests scripts ; uv run autotester doctor -> 277 passed; All checks passed; doctor: clean
Falsify[CM1..CM5, run_id]: below (throwaway copy `C:/Users/Lenovo/AppData/Local/Temp/t174-falsify-<8 hex>` per script run; `PYTHONPATH` = the copy's `src`, import path printed and asserted inside the copy; one anchor per edit asserted unique; copy deleted by its exact name afterwards; script outside the repo)
mutant-cap-raise: 8 mutants over 5 criteria plus the review-fix, one per contract Sabotage clause (CM1 collapse, CM2 print and scrub removed (two clauses: stdout purity, C5), CM3 dry-run calls the provider, CM4 approval skipped and stage import (two clauses), CM5 dependency removed) and one for the reviewer's high finding.

## Falsification records
All reds are assertion failures, none an import or setup error. "before" and "restored" were run in the same copy.

| Criterion | Edit in the copy | Before | After | Restored |
|---|---|---|---|---|
| CM1 | `RUN_REFUSED = 3` -> `= 2` in `schema/cli_output.py` | 8 passed | 3 failed (table test on the collapsed code, `each_code[RUN_REFUSED]`, help test) | 8 passed |
| CM2 (stdout purity) | `typer.echo('running 2 cases...')` before the JSON in `cli_run._emit` | 7 passed | 7 failed (`RunReport` validation on stdout) | 7 passed |
| CM2 (C5 scrub) | `_scrubbed` no longer calls `scrub_obj` | 3 passed | 1 failed (`test_the_planted_secret_appears_nowhere`) | 3 passed |
| CM3 | `plan_run` calls `RUN_SEAMS.judge_factory(loaded)` | 3 passed | 2 failed ("an outward-facing seam was touched") | 3 passed |
| CM4 (gate) | `require_live_case_approval` returns a minted approval instead of raising 403 | 8 passed | 3 failed (refused run now exits 0; `assert (0 == 3)`) | 8 passed |
| CM4 (thin adapter) | `mcp_server.py` imports `autotester.stages.run_launcher` | 1 passed | 1 failed (`test_the_server_calls_the_functions_the_cli_calls`) | 1 passed |
| CM5 | `"mcp>=2.3.0"` commented out of `pyproject.toml` | 1 passed | 1 failed (`test_mcp_is_a_declared_dependency`) | 1 passed |
| review fix (run_id) | the id pattern check and the id/project binding removed from `stored_run_report` | 5 passed | 1 failed (`[../../other/secretdir]`) | 5 passed |
First attempt at the run_id mutation passed (5 passed after) because the test planted its file at the wrong path; the test was corrected (`projects/other/secretdir/run.json`) and the table row is the second, valid run.

## Held
- CM2 parser-refusal clause: see "Owner question". Nothing was built for it; `cli.py` is untouched. Until the owner answers, `run demo <extra> --output json` still yields Click's text usage error with the token echoed, exit 2, empty stdout. This is the same defect the cycle-2 checker found, honestly carried, not fixed.
- Hence CM2 as a whole cannot PASS on this unit; the checker may PASS CM1, CM3, CM4, CM5 and CM2 minus the clause, or hold the unit, per its judgment.

Metrics: start=2026-10-12T00:00Z end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=8 defects_unit=0 defects_6c=0

Status: ready-for-check
