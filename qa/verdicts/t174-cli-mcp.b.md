# Verdict B (second blind coordinator) - t174-cli-mcp

Cycle checked: 0
Date: 2026-10-12
Bound root: D:/autoTesting/.worktrees/t174-cli-mcp; code judged: 742e9d8a (tree 401e532e; later commits on this branch change no src/tests/pyproject/uv.lock file); base 822dca2b (= merge-base with master).
Retry: none received (first dispatch). Policy-Version: proportional-verification/2026-10-10.9. Dual check: coordinator B only; no ledger rows written, no goal task touched.

## Check plan (step 0)
Tier L (dependency bump `mcp`; security surface: MCP tools that launch runs / return stored evidence; dual-trigger lines run_ops.py:154 and :67 confirmed real). Checks: CM1..CM5 re-run in a `git archive` copy with its own venv on C: (`uv sync --frozen`); affected tests; own adversarial probes (path traversal, cross-project, secret scrub on 6 surfaces, real `autotester mcp` stdio child); one falsification per criterion plus extras (cap 10, 5 beyond the floor); step 4c diff read; ONE full suite (shard_suite, 4 shards). No UI surface (no browser check). API-only: no persona walk.

## Result
VERDICT: BLOCKED-PROCESS (mandatory full suite not run; every other mandatory check evidenced)
Cause (cited): the machine-wide suite lock is owned by PID 2844 (`shard_suite --repo D:/autoTesting/.worktrees/t204-team-login --ref 17c1422d`, started 2026-10-12T12:30:16 IST, still held at 13:29, 59 min), not our PID, never killed. Three waits at the tool's 900 s limit each ended `exit 3`: 12:31:28-12:46:30, 12:51:06-13:06:07, 13:14:10-13:29:11 IST (logs t174b-suite-out/log.txt, log2.txt, log3.txt; summaries run1..run3/summary.json under C:/Users/Lenovo/AppData/Local/Temp). Retry budget (2) used. Next step per policy: maker re-dispatches with `Retry: 3` once the lock is free (else HUMAN_GATE). Nothing below needs re-running except the suite.

SCOREBOARD (pending the suite): CM1, CM3, CM4, CM5 met; CM2 met as written in qa/contracts/cli-mcp.md (see P1 for the held clause); invariants C3, C5, C11, CN1/CN9 hold on the evidence below.
TIER: L (new dependency; security surface run_ops.py:154 launch_run, :67 _scrubbed)

## Evidence (all produced by me, copy C:/Users/Lenovo/AppData/Local/Temp/t174b-205110586)
- Step 3, per criterion (`python -m pytest -p no:xdist -o addopts=`): CM1 10 passed; CM2 31 passed; CM3 3 passed; CM4 23 passed; CM5 2 passed (76 s, real stdio child). Matches the manifest counts.
- Affected set (tests/test_cli_*.py, test_doctor, test_hosting_deploy, test_run_launcher, test_run_launcher_approval): 277 passed in 139 s. ruff on src/tests/scripts: All checks passed; `autotester doctor`: clean (copy without my probe file).
- Own probes (tests/test_probe_b.py in the copy, 33 passed): 19 hostile run ids (`..`, `../../other/secretdir`, `a/b`, `a\b`, `C:\Windows`, newline, NUL, 5000 chars, fullwidth letters, `%2e%2e` ...) through `run_ops.get_report` and `report show`: all exit 2, planted foreign file never echoed, tree hash unchanged; 9 hostile project slugs through run / dry-run / report / catalog: all 2, tree unchanged; an unknown but valid slug creates no `projects/<slug>` dir on `run`, `run --dry-run`, `report show`, `catalog`; a run copied under another project with a mismatched project field is refused (404 -> 2); a failed run with a planted secret in verdict and error: secret absent from stdout/stderr of `run -o json|text`, `report show` json/text, `catalog` json/text; dry run on strict fakes: exit 0, planned ids listed, tree hash identical, and the same command without the flag and without approval exits 3 and creates no runs dir.
- Real transport: `autotester mcp` child over stdio (provider keys stripped): tools are exactly {get_catalog, get_report, run_tests}; no approval/force parameter exists (extra `approval`/`force` args are ignored and the run is still refused); `run_tests dry_run=true` over the wire (the reviewer's noted gap): exit 0, tree unchanged; `run_tests` real: refused as `usage_error` exit 2 ("no AI provider is configured"; the launcher checks provider before approval), no runs dir; hostile `get_report` run ids: exit 2, no foreign content; `get_catalog` of `../other`: typed error, exit 2; secret absent from every result and the child's stderr (0 bytes). mcp 2.3.0 runs sync tools in a worker thread (func_metadata.py:164 `anyio.to_thread.run_sync`), so the sync Playwright launcher is not on the event loop.
- Step 4c: `git diff 822dca2b...HEAD`: 16 files, 1576 insertions, ONE removed line (`from autotester import cli_issues, cli_video`, replaced by the same line plus `cli_run`). Every file is in the manifest's What changed; `cli.py`, `run_launcher.py`, `ui/routes_runs.py` untouched; nothing deleted or renamed. Golden `cli_commands.json` diff is exactly 3 added rows.
- Falsification (each in its own fresh `git archive` copy, imported path asserted inside the copy, green-before / red-after / restored-green, named test node, all assertion reds, none import/setup):
  - CM1: drop `ProviderError` from the INFRASTRUCTURE mapping -> `test_each_code_is_what_the_cli_exits_with[INFRASTRUCTURE]` red. (My first CM1 mutant, dropping `TimeoutError`, survived: an equivalent mutant because `TimeoutError` subclasses `OSError`; not a finding.)
  - CM2 scrub: `_scrubbed` without `scrub_obj` -> `test_the_planted_secret_appears_nowhere` red. CM2 stdout: an extra `typer.echo('done')` before the JSON -> `test_json_stdout_is_one_document_and_nothing_else` red (JSONDecodeError at char 0).
  - CM3: `if dry_run:` -> `if False:` -> both `test_dry_run_touches_nothing_and_lists_the_cases` params red.
  - CM4: refusal code collapsed to USAGE -> `test_run_tool_without_an_approval_starts_nothing` red (`assert 2 == 3`); a fourth tool added -> `test_the_server_exposes_exactly_three_tools` red.
  - CM5: `mcp` commented out of pyproject -> `test_mcp_is_a_declared_dependency` red.
  - run_id fix: regex check and project/id binding removed -> `test_an_unsafe_run_id_is_usage_and_reads_nothing` red (1 failed, 4 passed).
  - Survivor, a test gap and not a product defect: `_safe_sdk_boundary` ValidationError branch changed to `message=str(exc)` survives `test_sdk_errors_are_typed_without_echoing_inputs` (6) and `test_malformed_rpc_params_keep_protocol_rejection_without_inputs`. The branch is live (my probe reaches it with malformed `tools/call`), but pydantic's message did not contain the planted input in 12 malformed payloads, so no leak was demonstrated (P4, low).
- CM5 pyproject: `git diff 822dca2b HEAD -- pyproject.toml` adds the `mcp>=2.3.0` line and the B008 ignore in this unit's commit only.

## Findings (PROPOSED-ISSUE lines; none blocks under evidence-to-block)
P1 (medium, CM2/C5): the held clause reproduced. `autotester run demo hunter2-PARSER-9f3a --output json` -> exit 2, stdout 0 bytes, stderr "Got unexpected extra argument(s) (hunter2-PARSER-9f3a)". `autotester doctor <token>` does the same, so it is the framework's pre-existing parser behaviour and not a regression of this unit. The contract text of CM2 (stdout is one document and nothing else; planted-secret test over a fixture project) states no parser clause and the unit meets it. If the owner wants a JSON usage error and no echo, the checker (sole contract maintainer) must add it to cli-mcp.md and the gate must be answered. My position: CM2 is met as written; this does not fail the unit.
PROPOSED-ISSUE: {"severity":"medium","type":"security","criterion":"CM2","title":"Click usage errors echo the offending argv token (possible secret) to stderr unscrubbed and give empty stdout under --output json","repro":"autotester run demo <token> --output json; autotester doctor <token>","fix_direction":"owner gate for a bounded parser-boundary recovery; amend CM2 first"}
P2 (low): the manifest's held-clause gate `qa/gates/t174-parser-recovery.md` is not in this branch (`git ls-files qa/gates` has no t174 file); it exists only in the old `.worktrees/codex-t174-repair`. The hold has no authorizing record in the tree.
PROPOSED-ISSUE: {"severity":"low","type":"process","title":"t174 manifest cites qa/gates/t174-parser-recovery.md which is absent from the unit's branch"}
P3 (low): `run_tests` returns `is_error=false` with `status` "usage_error"/"refused" and a nonzero `exit_code`, while `get_catalog` returns `is_error=true` for the same class. A client keying on MCP `isError` reads a refused run as success; the contract only asks for the code in the result.
PROPOSED-ISSUE: {"severity":"low","type":"correctness","criterion":"CM4","title":"mcp_server.tool_run_tests: refused / failed run results have isError=false while get_catalog sets true"}
P4 (low): the test gap above (no test fails when the ValidationError branch of `_safe_sdk_boundary` echoes).
PROPOSED-ISSUE: {"severity":"low","type":"test-gap","criterion":"CM5","title":"no test pins the ValidationError branch of _safe_sdk_boundary"}
P5 (low): "no AI provider configured" (launcher 400) and any `ValueError` (including a corrupt stored file) map to USAGE 2, so CI cannot tell a missing provider or corrupt data from bad arguments (manifest owner questions 3 and 4, agreed). Because the provider is checked before approval, an unapproved run on a machine without a provider shows 2, not 3.
PROPOSED-ISSUE: {"severity":"low","type":"design","criterion":"CM1","title":"provider-missing and ValueError map to USAGE; consider INFRASTRUCTURE / INTERNAL"}
P6 (low): `mcp>=2.3.0` has no upper bound; uv.lock pins 2.3.0 but a bare install could take a later major that the imports (`mcp.server.mcpserver`, `mcp.server.context`) may not match.
PROPOSED-ISSUE: {"severity":"low","type":"dependency","title":"cap mcp below the next major or add a smoke on the declared range"}

## Remaining (for the Retry)
1. ONE full suite: `python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting/.worktrees/t174-cli-mcp --ref 742e9d8a --shards 4 -- -o addopts=` (or the then-current branch head; src/tests/pyproject/uv.lock are unchanged since 742e9d8a) when the machine lock is free. Known reds AT-858, AT-725, AT-750, AT-921, AT-924, AT-968 (flaky). Nothing else needs re-running: evidence identities are in the checkpoint. Estimate 15-30 min after the lock is acquired.

full-suite trigger: dependency manifest (pyproject.toml/uv.lock) + new third-party SDK (security dual-trigger).
CAPABILITY-COVERAGE: 10/10 falsification edits reproduced (8 red as intended, 1 equivalent mutant explained, 1 test-gap survivor P4); every criterion CM1-CM5 has at least one red
LIVE-BROWSER: not-applicable (no ui/, template or route file changed)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Every acceptance criterion and the run_id review fix were re-run and falsified in isolated copies, including a real stdio MCP child and hostile run ids and slugs; nothing found fails CM1-CM5 as written. The single mandatory full suite could not run because another session's suite held the machine lock for over 59 minutes through three 15-minute waits, so no PASS is possible yet.

Metrics: start=2026-10-12T06:59:42Z end=2026-10-12T08:00:00Z wall_min=15 agent_min=unavailable blocked_min=45 suite_runs=0 repeat_runs=0 mutations=11 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=3618 defects_unit=0 defects_6c=0
(Elapsed 60 min; the three 15-min lock waits ran concurrently with the checks above and are counted as blocked_min, so wall_min is 60-45.)
