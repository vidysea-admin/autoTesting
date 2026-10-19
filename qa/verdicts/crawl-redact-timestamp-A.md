# Verdict - crawl-redact-timestamp (dual coordinator A, blind)

**Verdict:** PASS
**Cycle checked:** 0
**Head checked:** 47153931 (base ec151a35), worktree .worktrees/crawl-redact-timestamp
Policy-Version: proportional-verification/2026-10-19.17
Tier: L, dual-trigger security src/autotester/stages/explore_summary.py:67 (confirmed: line 67 is the `_MINTED` exemption)

Metrics: start=2026-10-19T14:05Z end=2026-10-19T14:40Z wall_min=35 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=2100 mutants=1 defects_unit=0 defects_6c=0
slow: affected-set run 150 s (137 tests, one process); probe + mutant setup the rest

## Check plan
Criteria C1-C3 of the build brief, plus the dual-trigger focus: (1) can any `_MINTED` key carry a secret to disk, (2) does the crash guard end ABORTED and keep secrets out of `stop_reason`.

## Evidence (all produced by this checker)
- Affected set, run by me in the worktree: `uv run pytest tests/test_crawl_redact_timestamp.py tests/test_trace_numeric_secret.py tests/test_approval_prod_gate.py tests/test_approval_prod_gate_paths.py tests/test_explore_error_causes.py tests/test_explore_node_recovery.py tests/test_explore_blocked.py tests/test_explore.py` -> 137 passed. Log: scratchpad `check-crawl-redact-A/affected.log`. `ruff check` on the 4 changed files: clean; explore.py 295, explore_status.py 281, explore_summary.py 103 lines.
- Diff read in full (`git diff ec151a35 47153931` for explore.py, explore_status.py; explore_summary.py read whole).

## Dual-trigger question: can a `_MINTED` key carry a secret? NO
`_MINTED` is matched by dict key name anywhere in the dumped model (explore_summary.py:67-69). I traced every model that goes through `scrubbed` (callers: explore.py:156, explore_incremental.py:135, explore_node.py:72/85/120/184, explore_summary.py:102), so the models are ScreenNode, ScreenEdge, CrawlIssue, CrawlSummary:
- `id` (ScreenNode/ScreenEdge/CrawlIssue): `model_post_init` -> `content_id` = `<prefix>_` + first 12 hex of sha256 (schema/screen_graph.py:85-110, schema/crawl.py:115-129, core/ids.py:102-123). One-way hash; no page text, URL or user input survives into it. A secret cannot be recovered from it, and the hash holds no .env value.
- `discovered_by`: only assignment is `edge.id` (explore_node.py:116) -> same hash. `from_node`/`to_node`/`node_id`: always `node.id` or `""` (explore_node.py:52,62,82-96; explore_replay.py:131 passes the `node_id` of an existing node).
- `crawl_id`: `run_id("crawl")` = ULID, minted by every caller (cli_crawl.py:89, cli_orchestrate.py:123, ui/routes_crawls.py:263) or by `Crawl` default. `approval_id`: `content_id("appr", ...)` (schema/approval.py:105-107).
- `started_at`/`finished_at`/`heartbeat_at`: `_now_iso()` output only.
- No other model in the four carries a nested key named `id`/`node_id`/etc. (ElementRef has none; CrawlSummary has no `id`). No Path/Url/set typed fields exist in these models that the string-only walk would miss.
- Every free-text field (reason, name, target, selector, url_example, title, detail, console_errors, stop_reason, provenance.note/inputs) is still scrubbed. Empirical: with a numeric secret the free-text test passes, and mutant M4 below (adding reason/name/target to `_MINTED`) is caught by `test_free_text_still_masks_the_same_numeric_secret`.
Conclusion: no minted key can carry a secret into persisted crawl output; C2 holds for the exemption.

## Crash guard: terminal ABORTED, no secret in stop_reason
Probe in a `git archive` copy (scratchpad `check-crawl-redact-A/copy/tests/test_probe_A.py`, not in the bound tree): `visit_node` raises `RuntimeError("... pw=<secret> ...")`.
- Secret `hunter2-SECRETVALUE-xyz` and numeric `587`: `crawl.json` status ABORTED, `finished_at` set, summary status ABORTED. Persisted `stop_reason` = `crawl error -- RuntimeError: smtp login failed for pw=[REDACTED]:AUTOTESTER_SMTP_PORT at host`; summary stop_reason is the `crawl_error:` code form, also masked. `crash_reason` itself is not scrubbed, but `_finish` scrubs it at explore.py:217 (`secrets.scrub_optional`) and the summary path scrubs again (`scrubbed`, `stop_reason` not in `_MINTED`).
- A byte scan of every file written under the project dir (crawl.json, crawl_*.json, frontier.json, nodes.jsonl, approvals.jsonl, png; `.env` excluded) found the secret in none.

## Criteria
- C1 PASS: 3 selected tests plus the end-to-end `test_a_crawl_with_a_numeric_secret_in_every_timestamp_finishes` green; timestamps stay typed, ids stay joinable.
- C2 PASS: existing redaction tests unchanged and green (test_trace_numeric_secret, test_approval_prod_gate*, test_crawl_artifacts_mask_the_test_account_email within the 137); free text still masked; no key removed from the redaction set (the diff does not touch core/redact.py or browser/secrets.py).
- C3 PASS for the criterion as stated (exception mid-walk ends ABORTED with the error recorded, never `running`); see PROPOSED-ISSUE 1 for the residual hole.

## Falsification (floor, one per changed criterion, each in an isolated copy under scratchpad `check-crawl-redact-A/M1..M4`, control 5 passed)
- C1 M1 restore `scrub_obj(model_dump(mode="json"))`: 4 failed (ValidationError at explore_summary.py:80), restored control 5 passed.
- C2 M2 `return value if key in _MINTED else redactor.scrub(value)` -> `return value`: 1 failed (`test_free_text_still_masks_the_same_numeric_secret`).
- C3 M3 guard `except Exception` -> `except ZeroDivisionError` (at explore.py:281; my first attempt hit line 125 by mistake and was discarded): 1 failed (ValueError propagates).
- Security probe M4 (counts toward mutants=1, beyond floor, within the L cap): add reason/name/target to `_MINTED`: 1 failed, so the test pins that free text is not exempted.

## PROPOSED-ISSUE (non-blocking, not a verdict reason)
1. low/medium, correctness, C3 adjacent: the crash guard re-enters `_finish` (explore.py:281-283). If the failure is inside `_finish`'s prelude (`_fold_network_evidence` explore.py:214 or `crawl_coverage.of_run` explore.py:227), the second `_finish` raises again before `store.save_crawl`, so the crawl stays `running` on disk and the exception propagates. Reproduced: monkeypatch `explore._fold_network_evidence` to raise -> `run_crawl` raises, `store.load_crawl(id).status == RUNNING` (probe `test_p3_finish_internal_failure_leaves_terminal`, copy tests dir). Pre-existing (the base had no guard at all), outside the C3 wording (a walk exception) and acknowledged in the manifest residual risk ("If `_finish` itself raises inside the guard"), but the manifest says the exception propagates "after the first save_crawl", which is not true when the prelude is what raised. Suggest a minimal save of `ABORTED` status (envelope only) in the guard if `_finish` fails. Goes to Candidates, not into this unit.
2. low, wording: manifest Metrics carries `lane=normal`, a field retired by .16-1; ignored per the pin.

## Boundaries kept
No push, no merge, no qa/issues.jsonl, no qa/contracts edit; worktree source untouched; falsification and probes only in scratchpad copies; no PIDs killed; no .env value read or printed.
