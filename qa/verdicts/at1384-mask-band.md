# Verdict - at1384-mask-band (coordinator A, dual check)
Date: 2026-10-21 · Cycle checked: 0 · Policy-Version: proportional-verification/2026-10-19.17
Bound to: D:/autoTesting/.worktrees/at1384-mask-band · Base c437d3a5 (verified = merge-base with int/1019) · Head 6b2a679c (code 714720db)
Checkpoint: qa/checkpoints/at1384-mask-band.md · Resume/Retry: none (first dispatch)

## Check plan
Logic + privacy control changed (src/autotester/core/image_privacy.py, schema, 5 wiring sites): affected tests, one falsification per criterion, call-site sweep, security read, test-selection review (.13-7). No UI surface changed: Mode D not applicable. No data collected, no prompt text changed.

## Results
- Re-ran (own run, bound tree, 304 passed in 18 s): the manifest's 11 files plus tests/test_acceptance_baseline.py, tests/acceptance/test_ta09_tracker_export.py, test_run_case_pipeline.py, test_agent_tools.py. `ruff check src tests scripts`: All checks passed. `autotester doctor`: 2 violations, both docs/SNAPSHOT.md (matches the manifest). No full suite.
- (1) Default unchanged / per-project: schema/project.py `image_mask_limit` default 0.75, `0 < x <= 0.9`; only projects/pathlynks/project.json sets 0.85 (test asserts every other committed project is 0.75). Falsification: default 0.75 -> 0.85 in a copy: 5 red (green-before 165 passed in the copy).
- (2) 0.85 is justified: I re-ran the counts-only probe over the 38 real PNGs (read-only, nothing copied or saved): cumulative fractions identical to the manifest (max kept 0.8224; six at 1.0). Default: 18 kept / 19 mask_exceeds_limit / 1 text_remains; limit 0.85: 26 kept / 6 mask_exceeds_limit / 6 text_remains. Falsification: Pathlynks 0.9 -> 2 red.
- (3) Masking intact: `_text_boxes`, `_line_bands`, `_leftover_boxes`, the re-read loop untouched (diff read). Falsifications, each in its own copy: invalid-limit check removed -> 5 red; `text_remains_after_mask` raise -> `return` -> 2 red; mask box drawn zero-width -> 34 red incl. the every-band-black and real-OCR credential tests. Mostly-sensitive (1.0) image still withheld at 0.85 (probe + test).
- (4) Withheld screenshot still INCONCLUSIVE: `visual_decision` unchanged; unseen-gap guard disabled in a copy -> 5 red incl. the new at1384 test.
- Invalid limits fail closed: 0, -0.1, 0.95, 1.0, NaN raise `invalid_mask_limit` (core/image_privacy.py:155-157), withheld; also bounded in the schema.
- Golden tests/golden/pre_g11_project.json (+1 line `"image_mask_limit": 0.75`): additive, no assertion weakened; `Project` always writes the new default, and the byte-identical round-trip test (test_multi_role_schema.py:195) cannot hold otherwise. Justified; not a protected-test weakening (unit is already L).
- Call-site sweep: pass the project limit: run_case_pipeline.py:227,270 (via project_mask_limit(store)), orchestrate_downstream.py:162, agents/tools.py:161-163, run_artifacts.py:49,92. Default applies, no Project object in scope: leak_evidence.py:97 and oracle_responsive.py:69 (via store_masked_screenshot), video_frames.py:91, vision_probe.py:75, scripts/*. Default applies, no images reach it: ai_judge.py (text-only evidence), grade_errored_result (ERRORED short-circuits at grade.py:184). No caller silently drops a limit it has in scope.
- Security read of changed lines: `limit=None` reads MAX_MASK_FRACTION at call time; NaN and bool misuse rejected; the invalid-limit raise happens before any delivery, so the image is withheld; no new path out for raw pixels.

## FAILURES
- [C1] sev: medium - every production wiring site of the project limit is untested (.13-7a: a changed behaviour with no covering test). In copies, dropping the limit at run_case_pipeline.py:227 (s1), :270 (s2), orchestrate_downstream.py:162 (s3), run_artifacts.py:92 (s4), agents/tools.py:163 (s5), one site per copy, leaves 101 tests green (tests/test_run_case_pipeline.py, test_orchestrate_downstream.py, test_run_failure_artifacts.py, test_agent_tools.py, test_agent_loop.py, test_agent_fallback.py, test_grade_visual.py, test_ui_runs.py); `grep -rl mask_limit tests` finds only the three files the manifest lists, so only `grade()`/`judge_images`/`project_mask_limit` are pinned. The code is correct today (I read each line); a regression there silently re-withholds Pathlynks screenshots with all tests green, which is the incident AT-1384 closes. Fix direction: one test per site (project config limit 0.85 + stub OCR over the default, assert the screenshot is kept) so each dropped argument goes red · issue: P1

PROPOSED-ISSUE: {"severity":"medium","type":"test-gap","title":"AT-1384 project mask limit wiring untested at run_case_pipeline x2, orchestrate_downstream, run_artifacts, agents/tools","files":["src/autotester/stages/run_case_pipeline.py:227","src/autotester/stages/run_case_pipeline.py:270","src/autotester/stages/orchestrate_downstream.py:162","src/autotester/stages/run_artifacts.py:92","src/autotester/agents/tools.py:163"]}
PROPOSED-ISSUE: {"severity":"low","type":"gap","title":"store_masked_screenshot (leak evidence, responsive oracle) keeps the 0.75 default; dense Pathlynks evidence screenshots stay withheld (fail closed, disclosed in the manifest, no Project in scope there)","files":["src/autotester/stages/leak_evidence.py:97","src/autotester/stages/oracle_responsive.py:69"]}

VERDICT: FAIL
SCOREBOARD: 3/4 criteria met (C2, C3, C4; C1 fails on the wiring-test gap), invariants C12 holds
TIER: L (privacy masking on image sanitation before model delivery, src/autotester/core/image_privacy.py:152; dual-trigger cited in the manifest and confirmed)
CAPABILITY-COVERAGE: 4/4 manifest falsification rows' criteria reproduced independently (6 floor/guidance edits + 5 wiring edits, own copies)
LIVE-BROWSER: not-applicable (no UI paths changed)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The mechanism is correct and fail-closed: the 38-image measurement reproduces exactly, 0.85 is justified, masking and INCONCLUSIVE grading are intact. The unit fails only because none of the five call sites that carry the project limit into grading, failure bundles and the agent tool has a test, so the production path can regress unnoticed. Slow: none.
Metrics: start=2026-10-21T14:21:23Z end=2026-10-21T14:40:00Z wall_min=19 agent_min=19 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=12 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1120 mutants=9 defects_unit=1 defects_6c=0
