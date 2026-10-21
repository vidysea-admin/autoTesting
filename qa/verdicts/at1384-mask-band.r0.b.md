# Verdict - at1384-mask-band (coordinator B, blind dual check)

Date: 2026-10-21 · Bound root: D:/autoTesting/.worktrees/at1384-mask-band · Base c437d3a5 · Head 6b2a679c (code 714720db)
Cycle checked: 0
Policy-Version: proportional-verification/2026-10-19.17
Checkpoint: qa/checkpoints/at1384-mask-band.b.md

VERDICT: PASS
SCOREBOARD: 4/4 criteria met (C1 per-project + default unchanged, C2 measured 0.85, C3 masking/withhold intact, C4 INCONCLUSIVE rule), 1/1 invariants hold (core-invariants C12 fail closed)
TIER: L (security: image sanitation before external model delivery; dual-trigger src/autotester/core/image_privacy.py:152, read myself at :152-163)

## Check plan (step 0)
Diff = 10 src files, 3 test files, 1 golden, 1 project.json. Signals: logic changed (tests + 1 falsification per criterion), security/privacy control (security read of changed lines), config value (measurement re-derivation), shared schema (Project) + golden (protected-ish), all callers of sanitized_images/grade/judge_images (grep). No UI surface changed: no browser check. Prompt text untouched: no rubric grading. Serial, one coordinator (no shared port).

## Evidence
1. Verify commands, re-run by me on 6b2a679c (Pre-check reuse not used; independent run):
   - manifest 11-file set: 251 passed (matches claim). `uv run ruff check src tests scripts`: All checks passed. `autotester doctor`: 2 violations, both docs/SNAPSHOT.md (pre-existing, unrelated).
   - .13-8 candidates (`shard_suite.py --affected c437d3a5..6b2a679c --candidates`): reference-hit test files that mention a changed term (grade, judge_images, sanitized_images, project.json path, the golden, run_and_grade_case*): 1435 passed (335 s). The tool returned integration-required (dynamic globs), as expected; no full suite run.
2. C1 (per-project, default unchanged): read schema/image_privacy.py:8-11, schema/project.py image_mask_limit (gt=0, le=0.9, default 0.75), core/image_privacy.py `limit = MAX_MASK_FRACTION if limit is None else limit` (0.0 is not treated as "unset"). Every committed project other than pathlynks loads at 0.75 (test_pathlynks_declares_a_limit_above_the_default_and_other_projects_keep_it, green).
   Caller grep (git grep over src and scripts; every `sanitized_images`, `judge_images`, `grade(` site read):
   - passes the project limit: run_case_pipeline.py (both grade calls, `store` in scope), orchestrate_downstream.py:162, agents/tools.py:160-163, run_artifacts.py:92-93 (`project` loaded at :75), grade.py -> judge_images -> sanitized_images.
   - default, NO Project object in scope: video_frames.py:91, vision_probe.py:75 (synthetic probe images), leak_evidence.py:97 (`collect_leak_evidence` has `project_slug` only; oracle_tenant passes no screenshot), oracle_responsive.py:69 (`OracleContext` carries `project_slug` only, schema/oracle_context.py), ai_judge.py (text-only AI captures), scripts/* (no project). Default is the stricter side, so these fail safe, not open. Not a FAIL of (1): no project is in scope. See P2.
   - run_case_pipeline.py:299 `grade_errored_result` has a store but passes no limit: its only input is an ERRORED result, which `grade()` settles before any image is built (`_outcome_verdict`). No effect.
3. C2 (0.85 justified): I re-measured independently, in place, counts only, nothing copied: 38 PNGs under .worktrees/live-t136-r5/projects/pathlynks/runs, real engine, recorder on `_check_mask_area`. Final cumulative fractions sorted: max below 1.0 is 0.8224 (x2), six images at 1.0, 14 images in 0.75-0.83, 18 at or under 0.75. Identical to the manifest. Limit 0.75: 18 kept (19 mask_exceeds_limit + 1 text_remains). Limit 0.85: 26 kept, 6 mask_exceeds_limit (the 1.0 images), 6 text_remains_after_mask. 0.85 = 0.8224 + 0.0276; the next populated value above is 1.0, so nothing is let in beyond the measured set. Justified.
4. C3 (masking/withhold intact): `_text_boxes`, `_line_bands`, `_leftover_boxes`, the re-read loop are unchanged in the diff (read the full diff). Tests: kept dashboard has left/middle/right pixels black on every band incl. the secret line and the low-confidence line; 26-line image (> 0.85) still withheld; text_remains still withholds (reocr tests green).
5. C4 (INCONCLUSIVE): `visual_decision` in grade_images.py is untouched by the diff (only `judge_images`/`project_mask_limit` changed). test_at1384_a_screenshot_above_the_project_limit_still_grades_inconclusive and unchanged test_g2_pass_is_held... green.
6. Invalid limits fail closed: `_check_mask_area` raises `invalid_mask_limit` before any pixel work; `_mask` always calls it (even for a no-text image), NaN/0/negative/>0.9/True fail `0 < limit <= 0.9`; a non-number raises TypeError, caught by `sanitized_images`' `except Exception` -> withheld. Project field also bounded by pydantic (gt=0, le=0.9, NaN/inf rejected).
7. Golden `tests/golden/pre_g11_project.json` (+1 line `"image_mask_limit": 0.75`): this is test data a test loads at runtime (so the unit is L, which it already is), but NOT a protected weakening: no assertion deleted or loosened, no key removed or changed. test_pre_g11_fixture_is_byte_identical_after_round_trip compares write_json(read_json(golden)) to the golden bytes, so any always-written new Project field must appear there with its default; the value 0.75 equals the old behaviour. The same file was extended the same way for G11 (a9d07602). Justified.
8. Security read of the changed lines: no raw image, OCR text or path reaches a reason code (fixed strings only); the limit can only be set by project config (bounded 0.9) or caller code, never by page content; limit changes only when a mostly-text image is withheld, never which regions are masked; scratch copies are still in TemporaryDirectory; `_SAFE_COPIES` reuse is independent of the limit (an already-masked file). No defect found.

## Falsification (one per criterion, each in its own git-archive copy outside the bound root, PYTHONPATH on the copy, control M0 = 102 passed on 5 files; table: .work/tmp/chkB/mut_out.txt)
- C1 default: `DEFAULT_MASK_LIMIT 0.75 -> 0.85` -> 5 failed (green-before 102 passed).
- C2 value: pathlynks `image_mask_limit 0.85 -> 0.9` -> 2 failed.
- C3: `_mask` draws nothing -> 34 failed; text_remains raise -> `return` -> 2 failed; comparison `> limit` -> `> 2*limit` (limit never fires) -> 7 failed.
- C4: `if gap:` -> `if False:` in visual_decision (a withheld screenshot may PASS) -> 8 failed.
- C12 fail-closed: validation line -> `if False` -> 5 failed.
- Wiring probe (not a floor item): all four caller wirings (run_case_pipeline, orchestrate_downstream, agents/tools, run_artifacts) changed to ignore the project limit -> 84 passed across test_run_case_pipeline*, test_orchestrate_downstream, test_run_failure_artifacts, test_agent_tools, test_grade_visual, test_failure_bundle: untested wiring, see P1. The code itself is correct by read (point 2).

## Non-blocking findings (dual check: no ledger rows)
PROPOSED-ISSUE: {"sev":"low","type":"test-gap","title":"AT-1384 caller wiring has no test: removing the project limit from run_case_pipeline (x2), orchestrate_downstream:162, agents/tools:160, run_artifacts:92 leaves 84 related tests green; only grade->judge_images and project_mask_limit() are pinned","fix":"one spy test per call site asserting mask_limit equals the project's value","evidence":"qa/verdicts/at1384-mask-band.b.md falsification wiring probe"}
PROPOSED-ISSUE: {"sev":"low","type":"coverage-note","title":"Responsive/leak-oracle screenshots (oracle_responsive.py:69, leak_evidence.py:97) and video frames use the 0.75 default because OracleContext/collect_leak_evidence carry only project_slug; Pathlynks dense screens will be withheld there where graded ones are kept (fails safe)","fix":"decide whether to thread the limit through OracleContext; HUMAN call, not a defect","evidence":"schema/oracle_context.py project_slug only"}

CAPABILITY-COVERAGE: 4/4 floor rows reproduced red-after (control green), plus 3 extra mutants red and 1 wiring probe (green, see P1)
LIVE-BROWSER: not-applicable (no UI paths changed)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The limit is a bounded per-project field with the old 0.75 default, every in-project caller passes it, and an independent re-measurement of the 38 real screenshots reproduced the manifest's fractions exactly, so 0.85 keeps only the 8 extra images that are fully masked while the six 1.0 images stay withheld. Masking code, text-remains withholding and the INCONCLUSIVE rule are unchanged and each is red under its mutation; invalid limits fail closed. The golden edit is the routine additive-field update, not a weakened assertion. The only gaps are two low non-blocking items (untested wiring, and oracle/video paths using the stricter default).
Metrics: start=2026-10-21T14:10:00Z end=2026-10-21T14:40:00Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=9 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1800 mutants=5 defects_unit=0 defects_6c=0
slow: reocr-hit-set 5.6 (1435 reference-hit tests, .13-8 candidate files)
