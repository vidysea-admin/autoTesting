# HUMAN_GATE — run the url_pattern data migration on real project data?

**Raised:** 2026-09-11T02:40+05:30 · maker, T-135 cycle 3
**Blocks:** nothing (T-135 ships without it; this is stored-data cleanup)
**Authority for raising it:** checker B, T-135 cycle-2 verdict, AT-297b — *"a committed,
idempotent, tested migration under scripts/, run AFTER the AT-294 producer fix; raise a HUMAN_GATE
rather than edit real project artifacts in-flight."*

## The question

`projects/erp/screenmap.json` holds 3 `url_pattern` values corrupted by AT-287/AT-294:

```
'/vidysea.com/erp/trainers'  ->  '/erp/trainers'   (Trainers)
'/vidysea.com/erp/trainers'  ->  '/erp/trainers'   (Trainers List)
'/vidysea.com/erp/trainers'  ->  '/erp/trainers'   (Trainers List - Edit Drawer)
```

They render to a human today on `/projects/erp/product-map`. Do we repair them now?

## What is already true, either way

- **The producer is fixed.** `build_screen_map(ProjectStore('erp'))` on the real analyses now
  yields `/erp/trainers`. Nothing new is corrupted, and re-running Analyze on this project heals it.
- **The migration exists, is committed, and is tested** — `scripts/migrate_url_patterns.py`,
  covered by `tests/test_migrate_url_patterns.py`. Dry run by default; idempotent.

> ✅ **RESOLVED 2026-09-11 (AT-298).** This document previously claimed the migration "refuses to
> touch a first path segment that merely contains a dot". **That was false** — `repair('/v1.2/foo')`
> returned `'/foo'` and `repair('/index.html')` returned `'/'`, and the test named for that guard
> asserted only *deeper* segments, so it passed while its own property was untrue. Both cycle-3
> checkers filed it.
>
> **Fixed, and not by a better regex.** A pattern now counts as mangled only when its first segment
> is a host **this project declares** in its own `project.json` (`base_url` / `allowed_domains`).
> `/v1.2/foo`, `/index.html`, `/settings.json`, `/main.js` are all left alone; so is
> `/saucedemo.com/cart` inside the erp project, because that is not an erp host. Guessing host-ness
> from string shape is unwinnable — this is the third time in this saga that lesson has been paid
> for. `tests/test_migrate_url_patterns.py` asserts the FIRST-segment cases that
> actually broke.
>
> **Option A is now safe to choose.** The dry run on real data is unchanged: 3 rows, 1 file.

- **I did NOT run it.** In cycle 2 I hand-edited this file mid-unit, and checker B was right to
  fail that: the value was one the code could not then reproduce, the backup lived in gitignored
  `.work/`, and nothing tested it. That edit has been reverted; the file is back to its real state.

## Options

| | Action | Consequence |
|---|---|---|
| **A** | `uv run python scripts/migrate_url_patterns.py --write` | 3 rows repaired now; product-map reads correctly immediately. `projects/erp/screenmap.json` is untracked, so this is a working-tree data change with no commit to revert — take a copy first if that matters. |
| **B** | Re-run Analyze on `erp` | Heals through the normal pipeline, no bespoke script touching real data. Costs a vision run. |
| **C** | Leave it | Stale display on one page for one project until either A or B happens. Nothing else depends on it — coverage compares against the FlowSpec, and `projects/erp` has no `flowspec.json`. |

**Maker's recommendation: B, else A.** B exercises the fixed producer end to end and proves the fix
on real data rather than asserting it. A is the cheap equivalent if a vision run is not worth it.

## A note on this file

It states no test COUNT. It carried one twice — "9 tests", then "14" — and went stale both times,
because a count is a derived fact that every new test invalidates while the prose sits still
(AT-306, filed twice). A document a human decides from should reference what can be re-run, not
restate a number that rots.

## Answer

_(unanswered — append `Answered: <ISO date> — <choice> — <where>` below before acting)_

Answered: 2026-09-26T22:34:22+05:30 — B — Umesh via AskUserQuestion in the checker session. Re-run the normal Analyze pipeline on the erp project (one vision-model run, approved by this answer for that single run) so the fix is proven end-to-end on stored data; A (migrate_url_patterns.py --write) is not chosen.
