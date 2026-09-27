# at438 cycle-3 re-derivation notes (checker, 2026-09-26)

**Bound root:** `D:/autoTesting` · read-only toward `src/` and `tests/` (verified: no diff in the
working tree from this run) · **Chromium 151.0.7922.34** (real headed instance, `headless=False`,
launched from the repo venv `.venv/Scripts/python.exe`, same Playwright the product uses).

## Corpus

Recovered, not rebuilt from scratch: the cycle-3 checker's own
`qa/evidence/browser-at438-display-contents-2026-09-16-checker-c3/moded3.py` (60-layout table,
"cycle-1 layouts (regression floor)" + "point 1 attacks" + "point 3: dead-branch deletion", 60
`CASES` rows) and `attack3.py` (point-2 attacks on the NEW mechanisms, `ATTACKS`). I copied the
page-construction code (`CASES`, the shadow/attack helper functions, the ground-truth method)
verbatim into my own driver — 60 layout rows + 10 of the attack rows most relevant to U14(b)/AT-453/
AT-454 (A3, A4, A5, A6, A7, A1, A2, D4, D5, D7) = **70 rows total**. Ground truth per row: replace
the sentinel text node with same-length monospace glyphs and hash a full-page screenshot
before/after (identical method to moded3.py/attack3.py — never `color:transparent`, a real render
diff).

## Detector versions (extracted via `git show`, never touching the working tree)

| tag | commit | role |
|---|---|---|
| OLD | `c687b73^` | pre-AT-438, the true pre-unit baseline per the answered gate `qa/gates/at438-u14b-baseline.md` (a) |
| C3 | `9fc937d` | cycle 3, the unit's final committed detector |
| MASTER | `HEAD` (`f9b81f9`) | current master |

**C3 and MASTER `visual_order.js` text are byte-identical** (`diff` clean; also asserted inside the
driver). `git log --oneline -- src/autotester/browser/visual_order.js` shows `9fc937d` is still the
most recent commit touching the file — nothing has changed it since. So every C3 answer below is
also the MASTER answer, by direct measurement, not inference.

Injection matches the product exactly: `src/autotester/browser/observe.py` does
`page.evaluate(_VISUAL_ORDER_JS)` where `_VISUAL_ORDER_JS` is the raw file text (an IIFE
expression) — the driver does the same `page.evaluate(js)` per version.

## (i) U14(b): texts OLD reports that C3/MASTER does not

**Zero.** `u14b_old_yes_c3_no = []` and `u14b_old_yes_master_no = []` (`summary.json`). No layout
or attack row has OLD `reported=True` and C3 (or MASTER) `reported=False`. **No U14(b) violation
against either the pre-unit baseline or MASTER**, over the full 70-row corpus, live in a real
headed browser.

## (ii) FN / FP counts per detector (70 rows: 60 layout + 10 attack)

| detector | FN | FP |
|---|---|---|
| OLD (`c687b73^`) | 26 | 0 |
| C3 (`9fc937d`) | 2 | 6 |
| MASTER (`HEAD`) | 2 | 6 |

C3 and MASTER are identical on every row (expected, since the file is unchanged). Net: the unit
traded 24 false negatives for 6 false positives, which is the direction U14(b)'s tie-break accepts.

**The 2 FNs on C3/MASTER** — both AT-453, both also FN on OLD (so not new, not a U14(b) hit):
- `A3 closed, ::details-content{display:contents}`
- `A4 closed, ::details-content{display:inline}`

**The 6 FPs on C3/MASTER** — all pre-existing/disclosed classes, `ok` on OLD:
- `flex container contain:paint height:0`
- `grid container contain:paint height:0`
- `flex container clip-path hides all`
- `D4 slot->slot, inner CLOSED-mode shadow, slot in closed details`
- `D5 closed-mode shadow, slot inside CLOSED details`
- `D7 closed-mode shadow, slot inside cv:hidden div`

The first three match `qa/issues.jsonl` AT-451 ("text inside a zero-height `contain:paint` box …
pre-existing … reported=true painted=false"; open, filed 2026-09-16, explicitly "not caused by
at438" and predates it). The `clip-path` row is the same `contain:paint` family (same box also has
`clip-path:inset(0 0 100% 0)`) and was not previously singled out by name, but it is the same
paint-containment gap, not a new mechanism — flagged here for completeness, not raised as a new
issue. The three D-rows are AT-454 (closed-shadow `assignedSlot`), gated (c) at
`at438-u14b-baseline.md` as an accepted disclosed FP class.

## (iii) Is AT-438's own defect fixed on C3? On MASTER?

**Yes, on both.** AT-438 is "visible text directly inside a `display:contents` element is not
reported." Every plain `display:contents` layout in the 60-row table (`"plain contents"`, nested
`display:contents`, inside `<ul>`, inside a `<fieldset>` legend, inside a table row/cell, slotted
through an *open* shadow root, etc.) is `ok` on both C3 and MASTER — 0 FN among them, and the two
remaining FNs are the distinct AT-453 mechanism (a `::details-content` pseudo-element display
override), not the base AT-438 case.

## (iv) Do AT-453 and AT-454 still reproduce on MASTER?

**AT-453 — yes, still reproduces on MASTER.** `A3` and `A4` above: screenshot ground truth says
`painted=True` (the text is visibly on screen — see
`layoutA3-details-content-display-contents.png`), computed `::details-content` has
`contentVisibility:'hidden'` while `display` is `'contents'`/`'inline'` (content-visibility does
not apply to those displays, so the browser paints anyway), and MASTER reports `FALSE_NEGATIVE` on
both — identical to the cycle-3 checker's `report_attack3.json`. `fixdir3.py`'s measured candidate
(`cv === "hidden" && HIDES_ON.test(pseudo.display)`) was never merged into `visual_order.js`
(confirmed: `OLDL` string from `fixdir3.py` — `window.getComputedStyle(box, "::details-content")
.contentVisibility === "hidden") return false;` — is still present, unchanged, in the MASTER file
text extracted for this run).

**AT-454 — yes, still reproduces on MASTER.** `D4`, `D5`, `D7` above: screenshot ground truth says
`painted=False` (text does not render — closed shadow root swallows the slot), MASTER reports
`FALSE_POSITIVE` on all three, identical to cycle 3's `report_attack3.json` D4/D5/D7. This is the
gated (c) disclosed class, not charged against U14(b) (false positive, not false negative).

## Confidence

**High.** All three checks that would catch a close call did:
- Write-freedom: `mutations` empty for every one of the 210 (70 rows × 3 versions) evaluations —
  the detector never touched the DOM.
- Console errors: 0 across all 210 evaluations.
- Positive control (`POSCTRL_OK`) and ground-truth ("does it actually paint") are independent of
  which detector is under test — the screenshot hash never depends on `visual_order.js`.

The corpus is the checker's own from cycle 3, not narrowed or hand-picked; I added the three
`contain:paint`/`clip-path` FPs to the record even though nothing in the task required it, because
they are true positive-control-passing FALSE_POSITIVE rows on C3/MASTER that were not individually
named as AT-451/AT-454 before (the clip-path one specifically). Nothing here is rounded in the
unit's favor: AT-453 and AT-454 are both reported as still-open defects on MASTER, exactly as
`qa/issues.jsonl` already has them (`status: "open"` for both).

## Files in this directory
- `driver.py` — the driver script run (copy)
- `report.json` — full per-row detector output (all 70 rows × 3 versions)
- `summary.json` — FN/FP counts + the two U14(b) diff lists
- `layout01-plain-contents.png`, `layout43-details-content-visible.png`,
  `layoutA3-details-content-display-contents.png` — 3 representative layouts, screenshotted from
  MASTER's page
