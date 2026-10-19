# Verdict - t136-route-b (Mode A, cycle 0)
Cycle checked: 0
Date: 2026-10-19 · bound to D:/autoTesting/.worktrees/t136-route-b · base 4ce91ea8 (merge-base, verified), head 8f2f608b (code fcb97361) · Policy: proportional-verification/2026-10-19.16

## Check plan (step 0)
Logic changed (converter, schema fields, comparison wiring) -> affected tests + 1 falsification per criterion; no UI (no browser), no security/auth/prod-write trigger, no LLM output, no new external data collection. One check type, so no sub-checkers. Tier M kept: new stage + two schema field additions + comparison wiring.

## Evidence (my own runs)
- Manifest affected set: `uv run pytest tests/test_crawl_findings.py tests/test_bench_from_run.py tests/test_acceptance_comparison.py tests/test_bench.py -p no:xdist -o addopts=` -> 66 passed (matches manifest).
- Own reference-hit pass (.13-8): extra consumers of the changed schema/stage found by git grep (test_agent_comparison, test_ceo_benchmark, test_generic_acceptance, test_review_recall, test_review_recall_auto) -> 41 passed. Siblings agents/comparison.py and stages/ceo_benchmark.py read `BenchTrial.score`; the new fields are defaulted, claim holds.
- `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> clean (MAP in sync; the MAP diff is +1 generated line).
- Real data, in a COPY (qa/evidence/t136-route-b/real-data.md): `bench_from_run.py --crawl all` -> 14 findings (all source=crawl), `check_acceptance_comparison.py` -> exit 0; recall/detection `unavailable (no human list)`, human column absent, FP 1 unadjudicated. 0 evidence paths missing against the real tree; no navigation/overlay/dialog/warning row became a finding; those crawls hold no EVIDENCE rows.
- Schema: Finding, BenchTrial, ParticipantColumn keep extra=forbid; `source="web"` and unknown keys are rejected; an old trial without `source`/`crawl_ids_scanned` loads (test_case_findings_keep_source_case_and_old_trial_files_still_load).
- Step 4c: 11 files, all in the manifest's What changed; no function, test or key deleted (the 10 removed lines are modified docstring/signature/one print line); no out-of-scope file.

## Falsification (copies under scratchpad, autotester.__file__ confirmed inside the copy; green-before, red-after; bound tree untouched)
| Crit | Edit (single hunk) | Test | Before -> after |
|---|---|---|---|
| C1 | crawl_findings.py `_dedup_key`: drop the `first_party` guard | ::test_tool_failures_third_party_noise_and_crawler_state_are_never_product_findings | 1 passed -> `assert [Finding(... ads.example/pixel ...)] == []` |
| C2 | acceptance_comparison.py `_zero_after_scan`: ignore the scan | ::test_zero_findings_with_no_crawl_scan_still_fails_the_check_k8 | 1 passed -> `assert False` on the false_positive_rate problem |
| C2 | bench.py: drop `+ (crawl_findings or [])` | ::test_r4_shaped_run_with_crawl_502_gets_a_numeric_fp_rate_and_the_check_exits_zero | 1 passed -> `assert [] == ['crawl', 'crawl']` |
| C3 | acceptance_comparison.py `_column`: `if not human_missing and ...` | ::test_recall_against_a_human_stays_unavailable_when_crawl_findings_exist | 1 passed -> `'corpus mode not recorded' == 'no human list'` |
Each fired on the assertion the test is named for.

## Criteria
C1 dedup by kind+URL(query stripped)+status, evidence and screenshot refs, source label, exclusions: met. C2 numeric FP rate, or honest unavailable with the scan count; zero with no scan still exits 1 (K8): met. C3 recall/detection stay `unavailable (no human list)`, human absent: met. K3: scoring stays in `BenchTrial.score` (new code only counts and labels). K11b: an unknown crawl raises before the corpus or trial is written (test and code order).

## Non-blocking findings (ledger rows, no fix cycle)
- AT-1346 low: console `error:` lines carry no URL and `drain()` marks every console line first-party, so a third-party failed-resource console error would become a finding; 5 of the 14 real findings are console twins of a network finding already counted, plus a CSP report-only advisory. 14 is an upper bound; FP rate reads unadjudicated 1.0 either way.
- AT-1347 low (process): this check ran past the S/M 10 min hard checkpoint (protocol read plus a real-data copy run).

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 0/0 invariants named (core-invariants unaffected: no secret touched, extra=forbid kept, doctor-clean)
TIER: M (new stage + schema fields + comparison wiring; no security/prod-write trigger)
FAILURES: none
CAPABILITY-COVERAGE: 4/4 rows reproduced (floor of 1 per criterion met)
LIVE-BROWSER: not-applicable (no UI path changed)
ISSUES-WRITTEN: AT-1346, AT-1347
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Re-ran the manifest commands and a wider consumer set green, reproduced the real-data conversion in a copy (14 findings, exit 0, evidence paths resolve), and made four isolated falsifications red on the named assertions. Findings are not inflated by tool failures, third-party network rows, crawler state or warnings; the one soft spot is console lines without a URL (AT-1346).
Metrics: start=2026-10-19T15:30:00+05:30 end=2026-10-19T15:44:00+05:30 wall_min=14 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.16 check_s=840 mutants=0 defects_unit=0 defects_6c=0 slow: protocol-read-and-real-data-copy 8
