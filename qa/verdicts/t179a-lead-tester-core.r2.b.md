# Verdict - t179a-lead-tester-core, coordinator B, repair check (cycle 2)

Date: 2026-10-12 | Bound to D:/autoTesting/.worktrees/t179-lead-tester | Head 86d240a9 (code cc7f29ed) | Repair base c489e201 (ancestor-verified) | Base 16aaa402 (= merge-base with master)
Cycle checked: 2
Policy-Version: proportional-verification/2026-10-10.9 | Evidence: qa/evidence/t179a-lead-tester-core-r2-B/ | Checkpoint: qa/checkpoints/t179a-lead-tester-core.b.md

## Plan
Failed criterion AL6 (PI-1, gate ran on JSON text). The repair diff touches tools.py (AL6) and guards.py (AL3), so: AL6 re-run, AL3 re-run, AL2 wraps (handlers untouched by the diff) confirmed by the existing tests. Reads: repair diff c489e201..86d240a9 in full, whole-unit diff --stat. One falsification per repaired criterion. All work in `git archive 86d240a9` / `c489e201` copies on C: (own venv, `autotester.__file__` printed from the copy). No full suite from this seat (repair-scoped). No browser, no network, no .env read.

VERDICT: PASS
SCOREBOARD: 3/3 criteria met (AL2 unchanged and green, AL3 met, AL6 met for the tool boundary the unit claims), 0/0 invariants touched
TIER: L (security: dual-trigger src/autotester/agents/guards.py:166 `write_policy_refusal` and src/autotester/agents/tools.py:293 `dispatch`, both lines read at HEAD)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 rows reproduced (see Falsification)
LIVE-BROWSER: not-applicable (no UI surface; agent layer, no screen, route or CLI output)
ISSUES-WRITTEN: none (dual coordinator: findings below as PROPOSED-ISSUE lines)
EXECUTOR: claude-sonnet-subagent

## AL6 - PI-1 repair (the failed criterion)
- `tools._carries_credential` (tools.py:90-101) now walks the decoded strings (`_call_texts`) and gates each with `guards.guard_model_bound`, plus a `\uXXXX`-decoded form. It is used by `_withhold_if_credential`, `_release` and `_stage_error`. I read the lines.
- Own probe `p_split.py`: 9 result locations (error, hitl_prompt, not_run_reason, log_ref, evidence label, evidence path, evidence label after 5 rows, raised stage exception, tool summary) x 37 separators (TAB, LF, CR, CRLF, VT, FF, FS/GS/RS/US, NEL, NBSP, U+1680..U+3000 spaces, U+2028/2029, zero-width, U+2060, BOM, SHY, NUL, DEL, spaces, literal `\t`/`\n`/`\uXXXX`) x 6 cut points = 1,998 dispatches, oracle `SecretStore.guard_prompt(text)`. 0 leaks (every oracle-caught row returned SECRET, stored nothing, and neither half is in the outcome) and 0 over-withholds. Reversed, base64, hex, newline-split base64 and tab-split reversed forms in 3 locations: all withheld, nothing stored. `Verdict` fields note, scoreboard, grader_provider, rubric_hash with TAB, LF, ZWSP, VT splits: all raise `_Refused(SECRET)` before the save. The cycle-1 failure shape is closed.
- Affected tests: tests/test_agent_{credential_gate,destination_seam,read_only,tools}.py 392 passed; test_explore_safety, test_execute, test_schema, test_doctor 140 passed; test_goal_contract_registration 1 passed (full archive, it needs `.goal/`). ruff on src, scripts and the 4 agent test files is clean; `autotester doctor` is clean (tools.py 299 lines, guards.py 180).

## AL3 - guards.py changed, re-run
- Differential `p_guard.py`, 14,358 rows at head and at c489e201. Above READ_ONLY (TEST_ACCOUNT and ALLOW_WRITES), 210 NAVIGATE rows over 105 targets (ftp/ws/file/data/javascript, userinfo, backslash, IDN, TAB/CR/LF/NUL/DEL/NBSP/ZWSP at start, middle and end, placeholders): the guard refuses iff `check_destination(raw)` refuses, and never a `{{SECRET:..}}` target. 0 mismatches. The 13 targets cycle-1 reported are now accepted exactly as the seam accepts them.
- READ_ONLY: the table is identical to c489e201 except 32 rows: a whitespace-only FILL value in the login case no longer arms the credential entry (intended narrowing in `_declared_credential`). READ_ONLY stays fail-closed.

## AL2 - wraps unchanged
Handlers and `ToolSpec.wraps` are untouched by the repair diff; test_agent_tools is green (14 tests, incl. the wrap spies).

## Diff scope (step 4c)
Repair diff c489e201..86d240a9: guards.py, tools.py, 2 new test files, test_agent_read_only.py, manifest. test_agent_read_only.py drops 3 parameter rows (`ftp://app.test/x`, `/reports`, `Admin portal URL`): a protected-test weakening, justified because the cycle-1 FAIL required the guard to equal the seam, the seam accepts ftp and refuses bare paths, and that equality is pinned in the new test_agent_destination_seam.py (14 tests). Whole-unit 16aaa402..86d240a9: 13 files, all under agents/, schema/agent_layer.py, tests, the qa brief and manifest, and generated docs/MAP.md and docs/SNAPSHOT.md; 1 deleted line in total (a generated SNAPSHOT decision row). Nothing removed beyond the private `_error_text` -> `_stage_error` rename. Nothing unexpected.

## Falsification (copies on C:, own venv; green before from the copy, red after, restored byte-identical, green again)
| Row | edit | node | before | after |
|---|---|---|---|---|
| AL6 | `_carries_credential` gates `json.dumps(data)` (cycle-1 shape) | test_a_credential_split_by_a_separator_is_withheld_and_never_stored | 40 passed | 40 failed, `assert (True is False)` with `ok=True` and the split value released |
| AL3 | `_seam_refuses` drops the placeholder exemption | test_a_placeholder_target_is_left_to_the_seam_at_these_policies | 14 passed | 12 failed, 2 passed |
| AL6 extra | drop the `\uXXXX`-decoded form | same node as row 1 | 40 passed | 10 failed (the `\u0009` and `\u000a` rows), 30 passed |

## PROPOSED-ISSUEs (non-blocking; the maker mints rows after both coordinators PASS)
PROPOSED-ISSUE: {"id":"P1","sev":"medium","type":"availability","where":"src/autotester/agents/tools.py:90-101 (_carries_credential via _call_texts caps: 16 KiB, 256 nodes, depth 6)","what":"A secret-free stage result past the call-argument caps is withheld as 'carried a credential' and not stored. Reproduced with p_size.py through tools.dispatch: a RawResult with 21+ evidence rows, or 5 rows with labels of ~3.3 KB+, returns refusal=SECRET and load_results is empty; at c489e201 all 9 sizes store. In stored runs under projects/*/runs, 4 of 238 RawResults have >20 evidence rows (max 222) and 3 exceed 16 KiB of JSON, so the longest real flows could not be recorded or graded through the agent (grade_case needs a stored result). It is fail-closed by design and pinned by test_a_result_beyond_the_size_caps_is_withheld_not_skipped, but the manifest's open items do not disclose it and the message says 'credential'.","fix":"scan stage OUTPUT without the call-argument caps (the caps exist to bound model-supplied args), or scan in chunks; at least return a distinct refusal class instead of SECRET"}
PROPOSED-ISSUE: {"id":"P2","sev":"low","type":"security-hardening","where":"src/autotester/browser/session.py:54 check_destination (unchanged by this unit)","what":"The seam has no scheme allow-list: ftp://, ws://, wss:// with an in-domain host pass it, so with the guard now equal to the seam, TEST_ACCOUNT and ALLOW_WRITES accept them (READ_ONLY still refuses). Pre-existing; the browser would reject ftp/ws itself.","fix":"an http(s) scheme check in check_destination, then the guard inherits it"}
PROPOSED-ISSUE: {"id":"P3","sev":"low","type":"behaviour-note","where":"src/autotester/agents/guards.py:119-126","what":"Above READ_ONLY a bare-path or description NAVIGATE target ('/reports', 'Admin portal URL') now refuses the whole case up front as DESTINATION; before, earlier steps ran and the seam failed at that step. The seam refuses those targets either way (pathlynks cases.jsonl holds 10 such descriptive targets that can never navigate)."}

## Not run / limits
No full suite from this seat: repair-scoped check (impact rule) inside the 45 min wall. full-suite trigger: none new from this repair (no conftest, config or dependency change). Cyrillic-homoglyph and interleave secrets and `Case.rubric_ref` path validation are the manifest's declared out-of-scope items and were not judged. AL6 is judged at the tool boundary only, as the manifest claims; planning prompts and skill bodies are AL1/AL4 territory (held).

EXPLANATION: The PI-1 repair does what it claims: the credential gate now reads decoded strings, so a TAB, LF or Unicode-separator split secret in any stage result, error, summary or verdict field is withheld and never stored (1,998 oracle-checked rows, 0 leaks, 0 over-withholds), and the guard's navigate decision is exactly the browser seam's above READ_ONLY, with READ_ONLY unchanged except the intended blank-fill narrowing. The one real cost is P1: the call-argument size caps were reused on stage output, so large legitimate results are withheld and mislabelled as a credential; it is fail-closed, tested as intended, and outside every criterion, so it is a ledger row for the maker, not a FAIL.
Metrics: start=2026-10-12T07:10:56Z end=2026-10-12T07:48:00Z wall_min=37 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2224 mutants=1 defects_unit=0 defects_6c=0
slow: AL6 split matrix probe 10 min (1,998 dispatches, each building a store)
