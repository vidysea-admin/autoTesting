# Manifest - at1349-holes-scrub (AT-1349: crawl.json was saved unscrubbed; coverage holes kept raw selector, name and url_template)

**Status:** checked-PASS (qa/verdicts/at1349-holes-scrub.md + .b.md, dual, cycle 0)
**Fix cycle:** 0
**Contract:** qa/contracts/explore.md, qa/contracts/core-invariants.md (redaction: no raw secret reaches disk); no contract edited
**Goal task:** T-136 follow-up (PROPOSED-ISSUE 1, qa/verdicts/crawl-redact-timestamp-B.md)
**Dual check:** required
dual-trigger: security src/autotester/stages/explore_summary.py:83
**Persona walk:** skip (no UI surface)
**Issues addressed:** AT-1349 (high, open -> fixed; Umesh approved 2026-10-21 "hn")
**Executor:** claude-sonnet-subagent
**Base SHA:** 8956c9bc (worktree .worktrees/at1349-holes-scrub, branch wave/at1349-holes-scrub)

## What changed
- `src/autotester/stages/explore_summary.py:83-95` - new `save_crawl(rt, crawl)`: the one place a `Crawl` envelope is masked for disk. `coverage` (holes, screens_not_entered, permitted_holes: selector, link name, url_template, plus spec_error/error) and each `noise_counts` entry go through the existing `scrubbed` (the crawl-redact-timestamp helper, so ids/timestamps stay typed and `_MINTED` ids are kept); `stop_reason` goes through `Redactor.scrub`. It saves a `model_copy` so the in-memory crawl keeps real selectors. Config fields (bounds, policy, ids, counters) are not page text and are untouched.
- `src/autotester/stages/explore.py:230` (`_finish`) and `src/autotester/stages/explore_node.py:139` (`heartbeat`) now call it instead of `rt.store.save_crawl`. Same line count in both (explore_node.py stays 300).
- `src/autotester/stages/explore.py:272` (initial envelope, before the runtime exists) is unchanged: it carries only approval ids, project slug, bounds and policy, no page text.
- Tests: `tests/test_crawl_holes_scrub.py` (new, 3 tests).

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L (security: secret persistence)
Round: 3 src files, 1 test file, 2 criteria, est 20 min - one save helper, two call sites
Owners: OG-EXPLORE
Base / checked state: 8956c9bc / 1d3b9798, clean tree
Gate answers: Umesh 2026-10-21 "hn" approved AT-1349; no gate touches crawl persistence redaction; no new src module
Affected tests / full-suite trigger: no conftest or shared schema file changed; callers of the two edited call sites are run_crawl/heartbeat, covered by the explore/crawl/approval/report test files run. Builder ran no full suite.
Tests[C1]: tests/test_crawl_holes_scrub.py::test_a_secret_in_a_link_name_and_an_href_is_absent_from_the_written_crawl_json, ::test_a_real_crawl_with_a_secret_named_control_persists_a_masked_hole - a secret in a link name, selector and url_template is absent from the written crawl.json and the hole is still recorded (synthetic Crawl, and end to end through run_crawl)
Tests[C2]: tests/test_crawl_holes_scrub.py::test_a_numeric_secret_does_not_corrupt_the_crawl_envelope_ids_or_timestamps; regression tests/test_crawl_redact_timestamp.py, tests/test_explore_secret_scrubbing.py, tests/test_store_crawl.py, tests/test_crawl_liveness.py, tests/test_crawl_status_surfaces.py, tests/test_explore.py, tests/test_explore_completeness.py, tests/test_crawl_coverage.py, tests/test_crawl_coverage_bounds.py, tests/test_approval_prod_gate.py, tests/test_approval_prod_gate_paths.py, tests/test_explore_node_recovery.py, tests/test_crawl_report.py, tests/test_unified_report_secrets.py - nothing scrubbed before is now unscrubbed, and existing crawl tests stay green
Pre-check[C1]: 1d3b9798 uv run pytest tests/test_crawl_holes_scrub.py -> 3 passed t=7 blobs=tests/test_crawl_holes_scrub.py:be0612d
Pre-check[C2]: 1d3b9798 uv run pytest tests/test_crawl_holes_scrub.py tests/test_crawl_redact_timestamp.py tests/test_explore_secret_scrubbing.py tests/test_store_crawl.py tests/test_crawl_liveness.py tests/test_crawl_status_surfaces.py tests/test_explore.py tests/test_explore_completeness.py tests/test_crawl_coverage.py tests/test_crawl_coverage_bounds.py tests/test_approval_prod_gate.py tests/test_approval_prod_gate_paths.py tests/test_explore_node_recovery.py tests/test_crawl_report.py tests/test_unified_report_secrets.py -> 172 passed t=469 blobs=tests/test_crawl_holes_scrub.py:be0612d (run on the tree one ruff line-wrap before the commit; the only later change is a two-line split of one assert)
Falsification[C1]: copy-mutant in scratchpad mut1349 replacing `update["coverage"] = scrubbed(rt, crawl.coverage)` with the unscrubbed value -> 2 failed (::test_a_secret_in_a_link_name..., ::test_a_numeric_secret...); a second copy-mutant reverting the `_finish` call site to `rt.store.save_crawl(crawl)` -> 1 failed (::test_a_real_crawl_with_a_secret_named_control_persists_a_masked_hole); a third dropping the `noise_counts` scrub -> 1 failed (::test_a_secret_in_a_link_name...); restored control -> 3 passed. Base 8956c9bc has no `save_crawl` helper and writes holes verbatim (probe in qa/verdicts/crawl-redact-timestamp-B.md)
Falsification[C2]: the same coverage-unscrubbed mutant fails ::test_a_numeric_secret_does_not_corrupt_the_crawl_envelope_ids_or_timestamps (587 left in the hole name); restored control -> 3 passed
Lint: 1d3b9798 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> doctor: clean; explore_summary.py 116, explore.py 295, explore_node.py 300 (all <= 300)
Metrics: start=2026-10-21T00:00Z end=2026-10-21T00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 lane=normal check_s=469 mutants=4 defects_unit=0 defects_6c=0 tests=3 tests_min=1

## Residual risk and boundaries
- `url_template` of a hole is scrubbed as free text; `node_id` is a `_MINTED` key and is kept, so a secret embedded in a node id would not be masked (ids are content hashes).
- The initial envelope save (explore.py:272) is not scrubbed; it holds no page text. `Crawl.policy`/`bounds`/`project` are config and not scrubbed here.
- Other writers of coverage-derived files (reports, persona, frontier) were not audited in this unit.

## Live browser evidence
SKIP - maker smoke only; no UI surface changed (src/autotester/stages/explore*.py, tests only).
