# Verdict - at927-ai-persist
Cycle checked: 0
Date: 2026-10-17 · head 78288698 (product a62fa404) · base 9aaf1fe5 (git merge-base HEAD int/1017)

## Plan (step 0)
Logic changed in shared stage modules + core/paths.py (M): affected tests, 1 falsification per criterion (AT-927 persist; secret scrub as the hint-named AI14 floor), step 4c diff scope. No UI/rendered change, no browser, no LLM prompt change, no new CLI/UI surface. Lane: not applicable (cycle 0, 5 files, lane disabled by default). No dual check (no auth/tenancy/prod write: local project files only).

VERDICT: PASS
SCOREBOARD: 1/1 criteria met (AT-927; ai-target.md AI6/AI9/AI11/AI14 as the manifest names them), 0/0 invariants touched beyond C3/C5 (checked: one writer, scrub before write)
TIER: M (multi-file shared stage modules + core/paths.py; no L trigger: persistence is local project files, redaction only called, core/redact.py untouched)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (F2 persist, F1 scrub) - details below
LIVE-BROWSER: not-applicable (no UI or rendered path changed)
ISSUES-WRITTEN: AT-1025 (low, proposed)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: judge_capture(paths=...) now writes capture.json and verdict.json under projects/<slug>/ai/behavioural/<capture_id>/ through ProjectPaths and the one atomic write_json, after scrub_obj, revalidate and assert_clean; a surviving secret raises CaptureWithheld and writes nothing. export_ai_report reads the same ai_dir and defaults to ai/ai-report.xlsx; no CLI/UI surface added (Umesh 2026-10-17: Excel only). One low finding: a withheld second verdict leaves the previous run's verdict beside the new capture (AT-1025).

## Evidence I produced
- Step 3: uv run pytest tests/test_ai_persist.py tests/test_ai_report.py tests/test_ai_capture.py -> 111 passed (this check, worktree). uv run ruff check src tests scripts -> All checks passed. uv run autotester doctor -> clean.
- 4b falsification (copies outside the worktree, scratchpad m-f1/m-f2/m-f3, same src+tests, PYTHONPATH to the copy, autotester.__file__ confirmed in the copy):
  - green-before: unmodified copy mf3 -> 11 passed.
  - F2 (judge_capture persistence disabled via 'if paths is not None and False') -> red: test_judge_capture_with_paths_persists_the_capture_and_the_verdict, test_a_secret_in_a_judge_reason_never_reaches_verdict_json, test_capture_judge_store_report_round_trip (3 failed, 8 passed). Assertions, not import errors (files absent / 'CAPTURED, NOT JUDGED').
  - F1 (scrub_obj + assert_clean removed in persist_scrubbed) -> red: test_a_planted_secret_never_reaches_capture_json, test_an_encoded_secret_withholds_the_capture_and_writes_nothing, test_a_secret_in_a_judge_reason_never_reaches_verdict_json (3 failed, 8 passed).
  - Bound tree untouched; copies removed with the scratchpad.
- 4c diff scope (git diff 9aaf1fe5..HEAD): 6 files, all in the manifest's What changed (paths.py, ai_capture.py, ai_judge.py, ai_report.py, tests/test_ai_persist.py, manifest). Removed lines: ai_judge.py _case_id body (moved to capture_id; _case_id kept as a wrapper, no caller broken), the content_id import (now unused there), ai_report.py 'ai_dir = store.paths.dir / "ai"' and the 'out: Path' required param (now optional, callers unaffected). No function, class, test or config key deleted. Paths only via ProjectPaths (src/autotester/core/paths.py ai_dir, ai_capture_dir with safe_name, ai_report); stage reader uses store.paths.ai_dir; folder name == capture_id so the reader's folder.name pairing holds (round-trip test PASS shows 'PASS', not 'CAPTURED, NOT JUDGED').
- Secret path read: src/autotester/stages/ai_capture.py persist_scrubbed: scrub_obj on model_dump(mode=json), re-validate, assert_clean on the dumped JSON, then write_json (atomic); the write is last, so CaptureWithheld leaves no file (test asserts ai_dir does not exist).
- No new surface: git diff shows no cli/ or ui/ file changed.
- full-suite trigger: tests/conftest.py imports core/paths.py (changed): shard_suite --affected exits 2 integration-required (as the builder said); the merged-head 6c step covers it. Not run here (.13).

## Findings (non-blocking)
- AT-1025 low: stale verdict beside a new capture. Probe (scratchpad probe.py, run in the worktree venv): judge+persist run r1 -> capture.json + verdict.json; second run on the same capture_id with store_verdict raising CaptureWithheld -> capture.json holds the new response ("Lyon"), verdict.json still holds run_id 'r1'. The report would pair them. Reach: only when a secret survives scrubbing in a verdict, so not a criterion failure.

Metrics: start=2026-10-17T20:19:00Z end=2026-10-17T20:29:28Z wall_min=11 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=660 mutants=0 defects_unit=0 defects_6c=0
slow: reading the 1255-line checker protocol and procedural overhead ~5 min
