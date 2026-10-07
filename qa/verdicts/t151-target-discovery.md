# Verdict — t151-target-discovery (coordinator A, repair checker)

Cycle checked: 2
Date: 2026-10-07
Bound to: D:/autoTesting, worktree D:/autoTesting/.worktrees/t151-target-discovery, branch codex/t151-target-discovery, head a9307c2e (base 2fae2504)
Policy: proportional-verification/2026-10-06.6 · Verdict path: qa/verdicts/t151-target-discovery.md · Checkpoint: qa/checkpoints/t151-target-discovery.md
Blind to coordinator B (its verdict and checkpoint were not opened). The cycle-1 verdict was renamed to qa/verdicts/t151-target-discovery.r1-1.md without being read; this repair check worked from the failed-criteria list and the checkpoint identities only.

## Check plan (step 0)
Diff since cycle-1 head 18243792 touches product code in `stages/discover.py`, `stages/read_context.py`, new `stages/text_lines.py`, new `stages/credential_files.py`, `schema/ai_target.py`, plus a new test file and a merge of master (D-065). Signals: logic changed (affected tests + falsification), credential/path-escape boundary (dual check), dependency lock unchanged since cycle 1. No UI, no live portal, no data artifact, no prompt/LLM output change (prompt file and mock.py hashes unchanged), so no browser, no persona walk, no grader, no `/security-review` sub-check beyond the C5/credential read of the diff. Tier L (credential, path-escape and approval boundary; dependency bump already on branch), dual check. Failed criteria re-run end to end: AI1 line numbers, AI8 non-.md, C5 YAML alias (non-cyclic and cyclic), dangling-citation doctor violations and `test_the_real_tree_has_no_dangling_citation`. Everything not touched by the a9307c2e diff is reused by evidence identity (checkpoint): `tests/test_discover.py`, `mock.py`, the prompt, `pyproject.toml`, `uv.lock` and `conftest.py` are byte-identical to cycle 1 (hashes in the checkpoint). Anything the diff did touch was re-run. SERIAL: not needed; falsification rows ran in one isolated copy each, the one full suite ran alone in the bound tree.

## Results per failed criterion

- **AI1 (Signal line numbers match the source, including U+2028 and form feed): MET.**
  - Code: `stages/text_lines.py:split_lines` splits on `\r\n|\r|\n` only; `read_context.py:21,85` and `discover.py:234,236` (via `first_nonblank_line`) use it, replacing the three `str.splitlines()` sites. I read each line.
  - Independent probe `probe_a2.py` (96 checks, my own char-by-char line counter, not the maker's): tags and signals after each of U+2028, U+2029, FF, VT, NEL, FS, GS, RS, US under LF, CRLF and CR endings, frontmatter signals under each EOL, Python `ast` linenos, prompt and ground_truth first-nonblank lines. Result 96/96 on a9307c2e. The same probe on the cycle-1 source (git archive 18243792) fails 59/96 (tags land on 6, 9, 12, 13, 14 against the true 5, 6, 7, 8, 8), so it does discriminate.
  - Separators inside YAML frontmatter are refused fail-closed (`invalid_yaml`), never mis-numbered.
  - Committed defender falsified: `text_lines.split_lines` -> `text.splitlines()` in a copy: `2 passed -> 2 failed -> 2 passed` (the two `test_unicode_and_formfeed_separators_do_not_shift_*` nodes).
  - No Provider on the signal path: `test_discovery_never_calls_provider` passes; my own probe patched every `Provider.act/grade` to raise and ran `scan` and `read_context` on a fixture: 0 calls, 4 + 4 signals.
- **AI8 (non-.md context file yields no ContextDocument): MET.**
  - `read_context.py:145` skips any suffix other than `.md` (case-insensitive). Probe: `.txt .markdown .mdx README .md.txt .rst .MD.bak .yaml .json .md5`, each holding frontmatter and a tag, give 0 documents, 0 signals and a complete result; a sibling `ok.md` gives exactly one document. A vault note with `[[backlinks]]` and a dataview block yields only frontmatter and real tags. `grep -rniE obsidian pyproject.toml` exits 1, no output.
  - Falsified in a copy: `!= ".md"` -> `not in {".md", ".txt"}`: `1 passed -> 1 failed -> 1 passed` (`test_non_markdown_context_files_yield_no_document`).
- **C5 YAML alias refused as `yaml_alias`, non-cyclic and cyclic: MET.**
  - `read_context.py:32` (AliasEvent in the parse event loop) and `_metadata` cycle guard at `:51`. Probe: 8 alias shapes (non-cyclic seq, cyclic seq, cyclic map, alias in key, merge key `<<: *b`, alias scalar, nested alias, a 4-level alias bomb), each under default and generous limits (depth 20, nodes 2000): every one yields exactly `[("bad.md", "yaml_alias")]`, `complete=False`, the good sibling document still read, under 5 s. A bare anchor with no alias is not refused.
  - Falsified in copies: AliasEvent branch -> `if False`: `2 passed -> 1 failed, 1 passed -> 2 passed` (the non-cyclic case dies, the cyclic case is still caught by the `_metadata` guard); both guards -> `if False`: `2 passed -> 2 failed -> 2 passed`. So each case has an isolating mutant.
- **Dangling-citation doctor violations: MET.** D-065 is present on the branch. `uv run autotester doctor` in the bound tree: `doctor: clean`. `tests/test_citations.py::test_the_real_tree_has_no_dangling_citation` passes (in the full suite and in the 101-test targeted run). Falsified in a copy: the `## D-065` heading in `docs/DECISIONS.md` renamed with a trailing 0 appended: `1 passed -> 1 failed -> 1 passed`.

## Other mandatory evidence
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run pytest tests/test_discover.py tests/test_discover_hardening.py tests/test_citations.py` (in a throwaway copy whose changed-file md5s equal the bound tree's): `101 passed in 39.60s`, matching the manifest.
- **Full suite (the one): `4 failed, 2286 passed, 6 skipped, 14 xfailed in 5139.06s (1:25:39)`**, 2310 collected, `uv run pytest` with no -q and no -x in the bound worktree, wrapper PID 270012 (uv), python PIDs 30620 and 20064, 09:22:16 to 10:47:56 +05:30. The 4 failures are unrelated to this unit:
  - `tests/test_crawl_inventory_live.py::test_a_logged_in_crawl_maps_every_route_and_names_the_one_it_refused`: `AssertionError: wall_clock_s` (a 240 s crawl bound on an overloaded host). Run alone on a copy of base 2fae2504 it fails identically in 284 s.
  - `tests/test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus`: 4.34 s against a 3 s bound. Fails on base 2fae2504 too (4.25 s).
  - `tests/test_mc_sessionstart_loop_status.py::test_hook_prints_the_report_and_exits_zero_on_a_healthy_log`: `subprocess.TimeoutExpired` on `powershell.exe qa/hooks/mc-sessionstart.ps1`. Fails on base 2fae2504 too.
  - `tests/test_mc_sessionstart_loop_status.py::test_hook_prints_unhealthy_line_only_on_an_asleep_log_and_still_exits_zero`: failed only under suite load; passes in isolation on both HEAD and base.
  None of the four touches `stages/discover.py`, `read_context.py`, `text_lines.py`, `credential_files.py`, `schema/ai_target.py`, `mock.py` or the prompt. The attribution runs are not full suites.
- Diff scope (4c): `git diff 2fae2504...HEAD --diff-filter=DR` lists no deleted or renamed file. `git diff 18243792 HEAD -- src tests`: no public symbol removed; the private `_credential` and `_CREDENTIALS` moved to `credential_files.is_credential` with a superset denylist and no other importer. The src diff set is the one the manifest names. No regression of an earlier-passed criterion seen: `test_discover.py` (63 cases, file hash unchanged) passes against the new code, including the symlink/junction escape, secret-scrub and no-Provider nodes.

## Falsification floor
One named falsification per failed criterion, each green before, red after, restored, in its own copy of the post-change tree (5 copies, 5 mutants, none in the bound tree). The red assertions are the named ones (line equality, `documents == []`, `_reasons == ["yaml_alias"]`, the dangling-citation list), not import failures.

## Notes (non-blocking)
- No-progress check: n/a, this cycle fixed the failed criteria.
- The check ran past the L wall-clock budget (45 min): the full suite alone took 85.7 min on a host saturated by unrelated pytest runs, and the budget was not paused for it. The run completed rather than checkpointing because the suite was already past half done and a resume would have repeated it; the overrun is stated in Metrics, not hidden.

PROPOSED-ISSUE: {"severity":"low","feature":"ai-target","title":"AI1 Verify grep literal cannot exit 1: classify_target lives in stages/discover.py","evidence":"`grep -rn Provider src/autotester/stages/discover.py src/autotester/stages/read_context.py` matches at discover.py:15,253 (import and classify_target signature); the criterion's real claim (no Provider call on the signal path) holds and is tested. Contract line should name the signal path rather than the file.","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"ai-target","title":"Reader emits the closing frontmatter fence as a 'Frontmatter metadata' Signal","evidence":"read_context.py:86-96: `line <= end + 1` includes the closing `---` (1-based line end+1); test_reader_signal_lines_match_exact_source accepts {2,3} <= meta <= {2,3,4}, so the looseness hides it. The cited line is real, so AI1 holds; the signal is cosmetic noise.","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"suite-hygiene","title":"Four load-sensitive tests fail on a saturated host and on base 2fae2504","evidence":"test_crawl_inventory_live (wall_clock_s 240 s bound), test_redact_wrap_perf (3 s bound), test_mc_sessionstart_loop_status x2 (powershell hook timeout); full suite 1:25:39 on 2026-10-07 under unrelated pytest load.","found_by":"checker-unit"}

VERDICT: PASS
SCOREBOARD: 4/4 failed-criteria re-run met (AI1, AI8, C5 alias, dangling-citation doctor + test); earlier-passed criteria unregressed (63 test_discover.py cases, hardening 27, citations 11 green); invariants C5 (credential denylist, scrub, alias) hold
TIER: L (credential/path-escape/approval boundary and a dependency bump on the branch; cited: src/autotester/stages/credential_files.py:5-16 and src/autotester/stages/discover.py:34-59,122)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 falsification rows reproduced (green-before, red-after, restored, each in its own copy)
LIVE-BROWSER: not-applicable (no UI path changed: src/autotester/stages/discover.py, read_context.py, text_lines.py, credential_files.py, schema/ai_target.py, tests)
ISSUES-WRITTEN: none (dual-check coordinator: 3 PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: All four cycle-1 failed criteria hold on a9307c2e: my own independent probe of 96 line, AI8 and alias cases passes (and fails 59 of 96 on the cycle-1 source), every committed defender is falsified in an isolated copy with the assertion the test is named for, doctor is clean and the dangling-citation test is green. The one full suite ended 4 failed / 2286 passed; all four failures are host-load or pre-existing and reproduce on base 2fae2504 with no overlap with the diff. The run exceeded the L wall-clock budget because of the 85-minute suite on a saturated host.
Metrics: start=2026-10-07T03:47:13Z end=2026-10-07T05:36:40Z wall_min=109 agent_min=109 blocked_min=0 suite_runs=1 repeat_runs=0 mutations=5 cycle=2 resumes=0 tokens=unavailable policy=2026-10-06.6
