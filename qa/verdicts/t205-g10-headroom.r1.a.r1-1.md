# Verdict - t205-g10-headroom - coordinator A (blind dual check) - repair check

Cycle checked: 1
Retry: 0
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting. Tree: D:/autoTesting/.worktrees/t205-g10-headroom, head fb93776bbf216c91c5854e0c5ce58dff8a22e052 (product 57cec910), repair base 0b8325b6 (ancestor of head, verified), merge-base with master 09828f2d.
Manifest: Status ready-for-check, Fix cycle 1, `tick.mjs --lint-manifest` exit 0.
Blindness kept: no file under qa/verdicts/, qa/checkpoints/ or qa/evidence/ whose name contains `t205` was opened by this coordinator (one directory-name listing of qa/verdicts was attempted and denied by the harness; nothing was read).

## Plan
Failed list given: TF6 (Source lacked uploaded_by, uploaded_at, origin). Re-run: TF6; criteria whose inputs the repair touches: TF1, TF2 (guard tests), TF7 (safe names), TF8 (team_enums.py, MAP.md). TF3, TF4, TF5: input files untouched by the repair diff, recorded results kept. Plus affected tests, repair diff read in full, whole-unit diff scan, one falsification per repaired criterion, class attacks. Full suite owed at this head (security-class L).

VERDICT: BLOCKED-PROCESS (suite owed only; every criterion result below is recorded, so a suite-only retry can finish)
SCOREBOARD: 8/8 criteria met on the checks run (TF1 TF2 TF6 TF7 TF8 re-run; TF3 TF4 TF5 kept by evidence identity), invariants: none touched. Full suite NOT RUN.
TIER: L (security: run-approval gate src/autotester/stages/run_launcher.py:134-151, safe_name path guard src/autotester/core/safe_names.py:44-58)
CAUSE (cited): shard_suite.py exit 3, "[11:55:34] BLOCKED: suite lock busy after 901s; holder pid 13816, repo D:\hei-sweep, started 2026-10-11T10:56:19" (the machine-wide lock, a process that is not ours; not killed, not touched). Waited the full 15 min (blocked_min 15).

## Criterion results (all run by me, in the tree under test)
Proof of tree: autotester.__file__ = D:\autoTesting\.worktrees\t205-g10-headroom\src\autotester\__init__.py; pytest rootdir D:\autoTesting\.worktrees\t205-g10-headroom; 665 collected test node ids, all `tests/...` inside the tree (affected-tests.txt). Runs redone after the coordinator's correction: the first run used `uv run --project` with absolute in-tree test paths; it was repeated with `uv --directory <tree> run` (665 passed, 140 s), and ruff and `autotester doctor` were run the same way.
- TF6 MET. Source has uploaded_by / uploaded_at / origin, optional, default None; origin is the closed StrEnum SourceOriginKind {upload, zip, drive, recording}; extra="forbid" holds; Source.id unchanged. Old-shape lines load and re-serialise byte-identical (exclude_none, which every store writer uses); id identical between repair base and head for 3 shapes. test_project_schema_team.py + test_team_enums_home.py green.
- TF1 MET. tests/test_run_launcher.py 5 passed; the scan now resolves `as` aliases, `X = Y` chains, partial and pass-as-argument.
- TF2 MET. tests/test_run_launcher_approval.py 16 passed; pinned parameter and RunSeams allow-lists exact.
- TF7 (safe names) MET. test_safe_names_windows.py + test_team_store.py 569 passed within the 665 run.
- TF8 MET. ruff "All checks passed!", `autotester doctor` -> "doctor: clean", test_team_enums_home green.
- TF3, TF4, TF5: unchanged inputs, recorded results kept (not repeated).
Whole-unit diff scan (merge-base..head, 34 files): every file is named in the manifest; nothing outside declared scope. Repair diff (0b8325b6..head, 9 files) read in full: only safe_names.py, schema/project.py, schema/team_enums.py, MAP.md, 4 test files, manifest. Nothing removed.

## Falsifications (copies of `git archive fb93776b` outside the tree; green before, red after; see evidence/falsifications-and-attacks.md)
- TF6: fold uploaded_by into the id key -> test_origin_is_a_closed_set_and_provenance_never_moves_the_id RED (copy green, 11 passed, first).
- TF1: aliased second `Run(` site and aliased partial of the executor in ui/routes_runs.py -> both single-call-site tests RED; the repair-base test file stays green on the same tree (the old scan was blind).
- TF2: extra RunSeams field `skip_approval` -> test_the_gate_is_not_a_parameter RED (repair-base guard stays green); extra launch_run parameter -> RED; approval call deleted -> 6 tests RED; a seam-keyed skip that forges an approval so the run proceeds -> test_no_seam_value_skips_the_approval[free_ram_mb-true] RED.
- TF7: disable the `: < > " | ? *` check -> forbidden-character table RED (40 failed). The full file hangs on that mutant because `create_marker` opens `CONIN$`, which shows what the guard prevents.
Scratch copies: the delete command was denied by the harness; they remain under the session scratchpad (.../scratchpad/r1a), outside the tree, nothing in the repo.

## Class-attack findings
- safe_name through team_path and create_marker: refused `a:b`, `x:stream`, `nul:`, `con.txt`, `CON .txt`, COM/LPT superscripts with and without extension, `CONIN$`, `conout$.x`, `< > " | ? *`, control chars, 121 chars, `C:`; nothing was created on disk. Ordinary `conn`, `com10`, `com0`, `lpt0`, `aux1`, `console`, `a$b`, 120-char and accented names pass. Slot keys percent-encode. Master has no use of safe_names/team_path/create_marker, so no stored name on master can become unreadable.
- TF1/TF2 guards versus the repair base: no assertion removed or weakened for the four pinned targets; see P2 for what the old test covered that the new one does not.

## Findings (none blocks; coordinator verdict, no ledger writes)
PROPOSED-ISSUE: {"severity":"medium","feature":"team-foundation","title":"Source.origin type collides with t198a: branch wave/t198a-zip-drive-intake defines Source.origin: SourceOrigin | None (discriminated union UploadOrigin/ZipOrigin/DriveOrigin, schema/intake.py:83) while this unit defines Source.origin: SourceOriginKind | None (StrEnum, schema/team_enums.py). Same field, two incompatible types and two homes; whichever merges second conflicts in schema/project.py and breaks one concept, one place. TF6 says the enum lives in the Group 10 vocabulary home and T-198 extends it in place, so this unit conforms; the contract needs a ruling on which shape wins (suggest: SourceOriginKind stays as the discriminator values and the intake models carry the detail).","evidence":"wave/t198a-zip-drive-intake src/autotester/schema/project.py:130; this tree schema/project.py:126"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-foundation","title":"TF2 guard test narrowed against the repair base: the old test_the_gate_is_not_a_parameter scanned every function in run_launcher.py for banned name fragments; the new one pins exactly launch_run, prepare_run, require_live_case_approval and the RunSeams fields. run_cases_traced, plan_under_shared_budget, require_declared_values and is_entry_case are no longer scanned. Stronger on the pinned four (exact match, any name), weaker elsewhere; none of the unpinned functions can skip the approval because it is a prerequisite of Prepared.","evidence":"tests/test_run_launcher_approval.py:120-139 versus 0b8325b6 same file"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-foundation","title":"test_no_seam_value_skips_the_approval uses pytest.raises(Exception), so it also passes when the approval call is deleted (RunBudget raises ValueError downstream). The 6 refusal/proceed rows catch deletion; the per-field rows catch only a skip that lets the run proceed (mutation D). Acceptable defence in depth; narrowing the expected exception types would make the rows sharper.","evidence":"tests/test_run_launcher_approval.py:150-165; mutation C in evidence"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-foundation","title":"safe_name does not NFKC-normalise: fullwidth CON/aux/COM1 pass. Windows does not treat them as devices and no caller in this tree normalises, so no defect today; revisit if a caller NFKC-normalises names before the path join.","evidence":"core/safe_names.py:44-58"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-foundation","title":"The TF1 AST scan cannot see non-call constructions (Run.model_validate, importlib/getattr dispatch). Inherent to a static scan; the executor and approval gates still sit behind prepare_run.","evidence":"tests/test_run_launcher.py _calls"}

CAPABILITY-COVERAGE: 4/4 repaired-criterion falsification rows reproduced (TF1, TF2, TF6, TF7)
LIVE-BROWSER: not-applicable (changed paths: schema, core, stages, tests, MAP.md; no UI surface this cycle)
ISSUES-WRITTEN: none (dual coordinator)
SUITE: owed, not run. full-suite trigger: security-class L unit (one checker full suite at head fb93776b). Retry command: python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting --ref fb93776b --shards 4 -- -o addopts=  . Known reds to expect: AT-858, AT-725, AT-750, AT-920, AT-921, AT-924, AT-792 (branch predates master 05eb07bf).
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Every criterion in scope is met and each repaired criterion was falsified green-to-red in a copy, so the only thing missing for a PASS is the single owed full suite, which could not start because the machine-wide lock was held by another project's suite for the whole 15-minute wait. slow: environment contention (copies and pytest 5-10x slower than usual), included in wall_min.
Metrics: start=2026-10-11T05:10:00Z end=2026-10-11T06:55:00Z wall_min=90 agent_min=unavailable blocked_min=15 suite_runs=0 repeat_runs=0 mutations=8 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=5400 mutants=0 defects_unit=0 defects_6c=0
