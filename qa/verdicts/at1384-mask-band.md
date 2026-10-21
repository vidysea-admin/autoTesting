# Verdict - at1384-mask-band (coordinator A, repair check)
Date: 2026-10-21 | Verdict: PASS | Cycle checked: 1 | Resume: n/a
Bound to: D:/autoTesting/.worktrees/at1384-mask-band | Base c437d3a5 | Head 1515721a | Repair base 6b2a679c (ancestor of HEAD, verified with git)
Policy-Version: proportional-verification/2026-10-19.17 | TIER: L (security trigger src/autotester/core/image_privacy.py:152, privacy masking) | Dual check: this is coordinator A; coordinator B is blind and separate.

## Check plan
Repair checker scope: the failed criterion C1 (project limit wiring at 5 production sites) plus criteria whose inputs the repair touched. Repair diff 6b2a679c..1515721a excluding qa/verdicts and qa/checkpoints = tests/test_at1384_mask_limit_wiring.py (new, 132 lines) + the manifest; `git diff 6b2a679c..1515721a -- src projects` is empty, so C2, C3, C4 inputs are unchanged and keep their cycle-0 results (checkpoint). Whole-unit diff c437d3a5..1515721a scanned: no file outside src/{agents,core,schema,stages}, tests/, projects/pathlynks/project.json, qa/ (in scope).

## Evidence (own runs, bound tree + throwaway copy outside it)
- Manifest verify (11 files + the new wiring file): 256 passed (251 expected + 5 wiring tests). 212 passed on the wider caller set (test_run_case_pipeline, test_agent_tools added).
- `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: 2 violations, both docs/SNAPSHOT.md (stale-generated/stale-committed, pre-existing, none in this unit's files).
- C1 falsification, one mutant per production site, each in its own copy under D:/autoTesting/.work/tmp/chk1384A2_s1..s5 (PYTHONPATH on the copy, control 5 passed; the bound tree was never mutated):
  s1 run_case_pipeline.py:227 drops mask_limit -> FAILED ...ui_run_path...; s2 run_case_pipeline.py:270 -> FAILED ...parallel_run_path...; s3 orchestrate_downstream.py:162 -> FAILED ...downstream_stage...; s4 run_artifacts.py:92 passes None -> FAILED ...failure_bundle...; s5 agents/tools.py:163 passes None -> FAILED ...lead_agent_tool.... Each run: 1 failed, 4 passed. The five cycle-0 survivors are now killed, one test per site.
- Probe in the copy: Project rejects image_mask_limit 0, -1, 0.95, NaN, inf; accepts 0.85 and 0.9. `_check_mask_area` raises invalid_mask_limit for 0, -1, 0.95, NaN, inf (fail closed). projects/pathlynks/project.json = 0.85; the other 9 committed projects have no key, so they keep 0.75.

## Criteria
1. Per-project setting, old default unchanged: PASS. Wiring now proven at all 5 sites (above). Caller grep (sanitized_images, judge_images, grade, grade_errored_result, judge_capture, store_masked_screenshot): every caller with a Project/store in scope passes the limit, except the two cases below, neither a defect.
   - stages/run_case_pipeline.py:299 `grade_errored_result(case, result, judge, run_id, store)` has a store in scope but calls grade() without mask_limit. Not reachable with images: grade() returns at `_outcome_verdict` (stages/grade.py:212, ERRORED -> INCONCLUSIVE rule) before `judge_images`; all 5 callers (ui/run_execution.py:57,88,134,202) pass ERRORED results. Latent only; default is the fail-closed side.
   - ai_judge.py (capture evidence is NETWORK rows, no screenshots), leak_evidence.py:97 / oracle_responsive.py:69 (only a slug / OracleContext, no Project; oracle_tenant passes no screenshot), video_frames.py:91, vision_probe.py:75 (no project): default 0.75 applies, as the manifest states.
2. Pathlynks raised only as far as measured: PASS, unchanged. Input files (project.json, measurement) untouched by the repair; value 0.85 present and the manifest's 0.8224 max kept fraction + margin stays under the 1.0 fully-masked images. Not re-measured (real screenshots not copied; cycle-0 checkpoint holds the 38-PNG probe).
3. Every secret/PII region masked, mostly-sensitive withheld, text-remains withholds: PASS, unchanged (no product change since 714720db; engine/privacy/reocr tests green in the 256 run; invalid limits fail closed, probe above).
4. Withheld screenshot still INCONCLUSIVE: PASS, unchanged (visual_decision untouched; tests/test_grade_visual.py green).

## Judgements asked
- tests/golden/pre_g11_project.json (+1 line `"image_mask_limit": 0.75`): a golden loaded at runtime by tests/test_multi_role_schema.py, so a protected-class change and the reason this unit is L. Justified: `Project` now serialises the new field with its default, the fixture is the byte-identical round-trip proof, the change is additive, no key removed or changed, no assertion weakened; test_multi_role_schema is green.
- Security read of changed lines: ceiling 0.9 enforced twice (schema gt=0/le=0.9 and `_check_mask_area` at core/image_privacy.py:152-155); None resolves to the old default at call time; a bad value raises ImagePrivacyError and withholds; no OCR text or path reaches reasons/logs; every detected band is still masked full width (`_text_boxes`, `_line_bands`, `_leftover_boxes`, re-read loop untouched).

PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"grade_errored_result (stages/run_case_pipeline.py:299) does not pass project_mask_limit(store) to grade()","evidence":"store in scope; unreachable with images today because ERRORED returns at stages/grade.py:212 before judge_images","suggest":"pass mask_limit=project_mask_limit(store) so a future non-ERRORED caller cannot silently use 0.75"}
PROPOSED-ISSUE: {"severity":"low","type":"coverage","title":"leak-evidence and responsive-oracle screenshots (leak_evidence.py:97, oracle_responsive.py:69) always use the 0.75 default","evidence":"only a project slug / OracleContext is in scope, so a dense Pathlynks dashboard that grade() now keeps at 0.85 is still withheld there; fail-closed, not a leak","suggest":"thread the project limit through OracleContext if those screenshots matter for Pathlynks"}

Metrics: start=2026-10-21T14:36:00Z end=2026-10-21T14:52:00Z wall_min=16 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=960 mutants=5 defects_unit=0 defects_6c=0
