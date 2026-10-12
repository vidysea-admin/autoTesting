# Verdict: t202-any-model-provider merge-reconcile check A (mr1.a)
Cycle checked: 0 · Policy-Version: proportional-verification/2026-10-10.9 · Bound to D:/autoTesting · Head 868e3682 (worktree D:/autoTesting/.worktrees/t202-any-model-provider) · Reconcile base 94c569c0 (ancestor of head, verified) · Merged master 29d02c4b · Resumed after a session rate limit (no evidence lost; all of it below was produced by me)

## Plan
Tier L (the unit's pinned class; I raise nothing). Merge-reconcile: (1) per-file blob compare vs 94c569c0 using a clean 3-way merge (base db77d7bf, unit 94c569c0, master 29d02c4b) as reference; (2) cli.py ast compare; (3) AT-790 moved-test ruling and falsification; (4) nothing dropped from master; (5) affected tests, ruff, doctor, lock in the worktree; (6) merge forecast vs current master bd508b66. No full suite (per brief). Manifest lint exit 0.

VERDICT: PASS
SCOREBOARD: LL1-LL14 hold on the affected set; the reconcile touched LL2, LL8, LL11, LL12, LL14, each re-evidenced below. Invariants: none touched.
TIER: L (pinned by the manifest: dual-trigger security providers/litellm_provider.py:191; unchanged by me)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (merge reconcile; one falsification per touched criterion run by me, section 5)
LIVE-BROWSER: not-applicable (no screen added; routes_runs and routes_learn are driven through TestClient)
ISSUES-WRITTEN: none (dual coordinator PASS has no side effects)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## 1. Hunk classification (32 files the unit changed at 94c569c0; 12 differ at head)
(i) brought by master, (ii) conflict resolution, (iii) builder reconcile edit. Reference = `git merge-file` of unit/base/master; the residual diffs are in evidence/hunks-3way-vs-head.txt.

| File | Class | Detail |
|---|---|---|
| .env.example | (i) | clean 3-way equals head |
| docs/MAP.md | (i) | clean 3-way equals head; `autotester map` in a copy reproduces head byte for byte |
| ui/routes_runs.py, ui/run_execution.py, tests/test_credential_run_approval.py | (i) | clean 3-way equals head |
| src/autotester/cli.py | (ii) one conflict, rest (i) | `expand_cases` = master's stage_and_review / preflight / `store=` flow + the unit's `cli_orchestrate.usable_provider(provider)`. `ast.dump` per top-level node: head vs master differs ONLY in `expand_cases` (the usable_provider line in place of master's providers.get block); head vs unit differs ONLY in `expand_cases` and master's `release-report` registration. Semantic union. 295 lines |
| ui/routes_learn.py | (ii) one conflict, rest (i) | master's proposal-staging gate first, then the unit's `for_role` / `why_unavailable` refusal, then master's `expand(..., store=store)`. No builder trim: the 300-line fit is master's own AT-264 comment compression (base-to-master diff). ast: head vs master differs only in imports and `generate_cases` |
| tests/test_cli_advice_resolves.py | (ii) one conflict | EXPECTED_SITES keeps `("cli.py","expand")`, swaps `("cli.py","providers")` for `("cli_orchestrate.py","providers")` (the advice text moved); all other master entries kept; head vs master is a one-line swap; EXPECTED_SITE_COUNT 24 equals the real count (test passes; M4 with 23 goes red) |
| tests/test_ui_runs.py | (iii) 1 hunk | master's new priority test patched the removed `LangChainFallbackProvider`; retargeted to a `for_role` lambda, same assertions (M5 reddens it) |
| tests/test_ui_runs_serial_resilience.py | (iii) 1 hunk | two-line `for_role` patch collapsed to one line (`lambda p, r:`) to stay at the 300-line cap (301 after merge); behaviour identical, file's tests passed |
| tests/test_ui_learn.py | (iii) 2 hunks | (a) master's pending-proposals test retargeted `LangChainFallbackProvider` to `for_role`, same fail-if-reached body; (b) AT-790 test and its two now-unused imports removed (section 3) |
| tests/test_ui_learn_vendor_echo.py | (iii) new | the moved AT-790 test |
| qa/manifests/t202-any-model-provider.md | not product | |

Every (iii) hunk is justified: a removed symbol, the line cap, or the protected move judged in section 3.

## 2. Known reconcile edits
cli.py, routes_learn.py and the advice test are as classified. `autotester doctor` clean (cli.py 295, routes_learn.py 300 lines).

## 3. AT-790 moved test: RULING = NOT WEAKENED (line diff in evidence/at790-moved-test-diff.txt)
Body at 94c569c0 vs head: every assertion is identical: `status_code == 400 and "could not complete" in response.text`, `canary not in response.text`, `store.list_cases() == []`; same fake vendor errors (`403 ... ?key=<canary>` x60), same env (LITELLM_API_KEY, GEMINI_API_KEY = canary), same `LiteLLMProvider("gemini/gemini-2.5-pro")`, same `for_role` patch. Only differences: the added `_approve_proposals(store)`; the in-function import hoisted to module level; the function docstring moved to the module docstring (which names AT-790/LL8); `# noqa: F811`. No assertion deleted, loosened or made unreachable.
Does `_approve_proposals` change what is proven? No. The original predates t178's proposal gate, so "unapproved proposals" did not exist for it. F3 (copy): with the call removed the test goes RED at `"could not complete" in text`, because the route stops at "Case proposals need human review". So the call is what lets the test reach the provider-failure page, and the `"could not complete"` assertion stops `canary not in text` from passing vacuously. The proven claim, that the provider-failure page carries no vendor-echoed key, is the same.
Collected: `tests/test_ui_learn.py::test_generate_failure_page_...` is gone; the same name is collected as `tests/test_ui_learn_vendor_echo.py::test_generate_failure_page_does_not_carry_a_vendor_echoed_key` (PASSED in my run). Test-function-name set of tests/: 94c569c0 vs head, the only missing name is that one (present in the new file); master 29d02c4b vs head, nothing missing (evidence/tests-lost-*.txt).
F2 (copy outside the worktree): `hidden = []` in `litellm_provider._failure` (vendor text echoed) gives green before, RED after on `assert canary not in response.text` (canary visible in the page), green when restored.

## 4. Nothing from master dropped
`git diff 29d02c4b 868e3682 --name-status` lists 34 files: the unit's files plus the new vendor-echo test and nothing else. Every other file master changed since the base (629 files) therefore equals master's blob. SNAPSHOT.md equals master's and `autotester snapshot` in a copy reproduces it identically; MAP.md reproduces too.

## 5. Re-run on head, all through `uv --directory <worktree> run`
`autotester.__file__` = D:\autoTesting\.worktrees\t202-any-model-provider\src\autotester\__init__.py; pytest rootdir and interpreter are in the worktree (evidence/affected-tests.log). 29 test files (the unit's, every retargeted file, expand/cli/failure-bundle/pinned): **374 passed, 1 skipped** in 808 s. The skip is `test_ui_runs_serial_entry_mix_live.py` (`pytest.skip` when playwright or the browser is missing; present at the base). `ruff check src tests scripts`: All checks passed. `autotester doctor`: clean. `uv lock --check`: Resolved 123 packages, no change. The worktree `git status` stayed clean (all copies and mutants were on C:, outside it).
Falsifications, each in a copy of the head archive (green before, red after, restored; evidence/falsifications.txt): M1 cli ignores --provider (LL11): red; M2 routes_learn proposal gate removed (t178 piece kept by the merge): red; M3 routes_learn ignores `for_role` (LL2): red; M4 EXPECTED_SITE_COUNT 23 (advice guard): red; M5 routes_runs builds `LangChainFallbackProvider` (LL2): red; F2 AT-790 echo: red. All fired on the named assertions, none on import errors.

## 6. Merge forecast against CURRENT master bd508b66 (merge-base with head: 29d02c4b)
`git merge-tree --write-tree master 868e3682`: exit 1, ONE conflict, `.env.example` (master edited the AUTOTESTER_TIMEZONE comment and added AUTOTESTER_SCHEDULE_GRACE_MINUTES and AUTOTESTER_TICK_INTERVAL_S right above the trailing `AUTOTESTER_MODEL=` placeholder that the unit moves up to "Model providers"). Resolution: keep master's lines, drop the trailing placeholder. `docs/MAP.md` auto-merges, but master added schedule modules, so run `autotester map` after the merge. Master's other non-qa changes since 29d02c4b (schedule*, explore_consent, grade.py, test_grade*) touch no unit file; the integrated-master suite before push covers them. Report only: nothing merged.

PROPOSED-ISSUE: {"severity":"low","type":"wording","title":"manifest Metrics line lacks the .9 fields (lane, check_s, mutants, defects_unit, defects_6c); lint still passes","evidence":"qa/manifests/t202-any-model-provider.md:142"}
PROPOSED-ISSUE: {"severity":"low","type":"process","title":"merging t202 into current master conflicts in .env.example (schedule keys vs the moved AUTOTESTER_MODEL); resolve by hand and rerun autotester map","evidence":"qa/evidence/t202-any-model-provider-mr1-A/merge-forecast.txt"}

EXPLANATION: The unit's code at head equals the PASSed 94c569c0 code except master's hunks, three conflict resolutions that keep both sides, and four test reconcile edits, each justified; the AT-790 test moved with every assertion intact and goes red when the defect is reintroduced. Every other file equals master. No full suite was run (brief); the integrated suite covers the remainder.
Metrics: start=2026-10-11T06:16:21Z end=2026-10-11T09:15:00Z wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=6 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=5 defects_unit=0 defects_6c=0
Evidence: qa/evidence/t202-any-model-provider-mr1-A/ (a session rate-limit stop sits inside the wall time and is not separable, so wall_min and blocked_min are unavailable)
