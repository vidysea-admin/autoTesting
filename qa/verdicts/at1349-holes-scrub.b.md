# Verdict B - at1349-holes-scrub (dual check, coordinator B)

Verdict: PASS
Cycle checked: 0
Bound to: D:/autoTesting/.worktrees/at1349-holes-scrub (head 0f1c79e6, base 8956c9bc, merge-base with int/1019 = 8956c9bc)
Policy-Version: proportional-verification/2026-10-19.17
TIER: L (security: secret persistence; dual-trigger src/autotester/stages/explore_summary.py:83, read by me this check)
Contract: qa/contracts/explore.md, qa/contracts/core-invariants.md (redaction). Issue: AT-1349.

## Check plan (step 0)
Diff = 3 src files (+13/-2 lines of product code) + 1 new test file. Signals: logic changed -> affected tests + falsification floor; security (secret persistence) -> security read of the changed lines + independent differential probe. No UI, no persona walk, no live/model call (all offline fake site).

## Criteria
- C1 PASS. crawl.json never persisted with a raw secret.
  - Read src/autotester/stages/explore_summary.py:83-93 (save_crawl): coverage (holes, screens_not_entered, permitted_holes, spec_error, error), each noise_counts entry and stop_reason are masked; saved via model_copy so memory keeps real selectors. Call sites explore.py:230 (_finish) and explore_node.py:139 (heartbeat). Only other writer of crawl.json is explore.py:272 (initial envelope: approval ids, slug, bounds, policy, login_case_id; no page text). Grepped all of src for save_crawl/crawl_manifest: no other writer.
  - Field audit of schema/crawl.py:230-300 (Crawl): every free-text field is covered (coverage, noise_counts, stop_reason); the rest are config, ids, counters, timestamps.
  - Independent differential probe (my own script, .work/tmp/b-probe/probe.py + probe2.py; dummy AUTOTESTER_APPROVAL_KEY in process env, no .env opened): planted secret in a link name, a button name, selectors, an off-domain href, a same-domain href (/deep/<secret>) and a hole url_template. Base 8956c9bc: "secret in crawl.json: True" (holes carry it verbatim, incl. url_template /deep/<secret>). Head: "secret in crawl.json: False", same hole count (4 and 5), names/selectors/url_template now carry the mask and the holes are still recorded (reasons not_visited / bound:per_node_action_cap / off_domain intact).
  - Maker tests: uv run pytest tests/test_crawl_holes_scrub.py -> 3 passed (run by me).
- C2 PASS. Nothing scrubbed before is unscrubbed; crawl tests green.
  - Maker's regression set (15 files, exactly the Tests[C2] list): 172 passed in 412.78s (run by me, log .work/tmp/b-c2.log).
  - Reference-hit callers the maker did not list (see PROPOSED-ISSUE 1): tests/test_agent_gain.py test_check_crawl_approval.py test_coverage_wiring.py test_explore_error_causes.py test_explore_flows_doors.py test_generic_acceptance.py test_inbox_scope.py test_permission_coverage.py test_persona_diff_pipeline.py test_ui_crawl_approval.py test_ui_crawls.py test_unified_report.py: 119 passed in 228.08s (log .work/tmp/b-extra.log).
  - save_crawl adds scrubbing only; it removes none (scrubbed() keeps _MINTED ids/timestamps; test_a_numeric_secret... green, and explore_summary.py:56 rule reused unchanged).
  - ruff check src tests scripts -> All checks passed; autotester doctor -> clean; explore_summary.py 116, explore.py 295, explore_node.py 300 lines (<=300).

## Falsification (floor: 1 per changed criterion; copies under .work/tmp/b-mut, bound tree untouched)
- F[C1] control 3 passed; replace update["coverage"]=scrubbed(...) with raw coverage -> 3 failed (holes test, e2e test, numeric test); restored -> 3 passed.
- F[C1 call site] _finish reverted to rt.store.save_crawl(crawl) -> 1 failed (e2e masked-hole test); restored.
- F[C2] same coverage mutant fails ::test_a_numeric_secret_does_not_corrupt_the_crawl_envelope_ids_or_timestamps.
- Survivor: reverting the heartbeat call site (explore_node.py:139) -> 3 passed (no test pins it). Judged defensive only: noise_counts, stop_reason and coverage are set solely in _finish (explore.py:217,226,230), so a heartbeat-time crawl has nothing to mask. Not a criterion defect.

## Residual: secret inside a node_id (the builder's declared residual)
Does not leave C1 unmet. node ids are minted as content_id("node", {url_template, signature}) = "node_" + 12-char content hash (schema/screen_graph.py:86-88, core/ids.py:121-123), so a node_id never contains page text, an href or a link name; a raw secret can appear in it only as a coincidental substring of a hash (the exact case the _MINTED rule at explore_summary.py:51-52 exists for: masking it would break joins). Evidence: the probe wrote the secret into hrefs and url paths and node ids in crawl.json stayed hash-shaped; the secret was absent from the whole file. Separate, lowest-tier: no finding raised.

## Security read of changed lines
No new sink, no secret value logged or returned; Redactor comes from rt.session.secrets (same object the other scrubs use). scrubbed() re-validates a copy; model_copy(update=) does not re-validate, so the masked CrawlCoverage already validated. No injection or path concern. Not raised to dual-diverging.

## PROPOSED-ISSUE lines (dual check: no side effects)
PROPOSED-ISSUE 1 (low, process): manifest is pinned .17 but has no "## Test selection (haiku)" section, no Sibling: lines and no Dropped: lines (.13-6..8); 12 test files that reference save_crawl/heartbeat/_finish were not selected. I ran all 12 (119 passed), so no coverage gap remains; not a FAIL (no wrong behaviour, evidence-to-block).
PROPOSED-ISSUE 2 (low, test gap): no test fails if explore_node.py:139 heartbeat is reverted to the raw save (mutant survived). Defensive path; a test would pin it against a future change that moves coverage/noise before the heartbeat.

Metrics: start=2026-10-21T00:00Z end=2026-10-21T00:00Z wall_min=21 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1260 mutants=0 defects_unit=0 defects_6c=0
