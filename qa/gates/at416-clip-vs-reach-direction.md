# GATE — at416-clip-vs-reach-direction

**Opened:** 2026-09-16
**Blocks:** AT-379, AT-416 · and transitively the unit that wires `visual_text` into the crawl
**Unit that stalled on it:** `at379-scrollable-pane-reachability` (3 of 3 fix cycles spent)
**Evidence:** `qa/verdicts/at379-scrollable-pane-reachability.md` (cycles 1–3) ·
`qa/evidence/browser-at379-scrollable-pane-reachability-2026-09-16-checker-c3/report.json`

## The question in one line

When a scrollable pane sits inside a clipping box, should `visual_order.js` risk reporting text a
reader cannot see, or risk missing text a reader can?

## Why it needs you rather than another fix cycle

The same line has been wrong five times, always in the same direction, and each fix was written by
the same reasoning that produced the previous one:

| | the rule | what vanished |
|---|---|---|
| AT-373 | viewport-relative test | everything above the window's fold |
| AT-379 | a scrollable pane read as a hard clip | everything below the pane's fold |
| AT-392 | window offset only | everything before a scrolled pane's offset |
| AT-408 | walk stopped at the first one-axis scroller | nested panes' outer offset |
| AT-416 | outer clips intersected against the glyph's current rect | a pane inside any `overflow:hidden` card |

A sixth attempt by the same maker on the same line is not evidence of anything. The choice below is
between two costs the product's north star names explicitly, so it is a product call.

## The options

**A — Stop the CLIP contributing at a scrollable ancestor; re-accept AT-393.**

*Corrected after the stall diagnosis: this option originally said "revert to cycle 2", which would
also un-fix AT-408 — the checker's three-level nesting probe passes today and would stop passing.
Minimal A keeps the full walk and the accumulating `scrollX`/`scrollY`, and changes only which
ancestors contribute to the clip.* Side effects to book: the nested-clip test and mutation row 7
retire, and AT-393 flips back to `open`. AT-379 and AT-416 close; AT-393's nested
-clip **false positive** returns (text inside an outer clip is reported although a reader cannot see
it). Cost: the north star's false-positive-rate term. Smallest change, known-good behaviour.

**B — Intersect outer clips against the innermost SCROLLER'S BOX, not the glyph's rect.**
The checker's suggested fix: a glyph is reachable if the *container that can move it* intersects the
outer clip, wherever the glyph currently sits. Closes AT-379, AT-416 and AT-393 together. Cost: new
logic on the path every glyph takes, unproven, and this line's record is five for five against
confident reasoning. Would need its own unit and its own cycles.

**C — Ship neither; disclose the whole class.**
Add "a scrollable pane inside a clipping ancestor" to the module's `WHAT THIS DOES NOT SEE` block
and leave both defects open. Honest, costs nothing, and leaves a known false negative in an
instrument whose entire purpose is catching the false-negative class.

## Recommendation

**A**, unless you want B built as its own unit. A false positive costs a metric; a false negative
costs a missed credential, which is the failure this module exists to prevent — and the module's own
stated direction already prefers the former. C is worse than A here: the same exposure, minus the
fix, and disclosure does not make an instrument see.

## Measured since this gate opened (AT-423 PASS, 2026-09-16)

The scroll-invariance probe (`tests/test_browser_scroll_invariance.py`) now runs 50 generated shapes
against the current detector: **18 pass, 32 fail**. The checker attributed each failure by applying a
stand-in fix for each defect in turn. That turns the options below into numbers:

| fix applied | shapes that start passing | shapes that break |
|---|---|---|
| **option A, done fully** | **18** (every AT-416-only shape) | **0** |
| option A, **overflow branch only** | **10**, which is not enough (AT-427) | 0 |
| an AT-417 fix alone | 12 | 0 |
| both | 32, the whole red set | 0 |

**One thing option A must include (AT-427).** "Stop the clip contributing at a scrollable ancestor"
has to cover the **`clip-path` branch** of `reachOf` as well as the `overflow` branch. A change to
the `overflow` branch alone flips only 10 of the 18: in the 8 `hidden…+clip` shapes, the clip-path
branch still clips. The table above makes this checkable. A correct option A turns all 18
AT-416-only xfails into strict XPASSes and turns no passing shape red.

**The 2 shapes that have both defects stay failing under A.** They need AT-417 too, which is a
separate fix and not part of this decision.

## This gate no longer blocks work

The stall diagnosis found a contained, reversible recovery that needs no answer from you: **AT-423**,
a scroll-invariance probe that generates the shapes instead of requiring someone to imagine the
failing one. It is test-only, so it cannot change what the detector reports. It also answers the
question this gate cannot: whether option A closes AT-416 **without** re-opening AT-373/379/392/408
— which right now nobody knows, including me. The gate stays open and decoupled; take the measurement
first if you would rather decide on data than on my recommendation.

## How to answer

Reply with `A`, `B` or `C` (or your own direction). I will append
`Answered: <ISO date> — <choice> — <where>` to this file before acting on it.

Answered: 2026-09-26T22:34:22+05:30 — B — Umesh via AskUserQuestion in the checker session. Build the both-directions fix: the held candidate on wave/at408-416-scroll-reach becomes a checkable unit. It cannot PASS without real-Chromium Mode D and the 50-shape scroll-invariance corpus run on the branch (the static harness alone is not evidence).

## Update 2026-09-25 (maker): an option-B candidate exists, and it is HELD

The maker dispatched a build that implemented **option B** (`wave/at408-416-scroll-reach`, 553e8fa code, 7bf23dc manifest) **before this gate was answered**. That was a maker error: the brief followed the issue's "expected" text and did not check for this gate.

- **What the candidate does:** `reachOf`/`isReachable` carry an `innerClip` (tested against the glyph's rect) and an `outerClip` (tested against the innermost scroller's box). The code moves to `browser/visual_order_reach.js`.
- **What is NOT proven:** it has **not** run against real Chromium. RAM stayed below 1.5 GB for the whole build window. Only a static harness (7/7 on the checker's recorded P1/P2/P6/P7 geometries) and the non-browser suite (1591 passed) back it.
- **Status:** the branch is held. It is not merged and not submitted as PASS-able. It becomes a checkable unit only if Umesh answers **B**. If he answers **A**, it is discarded and option A is built fresh.
- **Why it can help the decision:** the 50-shape scroll-invariance corpus, run on this branch once RAM allows, would give the "decide on data" measurement this gate asks for.
