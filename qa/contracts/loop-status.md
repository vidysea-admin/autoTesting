# Contract — loop-status (is the maker-checker loop alive?)

**Status:** ACTIVE (authored by /checker 2026-09-26 under D-047). LS1, LS2 and LS4 describe behaviour already shipped and tested. LS3's pinning test arrives with unit at610-strict-out-of-order-pin.
**Feature:** `autotester loop-status [--strict] [--hours N]` reads `qa/.last-tick` read-only. It enumerates the gaps, classifies each one (explained by `qa/.paused`, or SLEEP), and reports anomalies in the log.
**Code:** `src/autotester/loop_status.py` (logic plus `report_lines`) · `src/autotester/cli_loop.py` (the terminal only).
**Tests:** `tests/test_loop_status.py`, `tests/test_loop_status_integrity.py`.
**Grounding:** AT-368 (a 4.85-day silent outage), AT-399 and AT-424 (anomalies computed but not shown), AT-592 (strict missed an all-future log), AT-610 plus the at610 gate (write-order corruption).

## Why it exists

Nothing in this repo runs while the app is closed. So this command does not keep the loop alive. It makes a silence **legible afterwards**, and `--strict` gives a caller something to key an alarm off.

## Criteria

### LS1 — What `--strict` exits non-zero for

`--strict` exits non-zero exactly when `LoopStatus.strict_unhealthy` is true. That is either of two cases:
- the loop is silent **right now** and nothing on disk explains it, meaning the open gap is at or over the threshold and no `qa/.paused` exists (`asleep_now`);
- ticks exist but **none is credible**, meaning every stamp is dated after now (`ticks > 0` and `last_tick is None`).

In every other state `--strict` exits 0. Without `--strict` the command always exits 0, whatever it prints. A historical (closed) gap never fails `--strict`: it says the loop once slept, not that it is sleeping. (AT-368, AT-592)

### LS2 — Every structured anomaly is rendered, not only counted

When the log has at least one tick, `report_lines` renders:
- a `CORRUPT` row for future-dated stamps, which are excluded from the gap arithmetic;
- a `CORRUPT` row for ticks written out of chronological order;
- a `last: none credible` row when no tick survives.

An all-future log is never rendered as "no ticks recorded", and never also claims "no gaps". Only a log with zero parsed ticks says "no ticks recorded". (AT-399, AT-424)

### LS3 — Write-order corruption is report-only (Umesh, at610 gate answer A, 2026-09-26)

Ticks written out of chronological order (`out_of_order > 0`) always get their LS2 `CORRUPT` row. They never, on their own, make `--strict` exit non-zero. With `out_of_order > 0` and a credible recent tick, `--strict` exits 0.

Liveness is judged only from the sorted credible ticks, never from file order. So write-order corruption cannot hide an outage: an asleep loop with out-of-order lines still fails LS1.

Making out-of-order lines gate `--strict` needs a new gate answer. It is not a fix.

### LS4 — Not part of doctor, and read-only

`loop-status` is never wired into `autotester doctor` or the adapter's verify chain. A stale loop must not fail every unit's verification, because a liveness signal that breaks the build is worse than the silence it replaces (AT-368). It never writes, repairs or re-sorts `qa/.last-tick`.

### LS5 — The session-start consumer is bounded and cannot block or break session start (at383, AT-622/AT-624)

`qa/hooks/mc-sessionstart.ps1` calls `loop-status` once, with a timeout (default 15000 ms). On timeout it kills the **whole process tree** (`taskkill /T /F`), not only the `uv` process. No `uv`-launched python grandchild may survive a timed-out call.

Any failure (timeout, missing `uv`, missing `taskkill`, non-zero exit) prints one skip line with a stderr tail and lets the hook continue with exit 0. The call sits inside an outer try whose catch prints that skip line. A test asserts this structure, not merely that `try {` and `catch {` appear somewhere in the file.

A behavioural test drives a real grandchild through the same path and asserts it is dead after the timeout.

## Out of scope

- Keeping the loop alive, or scheduling anything. That is the maker skill's ScheduleWakeup.
- Proving a **closed** gap was deliberate. `/maker resume` deletes `qa/.paused`, so a finished pause leaves no trace (`retro_blind`). That is disclosed in the output, not a defect here.
- The hook's other, pre-existing calls (e.g. the `autotester snapshot` regeneration). That is AT-623, gated for Umesh.

## No-fire list

- Historical gaps rendered as SLEEP (the `retro_blind` note explains why).
- A CORRUPT row alongside exit 0 for out-of-order lines. That is LS3 working as decided.

## Amendment log (append-only; git history is the version)

- 2026-09-26 · init · contract authored by /checker under D-047. It codifies at399, at424 and at592 (all checked-PASS and merged), and records the at610 gate answer A as LS3. No prior contract named loop-status; the at592 manifest asked for this decision. Nothing amended.
- 2026-09-27 · tighten · added LS5, which codifies at383 cycle 2 (checked-PASS, verdict df909e05, merged 0f503612): a bounded session-start call, a whole-tree kill on timeout, and a structural try/catch assertion. The out-of-scope bullet "where `--strict` is called from: gate at383" is replaced, because that gate was answered and is now LS5; AT-623 is named as the remaining out-of-scope call. Only tightening, so no DECISIONS entry is needed.
