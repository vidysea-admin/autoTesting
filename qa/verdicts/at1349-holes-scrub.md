# Verdict A (blind dual coordinator) - at1349-holes-scrub

Cycle checked: 0
Head reviewed: 47e4b8ad (product code = 1d3b9798, `git diff 1d3b9798 HEAD` is the manifest only; base 8956c9bc, worktree .worktrees/at1349-holes-scrub)
Policy-Version: proportional-verification/2026-10-19.17
Verdict: PASS
Tier: L (dual-trigger security src/autotester/stages/explore_summary.py:83 confirmed: `save_crawl` is the persistence-masking path for crawl.json)

Metrics: start=2026-10-21T07:15Z end=2026-10-21T07:38Z wall_min=23 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1380 mutants=0 defects_unit=0 defects_6c=0
slow: C2 regression set 15 files / 172 tests 412 s (maker had 469 s); run once, unlocked (suite_lock.py has only the exclusive `run` mode, no --slots)

## Check plan
Logic changed (explore persistence, security) -> affected tests + falsification floor (1 per changed criterion) + security read of the diff (4c). No UI, no live portal, no data artifact, no prompt: no browser, persona or auditor check. Only built-in checks apply, so no sub-checker fan-out; steps ran as tool calls with no shared port or DB.

## Diff read (4c, whole unit: `git diff 8956c9bc..1d3b9798 -- src`)
- explore_summary.py:83-93 new `save_crawl`: `coverage` (holes, screens_not_entered, permitted_holes, spec_error, error) via `scrubbed`, each `noise_counts` entry via `scrubbed`, `stop_reason` via `Redactor.scrub`, then `rt.store.save_crawl(model_copy)`; the in-memory crawl is untouched.
- explore.py:230 `_finish` and explore_node.py:139 `heartbeat` now call it. Only other writers of crawl.json (grep `save_crawl|crawl_manifest` over src): explore.py:272 (initial envelope: approval ids, project slug, bounds, policy, login_case_id, started_at; no page text) and crawl_store.py:31 (the primitive). No other src writer exists.
- Every `Crawl` field read (schema/crawl.py:230-275): the text-bearing ones are `coverage`, `noise_counts[].host`, `stop_reason`; all three are now masked. The rest are ids, enums, counters, ISO times or config (`bounds`, `policy.deny_patterns` etc., declared by the project, not page text).

## C1 - crawl.json never persisted with a raw secret: MET
- `.venv python -m pytest tests/test_crawl_holes_scrub.py` (in a copy at 1d3b9798, green control) -> 3 passed. I read the 3 tests: secret in link name, selector (href), url_template, screens_not_entered, permitted_holes, error, stop_reason, noise host; they assert `SECRET not in file text`, `MASK` in the hole fields and the hole count kept (test 1), and the same end to end through `run_crawl` -> `_finish` (test 2: secret-named control, href with the secret in the query; hole still recorded).
- Own probe beyond the maker's tests (D:/autoTesting/.work/tmp/at1349-A-probe/probe.py, secret `p@ss w0rd!9&x`): url_template `/r?k=p%40ss%20w0rd%219%26x`, selector with the `+`/percent form, name as HTML entities -> all three persisted as `[REDACTED]:AUTOTESTER_RESET_TOKEN`; the hole and its `reason` kept. Percent, plus and entity spellings are masked by the existing `Redactor` (AT-939), which `scrubbed` reuses.
- Falsification C1 (copy, restored): `update["coverage"] = scrubbed(rt, crawl.coverage)` -> `= crawl.coverage` gives 3 failed; call-site mutant `_finish` -> `rt.store.save_crawl(crawl)` gives 1 failed (::test_a_real_crawl_with_a_secret_named_control_persists_a_masked_hole); restored copy 3 passed.

## C2 - nothing scrubbed before is now unscrubbed; existing tests green: MET
- The diff only adds masking in front of the same `store.save_crawl`; no existing scrub is removed or reordered (stop_reason keeps the earlier `scrub_optional` at explore.py:217 and is scrubbed again, harmless).
- Minted-id rule kept: `scrubbed` exempts `_MINTED` keys, so a numeric secret (587) does not corrupt `id`, `started_at` or `node_id` (test 3 passes; the coverage-unscrubbed mutant also fails it, so it is falsified for C2 as well).
- Regression run by me, worktree venv, product tree = 1d3b9798: the 15 files of Tests[C2] -> 172 passed, 1 warning (D:/autoTesting/.work/tmp/at1349-A-regress.log). `ruff check src tests scripts` -> All checks passed. File sizes explore_summary 116, explore 295, explore_node 300 (all <= 300).

## Judgement: the node_id residual does NOT leave C1 unmet (separate, lower finding)
- `node_id` on a hole is always `node.id` or `edge.to_node` (crawl_coverage.py:98,208) or "" (:146). A `ScreenNode.id` is `content_id("node", {"t": url_template, "s": signature})` = `node_` + the first 12 hex chars of a SHA-256 (screen_graph.py:79-85, core/ids.py:102-123). A secret cannot be embedded in a 12-char hash, and page text never reaches that field. It is typed machine data, not page text, so C1's "fields carrying page text, link names or hrefs" is met.
- The residual is demonstrated only synthetically: the probe's hand-planted `node_p@ss w0rd!9&x` stays raw (the `_MINTED` exemption). The exemption is a real but unreachable path, the same finding class as the crawl-redact-timestamp unit's Focus 1 (it proved no `_MINTED` key is ever fed text).

## PROPOSED-ISSUE (non-blocking; no ledger write by this coordinator)
1. [low, residual] `CoverageHole.node_id` is exempt from masking via `_MINTED` (explore_summary.py:56-57); safe today because it is a 12-hex content hash. If a future producer puts text in a hole `node_id`, it persists raw. Suggest a schema validator on `node_id` (`^node_[0-9a-f]{12}$` or "") rather than a scrub change. Not C1: no reachable input.
2. [low, test gap] The `heartbeat` call site (explore_node.py:139) has no test that pins it to `save_crawl`; at heartbeat time `coverage` is None and `stop_reason` unset (coverage is computed only in `_finish`, explore.py:227), so nothing sensitive is written there today. I did not mutate it (not a floor item), so I make no claim that a revert would or would not fail a test.
3. [low, process] `suite_lock.py` has no `--slots` counting mode (rule .10-4); the C2 set ran unlocked. Same as the earlier crawl-redact-timestamp verdict.

## Falsification floor
C1: 2 named mutants above (green before 3 passed / red after / restored 3 passed). C2: the coverage-unscrubbed mutant fails ::test_a_numeric_secret_does_not_corrupt_the_crawl_envelope_ids_or_timestamps (3 failed in total with it). mutations=2; both edits ran serially in one isolated copy at D:/autoTesting/.work/tmp/at1349-A-mut1, restored after each; the bound tree was never edited.
