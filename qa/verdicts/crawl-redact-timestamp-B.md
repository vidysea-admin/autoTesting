# Verdict B (blind dual coordinator) - crawl-redact-timestamp

Cycle checked: 0
Head reviewed: 47153931 (base ec151a35, worktree .worktrees/crawl-redact-timestamp)
Policy-Version: proportional-verification/2026-10-19.17
Verdict: PASS
Tier: L (dual-trigger security src/autotester/stages/explore_summary.py:67 confirmed: the diff narrows what is scrubbed before persistence)

Metrics: start=2026-10-19T14:25Z end=2026-10-19T14:50Z wall_min=25 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1500 mutants=0 defects_unit=0 defects_6c=0
slow: affected-set run 150s (8 files, 137 tests; suite_lock.py here has no --slots mode, so ran unlocked)

## Focus 1 - can any _MINTED key carry a secret into persisted crawl output? NO
Models passed to `explore_summary.scrubbed` (grep of callers: explore.py:156, explore_node.py:72/85/120/184, explore_incremental.py:135, explore_summary.py:102): ScreenNode, ScreenEdge, CrawlIssue, CrawlSummary. Source of every _MINTED-keyed value, read in this check:
- `id` / `discovered_by` / `from_node` / `to_node` / `node_id`: `content_id(prefix, hash)` (schema/screen_graph.py:90,116; crawl.py:131 `model_post_init`; ids.py:121) or another node/edge id (explore_node.py:82,116,173-174). `discovered_by` = `edge.id` (explore_node.py:116), a 12-char hash, never page text. `add_issue` node_id is always `node.id`, `node_id` of drain, or "" (explore_node.py:52,62,96-100,169...; explore_replay.py:131).
- `crawl_id`: always `run_id("crawl")` ULID at every caller (cli_crawl.py:89, cli_orchestrate.py:123, routes_crawls.py via same); `approval_id`: `content_id("appr", bound payload)` (schema/approval.py:105-107).
- `started_at`/`finished_at`/`heartbeat_at`: `_now_iso()` (explore.py:45-46).
No _MINTED field is fed page text, URL, selector, user input or a model output. No model passed to `scrubbed` has a dict field with caller-chosen keys, so a key named like a _MINTED key cannot smuggle free text. Dynamic probe (copy at 47153931, tests/test_probe_b.py::test_probe_secret_everywhere_in_page_text): a unique secret placed in element name, selector, href, URL/title of a crawled page; full crawl completed (5 screens, 14 edges); the secret appears in NO node/edge/issue/summary file; `url_template` and names are masked (`/p/[REDACTED]:PROBE_SECRET`). C2 holds for the minted-key exemption.

## Focus 2 - crash guard (explore.py:279-290; explore_status.py:crash_reason)
- Terminal state: probe test_probe_crash_message_with_secret: `visit_node` raises; crawl.json status `aborted`, finished_at set, summary status `aborted`, summary stop_reason `crawl_error: ...`.
- No secret in stop_reason: exception message carried the secret raw and inside a URL query. `crash_reason` itself is unscrubbed, but `_finish` scrubs it (explore.py:217 `secrets.scrub_optional`, AT-350) before `save_crawl`, and `safe_stop_reason` + `scrubbed` run again for the tracked summary. Disk scan of the whole temp project (excluding .env): zero hits of the raw secret. crawl.json stop_reason: `crawl error -- ValueError: login failed for [REDACTED]:PROBE_SECRET at https://app.test/x?p=[REDACTED]:PROBE_SECRET...`; summary: `crawl_error: crawl error -- ValueError: login failed for :PROBE_SECRET at` (key name only, no value). (A reversed spelling of the secret is not masked, by design of `Redactor.scrub`; not claimed, not a defect of this diff.)
- `ApprovalRequired` is raised before the try (require_consent, explore.py:258-260) and is not swallowed.

## Acceptance (reran, not reused)
- `uv run pytest` on tests/test_crawl_redact_timestamp.py, test_trace_numeric_secret.py, test_approval_prod_gate.py, test_approval_prod_gate_paths.py, test_explore_error_causes.py, test_explore_node_recovery.py, test_explore_blocked.py, test_explore.py (in the worktree) -> 137 passed.
- `uv run ruff check` on the 4 changed files -> All checks passed; `uv run autotester doctor` -> clean; line counts explore.py 295, explore_status.py 281, explore_summary.py 103.
- Moved `login_failed_reason` is verbatim (git diff); only caller updated (explore.py:289).

## Falsification floor (one per changed criterion, in a copy of 47153931, restored after each)
- C1: restore `redactor.scrub_obj(model_dump(mode="json"))` -> 4 failed, restored 5 passed.
- C2: widen `_MINTED` to also exempt `reason`, `name`, `target` -> ::test_free_text_still_masks_the_same_numeric_secret failed (1 failed, 4 passed), restored 5 passed.
- C3: narrow `except Exception` to `except ZeroDivisionError` -> ::test_a_crawl_that_raises_mid_run_ends_terminal_with_the_error_recorded failed, restored 5 passed.
Base control: the same probe file on ec151a35 shows the guard absent (crash test propagates ValueError), confirming the copy ran the right tree.

## PROPOSED-ISSUE (non-blocking; no ledger write by this coordinator)
1. [security, pre-existing, NOT introduced by this diff] The `Crawl` envelope (crawl.json) is saved unscrubbed (`crawl_store.save_crawl`, explore.py:230 `store.save_crawl(crawl)`), and its `coverage.holes[]` carry raw `selector`, `name` and `url_template` from page text. Probe: a secret in a link name/href/selector appears verbatim in crawl.json, identically on base ec151a35 and head (HIT lines for selector, name, url_template). Nodes, edges, issues and the tracked summary are clean. This is the "other persistence paths not audited" residual of the manifest, now with a reproducer. Suggest S2 `security` row: scrub `Crawl` (coverage holes) before `save_crawl`. Not a FAIL here because the changed code did not touch that path and the unchanged behaviour is identical on base.
2. [low, residual already declared in the manifest] If `_finish` itself raises (probe: `crawl_coverage.of_run` raising), the guard's second `_finish` raises again before `save_crawl`; the exception propagates and crawl.json stays `running` (probe test_probe_finish_itself_raises printed `[RUNNING]`). The AT-483 stale-heartbeat display covers it. Suggest the guard write a minimal terminal envelope when `_finish` fails. Not a criterion failure: C3 is "an exception mid-walk ends ABORTED", which is met and tested.
3. [low, wording] The test docstring "any exception from the walk leaves a terminal status" over-states item 2.
4. [low] `suite_lock.py` at D:/ai_os/.claude/skills/checker/tools has only the exclusive `run` mode (no `--slots`), so rule .10-4 slot locking could not be used.
