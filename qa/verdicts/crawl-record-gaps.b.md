# Verdict — crawl-record-gaps (Checker B, adversarial)

**Checked by:** /checker (Mode A, fresh context, no builder reasoning)
**Date:** 2026-10-29
**Branch / head:** `fix/crawl-record-gaps` @ `1edd13c9` (worktree `.claude/worktrees/crawl-gaps`)
**Contract:** `qa/contracts/explore.md` X3, X4, X9/X11/X16; `qa/contracts/core-invariants.md` C1, C7
**Manifest:** `qa/manifests/crawl-record-gaps.md` — `Status: ready-for-check`, Fix cycle 0

**Cycle checked: 0**

## Verdict: PASS (4 non-blocking warnings, none a contract breach)

## What I re-ran myself

| Command | Result |
|---|---|
| `uv run pytest tests/test_crawl_record_gaps.py tests/test_explore.py -o addopts=` | 38 passed (84s) |
| neighbours the manifest did NOT list, 2 files per call: `test_explore_blocked`+`test_explore_completeness` | 59 passed |
| `test_explore_login_bypass`+`test_network_assertions` | 21 passed |
| `test_crawl_coverage_bounds`+`test_crawl_holes_scrub` | 14 passed |
| `test_explore_login_wall_bounds`+`test_crawl_redact_timestamp` | 13 passed |
| `test_agent_tools`+`test_coverage_wiring` | 22 passed |
| `test_explore_typing_guards`+`test_explore_login_spa_live` | 22 passed |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor` | 2 violations, both `docs/SNAPSHOT.md` stale-generated / stale-committed (generated file, not touched by this unit; manifest already declares it pre-existing). No design-rule violation from this diff; `explore_node.py` is exactly 300 lines, `explore.py` 299. |

## Falsification (each fix reverted in memory, `.work/test_falsify_cg_b.py`, 7 passed)

Each "reverted" case asserts the unit's own test goes RED with `AssertionError`; the control runs the unchanged test GREEN.

| Fix | In-memory revert | Unit test result |
|---|---|---|
| (a) toggle | `explore_node.same_screen = lambda n,new,el: new.id == n.id` | `test_a_layout_toggle_does_not_create_a_screen_record` RED; control GREEN |
| (b) API inventory | `explore_summary.apply_api_calls` no-op | `test_a_crawl_records_api_calls_on_the_screen_that_made_them` RED |
| (b) attribution | `take_responses` forced to `node_id=None` | same test RED |
| (b) filter | `network_capture.classify_request` always `first_party` | `test_api_inventory_keeps_first_party_...` RED |
| (c) class | `record_edge` forced `error_class=None` | `test_an_errored_edge_records_class_...` RED |
| (c) cap | `explore_node.MAX_REASON_CHARS = 10**6` | same test RED |
| (d) provider | not monkeypatchable (schema default); old default is `"mock"` at `a6e03fa4:src/autotester/schema/crawl.py`, so `tests/test_explore.py:60` (`is None`) and `test_a_crawl_records_no_provider` cannot pass without the change | by construction |

## Findings on the four focus areas

1. **PageObserver.api_responses growth (observe.py:63,111) — latent, not live.** Reproduced the pattern the builder flagged: simulating 20000 case-run steps (`_on_response` then `drain_responses()` per step, as `execute.py:102` does) leaves `api_responses` at 20000 entries (~3.7 MB, linear) while `responses` stays 0. So `execute._drain_network_evidence` does not drain the new list. In this tree, however, no case run ever sees a non-passive observer: the only `PageObserver()` constructions are the four crawl entry points (`cli_crawl.py:81`, `cli_orchestrate.py:122`, `agents/tools.py:77`, `ui/routes_crawls.py:261`), the only other one is `PageObserver(passive=True)` (`observe.py:153`), and a passive observer appends to neither list (`observe.py:101`). The one `run_case` inside a crawl is the login bootstrap (`explore.py:82`), and its leftovers are discarded by `take_responses(None)` in `_seed` (`explore.py:143`). In a crawl `api_responses` is drained on every action. **Not a blocker; recommend** draining it in `execute._drain_network_evidence` (one line) or capping the list, before anyone wires a non-passive observer into case runs.
2. **Crawl-scale memory (warning).** `ExploreRuntime.api_seen` (explore_runtime.py:~90) stores raw tuples for the whole crawl, a second copy of the XHR subset of `net_log`; `net_log` itself is the same volume the old undrained `observer.responses` held. A page that polls fast multiplies this by the actions in a crawl. Bounded by `max_actions`/wall clock, so not X4-unbounded, but aggregating into a counter at `take_responses` time would make it constant-size.
3. **Layout-toggle over-merge — contained, with a caveat.** Probed 15 names against `is_layout_toggle`. Matches: "Show navigation", "Toggle nav menu", "Hide side panel", "Show the sidebar", "Collapse main navigation". Non-matches (correct): "Open sidebar", "Close sidebar", "Toggle sidebar filters", "Show sidebar details". The merge needs same role (button/switch), a name matching the anchored regex, AND an unchanged `url_template`, so a toggle that navigates still mints a node. Caveat: "Show side panel" / "Show navigation" that opens a same-URL detail panel is recorded SAME_SCREEN and its controls are not enqueued. Also "Collapse Sidebar Menu" is not recognised (false negative, harmless). Node ids and `structural_signature` are untouched, so no id drift.
4. **api_calls leakage — query, host, fragment, userinfo, uuid/numeric/hex ids are clean; opaque path tokens are not templated (warning).** Probe through `network_capture.api_inventory`: query/fragment/host dropped; `user:pw@` URL dropped (not allowed domain); non-200 and `/_next/` and `.JS` dropped; uuid and 32-hex collapse to `{id}`. NOT collapsed because `core.urls.url_template` only knows numeric/uuid/ULID/hex>=16/date: a JWT in the path, an email in the path (`/api/users/john.doe@example.com/profile`), a base64 invite token (`/api/invite/Zm9v...`), a matrix param (`/api/session;jsessionid=ABC123DEF456`), and `ORD-2024-00081` style ids all persist verbatim into `nodes.jsonl`. Same limitation already applies to every stored screen `url_template`, and the `Redactor` only scrubs known secret values, so this is shared pre-existing behaviour and not new to this unit; the manifest's phrase "ids collapse" is true only for id-shaped segments. Worth a follow-up unit on `url_template`, not a reason to fail this one.
5. **Old records with provider "mock" load.** `Crawl._legacy_mock_default` (`schema/crawl.py:279`, `mode="before"`) maps `"mock"` to `None`; real ids are kept (`test_a_real_provider_id_is_kept_and_the_legacy_mock_default_reads_as_none`). No `src` reader of `Crawl.provider` (grep over `src` for `.provider` on a crawl: none). Side effect: an explicitly constructed `provider="mock"` also reads back as `None`; nothing sets it.
6. **Errored-edge cause (c).** Secrets are scrubbed before the whitespace collapse and the 400-char cap (`explore_node.py:75-80`), so a secret cannot be cut mid-value into an unredactable fragment. `error_class` is set at both errored sites (`try_action` and `ReturnLost`). Style nit only: the `error_class="ReturnLost"` continuation line at `explore_node.py:~261` is mis-indented; ruff accepts it.
7. **Regression hunt.** `net_log` replaces the end-of-crawl `drain_responses` so NETWORK evidence still sees every response (test_network_assertions and test_explore pass). `apply_api_calls` runs in `_finish`, which every `_walk` exit and the crash handler reach (`explore.py:263-281`), and uses `update_node` on the latest `rt.nodes` copy, so `_mark` statuses are not overwritten. A node that was never added (frontier cap) is skipped when its id is absent from `rt.nodes`.

## Not run
Whole suite (machine low on memory); live-browser Pathlynks crawl. Not needed to judge this diff.

## Followups (not blocking)
- Drain or cap `api_responses` in `execute._drain_network_evidence` (finding 1).
- Aggregate `api_seen` into counters instead of raw tuples (finding 2).
- Extend `url_template` (or `api_inventory`) to template email/JWT/base64/matrix-param/prefixed-id segments (finding 4).
