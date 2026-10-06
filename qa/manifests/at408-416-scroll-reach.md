# Manifest — at408-416-scroll-reach

## Goal reconciliation preparation — 2026-10-06

T185 remains pending despite the existing merged cycle1PASS. Independent
read-only audit matched branch ancestry and AT731 bookkeeping evidence;
no rebuild/remerge is needed. Current done-check still requires two actual
Chromium passes, not a missing-browser SKIP. Older PASS is retained with its
recorded coverage/timing limitations, not restamped as fresh acceptance.
Independent fixture-runtime plan APPROVE:qa/feedback-inbox.md heading
"2026-10-06 T185 independent bounded fixture-runtime plan review"
(Reviewer /root/build_t196_citation_checks). Manual image-based run needs no product/launcher
or enforcement edit. Image sha256:
e2dca6c5dd32e9c2a2c1ce2f3935363fd85eaa25625ce02b081b963d5ad0711f.
Root created an isolated178-file,1755536-byte cache-free fixture export at
.work/t185-fixture-runtime-55a0633c5fbd4326b604a70deffea5cf.
Every copied file matched its source before/after freezing; sorted
path|SHA256|size aggregate43230A705602324E2136F6C6BA2FC694E515CDD25BBA851F87229B97A0192944.
No .env/profiles/projects were included; source reparse count0 and selected
HTML external-asset references0. Frozen data is preparation only, not an
executed or independently accepted product check. Runtime input screening,
import binding and post-run identity checks remain required.
Reviewed runtime floor:one1GiB-capped container plus1GiB host margin,
fresh freeRAM>=2GiB. Latest measured963688KiB is below this floor; no
container/browser launched. T125's separate4GiB controller guard unchanged.
Require networknone/readonly/nonroot/capdrop/no-new-privileges, no ports,
readonly export-only mount, bounded owned-container lifecycle/cleanup, and
XML exactly2knownPASS/noSKIP before checker-owned goal reconciliation.
No new verdict, task closure, commit/push or live-account evidence claimed.

### Fresh runtime refusal — 2026-10-06

The reviewed manual lifecycle's inline preflight returned exit1 with
`T185 preflight below2GiB: 767360KiB`, before container creation or the
120-second lifecycle clock. No browser/test ran and no container needed
cleanup. A later read-only readiness sample was1371236KiB (about1.31GiB),
still below the unchanged2GiB floor. Do not interpret either refusal as a
product FAIL, a skipped test PASS, or permission to lower the resource guard.
Resume the exact two-node fixture run only after a materially changed runtime
meets the reviewed floor; repeated launch attempts on unchanged state are not
progress. Cloud capability research did not create or migrate a task.

**Unit:** AT-408, AT-416 — `reachOf`/`isReachable` (now `src/autotester/browser/visual_order_reach.js`)
**Contract:** `qa/contracts/ui.md` U14(a) scroll-invariance floor, U14(b) north-star tie-break ·
`qa/contracts/core-invariants.md` C2 (300-line cap), C7 (falsification)
**Related:** `qa/gates/at416-clip-vs-reach-direction.md` (opened 2026-09-16, **`Answered: 2026-09-26T22:34:22+05:30
— B`**, D-048 — see "The gate — resolved" below) · `qa/manifests/at379-scrollable-pane-reachability.md`
(STALLED status, the manifest this unit closes out) · `qa/issues.jsonl` AT-408, AT-416 (both high, open)
**Goal task:** T-185 (this dispatch), none at original build — issue-driven
**Date:** 2026-09-25 (build), 2026-09-27 (this post-merge re-verify + fix cycle)
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-408 (high) · AT-416 (high)
**Branch/worktree:** `wave/at408-416-scroll-reach`, `D:/autoTesting/.worktrees/at408-416-scroll-reach`
**Commit:** `553e8fa` (original code + tests) → merged master at `3095c3f4` → this cycle's fix, below.

## The gate — resolved (D-048, 2026-09-26)

`qa/gates/at416-clip-vs-reach-direction.md` carries `Answered: 2026-09-26T22:34:22+05:30 — B —
Umesh via AskUserQuestion in the checker session`, recorded in `docs/DECISIONS.md` D-048: "**at416 =
B.** The held both-directions candidate (wave/at408-416-scroll-reach) becomes a checkable unit. It
needs real-Chromium Mode D plus the 50-shape scroll-invariance corpus run on the branch (the static
harness alone is not evidence)." This build (2026-09-27) supplies exactly that: the branch merged
current master cleanly, then ran the real-Chromium 50-shape corpus for the first time (the RAM gate
that blocked it on 2026-09-25 has since cleared) — see "What the real corpus run found" below. The
previous "open gate" ambiguity this manifest flagged is now moot: the gate is answered, matches what
was built, and D-048 explicitly names this branch.

## What changed

- **`src/autotester/browser/visual_order_reach.js`** (new, 158 lines) — `reachOf`/`isReachable`,
  moved out of `visual_order.js` (which sat at the 300-line cap, C2) so the fix had room. Not its own
  script: `observe.py` splices its text into `visual_order.js`'s IIFE at a marker comment, so
  `page.evaluate()` still receives exactly the one `(() => {...})();` shape it always has.

  **AT-408.** Already structurally fixed by the existing "walk all the way up" code (added in the
  at379 manifest's cycle 3, commit `fafe7e7`) — the loop never stops at the first scrollable
  ancestor, it accumulates `scrollX`/`scrollY` from every one. This build did not need to touch that
  part; it stays fixed and is exercised by the existing `test_a_scrolled_pane_inside_a_scrolled_pane_loses_nothing`
  (not duplicated here — see `tests/test_browser_scroll_reach_at408_416.py`'s docstring) and by a
  static unit check against the checker's own P1 (three-level nested scroll) geometry, below.

  **AT-416.** `reachOf` used to narrow ONE running `clip` from every ancestor's box on the way up,
  and `isReachable` tested the glyph's CURRENT (scroll-dependent) rect against it. That is correct
  for ancestors *between* the glyph and the first genuinely scrollable one — nothing there moves
  relative to the glyph when that scroller scrolls — but wrong for ancestors *outside* the scroller:
  the glyph moves inside the scroller's own box as it is scrolled, so testing the glyph's current
  position against an outer clip made the verdict flip with the scroller's own scroll offset —
  `reported=false` at rest, `reported=true` only once the pane happened to be scrolled to exactly the
  right spot. `qa/contracts/ui.md` U14(a) charges exactly this as a defect: the SET of glyphs
  `visual_text` reports must not depend on where anything scrollable currently sits.

  Fix: two running clips instead of one. `innerClip` narrows from the glyph up to and including the
  first (innermost) genuinely scrollable ancestor, and is tested against the glyph's rect (invariant,
  as before). `outerClip` narrows from there outward, and is tested against that scroller's own box
  (`scrollerBox`, captured once — the innermost only, "carry the innermost scroller's box forward" per
  the gate's option B) rather than the glyph — the scroller's own box does not move when its own
  content is scrolled, so this stays invariant too. A `clip-path` ancestor routes into whichever
  bucket is active exactly like an `overflow` ancestor (AT-427's warning against a partial fix that
  only touches the `overflow` branch).

  **Superseded 2026-09-27, see "merged master, RAM gap closed" below:** this two-clip
  (`innerClip`/`outerClip`/`scrollerBox`) design only had ONE scroller boundary. The real corpus run
  this cycle found it breaks under two-or-more nested scrollers; the shipped code now generalizes this
  to a chain of `segments`. The two-clip description above is accurate for a single scroller and is
  kept for history; `reachOf`'s actual return shape today is `{segments, scrollX, scrollY}`.

- **`src/autotester/browser/observe.py`** — loads `visual_order_reach.js` and splices it into
  `visual_order.js`'s text at the `// AUTOTESTER:REACH_MODULE` marker before handing the combined
  string to `page.evaluate()`. Raises `RuntimeError` at import time if the marker is ever missing,
  rather than shipping a `reachOf is not defined` failure from inside the page.

- **`src/autotester/browser/visual_order.js`** — 300 → 228 lines. The `reachOf`/`isReachable` block
  (lines 106–187) is replaced by the splice marker and a short pointer comment; nothing else changed.

- **`tests/fixtures/bidi_site/at416_card.html`** (new) — reproduces the checker's own P6
  (`qa/evidence/browser-at379-scrollable-pane-reachability-2026-09-16-checker-c3/p6-scroller-inside-hard-clip.json`,
  a ~42px band) and P7
  (`.../p7-card-wrapper.json`, a taller card) probes: an `overflow:hidden` card wrapping a genuinely
  overflowing `overflow:auto` body. Plus a negative control on the same page — a card wrapping a pane
  that does **not** overflow (AT-393's shape, not AT-416's), so the fix cannot be checked by simply
  reporting everything a card wraps.

- **`tests/test_browser_scroll_reach_at408_416.py`** (new) — two real-Chromium tests over that
  fixture: reported at rest, and reported (and scroll-invariant) after actually scrolling both bodies
  to their end. AT-408 is deliberately **not** duplicated here (see its docstring) — the existing
  `#outer`/`#inner` test in `tests/test_browser_unreadable.py` already is that exact shape.

- **`tests/test_browser_scroll_invariance.py`** — `_open_defects` no longer appends `"AT-416"`.
  18 of the 50 generated shapes were marked `xfail(strict=True, reason="AT-416")`; per the fix above
  they should now pass. **This edit is UNVERIFIED against a real browser** (see "The RAM gap" below)
  — see the in-file comment for the reasoning it rests on instead. `AT-417` is untouched.

## 2026-09-27 — merged master, RAM gap closed, real corpus run, one real defect found and fixed

This dispatch (T-185) had three jobs: bring `master` in, re-verify for real, and fix anything the
merge broke.

**Merge:** `git merge master` from `553e8fa` (this unit's last commit before this cycle) onto
current master (`c473ceb8`) was **clean — no conflicts**. `git diff 553e8fac..HEAD -- src/autotester/browser/visual_order_reach.js
src/autotester/browser/observe.py src/autotester/browser/visual_order.js` is empty: none of this
unit's own files were touched by the merge, so nothing the merge did could have caused what follows.

**RAM:** free RAM this session measured 2.1 GB (`Get-CimInstance Win32_OperatingSystem`, total 23.71
GB) — still below the 3.5 GB gate the 2026-09-25 build used, but a bounded single-test probe
(`test_browser_scroll_reach_at408_416.py`, 100s timeout) ran and passed in 3.34s, so the RAM
gate itself is stale as a hard threshold; the actual constraint was other concurrent builders holding
memory on 2026-09-25, not a fixed number. The full 50-shape corpus ran real Chromium in 14.70–56.68s
per run across many repeated runs in this cycle. **The RAM gap this manifest declared on 2026-09-25 is
closed.**

**What the real corpus run found — a genuine defect in the shipped fix, not a merge break:** the
first real run of `tests/test_browser_scroll_invariance.py` against the merged (unmodified) code from
553e8fa produced:

```
$ uv run pytest tests/test_browser_scroll_invariance.py -o addopts= -v
FAILED [...][hidden-auto-auto]
FAILED [...][hidden-auto-auto+tall]
FAILED [...][hidden-auto-auto+clip]
FAILED [...][hidden-auto-auto+clip+tall]
4 failed, 32 passed, 14 xfailed in 14.70s
```

Prediction from the 2026-09-25 manifest was "14 red shapes, all AT-417" (i.e. 0 unexpected failures).
Four shapes failed for real, none of them predicted, none of them AT-417-shaped (AT-417 requires
`clip_path and shape[0] == "auto"`; these are `shape[0] == "hidden"`). **Root cause, confirmed with an
isolated Node mock harness before touching any test** (`scratchpad/at408416/harness.js`, not committed):
`hidden-auto-auto` is a hard clip (`L0`, `overflow:hidden`) wrapping TWO nested genuine scrollers
(`L1`, `L2`, both `overflow:auto`). `reachOf` captured `scrollerBox` from the INNERMOST scroller
(`L2`) only, and tested `L2`'s own box against the outer clip (`L0`). But `L2`'s
`getBoundingClientRect()` moves on screen whenever `L1` — which contains it — is scrolled, because
`L2` is part of `L1`'s scrollable content, exactly like a glyph is part of a scroller's content. So
testing the innermost scroller's box against an outer clip is scroll-variant with respect to any
scroller BETWEEN it and that clip — the identical AT-416 mistake, one level removed, that the static
7-case harness in the 2026-09-25 manifest could not have caught (its P1/P2/P6/P7 geometries are all
single-scroller shapes).

Mock harness proof (before the fix below):

```
L1 at rest (scrollTop=0):         isReachable= true
L1 scrolled (scrollTop=150):      isReachable= false
SCROLL-INVARIANT? NO -- BUG (same glyph, different verdict by L1 scroll alone)
```

**The fix (this cycle, `src/autotester/browser/visual_order_reach.js`):** generalizes the
gate-approved option-B mechanism ("test the scroller's own box, not the glyph's rect") from a single
inner/outer split to a chain of N segments, one per scroller crossing. `reachOf` now returns
`{segments, scrollX, scrollY}`, where each segment is `{clip, refBox}` — `refBox: null` for the first
segment (tested against the glyph's own rect, unchanged from before) and each subsequent segment's
`refBox` is set to the box of the scroller that OPENED it, replacing (not merging with) any earlier
scroller's box. `isReachable` requires every segment's clip to pass against its own `refBox`. This is
a strict generalization: with exactly one scroller in the chain it produces the same two segments
(`innerClip`/glyph, `outerClip`/scrollerBox) the previous code computed by name. No change to the
gate's chosen direction (option B) — this corrects an implementation gap in it that the previous
cycle's RAM-blocked build could not verify.

Mock harness proof (after the fix):

```
L1 at rest (scrollTop=0):         isReachable= true
L1 scrolled (scrollTop=150):      isReachable= true
SCROLL-INVARIANT? YES
```

Real Chromium, same shapes, after the fix:

```
$ uv run pytest tests/test_browser_scroll_invariance.py tests/test_browser_scroll_reach_at408_416.py tests/test_browser_unreadable.py -o addopts=
54 passed, 14 xfailed in 44.20s
```

54/54 non-xfail shapes pass; the 14 xfail are exactly the AT-417 shapes the corpus's own
`_open_defects` predicts (AT-417 is out of scope for this unit, pre-existing, untouched). Zero
unexpected failures, zero unexpected passes (`strict=True` on every xfail would itself fail the run
if the prediction were now wrong in the other direction — it did not).

## The RAM gap — historical (2026-09-25 build), superseded above

Every browser-launching command in my instructions was gated on free RAM ≥ 3.5 GB, polled every
300s for up to 30 minutes. Six polls, none cleared the gate (other concurrent wave builders in this
shared session were holding memory throughout, per `qa/.last-tick`):

```
2026-09-25T16:18:18Z poll=1 free_ram_gb=1.47
2026-09-25T16:23:23Z poll=2 free_ram_gb=0.77
2026-09-25T16:28:29Z poll=3 free_ram_gb=0.62
2026-09-25T16:33:33Z poll=4 free_ram_gb=0.90
2026-09-25T16:38:35Z poll=5 free_ram_gb=0.81
2026-09-25T16:43:38Z poll=6 free_ram_gb=0.88
RAM_NEVER_FREED
```

Per my instructions ("If RAM never allows it, commit the tests anyway, mark those rows UNVERIFIED
with readings, and declare it as a gap") the new tests are committed but **never run against real
Chromium in this build**. Declared as a gap, not disclosed as a pass:

- `tests/test_browser_scroll_reach_at408_416.py` — both new tests, UNVERIFIED live.
- `tests/test_browser_unreadable.py::test_a_scrolled_pane_inside_a_scrolled_pane_loses_nothing`
  (AT-408 regression coverage) — UNVERIFIED live against the new code this cycle (it is a pre-existing,
  previously-green test; my code change is reasoned not to affect its shape, but "reasoned" is not "run").
- `tests/test_browser_scroll_invariance.py`'s 50-shape corpus, in particular whether the 18 AT-416-only
  shapes actually XPASS as predicted — UNVERIFIED.

### Historical: what stood in for it before real Chromium ran (2026-09-25, superseded)

Not a substitute for the real thing, but not nothing either: `visual_order_reach.js` is loaded
**verbatim** via Node's `eval()` (not reimplemented) and exercised against hand-built
`getBoundingClientRect`/`getComputedStyle` mocks constructed from the checker's own recorded numbers
in `qa/evidence/browser-at379-scrollable-pane-reachability-2026-09-16-checker-c3/`:

```
$ node -e "... eval(fs.readFileSync('visual_order_reach.js')) ... P6 target (scrollable pane inside 42px hard clip) -> should be reachable"
PASS P6 target (scrollable pane inside 42px hard clip) -> should be reachable got= true expected= true
PASS P6 target AT REST (not yet scrolled) -> must STILL be reachable (invariance) got= true expected= true
PASS P1 three-level all-auto nested scroll, no hard clip -> reachable got= true expected= true
PASS P2 hidden-by-middle (real hard clip between glyph and outer scroller) -> excluded got= false expected= false
PASS P2 inner-top (inside the middle band) -> reported got= true expected= true
PASS non-overflowing auto box (not a real scroller) inside 40px hard clip, glyph below the 40px band -> excluded got= false expected= false
PASS same shape, glyph inside the 40px band -> reported got= true expected= true
```

Seven cases, covering: the exact P6 shape at rest AND after scroll (the crux of AT-416 — the SAME
verdict in both states); a three-level all-`auto` nest with no hard clip (AT-408, no regression); a
hard clip *between* the glyph and an outer scroller (must stay a real, glyph-tested boundary,
unaffected by the outer scroller's own scrolling — proves `innerClip` bucketing); and the
non-overflowing "NESTCLIP" shape from `tests/fixtures/bidi_site/scrolled_panes.html` that the
existing `test_a_pane_inside_a_clipping_box_does_not_leak_past_it` depends on (proves the fix does
not accidentally start treating a non-scrolling `auto` box as a genuine scroller).

**Known, disclosed shortfall of this fix, not covered by the harness above and not claimed:** the
gate's option B is deliberately coarse — once a glyph is inside a scroller whose own box overlaps an
outer clip at all, the fix reports the glyph reachable regardless of whether that SPECIFIC glyph's own
scroll range can actually align it with the overlap (a glyph near the very bottom of a very tall
scroller, with a small outer band near the scroller's top, may not really be reachable). This is the
`qa/contracts/ui.md` U14(b) north-star tie-break taken deliberately ("keeping the visible text wins" —
a false positive here costs a reviewer a look, a false negative costs a missed credential), not an
oversight; the checker's own P4a follow-up probe found exactly this edge case and separately concluded
its own initial expectation there was wrong, not the code.

## Verify (re-run 2026-09-27, post-merge, post-fix, real Chromium)

- `uv run ruff check src tests scripts` → `All checks passed!`
- `uv run autotester doctor` → `doctor: clean`
- `uv run pytest tests/test_browser_scroll_invariance.py tests/test_browser_scroll_reach_at408_416.py
  tests/test_browser_unreadable.py -o addopts=` (real Chromium, this unit's own tests + the corpus)
  → **54 passed, 14 xfailed** — 0 unexpected failures, 0 unexpected passes. The 14 xfail are exactly
  AT-417 (untouched, pre-existing, out of scope here).
- `uv run pytest` (full suite, no ignores, no extra `-q`, per AT-503) → see "Full-suite run" below —
  this is the exact command the dispatch specified; earlier cycles could not run it in full because
  of the RAM gate, which has since cleared.

## Full-suite run (`uv run pytest`, real numbers)

```
$ uv run pytest
[...]
FAILED tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild
1 failed, 2029 passed, 5 skipped, 14 xfailed, 15 warnings in 1299.25s (0:21:39)
```

`grep -c "^FAILED"` on the full log confirms exactly **1** FAILED/ERROR line in the entire 2035-test
run. It is the same pre-existing, environmental flake the 2026-09-25 manifest already proved
unrelated and non-regressive (`tests/test_flake_probe_real_process.py`, a real-subprocess-kill timing
test nowhere near `browser/`, previously shown to pass in isolation both on master and on this
worktree). The 14 xfailed match `test_browser_scroll_invariance.py`'s AT-417 prediction exactly. This
is the first time this unit's manifest reports a real, unrestricted `uv run pytest` run — the
2026-09-25 build could only run a hand-picked non-browser subset (1591 of these 2035+ tests) because
of the RAM gate; that gate is closed, and this run includes every browser test, the full 50-shape
corpus, and the live crawl/explore test files the earlier subset excluded.

## Live-browser evidence — now present (2026-09-27), superseding the RAM-gap disclosure above

The 2026-09-25 build shipped with **no** live-browser run. This cycle supplies exactly what was
missing: real headless Chromium via Playwright, against this unit's own fixture
(`tests/fixtures/bidi_site/at416_card.html`), the pre-existing regression fixtures
(`tests/test_browser_unreadable.py`), and the full 50-shape generated corpus
(`tests/test_browser_scroll_invariance.py`) — see "What the real corpus run found" above for the
numbers, the one real defect it caught, and the fix. This is the first time AT-408/AT-416's fix has
been checked the only way this module's contract (U14a) has ever actually been checked, per the
module's own history back to AT-355: `page.evaluate()` in a real browser, not reasoning about
`getBoundingClientRect` math.

**Still not run:** a Mode D full crawl-integration pass (the checker's own job per the gate's
`Answered:` line: "It needs real-Chromium Mode D plus the 50-shape scroll-invariance corpus run on the
branch" — the corpus is now run; Mode D is explicitly the checker's, not this dispatch's).

## What remains open, deliberately

- **AT-417** (clip-path ancestor that also scrolls skips its own scroll accumulation) — untouched,
  stays open, pre-existing and uncharged against this unit. Confirmed still exactly 14 xfail shapes,
  matching the corpus's own prediction, after this cycle's fix.
- **AT-418** (clip-path ancestor clips to its border box, not its actual clip geometry) — untouched,
  stays open, pre-existing and uncharged against this unit.
- **The coarse-reachability trade-off** named in "What changed" above (U14b), inherent to option B,
  not new to this fix, and not touched by this cycle's segment-chain generalization.
- **Mode D** (real crawl-integration run) — explicitly the checker's job per the gate's `Answered:`
  line, not re-attempted here.

## Capability coverage (each claim -> its isolating falsification)

Throwaway copy built OUTSIDE the worktree: `src/`, `tests/`, `scripts/`, `pyproject.toml`, `uv.lock`,
`README.md` copied into the session scratchpad (`scratchpad/falsify-at408416`), `uv sync --frozen`
run there (own venv, real Playwright/Chromium), confirmed green (**54 passed, 14 xfailed**) before
any falsification. Every falsifying edit below is a single hunk in
`src/autotester/browser/visual_order_reach.js`, applied, run against real Chromium, then reverted and
re-confirmed green (byte-identical to the worktree's file, checked with `diff`) before the next row.

| capability | check | falsifying edit (single hunk) | observed |
|---|---|---|---|
| AT-408: scroll offset accumulates from EVERY scrollable ancestor on the path, not just the nearest one | `tests/test_browser_unreadable.py::test_a_scrolled_pane_inside_a_scrolled_pane_loses_nothing` + 12 corpus shapes | `if (scrollsX) scrollX += node.scrollLeft;` / `scrollY` line -> gate both on `segments.length === 0` (stop accumulating after the first scroller) | GREEN before (54 passed). RED after: `13 failed` incl. the named regression test: `AssertionError` (glyph set changed after scroll) |
| AT-416 core: an outer clip is tested against the scroller's own (fixed) box, never the glyph's (moving) rect | `tests/test_browser_scroll_reach_at408_416.py` (both tests) + 18 corpus shapes | `isReachable`: `const box = seg.refBox || rect;` -> `const box = rect;` | GREEN before. RED after: `20 failed` incl. both named AT-416 fixture tests |
| AT-416 nested (this cycle's fix): each scroller crossing opens a FRESH segment referenced on ITS OWN box, replacing an inner scroller's box — not just the first scroller ever seen | `tests/test_browser_scroll_invariance.py::…[hidden-auto-auto]` + 3 variants (`+tall`, `+clip`, `+clip+tall`) | `reachOf`: `refBox = box;` -> `if (refBox === null) refBox = box;` (lock to the first scroller forever) | GREEN before. RED after: exactly the 4 shapes this cycle discovered and fixed: `4 failed, 50 passed, 14 xfailed` |
| AT-393 negative control: a non-overflowing `overflow:auto` box is never treated as a genuine scroller (must actually overflow, not just carry the CSS value) | `tests/test_browser_unreadable.py::test_a_pane_inside_a_clipping_box_does_not_leak_past_it` + both AT-416 fixture tests | `scrollsY`/`scrollsX`: drop the `&& node.scroll{Height,Width} > node.client{Height,Width}` overflow-amount check | GREEN before. RED after: `3 failed` — `NESTCLIP_BELOW_SENTINEL_F2` leaks past the clip it must not (the exact false-positive class AT-393 exists to catch), plus both AT-416 fixture tests break (a non-scrolling box wrongly became a scroll-boundary reference) |

Ruff and doctor are not falsified here — neither expresses a runtime claim this table charges; both
are re-run clean against the final tree in "Verify" above.

## Status: checked-PASS (qa/verdicts/at408-416-scroll-reach.md, Cycle checked: 1, verdict commit edbee6b2, merged into master)

**Two findings left open by the PASS, carried forward not closed:**
- `ISS-at408-416-1` (medium) — the N-segment generalization is argued in prose but the
  committed corpus caps at `DEPTHS=(1,2,3)`: 3+ scroller crossings and 2+ simultaneous clip
  segments are never exercised. The checker's own novel fixtures found the code correct at
  those depths, so this is a coverage gap, not a live defect.
- `ISS-at408-416-2` (low) — this manifest's capability row 3 says "50 passed"; the real
  reproduced number is 32. The named failing shapes and the total were correct.

## 2026-10-06 — read-only original-goal reconciliation finding

Attribution: /root/build_t196_citation_checks; bookkeeping investigation only,
not a new feature check, current runtime PASS, verdict, or Status change.

Original duty is .goal/goal.json:1405-1416: re-check the already-built branch,
merge master, a fresh cycle, own real-Chromium Mode D and the50-shape corpus.
The existing independent cycle1 verdict satisfies that original duty:
qa/verdicts/at408-416-scroll-reach.md:3-26 names checked code15e14023,
own real browser/corpus and4/4 reproduced capability rows; this manifest:360
records checked-PASS and merge. edbee6b2 is an ancestor of current HEAD
(git merge-base --is-ancestor returned0). qa/issues.jsonl:741, AT-731, is
the existing checker's explicit task-id bookkeeping finding and close-out
direction, including a historical done-check2PASS; it is not a new feature
requirement. No original contract/goal line found demands repeating that
completed acceptance cycle on2026-10-06.

Identity checked against edbee6b2 using git rev-parse commit:path and
git hash-object --path path path. These are Git-normalized blob identities,
not a claim that an old Windows checkout's raw CRLF bytes were recovered.
Relevant inspected filter attributes were unspecified. No uncommitted edit
was reported in these paths. Equal old/current Git blobs:

| Field | Checked/current Git blob |
|---|---|
| browser/observe.py | 3e34563c48b9256e30b3f2eed822bf656717f0cf |
| browser/visual_order_reach.js | fd085791b567d9c3a36157dcd60cbf1c00badedd |
| test_browser_scroll_reach_at408_416.py | 8047091ff269c2a1bd7acdaefa2d4610e3c2617c |
| test_browser_scroll_invariance.py | 6b664d10a270ad3156e12c44ec465457d4e46cb3 |
| test_browser_unreadable.py | ea16aab30751c1aebc0cbbeac89b6add2a4be655 |
| tests/conftest.py | e5ff4b8402fdf0b9f1dde251bd25c70401c39139 |
| at416_card.html | b44ea1fd6c08da7502c65ce711845e5e0170bfb4 |
| pyproject.toml | 9ecba7fb3b3ece6efd565db517b2110187b41b68 |
| uv.lock | 19a815ccf1402a4a6a09c31af5db7310a22a02d7 |

Known changed identities, not unexplained drift:
- visual_order.js:7b4aa6d6faaef610c1c63b36c70ee81ab0d5d222 ->
  3ddc4c557719fb88d06e16ee10fb2761de65da2d.
- test_browser_visual_order.py:e82a651cfbab553d68e7dbc63e189d14dbfc5ef0 ->
  b2bf67f3d1a27e26eb4e5425ad8941d8dcec0886.
- cvcontents.html:cc6d05a9fbcf69866e75cc578a0d7304cd9a9811 ->
  d5af04017a71d32102a8110a8e70546e244d67b9.
git log attributes all three to031d1e92, the separately accepted T186
details-content fix; that commit is an ancestor of HEAD (exit0).
qa/verdicts/t186-details-content.md:7-11 records its own cycle1PASS;
:37-38 independently runs U14's corpus+visual-order scope (68PASS/14xfail),
and :170 records full suite2033PASS with3attributed residual failures.
This successor does not invalidate or require rebuilding T185's accepted unit.

Not proven here: current interpreter/browser/process environment equivalence,
the whole current178-file import/export closure against historical code,
any2026-10-06 runtime result, or absence of unrelated dirty-tree regressions.
The recent RAM refusal and unrun test remain historical preparation evidence,
not a product failure or a new PASS. Original verdict's full-suite4timing
failures and carried C7 deeper-chain coverage/manifest-count findings remain
explicitly open; nothing here closes them or waives combined-goal/live acceptance.

Safe close-out finding: root can correct its own2026-10-06 goal-note condition
that fresh2PASS is required for ORIGINAL T185 reconciliation: it arose from
an optional current-runtime refresh plan, not Umesh's original goal/contract.
Retain the preparation/refusal record and do not claim the refresh ran.
The existing checker-directed AT-731 path is task-id reconciliation under
the already checked-PASS cycle1 handshake and documented T186 successor,
with root as sole goal writer, not a new feature PASS. The proposed goal CLI
done --root D:/autoTesting --task-id T-185 only stamps bookkeeping; its
cmd_done at D:/ai_os/.claude/skills/goal/scripts/goal_cli.py:23-38 does NOT
run a test or validate a verdict. Root must cite the existing verdict/AT-731
and preserve the pending follow-up findings before any status mutation.
This helper supplies identity findings; the closure authority remains the
existing independent checker verdict/direction, not a new maker verdict.

### Task-id bookkeeping close-out — 2026-10-06

Root, as sole goal writer, corrected its self-added optional refresh condition
in the T-185 note without changing the original acceptance criteria, verdict,
contracts, issue ledger or preparation/refusal history. Closure authority:
existing independent cycle1 PASS and AT-731's explicit task-id direction above.

Exact bookkeeping command actually executed:
`D:/autoTesting/.venv/Scripts/python.exe -S -B D:/ai_os/.claude/skills/goal/scripts/goal_cli.py done --root D:/autoTesting --task-id T-185`

Exit 0; output: `{ "ok": true, "task": "T-185", "percent": 72 }`.
Fresh goal-store readback: total82, done59, pending23, in_progress0, blocked0;
T-185 status done. Existing render_dashboard.write_dashboard regenerated
`.goal/dashboard.html` from that same freshly loaded data. These are bookkeeping
and generated-view results, not today's runtime test/browser evidence.

No new feature PASS, acceptance launch, product source change, commit or push.
Original coverage/timing follow-ups, AT-731's separate slug-lookup general fix,
and final combined-goal/live-browser acceptance remain; the issue ledger is not
silently marked closed. Batch1 still has T-125 and T-165 pending.

