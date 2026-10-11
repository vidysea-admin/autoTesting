# t205-g10-headroom r1 A - falsifications and class attacks (scratch copies deleted after use)

Copies: git archive fb93776b into scratchpad, run with the tree's venv python and PYTHONPATH=<copy>/src
(autotester.__file__ confirmed inside each copy). The bound worktree was never edited.

## TF1 (alias/partial resolution in the AST scan)
- green before (copy): tests/test_run_launcher.py -> 5 passed.
- mutation: append to ui/routes_runs.py `from autotester.schema.run import Run as _R`, `functools.partial(run_cases_traced as _go, 1)`, `lambda: _R(id="x")`.
- red after: test_exactly_one_non_test_call_site_builds_a_run and ..._executes_the_cases FAIL on
  `assert ['stages/run_...utes_runs.py'] == ['stages/run_launcher.py']` (2 failed, 3 passed).
- differential: the repair-base test file (0b8325b6) run against the same mutated tree -> 4 passed (the old scan was blind to the aliases).

## TF2 (exact allow-list + behavioural RunSeams test)
- green before: tests/test_run_launcher_approval.py -> 16 passed.
- A: add `skip_approval: bool = False` field to RunSeams -> new test_the_gate_is_not_a_parameter RED; repair-base test file on same tree -> 8 passed (old guard blind).
- B: add `approved: bool = False` parameter to launch_run -> test_the_gate_is_not_a_parameter RED.
- C (contract mutation, approval call replaced by `approval = None`): 6 tests RED (3x refuses_before_anything_exists, 3x covering_approval_proceeds); the 8 per-field behavioural tests stay green (see PROPOSED-ISSUE 3).
- D (behavioural test falsification): prepare_run forges a RunApproval when `seams.free_ram_mb` is not a function -> test_no_seam_value_skips_the_approval[free_ram_mb-true] RED (1 failed, 15 passed). Seam-keyed skip that lets the run proceed is caught.
- E (a skip that only drops the approval, `None if seams.free_ram_mb is True`): survives, because RunBudget refuses a None approval downstream (ValueError before any dir/session). Not a bypass; the run cannot start without an approval object.

## TF6 (Source provenance)
- green before: tests/test_project_schema_team.py -> 11 passed.
- mutation: fold uploaded_by into the Source.id key -> test_origin_is_a_closed_set_and_provenance_never_moves_the_id RED (1 failed, 10 passed).
- class attacks (own script, repair base 0b8325b6 vs head, same inputs): `model_dump_json(exclude_none=True)` of 3 old-shaped sources is identical apart from created_at (store writers all use exclude_none); old lines load -> re-serialise byte-identical; Source.id identical old vs new for all 3; origin "email"/"Upload"/"" refused, null accepted (optional), unknown key refused, bad uploaded_at refused, uploaded_by=5 refused; no src/ code hashes or compares an unfiltered Source.model_dump (grep). Full `model_dump_json()` gains 3 null keys but nothing consumes it.
- Source constructions in src (adapters, drive_register, email_register, ingest, read_context, routes_sources): all keyword args, none sets the new fields, none breaks.

## TF7 (safe_name)
- green before: tests/test_safe_names_windows.py -> 519 passed.
- mutation: disable the `_FORBIDDEN` check -> the forbidden-character table goes RED (40 failed, 2 passed in -k forbidden_character). The full file hangs on the mutant: create_marker on `CONIN$` opens the console handle (the guard is what prevents this).
- attacks through safe_name, team_path and create_marker: refused = `a:b`, `x:stream`, `nul:`, `con.txt`, `CON .txt`, `COM1` superscripts with and without extension, `LPT3.log`, `CONIN$`, `conout$.x`, `a<b a|b a?b a*b a"b`, `aux .`, NUL/US/DEL control chars, 121 chars, `C:`/`c:x`, a raw slot key `demo:fixed:...`; no file or directory created (root listing empty).
- ordinary names pass: conn, com10, com0, lpt0, aux1, console, a$b, my.file, a b, 120 chars, accented letters, nul1, CONIN, coninx.
- encode_slot_key: `demo:fixed:2026-10-11T09:30Z` -> `demo%3Afixed%3A2026-10-11T09%3A30Z`; `con` refused; `a*b` -> `a%2Ab`.
- passes that are NOT Windows devices (no finding): fullwidth `ＣＯＮ`/`ａux`/`ＣＯＭ１`, subscript `COM₁`, `con​`, `nul　`, `con\xa0`, `.con`, `  con`, fullwidth colon.
- regression on legitimate stored names: master has no use of core/safe_names, team_path, create_marker or encode_slot_key (git grep master), so no stored name on master can become unreadable.

## Overlap check (t198a)
branch wave/t198a-zip-drive-intake: schema/project.py `Source.origin: SourceOrigin | None` where `SourceOrigin = Annotated[UploadOrigin | ZipOrigin | DriveOrigin, Field(discriminator="kind")]` (schema/intake.py:83). This branch: `Source.origin: SourceOriginKind | None` (closed StrEnum in schema/team_enums.py). Same field name, two incompatible types and two homes.
