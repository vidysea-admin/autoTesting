# Verdict - at1384-mask-band (coordinator B, blind dual check, repair cycle)

Date: 2026-10-21 · Bound root: D:/autoTesting/.worktrees/at1384-mask-band · Base c437d3a5 (= merge-base with int/1019) · Head judged 1515721a (product code identical to 714720db) · Repair base 6b2a679c (ancestor of HEAD, verified)
Cycle checked: 1
Policy-Version: proportional-verification/2026-10-19.17
Checkpoint: qa/checkpoints/at1384-mask-band.b.md

VERDICT: PASS
SCOREBOARD: 4/4 criteria met (C1 per-project limit, default unchanged, wired at every project-scoped site; C2 0.85 from measured fractions; C3 masking and withhold intact; C4 INCONCLUSIVE rule), 1/1 invariants hold (core-invariants C12 fail closed)
TIER: L (privacy masking is a security control: src/autotester/core/image_privacy.py:152 limit comparison; unchanged in this cycle)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 repaired rows reproduced (one falsification per production site, a full-tree copy per mutant, green control first)
LIVE-BROWSER: not-applicable (changed paths: tests/test_at1384_mask_limit_wiring.py and qa/manifests only; no UI surface)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Check plan (step 0)
Repair diff 6b2a679c..1515721a (minus verdicts and checkpoints) is 1 new test file (132 lines) plus the manifest; zero product, golden or project-file lines. My cycle-0 side had no failed criteria, so: re-validate by evidence identity, re-run C1 (its test inputs changed: a new wiring file), one falsification per repaired row, read the repair diff in full, scan the whole-unit diff (16 files, all named in the manifest What-changed), grep every sanitiser caller, security read of the changed lines. Tier L, one coordinator on this side.

## Evidence
- Repair diff read in full: tests/test_at1384_mask_limit_wiring.py only. Each of the 5 tests stubs the callee (grade or sanitized_images) and asserts it received 0.85, with "dropped" as the sentinel for a missing kwarg.
- Product identity: `git diff 714720db..1515721a -- src projects tests/golden` is empty, so my cycle-0 results for C2, C3, C4 and C12 (checkpoint rows, head 6b2a679c) keep their evidence identity and are not repeated.
- Manifest verify set (11 files + the wiring file, my own run): 256 passed. `ruff check src tests scripts`: All checks passed. `autotester doctor`: 2 violations, both docs/SNAPSHOT.md stale-generated and stale-committed (pre-existing, not this unit's files).
- Falsification (floor 1 per repaired criterion; I ran one per site, 5 of the L cap 10). Control = unmutated full-tree copy, 5 passed. Each mutant ran in its own full-tree copy under D:/autoTesting/.work/tmp/chkB1/mut_M<k>, import path printed from the mutant tree; the bound tree was never touched (git status clean).
  - run_case_pipeline.py:227 -> mask_limit=None: 1 failed (ui_run_path), 4 passed
  - run_case_pipeline.py:270 -> None: 1 failed (parallel_run_path), 4 passed
  - orchestrate_downstream.py:162 -> None: 1 failed (downstream_stage), 4 passed
  - run_artifacts.py:93 -> None: 1 failed (failure_bundle), 4 passed
  - agents/tools.py:163 -> None: 1 failed (lead_agent_tool), 4 passed
  Each red names the test written for that site, so each test isolates its own site. My first attempt copied only src/ and every mutant survived because pytest loaded the unmutated copy; that run is discarded and is not evidence.
- Invalid limits fail closed (read-only probe in the bound venv, no edit): _check_mask_area raises invalid_mask_limit for NaN, 0, -1, 0.91, inf and True; None, 0.9, 0.85, 0.75 are accepted. Project(image_mask_limit=...) rejects NaN, 0, -0.1, 0.95, inf; accepts 0.9 and 0.85; default 0.75.

## Judgement items
- Call sites (git grep over src and scripts): every production caller with a Project in scope passes the project's limit: run_case_pipeline.py:227 and :270 (project_mask_limit(store)), orchestrate_downstream.py:162, agents/tools.py:163, run_artifacts.py:93 (-> _assemble_case -> sanitized_images). Callers left on the default have no Project object or no screenshot to judge: ai_judge.py:171/:227 (text AiCapture evidence), grade_errored_result (run_case_pipeline.py:299; the ERRORED shortcut returns before any image), video_frames.py:91 and vision_probe.py:75 (provider level), leak_evidence.py:97 and oracle_responsive.py:69 (project_slug string only). None is a silent default under a project in scope, and all of them err on the stricter side. C1 holds.
- Security read of the changed lines: the limit only decides when a mostly-text image is withheld; every detected band is masked before and independent of it (_text_boxes, _leftover_boxes and the re-read loop are untouched; text_remains_after_mask unchanged). The validity check runs on every _mask call, including blank images, so a bad limit withholds instead of delivering. The 0.9 ceiling is enforced in the schema (le=) and in the engine. _SAFE_COPIES caches by scratch path inside a deleted tempdir and holds fully masked output whatever limit produced it, so there is no cross-limit leak. A failing store.load_project() in project_mask_limit aborts the grade (or INCONCLUSIVEs on the resilient path), never PASSes.
- tests/golden/pre_g11_project.json (+1 line, "image_mask_limit": 0.75): a golden loaded at test runtime, so not test-only, but not a weakening. test_pre_g11_fixture_is_byte_identical_after_round_trip asserts read-then-write bytes are equal; Project now serialises the new default field, so the golden must carry it for byte identity. No key removed or changed, and old files without the key still load to 0.75 (test_every_committed_project_loads_without_the_new_fields, green in my run). Justified.
- Whole-unit scan c437d3a5..1515721a: 16 files, all in the manifest What-changed; no deletion or rename of an existing function, class, test or config key.
- Real screenshots: none copied or committed; the new tests use Image.new synthetic images and stubs only.

PROPOSED-ISSUE: {"severity":"low","category":"product","title":"scripts/run_pathlynks_first_cases.py and the leak/oracle screenshot paths (leak_evidence.store_masked_screenshot, oracle_responsive) still sanitise at the 0.75 default, so Pathlynks dashboards stay withheld there","detail":"run_pathlynks_first_cases.py:139 calls grade() with no mask_limit although main() loads the project; the leak/oracle paths receive only project_slug. Stricter than the project's 0.85, never unsafe; thread the limit only if Umesh wants those screenshots kept.","found_by":"at1384-mask-band coordinator B cycle 1"}

Metrics: start=2026-10-21T14:47:34Z end=2026-10-21T14:58:00Z wall_min=11 agent_min=11 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=630 mutants=4 defects_unit=0 defects_6c=0
