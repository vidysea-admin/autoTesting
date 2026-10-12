# Verdict - t205-g10-headroom, coordinator B (blind), repair check
Bound to D:/autoTesting. Cycle checked: 1. Policy-Version: proportional-verification/2026-10-10.9. Checkout: D:/autoTesting/.worktrees/check-t205-r1-b (detached fb93776b, left in place). Head fb93776b (product 57cec910). Repair base 0b8325b6 verified an ancestor of head. Date 2026-10-11.

## Check plan
Manifest `Status: ready-for-check`, `Fix cycle: 1`, `--lint-manifest` exit 0. Failed list: TF6. Plan: re-run TF6; criteria whose input files the repair diff touches (TF7 via `safe_names.py`, TF1/TF2 via the two guard tests, TF8 via `team_enums.py`); affected tests; step 4c on the repair diff (9 files) plus a whole-unit scope scan (34 files, all named in "What changed"); end-to-end data compatibility; hostile names on this Windows box; one falsification per repaired criterion. Instruments: `uv --directory <checkout> run ...` for ruff, doctor, pytest and `autotester.__file__` (all inside the checkout). Earlier runs that used `uv run --project` after a `cd` into the tree were redone with `--directory` (maker note): `redo-affected-with-directory.txt`, `redo-proof.txt`.

## Verdict block
VERDICT: PASS
SCOREBOARD: 8/8 criteria met (TF6 repaired and re-run; TF1 TF2 TF7 TF8 re-run on touched inputs; TF3 TF4 TF5 inputs untouched by the repair, cycle-0 result kept), invariants not enumerated in this contract
TIER: M (multi-file behaviour refactor; TF2 treated as L by the contract, dual-trigger src/autotester/stages/run_launcher.py:179)
FAILURES: none
CAPABILITY-COVERAGE: 12/12 repair falsification rows reproduced in isolated copies (table below)
LIVE-BROWSER: not-applicable (no route, template or page changed; changed paths are schema, core, tests, docs/MAP.md)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Per-criterion
- TF6 MET. `uv --directory <tree> run pytest tests/test_project_schema_team.py tests/test_team_enums_home.py` inside the 665-test affected run: all green. `Source.uploaded_by/uploaded_at/origin` exist, default None, `origin` is the closed `SourceOriginKind`; `extra="forbid"` kept (`uploader=` rejected); id stays `src_21e38144fee2` with or without provenance. All 9 committed `projects/*/project.json` load and round-trip (`real-committed-data.txt`; the repo holds no committed `sources.jsonl`).
- TF7 MET. 569 green (`test_team_store.py` 50 + `test_safe_names_windows.py` 519). Hostile names on Windows: table below.
- TF1 MET, TF2 MET (CRITICAL). `test_run_launcher*.py` 21 green. Guard behaviour: table below. The criterion's own mutations (Run pasted back, approval removed, `skip_approval` parameter) are caught.
- TF8 MET. ruff "All checks passed", doctor "clean", `test_team_enums_home.py` 3 green; `SourceOriginKind` lives in `schema/team_enums.py` only; `docs/MAP.md` row added.
- TF3, TF4, TF5: no input file touched by 0b8325b6..head (tests ran green in the 665 set anyway).
- Source users (`test_ingest*`, `test_orchestrate`, `test_reconcile_schema`, `test_cli_advice_resolves`, `test_ui_runs`, `test_ui_runs_live_case_approval`): 98 passed, 1 failed = the known red `test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen` (AT-792, not this unit).

## Data compatibility (stored shapes, `compat.txt`)
| Case | Result |
|---|---|
| sources + project written by the product's `ProjectStore` at base 0b8325b6 (git archive, `autotester.__file__` in the archive), read and re-written by head | ids unchanged (`src_21e38144fee2`, `src_c3372a9eb93e`); `sources.jsonl` bytes identical; `project.json` bytes identical |
| control: same rewrite by base code | identical (so no drift from the harness) |
| head writes a source WITH provenance | line gains `uploaded_by`, `uploaded_at` (`...Z`), `origin`; id equals the plain source's id; re-adding the plain source is idempotent (count 1) |
| base code (`extra="forbid"`) reads that provenance line | `ValueError ... 3 validation errors for Source ... Extra inputs are not permitted`; the whole `sources.jsonl` becomes unreadable by old code. Rollback after provenance is written is not safe; no criterion asks for it. PROPOSED-ISSUE P1 (low) |
| head reads its own provenance line | loads, `origin=SourceOriginKind.UPLOAD` |

## Hostile names (`hostile-names.txt`, scratch root, real `team_path`/`create_marker`)
75 names tried; every refusal is `UnsafeName` before any IO, validator and `create_marker` agree on all 75, a sentinel file beside the root is intact, nothing exists outside the root, no device was opened.
| Refused (no file) | Accepted and created as a regular file named exactly so |
|---|---|
| `ab:stream`, `nul:`, `NUL:x`, `a::$DATA`, `C:`, `c:\x`; `CON`, `con.txt`, `CON .txt`, `CONIN$`, `conin$.x`, `CONOUT$ .txt`, `LPT¹`, `lpt².log`, `COM³`, `com¹ .x`, `COM1`, `com9.x`, `LPT1 `, `AUX .tar.gz`, `prn  .x`; `x.`, `x `, `x..`, `...`, `..`; `< > " \| ? *` names; `/abs`, `a/b`, `a\b`, UNC; NUL/TAB/0x1f/0x7f; 121 chars | `conn`, `console`, `com10`, `com0`, `lpt0`, `aux-1`, `nul-x`, `a$b`, `$MFT`, `CLOCK$`, `a b`, `a.b`, `a..b`, `é`, NFKC look-alikes (`ＣＯＮ`, `ＮＵＬ`, `COM１`, `LPT⁴`, `ａｂ`, fullwidth `：／＼．`), `con<NBSP>`, `CON<ZWSP>`, 120-char name |
Windows treated every accepted name as an ordinary file (oracle: name present in the directory listing). NFKC look-alikes are accepted by design (no filesystem normalises them to separators or devices here).

## Falsifications (isolated copies of `git archive fb93776b`, green before / red after; `falsifications*.txt`)
| Row | Edit | Before | After |
|---|---|---|---|
| TF6 | delete `uploaded_by` | 11 pass | 3 fail |
| TF6 | `origin` -> `str` | 11 pass | 2 fail (closed-set, round-trip) |
| safe_name | `_FORBIDDEN` check off | 568 pass | 48 fail |
| safe_name | `conin$`,`conout$` removed | 568 pass | 26 fail |
| safe_name | trailing-space strip removed | 568 pass | 90 fail |
| TF1 | `Run as _R` alias + `_R(...)` in `ui/helpers.py` | 21 pass | 1 fail (single Run call site) |
| TF1 | `partial(run_cases_traced as _go, 1)` | 21 pass | 1 fail (executor call site) |
| TF1 | (a) `getattr(importlib.import_module(...), 'run_cases_' + 'traced')(...)` | 21 pass | 21 pass: NOT caught |
| TF1 | (a') `getattr(run_launcher_module, 'run_cases_traced')(...)` literal | 21 pass | 21 pass: NOT caught |
| TF2 | new `RunSeams.skip_approval: bool = False` (unhonoured) | 21 pass | 1 fail (pinned allow-list) |
| TF2 | field honoured, valid hand-built `RunApproval` in `prepare_run` | 8 pass | 2 fail (behavioural, both sentinels) |
| TF2 | field honoured only when value is a real `RunApproval` | 8 pass | 10 pass: behavioural test blind (sentinels are not RunApproval); the pinned allow-list catches the added field |
My first honoured-field mutant built an invalid `RunApproval` (ValidationError) and passed vacuously; it was rebuilt with valid fields and the red above comes from the rebuilt one (`m6c-debug*.txt`).
Judgement on (a): the contract wording is "one call site of `Run(` and `_execute_with_trace(`"; a string-resolved `getattr`/`importlib` call is not a call site in the AST sense, the manifest discloses it, and the pre-existing grep clause would not see the concatenated form either. TF1 and TF2 stay MET; nothing a tester can reach through the launcher's surface skips the gate. Old vs new guard tests: no assertion weakened on what it covered. Narrowing noted: the old banned-name test scanned every function in `run_launcher.py`; the new exact allow-list pins `launch_run`, `prepare_run`, `require_live_case_approval` and `RunSeams` only (P3).

## PROPOSED-ISSUEs
- P1 {"severity":"low","feature":"team-foundation","title":"Source rows with provenance are unreadable by pre-T205 code (extra=forbid); rollback past this commit needs a data strip","evidence":"compat.txt BASE read of head-with-provenance: ValueError, 3 validation errors"}
- P2 {"severity":"low","feature":"team-foundation","title":"TF1 AST scan misses string-resolved executor calls; a cheap extension flags string constants equal to run_cases_traced/_execute_with_trace outside run_launcher.py","evidence":"falsifications-3-guard.txt M5a/M5b: 21 passed after"}
- P3 {"severity":"low","feature":"team-foundation","title":"test_the_gate_is_not_a_parameter no longer scans helper functions in run_launcher.py; test_no_seam_value_skips_the_approval accepts any Exception, so a bad sentinel can pass vacuously","evidence":"tests/test_run_launcher_approval.py:121-170; m6c-debug.txt (vacuous pass on ValidationError)"}
- P4 {"severity":"low","type":"process","title":"Check ran 164 min wall: copying a 2,600-file archive per mutant took 3+ min each on this Windows host (Defender); excluding qa/ and .goal/ from mutant copies cut it","evidence":"Metrics slow: line"}

## Leftovers
Checkout D:/autoTesting/.worktrees/check-t205-r1-b (detached, left in place, `.venv` inside). Scratch mutant copies and archives deleted. Evidence: qa/evidence/t205-g10-headroom-r1-B/. No qa/issues.jsonl write, no merge, no push, no manifest flip. Blindness kept: no t205 verdict, checkpoint or evidence file was opened.

Metrics: start=2026-10-11T09:48 end=2026-10-11T12:32 wall_min=164 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=12 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=9840 mutants=12 defects_unit=0 defects_6c=0 slow: mutant copies ~150 min (Windows file copy contention; M-copy of 2,600 files per mutant)
