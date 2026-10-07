# Verdict: reconcile (cycle 0, single checker) - PASS

Date: 2026-10-07. Bound to D:/autoTesting (worktree .worktrees/reconcile, branch wave/reconcile). Checker: claude-sonnet-subagent; executor of the unit: maker (manifest). Contract qa/contracts/reconcile.md (8b9bdb89). Policy-Version: proportional-verification/2026-10-07.7. Cycle checked: 0. Resume: 0 of 2.

## Check plan
Diff base 6f351e11 (ancestor of HEAD, equals merge-base with origin/master) .. HEAD b78baf79: 13 product/test files plus the manifest. Tier M: multi-file behaviour, shared modules (schema, ingest, merge, screen_identity), a new stage. L triggers searched in the changed non-test files: none (no consent, credential, approval, deletion or prod-write change; no config, hook, CI or dependency change; no concurrency). `providers/`, `ui/`, `core/consent.py`, `stages/explore_consent.py`, `review.py`, `docker/`, `.env.example` and the golden prompts are untouched. Not UI, so no browser check. Checks run: the verify commands, the affected importers, one own falsification per criterion in throwaway copies (green before in each copy, red after), the public-repo safety read, the diff scope. Full suite not run (full-suite trigger: none; the pre-push integration check is the maker's step 6c).

TIER: M (additive default-valued schema fields and a new stage; no L trigger cited).

## Evidence
- `uv run pytest tests/test_reconcile.py tests/test_reconcile_schema.py tests/test_ingest.py tests/test_merge_flowspec.py tests/test_schema.py` -> 74 passed (exit 0). `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> clean.
- Importer set (22 test files that import the changed modules, no live-browser ones): 272 passed, 1 failed. The failure is `tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered`: it asserts on `.goal/dashboard.html` text against `.goal/goal.json`. The diff touches no `.goal/`, `plan.md` or `docs/DECISIONS.md`, so it is not this unit (a stale generated dashboard at the base).
- Frozen sample re-run by me through `reconcile` (mock judge 0.9): 27 canonical screens (new 25, matched 2), 2 judge calls, flows 6 in and 6 out, kinds ideal 5 / narrated 0 / variant 1, 1 unresolved step, 92 of 93 steps resolve to a screen (98.9%), 0 narration_unverified, 1 possibility. Matches the manifest. The fixture is non-trivial: 3 sources, 38 screens (10+12+16), 6 flows, `/counsellor/dashboard` in 3 sources, 2 same-named "Sign in" flows.

## Falsification (own; isolated copy per row; green before, red after; 27 rows)
Harness: `%TEMP%/rcfals/fals.py` and `fals3.py`. Each row is a fresh copy of src+tests+docs+scripts+pyproject run with `PYTHONPATH=<copy>/src`, only the named node(s). Every row was green in its copy and red after one single-hunk edit, and the failing node is the one named for the criterion:
- RC1 `screen_id=None` in `_to_step` -> red (2 tests).
- RC2a narration dropped, RC2b exit_screen dropped -> red.
- RC3 quote check removed -> red. RC3b step-level scrub removed alone SURVIVES (the second layer `_assemble.scrub_obj` also scrubs; disclosed by the maker as defence in depth); RC3c both layers removed -> red.
- RC4 fold removed -> red; RC4b route-less screens folded by name -> red.
- RC5 `>=` changed to `>` at 0.8 -> red (boundary 0.80); RC5b a second 0.8 literal -> red.
- RC6 confidence bar 0.8 lowered to 0.5 (0.79 promotes) -> red; RC6b judge called for rule rows -> red.
- RC7 `video_only` never set -> red.
- RC8 name-only flow id -> red (2 tests); RC8b last flow dropped from the output -> red (balance and frozen).
- RC9 crawl basis skipped -> red; RC9b modal pick replaced -> red.
- RC10 possibilities not recorded -> red; RC10c reconcile reads `review.status` -> red.
- RC11a idempotent return removed -> red; RC11b new flows in reversed order -> red.
- RC12a prompt not scrubbed -> red; RC12b `assert_no_raw_secrets` removed -> red; RC12c `import httpx` added -> red.
- RC13 `socket.socket()` inside reconcile -> red.
- RC14 reconcile.py padded to 332 lines -> doctor adds `file-too-long` (a bare copy always shows one stale-SNAPSHOT line; the bound tree is clean).
CAPABILITY-COVERAGE: 14/14 criteria reproduced, 27 rows.

## Criteria
- RC1 met: the field is optional with a default, `extra="forbid"` is kept, a pre-unit FlowSpec round-trips byte-identically (test_rc1_pre_unit_flowspec_loads_and_round_trips_byte_identically), 98.9% of steps resolve, and the rest are listed in `unresolved_steps`.
- RC2 met. RC3 met (judgement below). RC4 met.
- RC5 met: `MATCHED_AT` and `AMBIGUOUS_AT` are the only threshold literals in reconcile.py (grep shows no second 0.8 or 0.5).
- RC6, RC7 met.
- RC8 met: existing flow ids are never rewritten, and `_new_flows` recognises a legacy-id re-ingest of the same source.
- RC9 met.
- RC10 met: no `require_reviewed` or `ReviewStatus.APPROVED` in reconcile.py, and the review status is never read.
- RC11 met.
- RC12 met: only `Provider.judge`; the prompt comes through `load_skill_prompt("reconcile-screen")`; scrub then `assert_no_raw_secrets` before every call; no SDK, requests or httpx import.
- RC13 met: mock provider only; the sockets-blocked test is green and goes red under mutation.
- RC14 met: doctor clean, ruff clean, reconcile.py 292 lines, ingest.py 299, flowspec.py 255, screen_identity.py 145; `git diff --stat` shows no change to `stages/review.py` or `tests/test_review*.py`; no `_v2` or `_new` file.
Invariants: every new schema field is optional with a default and every new model keeps `extra="forbid"`; old FlowSpecs still load. Nothing is removed or weakened: the removed source lines are `_to_flow`, `ingest_video` and `_new_flows` refactor lines whose behaviour is kept and extended; no test line is deleted, no assertion weakened, no skip or xfail added.

## The two points the manifest flags
1. RC1, field requested through the response-schema `description`: ACCEPTED. The model sees the field, because `ObservedStep` is the Gemini `response_schema` (`providers/gemini.py:97`; `gemini_schema.py:41` keeps `description`). `tests/fixtures/golden_prompts/ingest-video.md` pins the ingest SKILL.md byte-for-byte (SK3). RC1 says the field is one "the vision prompt asks for", and the schema is part of what the vision call sends; the contract's no-fire list also defers the paid re-ingest. A SKILL.md body edit would be a golden-prompt change for Umesh and stays a candidate, not a defect of this unit.
2. RC3, narration check in reconcile, not ingest: ACCEPTED. RC2 requires ingest to keep the narration verbatim; RC3 requires a narration "kept on a step, or cited by the report" to be a transcript substring, and reconcile is the only stage that stores a narration as evidence or cites it (`Possibility.quote`). It fails closed: no transcript for a step's source means the narration is dropped and reported. Residual (low, P1): a FlowSpec saved straight from `ingest_video` and never reconciled holds the unverified narration.

## Public-repo safety (mandatory): PASS
I read `tests/fixtures/reconcile/frozen_sample.json` in full (66 lines) and grepped the whole diff (src, tests, docs/MAP.md, manifest). There are no emails, phone numbers, Mongo or DB URIs, token URLs, passwords, API keys or bearer strings. The only URLs are `https://app.example.test/` and `/signup`. Fill values are the literal "sample", the one learner name is "Sample Learner", and no person or student name appears. The fixture note records the sanitising and lists the synthetic parts. Screen titles are generic product UI labels (admin lists, onboarding forms, dashboards). The test secret `Zq7-hunter-Secret-991` is a synthetic constant. The words Vidysea and Pathlynks are the product's own names, not personal data.

## Other required checks
Model calls go only through `Provider.judge`. The judge prompt is `src/autotester/skills/reconcile-screen/SKILL.md`, loaded by `load_skill_prompt`, which follows the existing `skills/<name>/SKILL.md` prompts-as-files convention (siblings: ingest-video, expand-case, grade, video-issues); D-073 authorised the module and D-072 says "new modules yes". Tests use `MockProvider` only, and two tests assert no real-provider import and no network.

PROPOSED-ISSUE: {"severity":"low","feature":"reconcile","title":"A FlowSpec saved straight from ingest_video keeps a model-authored narration unverified and unscrubbed until reconcile runs","evidence":"src/autotester/stages/ingest.py _to_step (narration=s.narration or None); verification only in stages/reconcile.py verify_narration","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"reconcile","title":"reconcile judge prompt carries step values (typed input) to the model; scrubbing covers only known secrets and the judge does not need values","evidence":"src/autotester/stages/reconcile.py build_judge_prompt actions[].value (lines 95-96)","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"reconcile","title":"process: reconcile M check ran past the 10-minute wall (slow: falsification harness build and two copy-completeness reruns, about 7 min)","evidence":"Metrics line of qa/verdicts/reconcile.md","status":"open","found_by":"checker-unit"}
Candidate (human): ask the vision prompt for the step `screen` in the ingest-video SKILL.md when the golden pin is next regenerated, together with the paid re-ingest.

VERDICT: PASS
SCOREBOARD: 14/14 criteria met, invariants hold
TIER: M (multi-file behaviour, shared schema and a new stage; no L trigger in the changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 14/14 reproduced (27 rows)
LIVE-BROWSER: not-applicable (no UI path changed: src/autotester/{schema,stages,skills}, tests)
ISSUES-WRITTEN: three low rows in qa/issues.jsonl at merge (P1-P3)
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: Every criterion re-ran green and each has an own falsification that goes red for the named reason; the only survivor (step-level scrub) is a documented second layer and goes red when both layers are removed. The two flagged points are acceptable readings of RC1 and RC3. The fixture and the diff contain no personal or credential data.
Metrics: start=2026-10-07T18:23:17+05:30 end=2026-10-07T18:41:00+05:30 wall_min=18 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=27 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7 slow: falsification harness build and two copy-completeness reruns 7 min
