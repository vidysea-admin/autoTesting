# Verdict — t136-bench-foundation (T-136a foundation, K1-K8)

Cycle checked: 0
Bound to: D:/autoTesting/.worktrees/t136-bench (branch wave/t136-bench, commits 99ae4d85 + 484353e6, base 2fae2504)
Policy-Version: proportional-verification/2026-10-06.6 (manifest pin)
Date: 2026-10-07

## Check plan (step 0)
Diff: schema/bench.py, stages/bench.py, scripts/bench_trial.py, tests/test_bench.py, docs/MAP.md (+ manifest). No UI, no
portal, no data artifact, no security/auth/tenancy, no production write. Routed checks: affected tests, ruff, doctor,
15-row falsification floor (one per capability, one throwaway copy per row), diff-scope read (4c), mocked reproduction of
the unexecuted script's changed lines. No browser/model/network/.env use (t125 gate).

TIER: M (multi-file schema + scoring logic; no L trigger cited in a changed non-test file)

## What I ran (all by myself)
- `uv --directory <wt> run ruff check src tests scripts` -> `All checks passed!`
- `uv --directory <wt> run autotester doctor` -> `doctor: clean`
- `uv --directory <wt> run pytest tests/test_bench.py tests/test_regression_proof.py tests/test_core.py tests/test_schema_video.py tests/test_ledger.py` -> `98 passed in 1.33s`
  (the unit's own tests, the only test that imports bench_trial, and the schema/ledger/core round-trip tests).
- FULL SUITE: NOT RUN. The standing gate qa/gates/t125-fullsuite-browser-egress.md says "Full-suite/browser execution waits
  for proven containment", tests/conftest.py's module-scoped `page_factory` launches real Chromium, and about 35 test
  files start local servers or subprocesses. The dispatch also restricted me to mocked fixture runs. The blast radius of
  this diff is pure Python (schema/bench.py, stages/bench.py; importers = project_store, schema/__init__, test_bench,
  test_regression_proof), all covered by the 98-test run. The policy's one full suite for an M unit therefore stays with
  the orchestrator/backstop once containment is proven. suite_runs below counts it as 0.
- Falsification, 15 rows, each in its own copy (`fzrow1..15` in scratchpad, PYTHONPATH to the copy, autotester.__file__
  confirmed to be the copy), single-hunk single-file edit, named node only. Every row: green in the copy before, red after,
  and the assertion that fired is the one the check is named for (not an import/parse failure):
  K1 dup ids (DID NOT RAISE) · K1 mode/provenance (DID NOT RAISE) · K2 matched_bug_id=None (`None == 'bug_login'`) ·
  K3 wrapped score (dict mismatch) · K4 trials[:1] (KeyError 'human-oracle-baseline') · K5 ordering exclude=True
  (roundtrip inequality) · K6 kind check removed (3/3 DID NOT RAISE) · K7 prompted filter dropped (`prompted high-severity
  report cannot earn recall`) · K7 denominator filter (`only independently confirmed live truth counts`) · K7/K8
  unknown ordering (`0.75 is None`) · K7 ai_read_human_first (`0.75 is None`) · K8 duration default 0.0 (`0.0 is None`) ·
  K8 FP rate `else 0.0` (`0.0 is None`) · K8 unknown truth provenance (`0.25 is None`) · K8 unknown human-finding
  provenance (`0.0 is None`). 15/15 reproduced. The bound tree was never edited.
- Mocked reproduction of scripts/bench_trial.py's changed lines (corpus mode="fixture", `ordering="independent_parallel"`,
  `oracle_human_trial` with no duration, `scorecard`) with hand-built verdicts: AI side detected 1/1, recall 1.0, duration
  12.3; oracle side detected 1/1, duration None with reason `timing not recorded`; the script's own `ok` predicate
  (`detected == seeded == 1`) is True. The script itself was NOT executed.

## Criteria
- [K1] corpus with typed seeded truth + validators (duplicate ids, mode vs provenance): MET (tests + 2 falsifications). The
  corpus bench_trial.py builds is reproduced above.
- [K2] mechanical conversion verdict->Finding, matched_bug_id only via the case map: MET at the mechanical layer
  (test + falsification). K2-live (real non-mock judge) is out of scope and the manifest does not claim it.
- [K3] scorecard returns trial.score verbatim: MET (falsified).
- [K4] scorecard names every participant: MET (falsified).
- [K5] ProjectStore roundtrip preserves ordering/kind/provenance/nullable time: MET (falsified).
- [K6] typed `kind` field, kind/participant mismatch refused, carried into the score: MET (falsified, 3 params).
- [K7] ordering per trial, independent/prompted per finding, recall from the independent subset only, FP over all reports
  and labelled `false_positive_population`: MET (4 falsifications).
- [K8] unavailable, not a flattering default: ordering, kind, corpus mode, truth provenance, finding provenance, timing,
  zero reports: MET (6 falsifications).
- K9 and the human-findings comparison: out of scope; the manifest states they are NOT in this unit and keeps T-136 pending.

## 4c diff scope
The old test `assert trial.duration_s == 0.0` is replaced by `is None` plus a timed-oracle assertion, as K8 requires (the
old value is the defect K8 names); a contract-driven replacement, not a weakening. No function, class, route or config key
is deleted. Changed files are all listed in the manifest's "What changed".
Observation (not a FAIL): docs/MAP.md on this branch was regenerated against the base's committed source and so reverts
rows master's MAP carries for its uncommitted tree (`browser/session.py` and `schema/ledger.py` descriptions, the
`DecisionClaim` and `CitationReview` rows). doctor is clean here; after the master dirty tree is restored and this merges,
MAP needs `autotester map` again.

## Judgement on the "script never executed" claim
Consistent with the evidence: the scripts/bench_trial.py diff is 5 lines (corpus `mode="fixture"`, `ordering=`, a
comment), the script needs a native browser and a paid judge, and I did not run it. The manifest discloses it as UNVERIFIED
and defers it to T-136 K2-live. I accept that as out-of-scope capability evidence only because the changed lines are fully
exercised by the mocked reproduction above and the only unverified part is the live run. It is not evidence of the K2 live
criterion.

## Findings
PROPOSED-ISSUE: {"severity":"low","feature":"bench","title":"docs/MAP.md on wave/t136-bench was regenerated from base source and drops master's DecisionClaim/CitationReview and browser/session.py rows; on merge keep master's MAP.md, then rerun `autotester map`","evidence":"git diff 2fae2504...HEAD -- docs/MAP.md","type":"merge-note"}
PROPOSED-ISSUE: {"severity":"low","feature":"bench","title":"score() reports detected 0 and seeded 0 beside a None rate when the denominator is unavailable; the counts read as measured zeros","evidence":"src/autotester/schema/bench.py _eligible_truth returns {} truth, score() len(matched)/len(seeded)","type":"k8-adjacent"}
PROPOSED-ISSUE: {"severity":"low","feature":"bench","title":"Full suite for this unit is owed once the t125 containment gate allows it","evidence":"qa/gates/t125-fullsuite-browser-egress.md","type":"deferred-evidence"}

VERDICT: PASS
SCOREBOARD: 8/8 criteria met (K1-K8), invariants hold
TIER: M
CAPABILITY-COVERAGE: 15/15 rows reproduced
LIVE-BROWSER: not-applicable (schema/stage/script data model; browser forbidden by t125 gate)
ISSUES-WRITTEN: none (proposed only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: All eight foundation criteria are evidenced by my own runs: 98 affected/importer tests green, ruff and doctor clean, and 15 isolated green-before/red-after falsifications. The manifest claims neither K9 nor K2-live. The one deviation is the policy's full suite, withheld by the t125 gate and replaced by a bounded non-native run covering every importer of the changed files.
Metrics: start=2026-10-07T02:34:10+05:30 end=2026-10-07T02:38:30+05:30 wall_min=5 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=15 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
