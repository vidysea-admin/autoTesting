# Verdict — at438-display-contents

**Checker:** /checker Mode A + Mode D (fresh subagent, bound to `D:/autoTesting`)
**Date:** 2026-09-16
**Manifest:** `qa/manifests/at438-display-contents.md` (Status: ready-for-check, Fix cycle: 1)
**Cycle checked: 1**
**Code under check:** commit `c687b73` (the maker committed the unit before this verdict; the tree's `visual_order.js` equals that commit)

```
VERDICT: FAIL
SCOREBOARD: 0/1 criteria met (U13 detector port), 2/2 invariants hold (C2, C7)
FAILURES:
- [U13] sev: high · the probe <span> restarts author CSS animations keyed on :last-child / :has(), so VISIBLE text outside the display:contents element is dropped and the real page visibly changes; the old detector (c687b73^) saw that text · answer "is this contents element rendered?" without inserting a node an author selector can match, and pin an animated :last-child / :has() neighbour in the fixture · issue: AT-442
CAPABILITY-COVERAGE: 3/3 rows reproduced
LIVE-BROWSER: qa/evidence/browser-at438-display-contents-2026-09-16-checker/report.json
ISSUES-WRITTEN: AT-442, AT-443, AT-444, AT-445
EXPLANATION: The base fix works and the rejected walk-up candidate really leaks closed <details> and cv:hidden text, but "observing the page leaves it unchanged" is false. The probe adds a child to author DOM, and a forced style recalc turns that into a restarted animation. That drops visible text the previous detector reported, the false-negative-for-false-negative trade this module keeps making. innerHTML is byte-identical throughout, so the unit's own DOM assertion cannot see it.
```

## What I re-ran myself (bound tree, read-only)

| command | result |
|---|---|
| `uv run pytest` (bare) | `1312 passed, 2 skipped, 32 xfailed, 1 warning in 306.90s`. 0 failed. 32 xfailed matches the manifest. The count is higher than the manifest's 1296 because the other loop added tests to the shared tree |
| `uv run ruff check src tests scripts` | `All checks passed!` |
| `uv run autotester doctor` | `doctor: clean` |
| `wc -l` | `visual_order.js` **300** (at the cap), `tests/test_browser_visual_order.py` 282 |
| `scripts/mutation_check.py` for at438 / at429 / at358 / at410 / at379 / at423 | `3/3`, `4/4`, `21/21`, `1/1`, `7/7`, `3/3`. No SURVIVED, no anchor-count refusal |

## Capability coverage (step 4b): reproduced in a throwaway copy

Copy: `src tests scripts pyproject.toml` tarred to the scratchpad, outside the bound root. **Proof that the copy tests its own code:** inside pytest in the copy, `autotester.browser.observe.__file__` resolves to `...scratchpad\copy\src\autotester\browser\observe.py`, not to `D:\autoTesting\src`. The runs also set `PYTHONPATH=<copy>/src`. Each edit was applied from the manifest's `mutations.json` (anchor count == 1, file changed).

| row | before (copy, unedited) | after edit | assertion that fired |
|---|---|---|---|
| 1 drop `&& !contentsRenders(el)` | `2 passed` (T1 + `[contents]`) | `2 failed` | `assert 'CONTENTS_PLAIN_S1' in ...` and `contents paints but was dropped` (the named reporting assertions) |
| 2 walk-up candidate | `2 passed` | `1 failed` | `assert 'CONTENTS_CLOSEDDETAILS_S3' not in ...`. The seen string also contained `CONTENTS_CVHIDDEN_S4` |
| 3 probe never removed | `2 passed` | `1 failed` | `assert page.evaluate("() => document.body.innerHTML") == before` |

Every cell is a single-hunk edit to `src/autotester/browser/visual_order.js`, a file listed under "What changed". I found no inadmissible cell.

## Judged points

**1. False positives from the fix. None found** (`report.json` → `hiding_and_visible_contexts`). The ground truth is a full-page screenshot hash taken before and after replacing the sentinel text node with glyphs of the same length in a monospace font. This avoids the `color:transparent` method. Each page has a positive control (seen on every page) and 0 console errors. Every case below was correctly dropped:
- closed `<details>`, and closed `<details>` with `contents` nested twice
- a `content-visibility:hidden` block
- `display:none` and the `hidden` attribute
- `hidden="until-found"`
- a `visibility:hidden` ancestor, and a `contents` element that is itself `visibility:hidden`
- an `opacity:0` ancestor
- zero-alpha colour on an ancestor and on the `contents` element itself
- an `overflow:hidden` clip
- an off-screen absolute container
- `text-indent:-9999px`
- a closed `<dialog>`
- an unslotted light child of a shadow host

These were correctly reported: plain, open details, a slotted child, inside `<ul>`, and inside `<tr>`.

Two rows that looked wrong were not caused by this unit:
- **`clip-path`:** the old detector gives the same result with a plain div. This is AT-418, which already exists.
- **`cv:auto` far below the fold:** the screenshot method cannot see it. The text is reachable by scrolling, so reporting it is the intended behaviour.

**2. Writes to author DOM**
- **`innerHTML`:** unchanged in all 28 layouts. **Confirmed.**
- **MutationObserver:** on `document.body` with subtree, childList, attributes and characterData, it records exactly `childList #c added [SPAN]` followed by `childList #c removed [SPAN]`, and nothing else. **The disclosure is accurate.**
- **`:last-child` / `:has()` recalc: FAILS (AT-442).** The recalc forced while the probe is present does not change a sibling's *measured rect*, because the probe is gone before any glyph is measured. But it cancels an animation that depends on the selector, and removing the probe starts a **new** one at `currentTime 0`. Measured against the parent commit on identical pages:
  - `:last-child` animation: old `POSCTRL_OKSIBLING_ANIM` (animation 2950→3000); new `POSCTRL_OKSENTZQ_KEY` (3017→**0**). The after-screenshot shows `SIBLING_ANIM` gone from the actual page.
  - `:has()` animation on a `<p>` **outside** the contents element: old sees `HAS_TARGET`, new drops it (2983→0).
  - Control page with the same CSS but no `display:contents`: no restart, and both detectors see the text.
  - A 20 s `opacity` transition on `:not(:last-child)` did **not** fire (`getAnimations()` empty, opacity 1, text seen).
- **Parents `<table>/<tr>`, `<ul>`, `<select>`:** no structural failure. In `<tr>` and `<ul>` the text paints and is reported. In `<select>` it does not paint and is not reported. All agree with the screenshot.
- **`appendChild` throws (AT-445, low):** there is no DOM-level restriction that makes `appendChild` throw on an element parent. A page override does: `c.appendChild = () => {throw}` makes the whole `visual_text` evaluate throw, and the positive control is lost with it. A no-op `Element.prototype.remove` leaves `<span></span>` in `#c`. The `try` starts after `appendChild`.
- **Also found (AT-443, medium):** author CSS that matches the probe hides it, while the real text stays visible (screenshot). Three rules do this: `span:empty{display:none}`, `*:empty{display:none}` and `#c>span{display:none}`. The result is the AT-438 false negative again.
- **Also found (AT-444, low):** a `contents` element with `opacity:0` still paints its text, but old and new code both drop it through `effectiveOpacity`. This is pre-existing.

**3. The rejected candidate.** Row 2 reproduced in the copy. With the walk-up version, the seen string contains **both** `CONTENTS_CLOSEDDETAILS_S3` and `CONTENTS_CVHIDDEN_S4`. My Mode D run confirms by screenshot that neither of those paints. The choice of the probe over the walk-up rests on measurement.

**4. Line cap.** 300 lines by `wc -l` (was 298 at `c687b73^`). The `reachOf` function, and the whole block from its leading comment to `function isReachable`, is **byte-identical** to `c687b73^` (`diff` empty). What the shortened comments keep:
- **AT-374:** keeps "SVG text IS reported, by accident", "nothing pins it, so it is not claimed", and "listing it as unseen was false". It drops the rationale that a false entry in a limits block is worse than none. That rationale is not a defect guard.
- **checkVisibility note:** keeps "DEFAULT options on purpose", "opacity/visibility flags would subsume the rules below", and "a rule another rule covers cannot be falsified (C7)". It drops the literal option names `{opacityProperty, visibilityProperty}`, which is a small loss of searchability but no loss of fact.

**5. Repointed neighbour specs.** `git show c687b73` shows exactly one changed line in each spec, the `old` anchor (`...&& !contentsRenders(el)) return false;`). Names, `kills` and bodies (`if (false) return false;`) are unchanged. The unit removes no identifier; it only adds `contentsRenders`. So no body can reference a missing name. Both specs re-ran clean (at429 `4/4`, at358 `21/21`), and neither raised an anchor-count error.

## Contract judgement

- **U13 (the positive rendering detector, AT-358 port): NOT MET.** The unit fixes AT-438's layouts. It also makes the detector drop text that the previous commit reported, and it changes the rendered state of the page it observes (AT-442). For a detector whose ranked-worse error is a missed credential, that is a regression in the direction this unit set out to fix.
- **C2: holds.** Doctor is clean, the JS is counted by hand at 300, and the test file has 282 lines.
- **C7: holds.** The mutation harness asserted anchor count and file change. I reproduced all three rows independently in a proven copy, and the named assertions fired.

**Issues addressed:** AT-438 **stays open**. The base case is fixed but the unit does not PASS.

**Open question (not a failure):** the unit's code was committed as `c687b73` before any checker verdict existed. The project's own flow commits after a PASS. The next sweep should decide whether that counts as a bypass.


---

# Cycle checked: 2

**Checker:** /checker Mode A + Mode D (fresh subagent, bound to `D:/autoTesting`)
**Date:** 2026-09-16
**Manifest:** `qa/manifests/at438-display-contents.md` (Status: ready-for-check, Fix cycle: 2)
**Code under check:** commit `ba30b71`. The maker committed it before a verdict again. `git diff HEAD` is empty for `visual_order.js`, the test and the fixture.
**Criteria applied:** U14 of `qa/contracts/ui.md`, plus C2 and C7. U14 was added in `b90a695` at 18:15:50, before this cycle was submitted in `ba30b71` at 18:18:27, so its scope-in-time clause charges it. The dispatch named U13. U14 is the detector's own acceptance line and replaces the per-verdict U13 charge that cycle 1 used.

```
VERDICT: FAIL
SCOREBOARD: 0/1 criteria met (U14: (a) holds, (b) fails, (c) respected), 2/2 invariants hold (C2, C7)
FAILURES:
- [U14(b)] sev: medium · the walk decides a closed <details> by tag (DETAILS && !open) instead of by what actually hides the body, so an author details::details-content{content-visibility:visible} (a responsive accordion expanded on desktop) paints display:contents text that visual_text drops; the cycle-1 probe reported it · read getComputedStyle(box, '::details-content').contentVisibility (measured: matches the screenshot for closed, open, the author override and details{display:contents}) and walk the flat tree via assignedSlot, with fixture rows for both · issue: AT-449
CAPABILITY-COVERAGE: 5/5 rows reproduced
LIVE-BROWSER: qa/evidence/browser-at438-display-contents-2026-09-16-checker-c2/report.json
ISSUES-WRITTEN: AT-449, AT-450, AT-451
EXPLANATION: The write-free claim is true. Across 67 pages there were zero MutationObserver records and no animation clock went backwards, and all three sabotage overrides are harmless. AT-442, AT-443 and AT-445 no longer reproduce. But the walk has swapped one enumeration for another. Its claim that the nearest box covers everything above it holds only for the light tree and an unmodified <details>. Against the cycle-1 probe it loses one visible-text case (AT-449, charged) and gains four false positives (AT-450, filed low under the U14(b) tie-break).
```

## What I re-ran myself (bound tree, read-only)

| command | result |
|---|---|
| `uv run pytest` (bare) | `1316 passed, 2 skipped, 32 xfailed, 1 warning in 297.94s`. Matches the manifest |
| `uv run pytest` (bare, second run, loaded by 8 concurrent single-test runs) | `1316 passed, 2 skipped, 32 xfailed, 1 warning in 451.37s` |
| `uv run ruff check src tests scripts` | `All checks passed!` |
| `uv run autotester doctor` | `doctor: clean` |
| `wc -l` | `visual_order.js` **298**. `tests/test_browser_visual_order.py` **294**, not the manifest's 289, and still under the cap |
| `scripts/mutation_check.py`: at438 / at429 / at358 / at410 / at379 / at423 | `5/5`, `4/4`, `21/21`, `1/1`, `7/7`, `3/3`. The harness mutates a copy outside the repo (`mutation_check.py:135`) |
| U14 verify: `pytest tests/test_browser_scroll_invariance.py tests/test_browser_visual_order.py` | `50 passed, 32 xfailed`. Every xfail is `strict=True` (`test_browser_scroll_invariance.py:209`), and each reason is AT-416 (18), AT-417 (12) or AT-416 + AT-417 (2). All three are classes listed in U14(c) |

## Capability coverage (step 4b): reproduced in a throwaway copy

**The copy:** `src`, `tests`, `scripts`, `pyproject.toml` and `qa/evidence/at438-display-contents`, tarred into the scratchpad outside the bound root.

**Proof that the copy tests its own code:** a `-p pathproof` plugin prints `autotester.browser.observe.__file__` inside each pytest session. Every before run and every after run printed `...scratchpad\c2\copy\src\autotester\browser\observe.py`. `observe.py:17` loads `visual_order.js` from its own directory.

On every row the anchor count was 1 and the file changed. The scripts and raw output are `rows.py` and `rows.json` in the evidence directory.

| row | before (copy) | after | assertion that fired |
|---|---|---|---|
| 1 drop `&& !contentsRenders(el)` | 2 passed | 2 failed | `assert 'CONTENTS_PLAIN_S1' in ...` and `contents paints but was dropped` |
| 2 remove the DETAILS check | 1 passed | 1 failed | `assert 'CONTENTS_CLOSEDDETAILS_S3' not in ...` |
| 3 remove the content-visibility check | 1 passed | 1 failed | `assert 'CONTENTS_CVHIDDEN_S4' not in ...` |
| 4 cycle-1 probe `<span>` | 1 passed | 1 failed | `assert 'CONTENTS_PLAIN_S1' in 'Quarterly report for the trainers listopenclosed'` |
| 5 non-empty probe `<i>` | 1 passed | 1 failed | `assert 'LASTCHILD_SIBLING_S7' in '...CONTENTS_PLAIN_S1openCONTENTS_OPENDETAILS_S2closedCONTENTS_ANIMATED_S6'` |

**Rows 4 and 5 are admissible.** Each replaces the contiguous two-line loop header with a probe followed by that same header. That is one hunk in one file named under "What changed". The loop is unreachable after the `try/finally` return, which is the point: the probe answers instead of the walk.

**Row isolation (point 4).**
- **Row 5:** `CONTENTS_PLAIN_S1`, `S2` and `S6` are all present and only `S7` is missing. The failure is the sibling assertion, not row 4's defect.
- **Row 4:** the `:empty` mechanism is confirmed in the Mode D run. The probe drops the text on the page with the `:empty` rules (`:empty rules + contents`) and reports it on the same page without them (`plain contents`).

**The clock assertion (point 5).** `clock.py` ran these in the copy. The test was copied and edited there only.
- **Unmutated:** passes.
- **Row 5 applied, with `LASTCHILD_SIBLING_S7` removed from the test's `shown` tuple:** fails on the clock assertion itself, `AssertionError: ([416.719...], [0])`. So `before` is non-empty when the call is made, and a restart reddens the assertion on its own.
- **Under load:** 8 consecutive runs of the named test while a full suite ran concurrently: 8 passed (1.71–1.98 s).
- **Residual flake risk (not a failure):** `wait_for_timeout(400)` only bounds how far the clock has advanced. If a loaded browser samples `before` while the animation is still pending at `currentTime 0`, then `0 >= 0` passes and that run is blind to a restart. This lowers sensitivity. It can never produce a false red.

## Mode D (own Chromium, own pages; `moded2.py`, `classify.py`)

Every page ran three detector versions: **OLD** = `c687b73^`, **PROBE** = `c687b73` (cycle 1), **NEW** = the bound tree.
- **Ground truth:** a full-page screenshot hash taken before and after replacing the sentinel text node with glyphs of the same length. `color:transparent` is never used.
- **Controls:** every page has a positive control, and all three versions saw it on every page. Console errors were 0 everywhere.
- **Scale:** 60 layouts, 7 side-effect pages, and the unit's own fixture.

**Point 2 (write-free): CONFIRMED.**
- **MutationObservers.** One observes `document` and one the contents element, with subtree, childList, attributes and characterData. They recorded **0** records for NEW on all 60 layouts, on all 7 side-effect pages and on the fixture. PROBE produced 4 per probed layout, which proves the observers work.
- **`:last-child` animation.** NEW goes 2517→2533 and `SIBLING_ANIM` is seen. PROBE goes 2533→**0** and drops it.
- **`:has(span)` and `:has(*)` elsewhere.** NEW does not restart the animation and sees `HAS_TARGET`. PROBE restarts it to 0 and drops the text.
- **`:empty` rules.** NEW reports the text. PROBE drops it.
- **Sabotage overrides.** The page made `appendChild` and `insertBefore` throw (on the instance and the prototype), made `remove` and `removeChild` no-ops, and made `createElement` throw. NEW reported the text with the control seen, no exception and outerHTML unchanged. PROBE either threw or left a node behind.
- **Fixture `cvcontents.html` (the before/after report count U14(b) asks for):**

  | version | glyphs reported | animation clock | notes |
  |---|---|---|---|
  | OLD | 68 | — | |
  | PROBE | 48 | 417 → 0 | |
  | NEW | 128 | 417 → 433 | `CONTENTS_PLAIN_S1`, `S2`, `S6` and `S7` all present; 0 mutation records |

- **Cycle-1 `anim.py` and `moded.py`, re-run against the committed file.**
  - `anim.py`: NEW sees `SIBLING_ANIM` and `HAS_TARGET`, and the clock advances.
  - `moded.py`: 25/28 correct, `dom=True` on all 28, and every side-effect row is clean. The three wrong rows are `clip-path` (AT-418), `cv:auto` far below (a limit of the screenshot method) and `opacity:0` on the contents element itself (AT-444). This matches the manifest.

**Point 1 (is the walk complete?): NO.**

These attack cases are correct in NEW:
- `<summary>` itself `display:contents` in a closed `<details>`, and a contents span inside it.
- `hidden="until-found"` on a block box (hidden) and on an inline span box (painted and reported).
- Open non-modal `<dialog>`, and a modal one.
- `<fieldset>`: the legend itself `display:contents`, contents inside the legend, and contents in the body.
- `<table>`: a `display:contents` `<tr>`, a `<td>`, and tbody plus tr.
- A `<slot style=display:contents>`, a slot inside a visible div, and the slotted child that must be reported.
- Every nested `<details>` combination:
  - closed > closed, with contents at L1, at L2 and in the inner summary
  - closed > open, at L2
  - open > closed, in the inner summary (painted and reported) and at L2
  - a contents wrapper three deep

Regressions against the cycle-1 probe (PROBE right, NEW wrong):
- **False negative, charged (AT-449).** `details::details-content{content-visibility:visible}` on a closed details. The text paints, and both NEW and OLD drop it.
- **False positives, filed low (AT-450).** Four hidden layouts are reported:
  - a second `<summary>`
  - a closed `<details style=display:contents>`
  - a child slotted into a closed `<details>` inside a shadow root
  - a child slotted into a `content-visibility:hidden` box inside a shadow root

  There are three causes. The `SUMMARY` test accepts any summary, not only the first. The `continue` on `display:contents` skips a details that still hides its body. `parentElement` climbs to the shadow host instead of the slot.

Both PROBE and NEW wrong (pre-existing):
- **AT-451.** A zero-height `contain:paint` flex or grid box. A plain div child is reported too (`classify.json`).
- **AT-418.** A flex box with `clip-path` belongs to that existing class.

Correct in NEW:
- A 0-size grid track with overflow visible: the text paints and is reported.

**The fix direction was measured.** `getComputedStyle(details, '::details-content').contentVisibility` is `hidden` for a closed details and for a closed `display:contents` details, and `visible` for an open one and for the author override. It matches the screenshot in all four (`classify.json`).

**Point 3 (the dead-branch deletion): CONFIRMED.**
- **Not painted and not reported by NEW:** a `display:contents` child of `<video>` (with and without controls), `<audio>` (with and without controls), `<canvas>`, `<iframe>`, `<object>` with SVG data, `<textarea>`, `<select>`, `<img>` and `<input>`. The width guard holds well beyond the maker's fixture.
- **Painted and reported by NEW:** the fallback of an `<object>` with no data, which does render.
- **Slotted child:** reported.
- **No false positive** was introduced by the deletion.

## Contract judgement

- **U14 (the positive rendering detector): NOT MET.**
  - **(a) holds.** The invariance file is green, with every xfail strict and named.
  - **(c) is respected.** Nothing is charged against AT-416, AT-417 or AT-440.
  - **(b) fails, judged against the parent commit.**
    - **The baseline question.** `c687b73` is the unit's parent on master. It reports the `::details-content` text, and `ba30b71` stops. Against `c687b73^` this would not be new, because OLD dropped every contents text. I judge against the parent commit, as the dispatch does ("any case the walk gets wrong where the cycle-1 probe got it right is a regression").
    - **Why charge it.** The author pattern is a documented one: disclosure content forced visible on wide screens. The fix is small and has been measured.
- **C2: holds.** Doctor is clean. `visual_order.js` is 298 lines counted by hand, and the test file is 294.
- **C7: holds.** All 5 rows were reproduced in a proven copy, each on its named assertion, with the anchor-count and file-change assertions in place.

**Issues addressed:** AT-438, AT-442, AT-443 and AT-445 **stay open**, because the unit does not PASS. On `ba30b71`, AT-442, AT-443 and AT-445 do **not** reproduce, and the plain AT-438 layouts are fixed.

**Manifest accuracy (observations, not failures):**
- The Capability coverage section still pastes cycle 1's `3/3` mutation output under a 5-row table.
- It gives the test file as 289 lines; it is 294.
- The unit was again committed (`ba30b71`) before any verdict. This is the same open question cycle 1 raised.


---

# Cycle checked: 3

**Checker:** /checker Mode A + Mode D (fresh subagent, bound to `D:/autoTesting`)
**Date:** 2026-09-16
**Manifest:** `qa/manifests/at438-display-contents.md` (Status: ready-for-check, Fix cycle: 3 of max 3)
**Code under check:** commit `9fc937d`. `git diff 9fc937d` is empty for `visual_order.js`, the fixture, the test and `qa/evidence/at438-display-contents/`. The maker committed before a verdict for the third time.
**Criteria applied:** U14 of `qa/contracts/ui.md` (the detector's acceptance line; U13 names the detector only as not covered), plus C2 and C7. **Baseline for U14(b):** the same one cycle 2 used and charged AT-449 under, the cycle-1 probe `c687b73`. A case that cycle 3 gets wrong where an earlier committed version of this unit got it right counts against the unit.

```
VERDICT: FAIL
SCOREBOARD: 0/1 criteria met (U14: (a) holds, (b) fails, (c) respected), 2/2 invariants hold (C2, C7)
FAILURES:
- [U14(b)] sev: medium · the <details> check reads ::details-content's computed content-visibility but not its display, so a CLOSED details whose author sets ::details-content{display:contents} or {display:inline} (content-visibility does not apply there, the body paints; screenshot A3.png/A4.png) drops visible display:contents text; the cycle-1 probe reports it, and on the same page a plain <p> or <span> child IS reported by cycle 3, so the detector contradicts itself · gate the details branch on the pseudo's display too, the same measured HIDES_ON rule the module already applies to boxes (`cv === "hidden" && HIDES_ON.test(pseudo.display)`), plus a fixture row that must be reported · issue: AT-453
CAPABILITY-COVERAGE: 9/9 rows reproduced
LIVE-BROWSER: qa/evidence/browser-at438-display-contents-2026-09-16-checker-c3/report.json
ISSUES-WRITTEN: AT-453, AT-454
EXPLANATION: The 57/60 table reproduces exactly on my own harness, the write-free claim holds on every page, and all nine mutation rows kill on their own assertion; rows 4-7 each fail on exactly S10, S11, S12 and S13. But "<details> is judged by what the browser actually applies" is still a proxy: computed content-visibility says `hidden` on a ::details-content that is display:contents or inline, where Chromium ignores it and paints the body, the AT-437 fact HIDES_ON already exists for. That is a false negative the cycle-1 probe did not have, the class U14(b) ranks first, and it is the same shape as AT-449, which was charged last cycle.
```

## What I re-ran myself (bound tree, read-only)

| command | result |
|---|---|
| `uv run pytest` (bare) | `1326 passed, 2 skipped, 32 xfailed, 1 warning in 421.97s`, 0 failed. The manifest says 1323; the other loop added tests to the shared tree |
| `uv run ruff check src tests scripts` | `All checks passed!` |
| `uv run autotester doctor` | `doctor: clean` |
| `wc -l` | `visual_order.js` **300** (working tree and `git show 9fc937d:` both). `tests/test_browser_visual_order.py` **295**, which matches the manifest |
| `scripts/mutation_check.py`: at438 / at429 / at358 / at410 / at379 / at423 | `9/9`, `4/4`, `21/21`, `1/1`, `7/7`, `3/3`. No SURVIVED rows and no anchor-count refusals |
| U14 verify: `pytest tests/test_browser_scroll_invariance.py tests/test_browser_visual_order.py -rx` | `50 passed, 32 xfailed`. Every xfail reason names AT-416 or AT-417 (0 of 32 name anything else), and the xfails are `strict=True` |

## Point 1: the 57/60 table, reproduced on my own harness

`moded3.py` is my cycle-2 `moded2.py` with exactly one change: a fourth version, `C2 = git show ba30b71:visual_order.js`. `diff --strip-trailing-cr` shows only that line, the docstring, the report labels and the print line. The 60 CASES are byte-identical. NEW is read from the bound tree. Chromium 151.0.7922.34. The positive control was seen by every version on every page, with 0 console errors.

| version | ok | false negatives | false positives |
|---|---|---|---|
| OLD `c687b73^` | 38/60 | 22 | 0 |
| PROBE `c687b73` | 55/60 | 2 | 3 |
| C2 `ba30b71` | 52/60 | 1 | 7 |
| **NEW `9fc937d`** | **57/60** | **0** | 3 |

**The counts match the manifest exactly.** From C2 to NEW exactly five rows change, all to `ok`: the AT-449 accordion (FN), plus the four AT-450 rows (second summary, slot in closed details in shadow, slot in cv:hidden in shadow, details itself display:contents). Nothing else moves.

**"No layout where cycle 3 is wrong and an earlier version is right" is not literally true, even on these 60.** NEW is wrong on three rows: flex `contain:paint`, grid `contain:paint` and flex `clip-path`. OLD gets all three right, because it dropped all `contents` text. They are false positives, pre-existing in PROBE and C2 (AT-451 and AT-418), and I do not charge them. The claim holds only against the two earlier *cycles*. On pages outside the 60 it fails against PROBE as well (point 2).

## Point 2: attacks on the new mechanisms (29 + 6 pages, same four versions, same ground truth)

**`::details-content` support is real in this Chromium.** `CSS.supports('selector(::details-content)')` is `true`. On a closed `<details>` with no author CSS (A1), the computed value is `hidden`, the body does not paint (screenshot `A1.png`), and every version drops the text. Open (A2) gives `visible` and the text paints. An unsupported pseudo does **not** silently return `"visible"`: `getComputedStyle(details, '::no-such-pseudo').contentVisibility` returns `""`. In a browser without support, that would make `=== "hidden"` false and leak closed-details text. That is a false positive, not a missed credential, and fixture row S3 would go red on it.

**Charged false negative (AT-453): the pseudo's `display` is not consulted.**

| page | painted (screenshot) | OLD | PROBE | C2 | NEW |
|---|---|---|---|---|---|
| A3 closed, `details::details-content{display:contents}` | **yes** (`A3.png`) | FN | ok | FN | **FN** |
| A4 closed, `details::details-content{display:inline}` | **yes** (`A4.png`) | FN | ok | FN | **FN** |
| F1 same CSS as A3, child is a plain `<p>` | yes | ok | ok | ok | **ok** |
| F2 same CSS as A3, child is a plain `<span>` | yes | ok | ok | ok | **ok** |
| F3 same CSS as A4, child is a plain `<p>` | yes | ok | ok | ok | **ok** |
| F6 closed, `::details-content{display:flow-root}` | no | ok | ok | ok | ok |

On A3 and A4, `getComputedStyle(details,'::details-content')` reports `contentVisibility: "hidden"` with `display: "contents"` / `"inline"`. `content-visibility` does not apply to those displays, so the body paints. `contentsRenders` returns false on `cv === "hidden"` alone. **This is the exact AT-437 fact that `HIDES_ON` exists for, one line below, and it is not applied to the pseudo.** F1 to F3 show the detector disagreeing with itself: on the identical page, the same visible body is reported when its child is a `<p>` and dropped when it is `display:contents`. F6 shows that a hiding display still hides, so the fix direction holds.

**Filed low (AT-454): closed-mode shadow roots.** `assignedSlot` is `null` for a node slotted into a `mode:"closed"` shadow root, so `flatParent` falls back to `parentElement` (the host) and never sees the hiding box inside.

| page | painted | OLD | PROBE | C2 | NEW |
|---|---|---|---|---|---|
| D4 slot into slot, inner **closed** shadow, slot in closed details | no | ok | ok | FP | **FP** |
| D5 **closed** shadow, slot inside closed details | no | ok | ok | FP | **FP** |
| D7 **closed** shadow, slot inside cv:hidden div | no | ok | ok | FP | **FP** |
| D6 **closed** shadow, slot inside visible div | yes | FN | ok | ok | ok |

These are the AT-450 shadow layouts in closed mode. They are false positives that PROBE got right, ranked below false negatives by U14(b), so they are filed and not charged.

**Correct in NEW (every row screenshot-grounded):**
- **A5 to A7:** open with `::details-content{display:none}` (hidden, dropped); closed with `::details-content{content-visibility:auto}` (painted, reported, which C2 missed); open with `[open]::details-content{content-visibility:hidden}` (hidden, dropped, which C2 leaked).
- **B1:** the first `<summary>` is removed by script, the `contents` summary becomes first, and the text paints and is reported. `:scope > summary` is evaluated live.
- **B2:** a summary inserted by script before a body `contents` element; hidden, dropped.
- **B3:** a new summary is prepended before the `contents` summary, which demotes it; hidden and dropped (C2 leaked it).
- **B4 and B5:** a `<summary>` nested in a `<div>` wrapper or in a `display:contents` wrapper; hidden, dropped.
- **B6:** a `contents` element placed before the first summary; hidden, dropped.
- **C1 and C2:** `name="x"` exclusive accordions, where opening one by script closes the other. The closed body is dropped and the open body is reported. Calling NEW left every `details.open` unchanged (`details_open_unchanged_by_NEW: true` on all 29 pages).
- **D1 to D3:** a light child slotted into a slot that is itself slotted into an inner (open) shadow's slot, where the inner slot is inside closed details (dropped; C2 leaked it), open details (reported), or a visible div (reported).
- **D8:** a host inside closed light-DOM details with `<slot>` at the shadow-root top. Dropped, via the `parentNode.host` step.
- **D9:** a slot inside the first summary; reported.
- **E1 to E5:** `hidden="until-found"` or `content-visibility:hidden` set on the `<details>` element itself, with the `contents` text in the body or in the summary, open or closed. All hidden, all dropped.

**Termination.** On all 29 attack pages I evaluated the committed `flatParent` (extracted from the file) from **every** node of every tree, including closed shadow roots whose references were stashed during setup. The walk ended in at most 9 steps (cap 1000, never reached) and threw 0 times. `contentsRenders` loops only via `flatParent`, so it terminates too. At the document root, `document.host` is `undefined`, which falls through to `null`.

## Point 3: write-free, re-run

- **MutationObservers** on `document` and on the contents element (subtree, childList, attributes, characterData): NEW recorded **0** across all 95 layout and attack pages, the 7 side-effect pages and the fixture. PROBE recorded 328 on the same pages, which proves the observers were live.
- **`:last-child` animation:** NEW 2533→2550 with `SIBLING_ANIM` seen. PROBE 2517→**0**, dropped.
- **`:has(span)` / `:has(*)` elsewhere:** NEW 2500→2517 and 2517→2533, with `HAS_TARGET` seen. PROBE restarts to 0 and drops it.
- **`:empty` rules:** NEW reports the text. PROBE drops it.
- **Sabotage** (`appendChild`/`insertBefore` throwing on the instance and prototype, `remove`/`removeChild` no-ops, `createElement` throwing): NEW saw the text and the control, raised no exception, and left `outerHTML` unchanged.
- **Fixture `cvcontents.html`:**

  | version | glyphs | clock | observer records |
  |---|---|---|---|
  | OLD | 78 | 417→450 | 0 |
  | PROBE | 58 | 400→**0** | 22 |
  | C2 | 217 | 433→450 | 0 |
  | NEW | 160 | 417→433 | 0 |

  NEW sees S1, S2, S6, S7 and S10, and none of S3, S4, S5, S8, S9, S11, S12 or S13.

## Capability coverage (step 4b): 9/9 reproduced in a throwaway copy

**The copy:** `src`, `tests`, `scripts`, `pyproject.toml` and `qa/evidence/at438-display-contents`, tarred into the scratchpad outside the bound root. `cmp` confirms its `visual_order.js` equals the bound tree's.

**Path proof:** a `-p pathproof` plugin printed `...scratchpad\c3\copy\src\autotester\browser\observe.py` in every before run and every after run (`PYTHONPATH=<copy>/src`).

**Every cell is admissible:** each is a single-hunk edit to `src/autotester/browser/visual_order.js`, a file listed under "What changed". Each row had anchor count 1 and the file changed. The copy was restored after each row and asserted byte-equal at the end. I also evaluated each mutated detector directly on the fixture and listed **every** sentinel it gets wrong, so row isolation is measured rather than read off the first assertion (`rows3.py`, `rows3.json`).

| row | before (copy) | after | first assertion that fired | every sentinel wrong on the fixture |
|---|---|---|---|---|
| 1 drop `&& !contentsRenders(el)` | 2 passed | 2 failed | `'CONTENTS_PLAIN_S1' in` | missing S1, S2, S6, S10 |
| 2 remove the details check | 1 passed | 1 failed | `'CONTENTS_CLOSEDDETAILS_S3' not in` | leaked S3, S11, S12, S13 |
| 3 final check `return true` | 1 passed | 1 failed | `'CONTENTS_CVHIDDEN_S4' not in` | leaked S4 |
| **4** back to `!box.open` (AT-449) | 1 passed | 1 failed | `'CONTENTS_ACCORDION_S10' in` | **missing S10 only** |
| **5** exempt every `SUMMARY` | 1 passed | 1 failed | `'CONTENTS_SECONDSUMMARY_S11' not in` | **leaked S11 only** |
| **6** skip `contents` first | 1 passed | 1 failed | `'CONTENTS_DETAILSCONTENTS_S12' not in` | **leaked S12 only** |
| **7** `flatParent` → `parentElement` | 1 passed | 1 failed | `'CONTENTS_SLOTINCLOSED_S13' not in` | **leaked S13 only** |
| 8 cycle-1 probe `<span>` | 1 passed | 1 failed | `'CONTENTS_PLAIN_S1' in` | missing S1, S2, S6, S7, S10 (the `:empty` rule hides the probe) |
| 9 non-empty probe `<i>` | 1 passed | 1 failed | `'LASTCHILD_SIBLING_S7' in` | missing S7 only |

**Rows 4 to 7 share one test, but each fails on its own sentinel, and on the fixture each mutation gets exactly that one sentinel wrong and nothing else.** No row rides on another row's defect.

**No row covers AT-453.** No fixture row has a `::details-content` whose display is `contents` or `inline`, and no mutation drops a display check, because there is none.

## Point 5: the line cap and the gated block

- **Line count:** `visual_order.js` has **300** lines.
- **Unchanged code after line 97:** relative to `c687b73`, the only hunks are `@@ -13,25 +13,16 @@`, `@@ -63,14 +54,26 @@` and `@@ -85,13 +88,10 @@`. Everything after line 97 of the new file is unchanged, including the whole `reachOf` block: its leading comment, `const SCROLLS` at line 106, `reachOf` at 124 and `isReachable` at 161. The extracted `const SCROLLS … function isReachable` span (56 lines) is **byte-identical** (`cmp`).
- **Facts kept in the `HIDES_ON` comment:**
  - checkVisibility misses text whose own **PARENT** is cv:hidden (AT-429);
  - computed style says `hidden` where Chromium paints (inline, ruby, table rows, `table`, `contents`: AT-437);
  - it is a **measured** allow-list;
  - the pointer to the ground-truth script, `at429 groundtruth.py`, which resolves uniquely to `qa/evidence/at429-content-visibility-hidden/groundtruth.py`;
  - an unmeasured display is reported, never a missed credential.
- **Facts dropped from that comment (observations, not failures):**
  - "the ancestor case is already checkVisibility's", although "own PARENT" implies it;
  - "hidden only hides on a box that takes containment";
  - "by screenshot diff";
  - the full path of the ground-truth script.

## Contract judgement

- **U14 (the positive rendering detector): NOT MET.**
  - **(a) holds.** The invariance file is green, and every xfail is strict and names a (c) class. Measured: `50 passed, 32 xfailed`.
  - **(c) is respected.** Nothing is charged against AT-416, AT-417, AT-440, AT-418 or AT-451.
  - **(b) fails on AT-453.** It is the same shape as the AT-449 charge last cycle: an author's `::details-content` rule makes a closed `<details>` paint its body. The cycle-1 probe reports that text; cycle 3 drops it. Measured by screenshot and confirmed visually.
    - **Why charge it rather than file it.** The unit's stated mechanism for this cycle is "judge `<details>` by what the browser actually applies". The module already records that computed `content-visibility` does not mean hidden on every display (AT-437), and the fix is one conjunct using the existing `HIDES_ON`.
    - **The unit is otherwise strong.** It has zero false negatives on the 60 layouts, it is write-free, and it has nine isolating mutations. Only this one mechanism leaks.
- **C2: holds.** Doctor is clean, `visual_order.js` is 300 lines by hand, and the test file is 295.
- **C7: holds.** All 9 rows were reproduced in a proven copy, each on its named assertion, with anchor-count and file-change assertions.

**Issues addressed:** AT-438, AT-442, AT-443, AT-445, AT-449 and AT-450 **stay open**, because the unit does not PASS.
- **Measured on `9fc937d`:** AT-442, AT-443 and AT-445 do not reproduce. The AT-449 accordion is reported. The four AT-450 layouts are dropped.
- **AT-450's closed-shadow variant** is the new AT-454.

**Manifest accuracy (observations):**
- "No layout where cycle 3 is wrong and an earlier version is right" is false against OLD on the three AT-451/AT-418 rows. It holds only against the earlier cycles, and only on the 60 layouts.
- The unit was again committed (`9fc937d`) before a verdict.

**This was the last fix cycle.** Under the protocol the maker flips the manifest to STALLED. The remaining defect is in AT-453, and its fix direction is measured. I ran the one-conjunct candidate (`cv === "hidden" && HIDES_ON.test(pseudo.display)`, in `fixdir3.py` / `report_fixdir3.json`) on 26 details-shaped pages: A1 to A7, B1 to B6, closed `::details-content{display:flow-root}` and `{display:grid}`, and every details row of the 60 layouts. It is correct on all 26, including A3 and A4, and it breaks nothing that NEW got right.

# Re-ruling of cycle 3 (2026-09-26, D-048 gate answer a+b+c, D-049)

**Cycle checked: 3 (re-ruled; no new manifest cycle)**

```
VERDICT: PASS (re-ruled; supersedes the cycle-3 FAIL above for U14(b) only)
SCOREBOARD: 1/1 criteria met (U14: (a) holds, (b) holds against the pre-unit detector c687b73^, (c) respected with AT-454 added), 2/2 invariants hold (C2, C7)
FAILURES: none
CAPABILITY-COVERAGE: 9/9 rows reproduced (cycle 3, unchanged)
LIVE-BROWSER: qa/evidence/browser-at438-rerule-2026-09-26-checker/ (headed Chromium 151, 70 layouts x 3 detectors, 0 console errors, 0 DOM mutations across 210 evaluations)
ISSUES-WRITTEN: none. AT-438/449/450 fixed (9fc937d is on master), AT-454 wontfix (U14(c)), AT-453 stays open as its own unit
EXECUTOR: maker builder (checker: claude-opus orchestrator + sonnet subagents)
EXPLANATION: Umesh answered qa/gates/at438-u14b-baseline.md with (a): U14(b) compares against the detector before the unit began, c687b73^, not the failed cycle-1 probe. The cycle-3 FAIL's only charge (AT-453, A3/A4) is a false negative that c687b73^ also has, so it is not a regression under that baseline. It stays open as its own capped unit (gate option b).
```

## Measurement (independent, real Chromium)

- Three detectors were extracted with `git show`: OLD `c687b73^`, C3 `9fc937d`, MASTER `HEAD`. C3 and MASTER `visual_order.js` are byte-identical.
- Texts OLD reports that C3/MASTER drop: **0**.
- False negatives / false positives over 70 rows: OLD 26/0, C3 2/6, MASTER 2/6. The 2 false negatives are AT-453 (A3 `::details-content{display:contents}`, A4 `{display:inline}`). The 6 false positives are AT-454 (D4, D5, D7, closed shadow) plus 3 from the already-filed AT-451 family.
- AT-438's own defect (display:contents text through a hiding ancestor) has 0 false negatives across every plain display:contents layout.
- An adversarial skeptic built 16+ more shapes: 5-level nested contents, mixed details/contents chains, multi-level open-shadow slot chains, runtime attribute removal, content-visibility:auto. It found no case where OLD caught painted text that C3 drops. Refuted: false.
