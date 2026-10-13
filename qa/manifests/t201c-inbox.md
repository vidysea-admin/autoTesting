# Manifest - t201c-inbox

**Unit:** T-201 `t201c-inbox`: the website inbox "My reports" (TT7), also the owner-visible, non-email half of T-200 TS5/TS7 (one inbox, one list).
**Contract:** `qa/contracts/team-test-button.md` TT7 (TT8/TT9 email DEFERRED, D-093 item 2); `team-schedule.md` TS5/TS7 owner-visible half; `auth.md` AU12/AU13/AU16; `hosting.md` HO25.
**Branch / base:** `wave/t201c-inbox` from master `eaf44d8c`.
Tier: L (auth-scoped listing)
Dual check: recommended (scope filter)
Fix cycle: 1
Executor: claude-sonnet-subagent (maker build subagent)
Code commit (pre-check sha): branch tip of wave/t201c-inbox
Status: ready-for-check

## What changed

| Path | One job |
|---|---|
| `src/autotester/stages/report_delivery.py` (new) | `report_label` (the one place the label is computed) and `inbox_for` (rows filtered per project by `authorize(report.view)`). |
| `src/autotester/ui/routes_inbox.py`, `ui/inbox_view.py` (new) | `GET /inbox` and its markup: labelled table, `aria-label` on each Open-report link, auto-refresh while any row is queued or running. |
| `schema/delivery.py` | Additive `InboxEntry` (extra="forbid"); no new store: rows are derived on every read from the persisted queue plus the run's verdicts. |
| `auth/policy.py`, `tests/test_ui_auth_policy_table.py`, `ui/routers.py`, `ui/theme.py` | Policy row `GET /inbox` = key `report.view` (no new permission key); pin added additively; router wired (stub stays); nav link "My reports". |
| `tests/test_inbox_scope.py` | TT7 evidence. |

## Design notes

- Source is the run queue's persisted entries (they carry done, failed, refused and interrupted requests, button and schedule); a refused/interrupted request has no run directory, so the queue is the only record of it. Schedule-owner entries are the same rows (owner is entitled through `report.view@own`), labelled "scheduled".
- Label is computed on read by one function, not written to disk: the contract's "one stored value" is met as "one definition"; persisting it would need a new store. The checker may rule on that.
- The queue keeps only `KEEP_FINISHED` finished entries, so the inbox is recent history, not an archive.
- Direct URL for a non-done row is the existing `/projects/{slug}/test/{run_id}` status page (report.view, 404 when hidden); a done row links to `/projects/{slug}/runs/{run_id}`.

## Evidence (per-file; no full suite; no browser started)

- `tests/test_inbox_scope.py`: anonymous 302, pending account 403, 4 users x 2 projects x {list, direct URL}, hidden vs missing 404 identical, cross-user isolation, refused/interrupted/low-coverage/all-blocked/green labels, schedule row, label defined once (grep), queued-with-position under a one-slot queue (real `RunQueue`, manual spawner).
- `tests/test_ui_auth_policy_table.py` and `tests/test_routers_list.py` pass beside it (14 passed in the combined run, scope-table test fixed and re-run: pass).
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: clean (advisory D-087 warnings only).

## Owed to checker

- Full suite; mutation runs (list without `authorize`; recompute the label in the view).
- Headed-browser persona walk of `/inbox` (not done here; CPU shared with a live run).
- Email (TT8/TT9) deferred; `DeliveryRecord` channel `inbox` is not written (rows are derived), flagged for the checker.
