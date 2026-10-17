# Manifest — at699-sweep-stamp
**Contract:** qa/contracts/living-ledger.md L11
**Goal task:** none (issue row AT-699, `qa/issues.jsonl:710`)
**Date:** 2026-10-18
**Fix cycle:** 0
**Dual check:** no (a local append to a tracked bookkeeping file through a new CLI command; no hook, settings, auth, tenancy or production-data write)
**Issues addressed:** AT-699 (option (a) only; option (b), the PreToolUse guard, is out of scope and stays a gate)
**Executor:** claude-sonnet-subagent
**Executor rationale:** single unit, one new module plus one registration line; fixtures only, no browser, model or network call, no `.env` read.
**Authority:** D-104 item 2 (Approved-by: Umesh 2026-10-17) authorizes the new module `src/autotester/cli_sweep.py`.

## Criterion (verbatim, qa/contracts/living-ledger.md L11)
> `qa/.last-sweep` is the checker's append-only sweep log: one line per sweep, history never rewritten. A writer
> `autotester sweep stamp "<line>"` (new `src/autotester/cli_sweep.py`, registered through `cli_subapps.py`; D-104 item 2 authorizes the new
> module) is the one documented write path, the `autotester ledger add` pattern. It appends exactly one line to `qa/.last-sweep`, creates
> nothing else, never truncates or rewrites existing content, and **refuses an empty or whitespace-only line with a non-zero exit, leaving the
> file byte-identical**. A line containing a newline is refused (one stamp = one line). If the file does not exist it is created with the
> one line. The writer adds no schema, migration or reformatting of existing lines, and the sweep's content (what a sweep records) is unchanged.
>
> **Verify:** a fixture file with N lines (use a tmp copy, never the real log): `autotester sweep stamp "x"` exits 0, the first N lines are
> byte-identical to before and line N+1 is `x`; an empty line and a whitespace-only line each exit non-zero and leave the file byte-identical; a
> two-line argument is refused and leaves it byte-identical; CRLF/LF of existing lines is preserved. **Sabotage:** open the file with `"w"`
> instead of `"a"` - the N-line fixture goes red; drop the empty-line refusal - the empty-line fixture goes red.

## What changed
- `src/autotester/cli_sweep.py:1-57` (new, 57 lines) - typer sub-app `app` with command `stamp`, plus `append_stamp(root, line)`: refuses blank or multi-line input (`StampRefused`, exit 2) before touching the disk; opens `qa/.last-sweep` with `"ab"` only; the new line borrows the log's own line ending (CRLF for the real log), and a log with no final newline gets one terminator first so lines never glue.
- `src/autotester/cli_subapps.py:13,21` - import `cli_sweep` and register `("sweep", cli_sweep.app)` (`cli.py` is at the 300-line cap and is not edited).
- `tests/test_cli_sweep.py` (new, 17 tests) - the L11 Verify fixture plus LF/CRLF/no-final-newline/missing-file/accumulation cases; every test points `AUTOTESTER_ROOT` at a tmp tree, the real log is never touched.
- `tests/golden/cli_commands.json` (+4 lines) and `tests/test_cli_subapp_hook.py:32` - the pinned command listing and the registered-groups set now include `sweep`; both went red on the registration and are the intended update.
- `docs/MAP.md` - regenerated with `autotester map` (+1 line for the new module); the generated file, not hand-edited.

## Verification scope
Policy-Version: proportional-verification/2026-10-17.13
Tier: M (new public CLI command + shared `cli_subapps.py` edit)
Base / checked state: base 4df66032, head = the commit that carries this manifest (see `git log`)
Gate answers: D-104 item 2 (new module authorized); option (b) not built.
Affected tests / full-suite trigger: `shard_suite.py --affected 4df66032..HEAD --list --candidates` reports `integration-required` (exit 2: conftest/dynamic-glob uncertainty, 488 selected); no .13-2 full-suite trigger applies (no tier-L, no dependency or conftest change by this unit), so the behaviour-scoped set below plus the collection check is the builder's run.
Tests[L11]: tests/test_cli_sweep.py — every L11 Verify clause (append and byte-identical history, CRLF/LF preserved, empty/whitespace/multi-line refusal leaves the file identical, missing file created, registration)
Tests[L11]: tests/test_cli_subapp_hook.py — the sub-app registration seam `cli_subapps.py` that this unit edits; its golden `tests/golden/cli_commands.json` and the registered-groups set gained `sweep` (the only edits to existing test files)
Sibling: src/autotester/cli_subapps.py:16-21 — changed (one new pair appended, existing pairs and `register_subapps` untouched)
Falsification[L11]: copy-mutants outside the worktree (below)
Pre-check[L11]: 527e737 uv run pytest tests/test_cli_sweep.py tests/test_cli_subapp_hook.py -> 21 passed t=3 blobs=tests/test_cli_sweep.py:0a91cfb,tests/test_cli_subapp_hook.py:d650ebf
Falsification[L11]: copy-mutants in C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/e46c0e51-15e9-4a31-a0b0-cf49de9d445f/scratchpad/at699-sweep-stamp/{base,w,a} (outside the worktree): base 17 passed; `"ab"`->`"wb"` (contract sabotage 1) 4 failed (test_stamp_appends_one_line_and_keeps_history_byte_identical, test_stamp_keeps_lf_style_of_an_lf_log, test_stamp_after_a_log_with_no_final_newline_does_not_glue_lines, test_repeated_stamps_accumulate_in_order); empty-line refusal dropped (`if not line.strip():`->`if False:`, sabotage 2) 5 failed (4 whitespace cases of test_empty_or_whitespace_line_is_refused_and_file_unchanged plus test_refused_stamp_does_not_create_a_missing_log; the bare "" case stays refused by the one-line splitlines guard, which is a second defence, not a gap)
Metrics: wall_min=40 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 policy=proportional-verification/2026-10-17.13 tests=21

## How to verify (commands + expected)
- `uv run pytest tests/test_cli_sweep.py` → expected: 17 passed
- `uv run ruff check src tests scripts` → expected: All checks passed!
- `uv run autotester doctor` → expected: only the pre-existing `stale-generated: docs/SNAPSHOT.md` (not this unit's; regenerated by the loop) and the decision-citation advisories

## Actual outputs (my own run, 2026-10-18)
- `uv run pytest tests/test_cli_sweep.py tests/test_cli_subapp_hook.py` -> `21 passed`.
- Wider run of the behaviour-adjacent set (all `tests/test_cli*.py`, `test_doctor*`, `test_map*`; 17 files) on 6cd070cf, before the golden update: `3 failed, 309 passed`. Two failures were the golden/registered-groups tests this unit's registration changes (fixed in 527e737, now green). The third, `tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve`, reports `ui/routes_crawl_approval.py:184`, a file this unit does not touch (`git diff 4df66032..HEAD --stat` lists only cli_subapps, cli_sweep, MAP, the two test files, the golden and this manifest): not mine; the checker should confirm it is red on base.
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run pytest --collect-only -q` -> exit 0 (every test file imports).
- `uv run autotester doctor` -> 1 violation: `stale-generated: docs/SNAPSHOT.md` (pre-existing, named in the brief as not this unit's), plus the decision-citation advisories. `docs/MAP.md` is fresh after `autotester map`.
- `uv run autotester --help` lists `sweep  The checker's append-only sweep log (qa/.last-sweep).`

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| L11 | appends one line, history byte-identical, never truncates | tests/test_cli_sweep.py::test_stamp_appends_one_line_and_keeps_history_byte_identical | `"ab"` -> `"wb"` | base `17 passed`; mutant `4 failed` (this node among them) |
| L11 | empty/whitespace-only line refused, file byte-identical | tests/test_cli_sweep.py::test_empty_or_whitespace_line_is_refused_and_file_unchanged | `if not line.strip():` -> `if False:` | base green; mutant `5 failed` (4 blank cases of this node) |
| L11 | multi-line argument refused | tests/test_cli_sweep.py::test_multi_line_argument_is_refused_and_file_unchanged | (none named in L11; covered by the `splitlines() != [line]` guard, which is not mutated) | green on base |
| L11 | CRLF/LF of existing lines preserved; missing file created | test_stamp_keeps_lf_style_of_an_lf_log, test_missing_log_is_created_with_exactly_the_one_line | `"ab"` -> `"wb"` | LF node red on the `wb` mutant |
| L11 | registered through cli_subapps, cli.py untouched | test_sweep_is_registered_in_subapps, tests/test_cli_subapp_hook.py | remove the SUBAPPS pair | red (verified when the pair was in place and the golden stale) |

## Live-browser verification
Not applicable: a CLI-only unit, no screen, route or template.

## Status: checked-PASS (qa/verdicts/at699-sweep-stamp.md, cycle 0)
