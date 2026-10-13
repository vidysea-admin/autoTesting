# Contract — Generic two-mode acceptance (T-169)

**Unit:** T-169 "Generic two-mode acceptance: rich teaching inputs and URL-plus-credentials only, no CLI".
**Serves:** `docs/intent.md` O6; `docs/spec.md` R31; `qa/contracts/bench.md` K3, K9, K10, K11; `qa/contracts/orchestrator.md` OR1.
**Authority:** D-089 item 3 and D-090 (build and accept without the independent human list; recall is "unavailable", FP rate and time are measured).
**Origin:** folded by /checker (2026-10-13) from the maker's GA1-GA4 in `qa/feedback-inbox.md`, tightened, plus GA5 and the REAL criteria.
`done_check`: `uv run pytest tests/test_generic_acceptance.py`.

Scope tags: **LOCAL** = provable now on the in-repo fixture product (`tests/fixtures/regression_site`), no browser, no model, no network beyond
127.0.0.1. **REAL-TARGET** = needs a real product run; not closable in this unit's local pass.

## LOCAL criteria

- **GA1 (LOCAL)** Each entry mode runs end to end on the fixture product through the app's own routes (`POST /onboard`, flowspec approve,
  `cases/generate`, `run`) and `orchestrate.run_or_resume`; no CLI is invoked. Teaching sources (a video plus a doc) make the orchestrator
  choose INGEST (mode `learn`); a URL plus test credentials only make it choose DISCOVER (mode `explore`). The other entry stage never appears in
  that run's ledger, and MODEL ends `done`. Verify: a test per mode asserts the chosen stage, the absent stage, an approved FlowSpec with at least
  one flow, stored cases, and a stored run. Mutation: route credentials-only to INGEST and the url_only test goes red.
- **GA2 (LOCAL)** Each mode ends in the EXISTING `bench_from_run` followed by `build_comparison`/`completeness_problems`. The harness defines no
  scorer, rate, or comparison of its own (one concept, one place). With no human list: `human_list == "absent"`, recall carries the K10 reason text
  and is never `0.0`, FP rate and duration are numbers from the trial, and `completeness_problems` is empty. Verify: the e2e asserts these; grep
  shows `generic_acceptance.py` imports and calls `bench_from_run`, `build_comparison`, `completeness_problems` and defines no scoring math.
- **GA3 (LOCAL)** The harness is slug-driven: `ModeSpec.onboard=False` drives an already-onboarded project without re-posting `/onboard`, so the
  same harness can later run on Pathlynks. Every model/browser contact is a seam on `ModeSeams`; the module imports no browser and no live
  provider. Verify: a test runs a second pass with `onboard=False` and asserts `/onboard` was not posted.
- **GA4 (LOCAL)** Orchestrated parked proposals (`runs/<id>/ingest.flowspec.json`, `discover.flowspec.json`) are aux files: `load_results` skips
  exactly them, `prune_old_videos` no longer crashes on a run dir that has them, and an unreadable non-aux JSON in a run dir still fails loudly.
  Verify: a direct `load_results` regression test (both directions).
- **GA5 (LOCAL, verdict on a gap) "No CLI" requires a UI route for case-proposal review.** `POST /cases/generate` refuses until proposals are
  reviewed, and no route exists to review them, so a user without the CLI is stuck after flowspec approval. The harness approves proposals through
  `ModeSeams.review_proposals`, a code seam, which is acceptable for the harness test only as a stand-in. GA5 is: a UI route lets a human review
  (approve/reject) staged case proposals, and the harness drives it instead of the seam. It is built separately as unit `proposal-review-ui`.
  Until that unit passes, T-169 may close LOCAL-PASS-with-gap but "no CLI" is not fully true for Mode 1/2 end to end.
- **GA6 (LOCAL)** Design rules: file at most 300 lines, function at most 50 lines, module docstring states one job, no `*_v2`; `ruff check src
  tests scripts`, `autotester doctor`, and the neighbours (orchestrate, bench, acceptance comparison, video retention) stay green.

## REAL-TARGET criteria (not closable by the local pass; record, do not fake)

- **GR1 (REAL)** Both modes run on a real target (Pathlynks, after T-145 provides data) with real vision, agent and browser seams, driven through
  the same harness (`onboard=False` if the project exists), without a CLI.
- **GR2 (REAL)** Per mode, the comparison artifact reports bugs found, FP rate, branch coverage and wall-clock from `BenchTrial.score` against the
  seeded-or-confirmed list; recall vs a human is "unavailable until the human list arrives" (D-089 item 3, D-090) and then computed from the
  independent subset only (K7).
- **GR3 (REAL)** Umesh's verdict (AutoTester vs the expert human tester) is recorded as a decision on that artifact, never computed by it; the
  real thresholds are open question Q3 (`docs/intent.md`) and are his to set.
- **GR4 (REAL)** The real UI runs keep the AT-570 gap visible: a UI case run enforces no signed approval today; the report states what the run did.

## Changelog
- 2026-10-13 · /checker fold-in · GA1-GA4 from the maker's proposal, GA5 (proposal-review route ruling) and GA6 added, GR1-GR4 added.
