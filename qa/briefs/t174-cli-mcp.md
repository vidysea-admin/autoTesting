# Build brief - t174-cli-mcp (T-174, readiness pass 2026-10-11, NOT-DISPATCHABLE: STALLED at the fix-cycle cap behind an unanswered human gate)

Written by a read-only readiness pass. Nothing here was built or run. Where the repo does not say, this brief says `unknown`.
Verdict: **NOT-DISPATCHABLE.** Hard blocker: `qa/gates/t174-parser-recovery.md` is `State: OPEN` with `Answered: pending`. The unit has used its two normal repair cycles (`Fix cycle: 2`, manifest `Status: STALLED`); a third build may start only as one separately named, human-authorized recovery attempt, and only against an independently approved seam plan, which does not exist yet. Two further preconditions: the repo cites no authorization for the unit's new modules, and the unit needs a `pyproject.toml`/`uv.lock` writer slot. Dispatch trigger: the gate line is answered yes, a plan review picks the parser seam, a module authorizer is cited, and the lock slot is free.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9` for the recovery attempt. History: cycles 0-2 ran under `proportional-verification/2026-10-07.7` and keep that stamp; do not rewrite them.
- Tier: **L**. Triggers: a dependency addition (`mcp>=2.3.0`, D-071); a changed secret and approval boundary (output scrubbing C5, the `RunApproval` gate CN1/CN9); a refactor of the approval-gated run path (`ui/routes_runs.py::run_project`).
- `Dual check: required`. Triggers: `security src/autotester/cli_run.py:108` (the default Typer command whose parser refusal echoes untrusted argv, the open cycle-2 finding) and `security src/autotester/run_ops.py` (the output scrub gate; exact line `unknown`, cite it in the manifest). Cycle-2 verdict `qa/verdicts/t174-cli-mcp.md` confirms the unit is judged as security tier L.

## 2. Root and base

- Root: `D:/autoTesting`
- Base: master `3a16616cf2c99a63c8d763150a1ca6410dfc0acc` (re-read at dispatch). The candidate's base is `3adc00d8` (T-125 merged); master has moved by catalog/bench/eval_compiler work only, none of it in T-174 files (`git diff --name-only 3adc00d8 master -- src pyproject.toml uv.lock` lists `schema/ai_check.py`, `bench.py`, `catalog.py`, `portal_persona.py`, `scenario.py`, `stages/ai_catalog.py`, `bench.py`, `eval_compiler.py`, `knowledge_graph.py`). A trial merge of the candidate into master conflicts only in `docs/MAP.md`.
- Branch: fresh `wave/t174-cli-mcp-recovery` from master. Reason: D-080 item 1 (master is the single trunk; worktrees and branches are INPUT, re-landed unit by unit). INPUT sources: branch `t174` / `codex/t174-repair` committed at `7af87feb5c508931bcb890a8c98aed96159202f3` (one commit ahead of `3adc00d8`) PLUS the uncommitted cycle-2 repair in the dormant worktree `D:/autoTesting/.worktrees/codex-t174-repair` (modified: `cli_run.py`, `mcp_server.py`, `run_ops.py`, `tests/cli_walk.py`, `tests/test_cli_harness_safety.py`, `tests/test_cli_mcp.py`, `tests/test_cli_surface.py`, plus QA files). The uncommitted repair is the newest code: read it from the worktree path, not from git.
- Counter rule (gate text): "Fix cycle: 2 (normal repair cap reached; do not reset)". The fresh branch is a re-landing, not a reset: the manifest keeps `Fix cycle: 2`, records the work as one separately named human recovery attempt, and links the three prior failures. Whether a fresh branch from master satisfies "record one separately named human recovery attempt" is for the plan reviewer and Umesh to confirm in the gate answer (section 10).

## 3. Acceptance criteria (verbatim from `qa/contracts/cli-mcp.md`, status DRAFT, goes ACTIVE on T-174's first checker PASS)

### CM1 - One exit-code table, and every code in it is provoked by a test

Exit codes distinguish at least: **test failed**, **run refused** (no valid `RunApproval`, consent
gate), **usage / validation error**, **infrastructure or timeout**, **internal error**. The table is
defined in ONE place (one enum in one module, mirrored in the CLI's `--help`), not scattered
literals. `doctor`'s existing contract (0 clean, 1 violation) is unchanged.

**Verify:** for each code in the table, a fixture provokes it and asserts `exit_code ==` that code.
A code with no provoking test fails the check. Sabotage: collapse two codes to one value — the
named per-code test goes red on the assertion for the collapsed code, not on an import error.

### CM2 - `--output json` is machine output, schema-typed, and scrubbed

With `--output json` stdout carries **one valid JSON document and nothing else**: no ANSI, no
progress text (those go to stderr). The document is a Pydantic model in `schema/` with
`extra="forbid"` — not an ad-hoc dict — and carries the run id, per-case outcomes, verdict counts
and evidence paths. No secret value appears in it (C5).

**Verify:** parse stdout with `json.loads` and validate against the model; run with a planted secret
value in the fixture project and assert the value appears nowhere in stdout or stderr
(`Redactor.scrub` is the gate). Sabotage: `print()` one human line to stdout — the parse test goes red.

### CM3 - `--dry-run` sends nothing and starts nothing

A dry run launches no browser, makes no provider call, opens no network connection, and creates no
run directory or `RunState`. It reports what **would** run (case ids and count). It is an offline
exercise of the code path, never a weaker run that quietly does real work.

**Verify:** run a fixture project with the browser factory and every provider replaced by fakes that
**raise on use**, and the filestore tree hashed before and after — identical hashes, exit 0, and the
report lists the case ids. The same command **without** `--dry-run` and without an approval still
exits with the "run refused" code (a dry run is not a route around CN1). Sabotage: let the dry-run
branch call the provider — the raising fake turns it red.

### CM4 - The MCP server is a thin adapter over the existing functions, and the approval gate stands

The server exposes exactly **run tests**, **get report**, **get catalog** (D-041 names these). Each
tool calls the function the CLI already calls — no second implementation of a stage (C3). A **run**
tool call goes through the same `RunApproval` gate as every other entry point (CN1, CN9); the MCP
layer can neither grant nor bypass an approval. Tool outputs use the CM2 schema.

**Verify:** list the server's tools — the set equals the three names. Call **run** with no valid
approval: nothing starts (no run directory, no navigation), and the result carries the "run refused"
code. Grep the server module for an import of any stage's internals that the CLI does not also
use — none. Sabotage: skip the approval check inside the run tool — the refusal test goes red.

### CM5 - The MCP dependency is declared in this unit only, and no tool reads a raw secret

`mcp` (or whichever SDK the build picks) is added to `pyproject.toml` only within this unit
(C11) and `autotester doctor`'s `check_dependencies_declared` reports clean. No tool description or
output contains a secret value; **get report** returns the already-redacted report artifact.

**Verify:** `git diff` shows the `pyproject.toml` line arriving in this unit's commit and not
earlier; planted-secret test as CM2, run through the MCP transport.

### Also binding (verbatim)

- Contract no-fire list: "A hosted or remote MCP deployment, authentication for a network transport — local stdio server only until a decision says otherwise." / "The concrete choice of MCP SDK." / "Exit codes for commands that do not exist yet."
- The open finding that must close, from `qa/verdicts/t174-cli-mcp.md` (cycle 2, VERDICT: FAIL): "CM2 + core C5: the new `run` command's parser refusal bypasses the typed scrubbed output boundary. `src/autotester/cli_run.py:108` registers a default Typer command; `run_tests_cmd` at line49 and its run_ops output gate are never reached on an extra argument. The existing Typer app setup at `src/autotester/cli.py:25` formats that untrusted input directly as its usage error." Reproduction: `run demo <planted-secret> --output json` exits 2 with empty stdout and `Got unexpected extra argument(s) (synthetic-cli-parser-secret)` on stderr.
- Recovery scope the gate offers (`qa/gates/t174-parser-recovery.md`): "authorize one bounded human-approved recovery of the existing CLI argument-parser output boundary, existing files only, independent plan approval before implementation, fresh acceptance and no push without all required PASS." It is explicitly "not a request to waive CM2/C5, ignore a secret leak, reset counters, broaden credentials/target authority or run paid/live tests."

## 4. What exists and what is missing

- **On master:** nothing for CM1-CM5 (`grep -rniE "mcp" src pyproject.toml` empty per the contract; `cli.py` is 295 lines and `doctor` exits 0/1 only).
- **Committed candidate** (`7af87feb`, manifest `qa/manifests/t174-cli-mcp.md`): `schema/cli_output.py` (`ExitCode` OK 0, TEST_FAILED 1, USAGE 2, RUN_REFUSED 3, INFRASTRUCTURE 4, INTERNAL 5; `RunReport`; `CaseOutcome`, all `extra="forbid"`), `run_ops.py` (`perform_run`, `get_report`, `get_catalog`, `exit_code_for`, the one function set both surfaces call), `cli_run.py::attach_commands(app, report_app)` (registers `run`, `catalog`, `mcp`, `report show`; the exit-code table rendered into `run --help` from the enum), `mcp_server.py` (stdio server, exactly `run_tests`, `get_report`, `get_catalog`, imports only `run_ops` and `schema`), `ui/routes_runs.py` edited in place (`run_project(slug)` extracted from `trigger_run`, `plan_project_run` for the dry run, `RunNotStarted(HTTPException)` carrying an `ExitCode`), `cli.py` (+2 lines: import and `attach_commands`), `pyproject.toml`/`uv.lock` (`mcp>=2.3.0`). Cycle-0 and cycle-1 failures were operation-error and SDK-validation sinks.
- **Uncommitted cycle-2 repair** in `codex-t174-repair` (frozen, dirty, dormant): MCP middleware for SDK validation errors and a log sanitizer. Cycle-2 checker evidence: affected closure 292 passed, 1 skipped, 54.26 s; CM1, CM3, CM4, CM5 evidenced; eight isolated one-change mutations each baseline 0, intended red, restored 0. The one skip is the live Chromium serial entry-case test (RAM below the 3584 MB gate), not a PASS.
- **Missing:** the parser-boundary fix: machine-output mode must wrap Typer/Click argument errors (extra/missing arguments, unknown options, malformed `--output` mode, invalid project or run id, a secret inside an offending token) so a refused JSON invocation emits exactly one schema-valid scrubbed `RunReport` with the `USAGE` code and no raw argv or formatter traceback on either stream, while ordinary help and successful runs stay unchanged. The debug report (`qa/debug/t174-cli-mcp-cycle2.md`, "Smallest recovery proposal") says: "an independent plan reviewer must choose the exact existing Typer/Click extension seam and name existing files/functions." No such plan exists; the seam is `unknown`. Candidates the reviewer may weigh (not decided here): a custom Typer/Click command or group class set where the app is built (`cli.py:25`, `app = typer.Typer(help="AutoTester — AI automated end-to-end tester", no_args_is_help=True)`), or catching `click.UsageError` around invocation in `attach_commands`/`main`.
- Not on any branch: nothing documents the MCP tool list for `docs/ARCHITECTURE.md`; the maker does not edit it (Lab Protocol) and records the gap in the manifest.

## 5. Files the builder will touch (line counts: master where it exists, else the INPUT in the dormant worktree)

| # | Path | New/Existing | Lines | Note |
|---|---|---|---|---|
| 1 | `pyproject.toml` | existing | 74 | one line, `mcp>=2.3.0`, plus the ruff `B008` per-file ignore for `cli_run.py`; **lock writer, serialize** |
| 2 | `uv.lock` | existing | `unknown` (generated) | regenerate with `uv lock` on the new base; **lock writer** |
| 3 | `src/autotester/cli.py` | existing | 295 | +2 lines (import, `attach_commands`) -> 297; parser seam may need a few more, cap 300; T-178 also edits it |
| 4 | `src/autotester/cli_run.py` | **new** | 111 | commands; parser-boundary fix lands here or in `cli.py` per the plan review |
| 5 | `src/autotester/run_ops.py` | **new** | 152 | shared operations and the scrub gate |
| 6 | `src/autotester/mcp_server.py` | **new** | 109 | stdio MCP server, three tools |
| 7 | `src/autotester/schema/cli_output.py` | **new** | 71 | `ExitCode`, `RunReport`, `CaseOutcome` |
| 8 | `src/autotester/ui/routes_runs.py` | existing | 204 | extract `run_project`, add `plan_project_run`, `RunNotStarted`; the same file is edited by T-203/T-202/T-178/T-205/T-204 |
| 9 | `tests/cli_mcp_fixture.py` | **new** | 95 | shared fixtures |
| 10 | `tests/test_cli_mcp.py` | **new** | 300 | at the cap; new parser cases may not fit, see rule below |
| 11 | `tests/test_cli_surface.py` | existing | 237 (INPUT 300) | CLI surface; the INPUT repair brought it to the cap |
| 12 | `tests/test_cli_harness_safety.py` | existing | 184 (INPUT 295) | harness safety |
| 13 | `tests/cli_walk.py` | existing | 92 | walk helper |
| 14 | `docs/MAP.md` | existing | generated | last step, `uv run autotester map` |

- No other new file. If the parser tests cannot fit under the 300-line cap, STOP and report the exact file; do not create a `*_v2` or a near-duplicate. Whether a new test file is allowed is a plan-review question, not a builder choice.
- The four product modules (rows 4-7) and the fixtures (row 9) are new files: see section 8 for their missing authorizer.

## 6. Test scope (exact files and nodes; no directory, no full suite)

`uv run pytest <path>[::node]`, no `-q`. The goal task's done check is `uv run pytest tests/test_cli_mcp.py`, expect exit 0.

- `tests/test_cli_mcp.py` (file; 25 tests at cycle 0, includes `test_each_code_is_what_the_cli_exits_with[...]`, the table test, the help test, the MCP tool-set test, the planted-secret stdio test).
- `tests/test_cli_surface.py` and `tests/test_cli_harness_safety.py` (files, both touched by the repair).
- New parser-boundary cases (names `unknown`, to be fixed by the plan review): extra argument, missing argument, unknown option, malformed `--output`, invalid project id and run id, each with a planted secret inside the offending token; each asserts exit code `USAGE`, one schema-valid `RunReport` on stdout, no secret on stdout or stderr, no run directory, provider or browser touched. At least one must be a real subprocess in addition to `CliRunner`, and one isolated mutation must restore the old unsafe parser path and go red at the leak assertion.
- Run-path regression guards for the `routes_runs.py` refactor, by file: `tests/test_ui_runs.py` (250), `tests/test_ui_runs_live_case_approval.py` (`unknown` lines; the approval gate is one gate), `tests/test_ui_runs_parallel_trace.py`, `tests/test_ui_runs_parallel_crash_recovery.py`, `tests/test_ui_runs_serial_entry_mix_live.py` (the live Chromium one skips under the RAM floor; treat its skip as "not run", never as pass).
- `uv run ruff check <touched product and test files>`; `uv run autotester doctor` once at the end. Base `doctor` already reported one violation, `ledger-row-missing: T-125`, on the candidate's base per its manifest; re-check on current master and report the baseline rather than attributing it to this unit.
- Windows note: the stdio MCP test and the real-subprocess parser check need native asyncio; the default sandbox failed Windows asyncio startup in cycle 2 and the checker ran them on the real local runtime with synthetic data. Use synthetic secrets only; no real credential, provider, remote target or paid call.

## 7. Reachable test cases per criterion (happy path first)

**CM1** (a) happy: `autotester doctor` still exits 0 clean / 1 on a violation (unchanged); (b) one provoking fixture per code: `OK` 0, `TEST_FAILED` 1 (a case fails), `USAGE` 2 (bad arguments, no cases), `RUN_REFUSED` 3 (no valid `RunApproval`), `INFRASTRUCTURE` 4 (timeout or browser/provider outage, fake), `INTERNAL` 5 (injected unexpected exception); (c) the table is one enum, rendered into `run --help`; (d) sabotage: `RUN_REFUSED = 2` -> the RUN_REFUSED per-code test, the table test and the help test go red on the assertion.

**CM2** (a) happy: `run <project> --output json` stdout parses with `json.loads` and validates against `RunReport` (run id, per-case outcomes, verdict counts, evidence paths); (b) no ANSI, no progress text on stdout (they go to stderr); (c) a planted root credential appears in neither stream; (d) the cycle-2 failing case: `run demo <planted-secret> --output json` -> exit `USAGE`, exactly one scrubbed `RunReport`, no raw token, no formatter traceback, on stdout or stderr; same for missing argument, unknown option, malformed `--output`, invalid project and run id; (e) help and a successful run are byte-for-byte what they were; (f) sabotage: `print()` one human line to stdout -> parse test red; restore the unsafe parser path -> leak assertion red.

**CM3** (a) happy: `--dry-run` with provider and browser fakes that raise on use and a hashed filestore: identical before/after hashes, exit 0, the report lists case ids and count; (b) the same command without `--dry-run` and without an approval exits `RUN_REFUSED`; (c) sabotage: the dry-run branch calls the provider -> the raising fake goes red.

**CM4** (a) happy: an approved fake run through the MCP `run_tests` tool succeeds and returns the CM2 schema; (b) the tool set equals `{run_tests, get_report, get_catalog}`; (c) `run_tests` with no valid approval starts nothing (no run directory, no navigation) and returns `RUN_REFUSED`; (d) invalid SDK input returns a typed, scrubbed error (the cycle-2 middleware); (e) `mcp_server.py` imports only `run_ops` and `schema`, no stage internals the CLI does not use; (f) sabotage: skip the approval check -> the refusal test goes red; direct stage import -> red.

**CM5** (a) happy: `mcp>=2.3.0` is declared in `pyproject.toml` and `check_dependencies_declared` is clean; (b) the dependency line arrives in this unit's commit and not earlier (`git diff`); (c) the planted-secret test through a real stdio child process, stderr included; (d) `get_report` returns the already-redacted artifact; (e) sabotage: remove the declared dependency -> doctor goes red.

## 8. Gate answers

- **OPEN, blocks dispatch** - `qa/gates/t174-parser-recovery.md` (verbatim): `Answered: pending — no answer has been inferred from older generic approvals.` Its question: "authorize one bounded human-approved recovery of the existing CLI argument-parser output boundary, existing files only, independent plan approval before implementation, fresh acceptance and no push without all required PASS?" Its recommended direction: "authorize that exact scoped recovery." D-081 (owner asked for all remaining work to run) answered seven other inputs and did not answer this gate; do not infer an answer from it. Queue row `t174-cli-mcp` says `approved: 2026-10-10`, which approves the work, not the cap-breaking recovery.
- D-071 (`docs/DECISIONS.md:2141`): "(3) T-174: the `mcp` SDK dependency is authorized. The CLI stays a first-class surface next to MCP." (`Approved-by: Umesh`, chat 2026-10-07 per its Why.)
- D-041 names the three tools; D-018/D-068 keep the approval gate; `qa/gates/write-policy-tier.md` is not touched by this unit.
- **New-module authorization: `none` found.** D-072 item 2 lists T-176, T-202, T-203/T-204, Group 10, T-190 and `agents/`, not T-174; `qa/gates/new-module-authorization.md:77` reads `Answered: 2026-09-29 — A — "A: new ledger/citations.py (Recommended)", AT-710 only (standing-rule variant not chosen); Umesh via AskUserQuestion in session autotesting-23, re-confirmed to the maker session; recorded as D-057`. The candidate's manifest does not cite one either, and the cycle-0..2 checkers did not raise it. Precondition: cite the exact authorizer for `cli_run.py`, `run_ops.py`, `mcp_server.py`, `schema/cli_output.py`, or ask the owner a one-line gate.

## 9. UI surface and persona walk

- `Persona walk: skip (no screen, route template or visible control is added; the CLI and MCP are API-only surfaces, docs/plan.md row 14 says skip, and the cycle-2 checker's check plan records "API-only operator/CI/MCP surface")`.
- Caveat for the checker: `ui/routes_runs.py` is refactored (`run_project`, `plan_project_run`, `RunNotStarted`). Every UI status code and message must stay unchanged; the existing UI run tests above are the guard, and the Run button redirect (303 to `/projects/{slug}/report`) is asserted. If the refactor changes any UI behaviour, the persona walk flips to `required (tester)` and the browser lane applies.

## 10. Dependencies and conflicts

- Must clear first: (1) Umesh answers `qa/gates/t174-parser-recovery.md` (yes/no); (2) an independent plan review approves the exact parser seam and files (the same pattern as the T-177 and T-178 plan reviews; it can run now in parallel with those); (3) the module authorizer is cited; (4) a lock slot.
- Land order: after **T-178** (both edit `cli.py`: T-178 nets about -3 lines, T-174 adds +2; whichever lands second reconciles) and after **T-203** (queue line 40 makes T-203 the first to land in `ui/routes_runs.py`; T-174's refactor of `trigger_run` into `run_project` will conflict with it, T-202, T-178's `priority` parameter and T-205). Proposed order for `routes_runs.py`: t203, t178, t174 (rebasing its extraction onto the new `trigger_run`), then t205/t204. After **T-177** and **T-202** on `pyproject.toml`/`uv.lock` (queue line 86, one lock writer at a time): both browser-use and mcp resolve `mcp 2.3.0` (D-071), so the later writer re-runs `uv lock` and expects no package movement beyond its own.
- Shared files and proposed ONE owner each:

| File | Also edited by | Owner |
|---|---|---|
| `pyproject.toml`, `uv.lock` | t202, t167, t177, t179 | one writer at a time; T-174 last of the three named above |
| `cli.py` | T-178 (`expand_cases`), T-202 (`codex/t202-completion` edits it) | T-178 first (queue says `cli.py: this row` for T-174, which I propose to change: the real order is t178, then t174, then t202's hunk); `unknown` whether the queue owner line is amended by the maker |
| `ui/routes_runs.py` | t203, t202, t178, t205, t204 | t203 first (queue line 40), then t178's `priority` hunk, then T-174's extraction; one reconciler per landing |
| `docs/MAP.md` | every branch | last commit of each unit |

- Parallel-safe with: the T-177 plan review, the T-178 build (disjoint files except `cli.py`, `routes_runs.py` and the lock).
- Owner decisions: (a) answer the parser-recovery gate; (b) confirm that re-landing on a fresh branch from master counts as the named human recovery attempt and not as a counter reset; (c) the module authorizer; (d) whether the parser-boundary fix may add a test file or must fit the existing test files (they are at the 300-line cap).

## 11. Budget and process rules

- Budget: **L, 45 minutes** of builder wall-clock for the recovery attempt. Phase A (port INPUT + `uv lock` + MAP) and Phase B (the parser-boundary fix) are separate checkpoints; stop at 45 minutes and write state to the manifest. Do not start a third automatic normal cycle.
- The builder runs only the files and nodes in section 6; no full suite (one primary security full suite under the machine lock is a mandatory later step, run by the maker once, per the debug report). Do not rerun the already-failed discriminating proof repeatedly.
- Red first: write the parser-boundary tests and show them RED against the ported INPUT before the fix, then GREEN; import or setup errors do not count.
- Falsification only in a throwaway copy, one named green / red / restored run per changed criterion; never leave a mutant in the tree. Kill only PIDs the builder started, verified by identity first (the machine holder `PID10880` seen in cycle 2 was another unit's and must be left alone).
- Synthetic secrets only. No real credential, provider, external target, production write or paid call. The maker never edits `qa/contracts/`.
- Handshake is files: manifest `qa/manifests/t174-cli-mcp.md` carried forward with `Fix cycle: 2` and a named recovery attempt, `Status: ready-for-check`, `Policy-Version: proportional-verification/2026-10-10.9`, `Tier: L`, `Dual check: required`, the two `dual-trigger:` lines from section 1; verdicts at `qa/verdicts/t174-cli-mcp.md` (cycle 2 FAIL stays as history; the new check writes a new cycle section). Use `git -C D:/autoTesting ...`, never `cd X && ...`; no merge of `t174` or `codex/t174-repair`; no push without all required PASS.
