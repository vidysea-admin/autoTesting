# Verdict A — d063-grant-budget (+ stacked pathlynks-exact-host), repair cycle 1

Date: 2026-10-07 · Checker coordinator A (dual check, blind) · Bound root: D:/autoTesting/.worktrees/d063-grant-budget · Head checked: b90618c9 · Base bd2fe8f4 · Cycle-0 code head a4bd0a60
Cycle checked: 1
Policy: proportional-verification/2026-10-06.6
Prior cycle-0 verdict archived at qa/verdicts/d063-grant-budget.r0-1.md (not re-read beyond my checkpoint).

## Check plan (step 0)
TIER: L (unchanged; cycle-0 L triggers core/consent.py, core/ids.py, browser/secrets.py:88, routes_runs.py). Cycle-1 diff since my checked state a4bd0a60: `git diff a4bd0a60 HEAD --stat -- src scripts projects .goal docs` is empty (no product, config or registry lines). Changed non-qa files: tests/test_approve_cli_bounds.py (new), tests/test_consent.py (+1 assertion line). No conftest, fixture, lock or config change (tests/conftest.py sha256 9bbb6a4bc2be7eb9.. and uv.lock 188681b3a300c36f.. identical to my checkpoint). Not a protected test change: nothing deleted, weakened, skipped or thresholded. Dual check: both coordinators must PASS.

Evidence-identity reuse (code hashes unchanged): full suite, doctor, mix_live, exact-host 5 files + 4 mutants, grant-path review, budget review, and the 9 cycle-0 capability rows whose src and test nodes are byte-identical. Re-run: ruff over tests (tests changed), the 3 affected test files, and the 4 new or changed capability rows, each in its own throwaway copy outside the root.

SERIAL: none needed (one copy per row; the only runs in the bound tree were ruff and the affected pytest files).
Full suite NOT re-run: src identity unchanged since the one suite already recorded; the diff only adds tests that the affected run covers (RAM constrained, another checker runs a suite).

## Evidence
- ruff check src tests scripts (bound root): All checks passed.
- Affected tests in the bound root: tests/test_approve_cli_bounds.py tests/test_approve_cli.py tests/test_consent.py -> 57 passed in 0.86s (matches the manifest).
- Capability rows (copy of HEAD src/scripts/tests/pyproject, PYTHONPATH=src:scripts, single node each, green-before in the copy, red-after, restored from git archive):
  - C3 CLI nan/inf: cli_crawl.py:256 `if not math.isfinite(wall_clock) or min(...) <= 0:` -> `if False:`; node test_approve_refuses_a_nonpositive_or_nonfinite_bound_and_writes_nothing: before 9 passed; after FAILED [--wall-clock-nan] and [--wall-clock-inf] (2 failed, 7 passed; the failing assertion is the exit-code one at test_approve_cli_bounds.py:52, which the test is named for); restored 9 passed. The 0, negative and -inf cases stay green because typer `min=` refuses them first, as the manifest discloses.
  - C3 defaults: cli_crawl.py:246 `False, "--production"` -> `True`; node test_approve_defaults_are_positive_finite_and_not_production: before 1 passed; after FAILED at :65 (row.production True); restored 1 passed.
  - C1 account grant never production: consent.py:85 `production=False` -> `True`; node test_account_grant_is_new_exact_and_bounded: before 13 passed; after FAILED [valid] and [unused] at test_consent.py:258 (the new `assert row.production is False`); restored 13 passed.
  - C1 scope (cycle-1 replacement row): consent.py:45 `_host_matches(host, d, ref.include_subdomains) for d in` -> `True for d in`; node ...[scope]: before 1 passed; after FAILED at test_consent.py:250 (no refusal raised); restored 1 passed. This is the edit cycle 0 lacked (clause -> False kept the node green); it now isolates.
- Cycle-1 diff scope (4c): files touched are exactly those in the manifest's "What changed" plus qa/manifests; no function, test or key deleted. The manifest says tests/test_approve_cli.py changed and was "split" at the 300-line cap; the commit leaves it untouched (276 lines). Wording only, low.
- Exact-host slice: manifest re-pin .5 -> .6 and Status BUILDING -> ready-for-check only; src, tests and projects/pathlynks are unchanged vs my cycle-0 identity, so acceptance 1-4 and the 4 killed mutants carry over.
- Acceptance 1-7: judgement as in my checkpoint, with the two cycle-1 gaps closed: the CLI path of criterion 3 has isolated tests (nan/inf) and the production default is pinned; criterion 1 scope row now falsifies.

## Findings (non-blocking)
PROPOSED-ISSUE lines P1-P5 from cycle 0 stand unchanged (credential-free LIVE_CASE reuse of the account-derived row, preflight probes=0, probe default sizing and stop reason not in run.json, master-tip test_goal_contract_registration failure, low rows). This cycle adds:
PROPOSED-ISSUE: {"title":"d063 manifest cycle-1 note says tests/test_approve_cli.py changed and was split; the commit leaves it untouched","severity":"S3","type":"wording","location":"qa/manifests/d063-grant-budget.md Fix cycle 1 F1","detail":"wording only, no behaviour claim"}
HUMAN_GATE-REQUEST: unchanged from cycle 0: should a minted account-derived LIVE_CASE row authorise only the case set it was derived for, or any credential-free LIVE_CASE run on the same target until expiry (CN5 vs CN11)? Umesh rules.

VERDICT: PASS
SCOREBOARD: 7/7 acceptance criteria met (exact-host acceptance 1-4 also met), invariants C5, C12, CN10 hold
TIER: L (security/auth grant and key creation: consent.py, ids.py; credential scope secrets.py:88; src unchanged this cycle)
FAILURES: none
CAPABILITY-COVERAGE: 4/4 cycle-1 rows reproduced (CLI nan/inf, CLI default production, grant production, scope True); 9/9 cycle-0 rows carried by identity; exact-host 4/4 mutants carried
LIVE-BROWSER: not-applicable (no screen or template changed; tests only this cycle)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE lines above and in the archived cycle-0 verdict)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-1 commit changed only tests and manifests; src identity equals the cycle-0 checked state, so the recorded suite, doctor and review evidence carries. The new CLI-bound and production-default tests and the added `row.production is False` assertion each go green-before, red-after on the named assertion and green restored in isolated copies, and the replacement scope falsification now isolates its row. No reproduced defect.
Metrics: start=2026-10-06T20:32:04Z end=2026-10-06T20:36:00Z wall_min=4 agent_min=4 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
