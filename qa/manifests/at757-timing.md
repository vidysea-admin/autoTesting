# Manifest - at757-timing (AT-757 timing scale for load-sensitive tests)

Contract: qa/contracts/core-invariants.md (no assertion removed; C2 file/function caps); ruling AT-757 (qa/issues.jsonl), approved by Umesh in chat 2026-10-07.
Goal task: none (suite-health ruling AT-757; also closes AT-767, AT-771)
Policy-Version: proportional-verification/2026-10-07.7
Fix cycle: 0
Status: checked-PASS
Tier: L - protected test change (it can loosen a threshold); one checker, no dual check.
Base: 642ab4bd783624f63ff75caa4f7fd5f816238810 (origin/master), branch wave/at757-timing
Source: c9832b19424c2371ebd0a77c90de004ac3227ce1

## What was built

- `tests/timing_scale.py` (new, test-only, one job): `timing_scale() -> float` reads `AUTOTESTER_TIMING_SCALE`; unset, empty, unparseable or non-finite -> 1.0; below 1.0 -> 1.0 (loosen only); above 4.0 -> 4.0. Placed as a small tests helper module per the ruling, which says NOT conftest.py (its own L trigger); no existing tests helper owns timing. Imported as `from timing_scale import timing_scale` (tests/ is on sys.path, as `crawl_fake` is).
- Five bounds scaled, nothing else touched:
  - tests/test_crawl_inventory_live.py:104 `wall_clock_s=240.0 * timing_scale()` (max_screens/max_actions and every COMPLETED/coverage assert untouched)
  - tests/test_mc_sessionstart_loop_status.py:143 `timeout=60 * timing_scale()`
  - tests/test_redact_wrap_perf.py:192-193 `3.0 * timing_scale()`, message prints the scaled bound; line ~210 ratio < 3.0 superlinear guard UNCHANGED
  - tests/test_redact_ignorable_perf.py:143 CJK/ASCII multiple `2.5 * timing_scale()` (AT-771 2.86x flake); absolute `cjk_time < 15.0` ceiling UNCHANGED
  - tests/test_video_parallel_sweep.py:42 `_WAIT_S = 30.0 * timing_scale()`
- `tests/test_timing_scale.py` (new, 20 cases).

## How to verify

```
uv run pytest tests/test_timing_scale.py                       # 20 passed
uv run ruff check src tests scripts                            # All checks passed!
uv run autotester doctor                                       # doctor: clean
git diff 642ab4bd..c9832b19 --stat                             # 7 test files only, no src/
AUTOTESTER_TIMING_SCALE=2 uv run pytest tests/test_redact_wrap_perf.py tests/test_mc_sessionstart_loop_status.py tests/test_crawl_inventory_live.py
```

## Coverage table

| claim | check | falsifier |
|---|---|---|
| default is 1.0 when unset | test_default_is_one_when_unset | default 2.0 -> red (floor row 3) |
| valid in-range values used | test_valid_value_in_range_is_used (2, 1.5, " 3 ", 4) | returning constant |
| below 1.0 never tightens | test_below_one_clamps_up_* (0.5, 0, -3, 0.999) | drop low clamp -> 4 red (floor row 2) |
| above 4.0 capped | test_above_four_clamps_down_to_four (4.01, 10, 1e6) | drop high clamp -> 3 red (floor row 1) |
| empty/invalid/nan/inf -> 1.0 | test_empty_or_invalid_falls_back_to_one (7 inputs) | removing the ValueError / isfinite branch |
| every bound identical at default | test_every_bound_equals_its_literal_at_the_default (240.0, 60, 3.0, 2.5, 30.0) | default 2.0 -> red |
| scale still discriminates | AT-757 checker re-check (synthetic regression at scale 2); maker did not run it | see Open items |
| no assertion removed | `git diff` shows only the five bounds + imports; ratio guard and 15 s ceiling untouched | n/a |

## Evidence

- Touched files, full run under heavy host load (default scale): 59 passed, 3 failed (crawl_inventory_live wall_clock_s, mc_sessionstart grandchild-kill, redact_wrap_perf) - these are the AT-750/767 load-sensitive tests failing on the host's own load, same as on base.
- Re-run of the three failing files, default scale: 19 passed, 2 failed (`500 KB scan took 3.22s, expected under 3s`; crawl `STOPPED_BOUND` instead of `COMPLETED` at 240 s). Same files with `AUTOTESTER_TIMING_SCALE=2`: 21 passed in 334 s. So the helper turns the load flakes green and scale 1.0 is behaviour-identical to base.
- ruff: All checks passed! ; doctor: clean.
- Floor (throwaway copy in scratchpad/at757-fals, bound tree untouched): baseline 20 passed; remove high cap -> 3 failed; remove low clamp -> 4 failed; default 2.0 -> 2 failed; restored -> 20 passed.

## Open items

- Mode B sharded sweeps and backstop runs should set `AUTOTESTER_TIMING_SCALE=2` (ruling point 3); that is the launcher's job, not this diff.
- Checker re-check of the synthetic regression at scale 2 (quadratic scan > 6 s still red; hung close / unbounded crawl still red) is the checker's.
- Full suite not run (brief). tests/test_mc_sessionstart_loop_status.py::test_the_timeout_kills_the_real_grandchild_process_not_just_uv failed once under load at default scale and passed at scale 2 and in the second default run.

Metrics: start=2026-10-07T10:50:00Z end=2026-10-07T11:25:00Z wall_min=35 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=2 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7
