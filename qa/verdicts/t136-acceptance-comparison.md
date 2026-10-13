# Verdict - t136-acceptance-comparison

**Cycle checked:** 1
**Result:** PASS for the unit as scoped (script + logic + tests, no-human-list mode). T-136 itself stays pending: no Pathlynks data exists.
**Caveat:** the same delegated agent wrote the maker and checker halves in one run, as the dispatch asked. Criteria were re-read from `qa/contracts/bench.md` before judging. Recall is judged "unavailable allowed" per D-089 item 3.

| Criterion | Result | Evidence |
|---|---|---|
| K3 scoring only via `BenchTrial.score` | PASS | `_column` calls `bench.scorecard(corpus, [trial])`; no rate arithmetic in the stage, schema or script. |
| K4 comparative, both participants named | PASS | `AcceptanceComparison` has `autotester` and `human` columns; `render` prints both. Absent human reads `unavailable (no human list)`. |
| K5 persisted through the store | PASS | Reads via `load_bench_corpus`/`list_bench_trials`; the comparison is saved with `write_json` to `ProjectPaths.bench_comparison`. |
| K6 human kind typed in the artifact | PASS | `ParticipantColumn.kind` comes from `BenchTrial.kind`; completeness fails on kind `unknown` (test `..._fails_k6`). |
| K7 ordering and independent/prompted split | PASS | Columns carry `ordering`, `independent_findings`, `prompted_findings`; a prompted-only human detects 0; FP population states `all_reported_findings`. |
| K8 missing input is unavailable, never a default | PASS | `Measure` forbids value-and-reason or neither. Tests build untimed, zero-finding and unknown-ordering trials and assert unavailable plus an incomplete result. |
| K9 completeness script | PASS with noted limit | Exit 2 naming the missing input, 1 if incomplete, 0 if complete. Per-bug rows and the bug list are present; an empty bug list is marked `unavailable (no ground-truth bug list)`. It never judges who won; the verdict field says Umesh records it. |
| D-089 item 3: no-list supported, FP and time must pass | PASS | `test_no_human_list_is_a_supported_mode...`: exit 0 with recall `unavailable (no human list)`; AutoTester FP rate and `duration_s` must be numbers or the run is incomplete. |
| Human list plugs in as files, no code change | PASS | `test_human_list_plugs_in_as_files_with_no_code_change` adds a corpus and trial JSON only. |
| Design rules | PASS | All files at or under 300 lines, `extra="forbid"` models, module docstrings, ruff clean. Doctor shows only 3 pre-existing dangling-citation violations in other verdicts. |

## Findings for the maker queue (not blockers)

1. Nothing produces `pathlynks-acceptance` corpus + AutoTester trial from a real run yet, so the `done_check` cannot pass until that step exists.
2. With an empty bug list, `BenchTrial.score` treats every finding as a false positive (FP rate 1.0). FP rate is only meaningful after findings are adjudicated. A scorer-level question, so left to a separate unit.
