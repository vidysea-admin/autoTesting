# HUMAN_GATE — at516: what happens to a unit's evidence when a later unit splits the file its tests live in

**Opened:** 2026-09-18 · **Status: OPEN** · **Approver:** Umesh
**Blocks:** nothing today — this is a policy question, not a defect. Filed by the at513 cycle-1
checker as **AT-516** (medium, evidence-integrity) after it independently reproduced the breakage.
**Evidence:** `qa/verdicts/at513-the-block-tests-leave-the-row-tests.md` ·
`qa/manifests/at513-the-block-tests-leave-the-row-tests.md` (Known limits) ·
`scripts/mutation_check.py:319-323`

## The question, in one line

When a unit splits a test file, the `mutations.json` of every EARLIER unit whose tests moved now
names node-ids at the old path and can never be run again. **Is that acceptable as history, or is
an evidence spec supposed to stay runnable?**

## Why it is being asked now rather than earlier

It has happened twice, which makes it a pattern rather than an accident:

| split | broke | 
|---|---|
| AT-506 (moved the record rules out of `test_doctor.py`) | `at504`'s spec |
| AT-513 (moved the block-reading tests out of `test_ledger_checks.py`) | `at506`, `at509`, `at511`'s specs — **measured, 3 of 33** |

Both times the maker left them alone on the reasoning that *a unit's evidence is the record of what
that unit ran*. Both times nobody had decided that; it was inherited from the first occurrence.

**The failure is benign today and that is exactly why it needs deciding now.** The specs fail
**closed** — `mutation_check.py:319-323` refuses with *"a 'kills' label is a claim, not a comment"*
when a named test is not collected — so nothing silently mis-reports. The cost is only that the
evidence can no longer be re-derived. But the count grows with every split, and the day someone
needs to re-verify an old unit's mutation evidence is the day it is discovered to be unrunnable.

## Options

- **(a) Evidence is history; leave broken specs alone.** What has happened twice by default becomes
  the written rule. Cheap, honest about what the artifact is: a record of a run that really happened
  on a tree that no longer exists. Cost: the repo accumulates specs that cannot be re-run, and
  nothing distinguishes "stale because of a legitimate split" from "stale because someone deleted a
  test".
- **(b) The splitting unit repoints the specs it breaks.** The unit that moves a test fixes the
  node-id paths in every affected `mutations.json` as part of its own diff, and proves it by running
  them. Keeps every spec runnable forever. Cost: a unit's committed evidence gets edited by a later
  unit — the artifact stops being a faithful record of its own run, which is the objection that
  produced (a) in the first place.
- **(c) Split the difference: leave the spec, add a tombstone.** The splitting unit appends a
  machine-readable `superseded_by` / `moved_to` note to each spec it breaks, so a reader knows the
  spec is stale *by design* and where the tests went, without rewriting the historical claims. A
  `doctor` rule could then flag a spec that is stale **without** a tombstone — which is the case that
  actually indicates a lost test.
- **(d) Do nothing and stop filing it.** Accept the drift and close AT-516 as won't-fix.

## Recommendation

**(c)**, and I would not implement it until you say so, because it adds a `doctor` rule and this
project has learned twice this week that a rule written before the corpus is measured accuses the
innocent (AT-504's false counts, AT-511's 167 matching lines that turned out to change nothing).
The measurement to do first is: *how many of the repo's 33 specs are currently stale, and for how
many is the cause a legitimate move rather than a deleted test?* Only 3 are known stale from AT-513;
`at504`'s from AT-506 makes 4. That is small enough to fix by hand under (b) and small enough to
ignore under (a), so the honest statement is that **the cost of being wrong here is still low, and
it is cheapest to decide now while it is.**

I am **not** treating this as delegated the way `at355-guard-shape` was, because unlike that one this
changes how the project treats already-committed evidence — the thing the maker-checker pair exists
to keep trustworthy.

## How to answer

Append a line to this file and nothing else is needed:

`**Answered:** <ISO date> — <(a) | (b) | (c) | (d), with any narrowing> — Umesh`

**Answered:** 2026-09-26T22:34:22+05:30 — (c) — Umesh via AskUserQuestion in the checker session. Leave a stale evidence spec byte-intact but tag it 'stale on purpose, test moved to <new node id>', so a check can tell an intended stale spec from an unexplained one.
