# Verdict — crawl-record-gaps (cycle 0)

**Checked by:** /checker A (contract), fresh context, read-only toward src/tests
**Date:** 2026-10-29
**Branch / head:** `fix/crawl-record-gaps` @ `1edd13c9` (base `a6e03fa4`), worktree `.claude/worktrees/crawl-gaps`
**Contract:** `qa/contracts/explore.md` X3, X4, X9, X11, X12, X16; `qa/contracts/core-invariants.md` C1, C7
**Manifest:** `qa/manifests/crawl-record-gaps.md` — `Status: ready-for-check`, Fix cycle 0

**Cycle checked: 0**

## Verdict: PASS

## What I re-ran (all `uv run pytest <2 files> -o addopts=`, one at a time)

| Files | Result |
|---|---|
| test_crawl_record_gaps + test_explore | 38 passed |
| test_explore_error_causes + test_screen_identity | 17 passed |
| test_store_crawl + test_explore_traversal | 18 passed |
| test_explore_modal + test_explore_node_recovery | 8 passed |
| test_explore_return_determinism + test_explore_typing | 14 passed |
| test_crawl_liveness + test_explore_secret_scrubbing | 8 passed |
| test_crawl_coverage + test_explore_replay | 24 passed |
| test_explore_flows + test_observe | 31 passed |
| test_explore_login_wall | 16 passed |
| `uv run ruff check src tests/test_crawl_record_gaps.py tests/test_explore.py` | All checks passed |
| `uv run autotester doctor` | 2 violations, both `docs/SNAPSHOT.md` (stale-generated / stale-committed, generated file, predates the branch). Only dangling-citation advisories otherwise (not defects per task). |
| line caps | explore_node.py 300, explore.py 299, crawl.py 288, others < 170 (no file > 300) |

Full suite not run (machine low on memory); the manifest says the same.

## Criteria

1. **(a) layout toggle is not a screen — PASS.** `screen_identity.py:42-61` (`is_layout_toggle`, `same_screen`);
   used at `explore_node.py:169-171`, recorded `SAME_SCREEN` with `to_node == from_node`. `structural_signature`
   and node ids untouched (diff shows only additions in that file). Tests pass, incl.
   `test_a_layout_toggle_does_not_create_a_screen_record`. My probe of 9 names: collapse/show/hide/toggle +
   sidebar/nav/side panel match; "Expand all sections", "Hide password" do not; role must be button/switch and
   `url_template` must be unchanged. X3's own verify (same-URL filter toggle = second node) still passes
   (`test_explore_traversal`). After a toggle press `return_to` still runs each action (`explore_node.py:256`), so the
   page state is reset.
2. **(b) per-screen API inventory — PASS.** `network_capture.py:50-75`. My probe of `api_inventory`: query string,
   fragment and host dropped; numeric and 16+ hex ids collapsed to `{id}`; third-party, status >= 400, `/_next/`, `.js`
   dropped; capped at 100 rows. `ScreenNode.api_calls` defaults `[]` (old nodes load: test passes). Attribution is
   drained at `explore_node.py:153,170`, `explore.py:143,155`, folded once in `_finish` (`explore.py:218`).
   `ApiCall` is `extra="forbid"` (`screen_graph.py:54`).
3. **(c) errored edge cause — PASS.** `explore_node.py:70-80` scrubs first, then single-lines and caps at 400;
   `error_class` set at both error sites (`:160-161`, `:259-261`). Test passes.
4. **(d) provider — PASS.** `schema/crawl.py:255` `str | None = None`; `mode="before"` validator reads "mock" as
   None, real ids kept (test at `tests/test_crawl_record_gaps.py:201-206`). No reader of `Crawl.provider` in
   `src/autotester/ui`, store or cli (grep). Old `crawl.json` with `"provider": "mock"` loads.
5. **Design rules — PASS.** No new src module, no `*_v2`; doctor flags no size/function/duplicate rule.

## Focus items

- **Unbounded `api_responses` — not a defect today, latent (Warning W1).** The manifest says it fills during case
  runs; in `src` it does not: the only non-passive `PageObserver()` constructions are the four crawl entry points
  (`cli_crawl.py:81`, `cli_orchestrate.py:122`, `ui/routes_crawls.py:261`, `agents/tools.py:77`), and every one
  runs `run_crawl`, which drains both buffers per action (`explore_runtime.py:99-100`). Case runs use the passive
  observer (`observe.py:149-153`), which appends nothing (`observe.py:101`). A crawl's growth equals what
  `responses` already was (it used to drain only at the end); now `net_log` keeps that and `api_seen` keeps a second
  raw copy of the XHR subset until `_finish`, so crawl memory is roughly one extra tuple per XHR, bounded by
  `max_actions`/wall clock. If a future caller gives a case run a non-passive observer, `execute.py:102` drains
  only `responses` and `api_responses` grows without bound. Cheap hardening (not required for PASS): drain or
  cap `api_responses` in `execute._fold_network`, or aggregate `api_seen` into counts as it arrives.
- **Toggle must not merge different screens — Warning W2.** The match is name-based, same-URL only. Residual risk: a
  hamburger "Toggle navigation" that reveals links hidden while collapsed now records SAME_SCREEN, so those revealed
  links are not enqueued from that press (before, the expanded state minted a node that was explored). The Pathlynks
  gap this fixes is the opposite case (labels flip, hrefs stay). Not a contract failure; worth a note on the next crawl
  comparison (frontier size on a mobile-width or hamburger site).
- **No ids/tokens/query/host in `api_calls` — PASS with Warning W3.** Query, host, fragment and numeric/uuid/ULID/
  16+hex ids never appear (probe above). Residual, same limit as screen identity (`core/urls.py:_template_segment`,
  C1: one normaliser): an opaque short path token (`/api/reset/Xk29aPq`), an email in a path
  (`/api/users/john.doe@example.com/inbox`) or a matrix parameter (`/x;jsessionid=ABC123`) survives into
  `nodes.jsonl`. Redactor only scrubs configured secret values. Fix belongs in `url_template` (shared with
  ingest), not here.
- **Old records with provider "mock" load — PASS** (test plus validator read).

## Contract amendments by this checker

`qa/contracts/explore.md`: X12 text restated (`provider=mock` became `provider=None`), X3 gains the one named
layout-toggle exception, change-log line appended. No criterion removed.

## Findings

No blocking findings. Warnings W1, W2, W3 above are for the maker's backlog, not a fix cycle.
