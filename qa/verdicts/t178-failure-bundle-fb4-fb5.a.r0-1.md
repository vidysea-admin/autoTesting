# Verdict A - t178-failure-bundle-fb4-fb5 (coordinator A of a blind dual check)

Date: 2026-10-11. Bound to D:/autoTesting. Policy-Version: proportional-verification/2026-10-10.9. Commit checked: a7d3fa6c (product bb76275f + c273a4a6 docs/MAP.md). Cycle checked: 0. Resume: dispatch restarted after a session limit; this verdict's Remaining list is the suite only.
Copy: `git archive a7d3fa6c`; the bound worktree was never touched. I read no `.b.md`, `-b` directory or B checkpoint.

## Plan (step 0)
Diff = 12 src files + 9 test files. Checks routed: FB4 and FB5 end to end; one falsification per criterion plus containment and queue mutants (separate copies); security-class ruling; step 4c diff read (src diff read in full, tests diff scanned for removed assertions); secrets planting; UI browser + dev persona walk (routes_learn.py, routes_runs.py changed); affected tests, ruff, doctor; one full suite (security-touching L unit).

VERDICT: CONTINUE-NEEDED
SCOREBOARD: 2/2 criteria met (FB4, FB5), containment amendment met; FB1-FB3 not re-judged but their nodes pass (test_failure_bundle.py 23 passed). Full suite not run.
TIER: L (security hunk: path containment in `stages/failure_bundle.py:211-212`; persisted-state write: case_proposals.jsonl)
REMAINING (only this): the ONE full suite on a7d3fa6c, `shard_suite.py --repo D:/autoTesting --ref a7d3fa6c --shards 4 -- -o addopts=`. Cause: the suite lock was busy for 901 s (holders pid 57972 `--ref 575a7c3f`, then pid 5752 `--ref 4b93d952`, neither ours); log `qa/evidence/t178-failure-bundle-fb4-fb5-checker-a/suite-lock-wait.log`, exit 3. Estimate 10-15 min once the lock is free. Known ledgered reds to expect: AT-725 test_redact_wrap_perf, AT-792 test_reconcile_schema rc2, AT-858 test_mc_sessionstart_loop_status healthy-log, AT-750 test_crawl_inventory_live; `test_env_example_documents_every_key_the_code_reads` is unconfirmed on master and must be shown there before it is called pre-existing.

FAILURES: none found in the checks run.

## FB4 - met (own runs)
- `pytest tests/test_schema.py test_store.py test_pinned_regression.py test_failure_bundle.py` -> 75 passed. Affected set (test_expand, test_expand_cli, test_eval_compiler, test_cli_issues, test_regression_proof) -> 78 passed; (test_ui_learn, test_ui_runs, test_run_queue, test_run_queue_resilience, test_ui_runs_queue) -> 55 passed. Total 208, equals the builder's Pre-check; I re-ran everything, reused nothing.
- Probe (evidence `fb4-legacy-queue-probe.py`): a case without priority loads p2; legacy pinned stored p3 loads p0; p9 and an unknown key are rejected (`extra=forbid`); `delete_case` on a pinned case raises `PinnedCaseError`; an old `run_queue.json` row without `priorities` loads as None; a queue priority outside p0-p3 is rejected.
- Falsify[FB4]: `list_cases` `if priorities is None:` -> `if True:` in a copy; node green before (1 passed), red after on the list equality ("Left contains 3 more items").

## FB5 - met (own runs)
- test_expand.py five-nonhappy-prune test asserts exactly 2 provider calls, prune-all 0, no approval 0; CLI and UI nodes confirm nothing is generated without a recorded human approval (all inside the 208).
- Falsify[FB5]: `approved_batch` returns every batch member instead of approved ones; copy green before (2 passed), red after `assert 5 == 2` and `assert 5 == 0`.
- Containment: Falsify[CONTAIN] removing `is_relative_to(root)` in `load_bundle` -> junction test red on "escaped file reached hashing/read". Fixed bundle file names are code-generated (`stages/failure_bundle.py:132-150`), so the new `BundleFile.name` validator cannot refuse a bundle the writer produces.

## Ruling: security class and the round cap
- Dual trigger and suite: VALID. The diff adds a real containment control on a file-reading path (a manifest name is joined to the bundle dir; `target = (root / f.name).resolve()` at `stages/failure_bundle.py:211`, check at :212; I falsified it). This is the dual-check security trigger and the unit touches a security path, so the one full suite is owed.
- Round cap: I rule the UNIT NOT security class for D-014 purposes. The hook text (D:/ai_os/.claude/hooks/delivery-gate-stop.ps1:263-285, 321-335) is class-based (tenancy, auth, cross-tenant read, data write, credential handling) and counts prior PASSed units whose manifest seam shares at least one path; `qa/gates/at673-round-cap.md` warns against stretching "security class" to escape the cap. The security hunk is confined to `schema/failure_bundle.py` and `stages/failure_bundle.py`; the other 10 files carry priority, proposals, the expand gate and queue plumbing, none of it security. The manifest's `Round cap: SECURITY CLASS` line therefore covers only the failure_bundle seam.
- Real earlier PASS counts (distinct PASSed units that edited the file, not name-grep; floors where noted; the unit under judgement excluded; no counter reset or waiver for these files exists, D-056 covers mc-sessionstart only): schema/case.py 5 · stages/expand.py 4 · store/project_store.py 15+ · core/paths.py 12 · cli.py 11+ · ui/routes_runs.py 14+ · ui/routes_learn.py 4 (the builder said 2) · schema/failure_bundle.py 1 · stages/failure_bundle.py 1 · stages/eval_compiler.py 1 · ui/run_queue.py 1 · schema/run_queue.py 1 (builder said 0). Seven seams are past the cap of 2 (the manifest says six). The owner must waive in a DECISIONS entry with `Approved-by` before merge; this is not a FAIL ground.

## Step 4c diff read (21 src+test hunks listed in the diff; src read in full)
- Nothing removed that a criterion does not require; no test assertion removed or weakened (removed test lines are only changed signatures; `grep` of removed lines for assert/raises/skip/xfail: none). The AT-239/260/264 rationale compaction left behaviour intact except one message: `cli.py expand_cases` now says `generation failed, no cases persisted` for ProviderError (was `model call failed`); exit code and no-persist unchanged, tests green. Non-behavioural: typer colours as strings, docstring and section-comment removals.
- Queue field (smallest correct change?): YES. `trigger_run` only queues (hosting merge), so the filter must travel with the entry; adding `QueueEntry.priorities` (default None) + `RunQueue.submit(priorities=)` + `_run_queued` passing `entry.priorities` is the minimum. An old queue file loads (probe). A queued row persisted to `run_queue.json` keeps its filter across restart (`recover` reloads the same entries). The filter cannot be dropped: QUEUE mutant dropping it in `_run_queued` goes red; it cannot be widened: `list_cases` selects only listed priorities plus pinned p0. Residual: `submit` types priorities as `list[str]`; QueueEntry still validates against the literal.
- Doctor: files at 300/299/300/295 lines, `autotester doctor` -> clean; `ruff check src tests scripts` -> All checks passed.

## Secrets (item 5) - planted `Pa$$w0rd"<b>&'\ü-ZZ9` in every free-text input
Evidence: `secrets-probes/` (5 scripts, baseline 3d8f7d5a compared).
- Failure bundle path: STORED SCRUBBED (case, verdict, result, error, steps, trace, manifest), `check_no_secrets` clean, a secret in a span is refused and the `.partial` left is clean. Unchanged FB3.
- Tampered `BundleFile.name` with `: / \`: REJECTED by the new validator, message constant (baseline echoed it raw; improvement).
- UI refusal page: message HTML-escaped, no secret form in the body. QueueEntry priorities: Literal-rejected, nothing stored.
- NOT scrubbed, newly opened: `case_proposals.jsonl` stores `reviewed_by` (the `--by` text) and a second copy of flow name/id (title, flow_id) raw, and `--proposals` echoes the title on stdout. The store layer never scrubs (no Redactor in store/*.py) and baseline already stores flow name raw in cases.jsonl; the new file is not read by any bundle, report, prompt or log. I rule this not a FAIL (same surface class as baseline, no new exposure route), recorded as PROPOSED-ISSUE P1.
- `POST /run?priority=<bad>` 422 echoes the caller's own value (default FastAPI handler, nothing stored): P2.

## Browser (Mode D) and dev persona walk - done
LIVE-BROWSER: qa/evidence/browser-t178-failure-bundle-fb4-fb5-2026-10-11-checker-a/ (headless Chromium, one context, server on 127.0.0.1:8791, throwaway root, no model call, server stopped, port free). Pages 200 with 0 console errors; the two themed refusal pages return 400 (one expected "Failed to load resource" each). Refusal 1 names the exact CLI command, escapes `<b>` in the project name; refusal 2 (after CLI approvals) is the credential page; approval is checked before credentials; `?priority=p9` 422; no run queued. Persona walk (dev): findings low only (no onward link on refusal 1, Cases page shows no priority/pinned, `/run` refusal is raw JSON and the provider gate hides the selection result).

## PROPOSED-ISSUE
- P1 {"severity":"medium","feature":"failure-bundle","title":"case_proposals.jsonl stores reviewed_by and a flow-name copy unscrubbed (store layer never calls Redactor.scrub; C5 'every stored artifact')","evidence":"cli.py expand_cases --by -> schema/case.py CaseProposal.reviewed; probe secrets-probes/probe1b_disambig.py"}
- P2 {"severity":"low","title":"POST /run?priority=<value> 422 body reflects the raw query value; no RequestValidationError handler","evidence":"secrets-probes/probe3_http.py"}
- P3 {"severity":"low","title":"scripts/check_no_secrets.py scan tests `value in text`, so a secret containing quote or backslash stored JSON-escaped reads clean (Redactor.contains_folded detects it)","evidence":"secrets-probes/probe4_scanner_gap.py"}
- P4 {"severity":"low","title":"routes_learn.generate_cases runs proposal staging before the provider-availability refusal; the existing credential-refusal test had to be edited to approve proposals first (brief section 10 asked the pure availability refusal to come first)","evidence":"ui/routes_learn.py:238-253; tests/test_ui_learn.py diff"}
- P5 {"severity":"low","title":"trigger_run priority set matching zero cases answers 'no cases to run' (builder's note); Cases page shows no priority; files at the 300-line cap (paths.py, routes_learn.py) and project_store.py 299","evidence":"manifest PROPOSED-ISSUE lines"}
- P6 {"severity":"low","title":"CaseProposal approvals are unsigned file rows (id excludes status): a hand-edited status/reviewed_by passes validation, same trust model as flowspec approve","evidence":"schema/case.py compute_id"}
- P7 {"severity":"low","title":"manifest round-cap list is inexact (7 seams past the cap, not 6; routes_learn 4 not 2; schema/run_queue 1 not 0); ARCHITECTURE.md still owes case_proposals and QueueEntry.priorities lines","evidence":"this verdict, ruling section"}

CAPABILITY-COVERAGE: 4/4 falsifications reproduced (FB4, FB5, CONTAIN, QUEUE)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only)
full-suite trigger: security-touching L unit; the suite is the Remaining item, not deferred to 6c
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Every mandatory item except the full suite is done and green; the suite lock stayed busy for 15 min, so per the dispatch this returns CONTINUE-NEEDED with only the suite remaining. Not a FAIL. If the suite is clean apart from ledgered reds this side converts to PASS, but the owner round-cap waiver (seven seams) is still required before merge.
Metrics: start=2026-10-10T20:48:08Z end=2026-10-11T00:21:00Z wall_min=40 agent_min=unavailable blocked_min=15 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2400 mutants=2 defects_unit=0 defects_6c=0
slow: suite lock wait 15 min (blocked_min); session-limit gap excluded from wall_min
