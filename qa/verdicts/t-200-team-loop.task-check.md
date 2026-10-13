# Task-level verdict - T-200 scheduled auto-test (independent close-out check, 2026-10-13)

Contract `qa/contracts/team-schedule.md` TS1-TS7. Merged and checked-PASS: t200a (core), t200b (scheduled test), t200-schedule-wiring (TS3-TS7 tick/CLI side, HO23).

VERDICT: FAIL (task not closed; the file at the done_check path is deliberately not written)

Gaps:
1. TS1 routes: no route changes or shows a schedule. `ROUTERS` holds only the empty "schedule" stub; no policy row in `auth/policy.py` uses `schedule.manage`; the per-project schedule card (GET needs `project.view`, every POST needs `schedule.manage`, 403 naming it) does not exist. The wiring verdict itself lists routes, schedule.manage, HO24 "refused", the card and inbox as HELD.
2. Persona walk (Mode D, "judged once the schedule UI exists"): cannot be run, no UI.
3. The goal-note blocker (T-205) is cleared and T-204 is merged now; the missing unit is the schedule routes/card slice (held on T-205 and T-204, both now available).

---

# Re-judge 2026-10-13 (after merge of check/t200-walk, security checker PASS, qa/verdicts/t200-walk-auth-refactor.md)

VERDICT: FAIL (task still not closed; the file at the done_check path is deliberately not written). One gap left; the first three gaps above are closed.

Closed since the first check: routes and card (t200c r1-r3 PASS; policy rows schedule.manage; 403 names the key), HO24 owner guard (fails closed with auth ON), persona walk (t200-walk r1-r3: preview, inline refusal, credentials link, subadmin, unassigned 404, run attribution, tick waits for its runs).

| Row | Result |
|---|---|
| TS1 schedule typed, persisted, schedule.manage only | PASS |
| TS2 due() pure, one marker per slot | PASS (t200a) |
| TS3 grace window catch-up | PASS (t200a, wiring) |
| TS4 overlap skipped | PASS |
| TS5 credential gate, zero trace | PASS for the gate and the project-page half |
| TS5 "the schedule owner sees the refusal ... in their website inbox" | **GAP** |
| TS6 one launcher, tick never starts a browser | PASS (closure test green with the loopback split) |
| TS7 failures loud, heartbeat, CLI | PASS; a failed scheduled run reaches the owner's inbox (t201c r2 DeliveryRecord to the schedule owner) |

The gap: a `blocked_no_credentials` or `refused` slot creates no run and no queue entry, so nothing reaches `/inbox`
(inbox rows are derived from queue entries and DeliveryRecords of runs; `ui/inbox_view.py` and `routes_inbox.py` read no slot
records). The owner sees the refusal only on the schedule card and its history. TS5 requires the website inbox as well
(only the email half is deferred, D-092 item 1). Fix: write an inbox DeliveryRecord (or inbox row) for the schedule owner when a slot
is recorded blocked/refused, with a test; then T-200 can close.
