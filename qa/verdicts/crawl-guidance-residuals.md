# crawl-guidance-residuals - combined checker A (contract) + B (adversarial)

Cycle checked: 0
Source checked: branch `fix/crawl-guidance-residuals`, code/test commit `2e17d653` (cut from `feat/crawl-guidance` `e947c8f2`); delta judged: `git diff e947c8f2..2e17d653 -- src tests` (enumerate.js, explore_guidance_payload.py, tests/test_crawl_guidance_egress.py)
Contract: `qa/contracts/crawl-guidance.md` G3 (egress) and G5 (guidance-off byte identity). G12 HELD, not judged.
VERDICT: PASS
SCOREBOARD: N1, N2, N3, N5 all CLOSED. G3 holds for every residual shape; G5 holds. One new non-blocking regression (N7, hidden text in an `aria-labelledby` target) for the maker to take in one small commit; it is not an input value, a typed value or option text, so no G3 criterion fails.

Everything below was re-derived by running code. No real model call (fake provider only), no `.env` value read, nothing under `src/` or `tests/` edited. Reverts ran in memory (a string-edited copy of `enumerate.js` held in the probe process, a patched module attribute) or in a `git archive` scratch copy; never on disk in the worktree, never a stash. Probe scripts: scratchpad `gr/`.

## FINDINGS (F = must fix, N = non-blocking)

No F items.

### N1, N2, N3, N5 - CLOSED (own real-Chromium probes)
`gr/probe_res.py head`: the REAL `enumerate.js` in headless Chromium -> `ElementRef` -> `Guidance.order` -> captured prompt, 47 markup cases, each planted value a fresh random non-word string (`Q` + 11 chars of `bcdfghjklmnpqrstvwxz0123456789`, seed 77, different from the maker's seed 20261029), leak = full value or any 5-char slice in the prompt. `assert model.calls == 1` per case so a case that sends nothing proves nothing.
- N1 CLEAN: `<select><button>`, `appearance:base-select` + `<selectedcontent>`, `<option onclick>`, `<optgroup><option tabindex>`, `<datalist><option tabindex>` -> `<field:button>` / `<field:option>` / `<field:select>` (`enumerate.js:100`, `closest("select, datalist")`). A `<select multiple tabindex>` -> `<field:select>`.
- N2 CLEAN: `<label>` wrapping or `for=` a `role=combobox`, `role=textbox`, `contenteditable` (shallow and 4 levels deep), `role=slider`, `role=listbox>option`, a nested `<label>`, `<button aria-haspopup>`, `<datalist>`, `<textarea>`, a `<select>` inside a `<span>`: label is the caption only (`Field`, `Outer Inner`, `F`). Label whose only content is a field: `<field:text>`.
- N3 CLEAN: target holding a `<select>`, a listbox/option, a contenteditable, target that IS a listbox or combobox, target inside a `<select>`, chain A->B->C (only A's own text, no chain followed), a cycle (`input aria-labelledby=a`, `a aria-labelledby=input`; no hang, `Lbl`), two targets (`Lbl` + a listbox target contributes nothing).
- N5 CLEAN: `foo combobox`, `a b c textbox`, `foo<TAB>combobox`, `foo<LF>combobox`, `"  generic  LISTBOX "`, `x slider` -> `<field:combobox|textbox|listbox|slider>` (`explore_guidance_payload.py:71-74`).
- Shadow DOM and slots: a combobox in an open shadow root of a label / target is not walked (`createTreeWalker` does not enter shadow roots, `enumerate.js:106`), so nothing leaks; label stays `Name`. A slotted light-DOM combobox in a label is dropped (`Name`). `slot-in-target`: the planted value appears in the input's `name` key only (unchanged `nameOf`); `field_label` is `Name`, and `is_field` is true so `name` is never sent. iframe `srcdoc` text, `<template>` content: not in the label.
- `contenteditable` ancestor of the whole label: label empty -> `<field:text>` (safe direction).

### Falsification (the new tests and both halves are load-bearing)
Scratch `git archive HEAD` copies with one half reverted, `uv run`'s venv python, `PYTHONPATH` = scratch `src;tests`, `uv run pytest tests/test_crawl_guidance_egress.py -o addopts=`:
- `enumerate.js` from `e947c8f2`: `1 failed, 6 passed` (`test_residual_shapes_never_send_a_planted_value`).
- `explore_guidance_payload.py` from `e947c8f2`: `1 failed, 6 passed` (`test_a_role_fallback_list_is_read_token_by_token_for_an_old_stored_graph`).
In-memory mutations of the new JS (`probe_res.py mut-*`), each leaks the intended shapes: drop `closest("select, datalist")` -> 5 N1 shapes + `n2-label-datalist` + `n3-target-inside-select` leak; `textOutsideFields` returns plain `textContent` -> all N2 and N3 shapes leak; drop the `isFieldEl(p)` ancestor test in the walk -> same set. `revert-both` leaks N1/N2/N3 and all six N5 shapes.
Observation (non-blocking, N8): reverting only the JS half of N5 (`roles.some` -> `roles[0]`, `mut-roles`) leaks nothing, because the Python half `_field_role` catches the same element in the live path. The JS half of N5 is defense in depth and is not independently proven by any test; harmless.

### N7 (new, non-blocking) - hidden descendants of an `aria-labelledby` target now reach the label
`enumerate.js:104-115` (`textOutsideFields`) reads raw text nodes, not rendered text, and `:124` applies it to `aria-labelledby` targets that were previously read with `innerText` (hidden descendants excluded). Same probe, old (`revert-js`) vs new:
- NEW leaks, OLD clean: `<div id=t>Name <span style="display:none">V</span></div>`, `<span hidden>V</span>`, `<span style="visibility:hidden">V</span>`, a closed `<details>`, `<noscript>V</noscript>` inside the target -> label `Name Q...`.
- Unchanged vs old (old also leaked): `aria-hidden="true"`, `position:absolute;left:-9999px`, a fully hidden target, hidden text in a `<label>` (labels were already read via `textContent`).
Per the accname spec a referenced node's hidden descendants are excluded, so this is a regression against both the old behaviour and the spec; the maker disclosed the CSS-visibility change in the manifest "Known limits". Ruling: no G3 criterion fails (hidden page text is not an input value, a typed value, a shown value or option text, and the planted-value shapes N1/N2/N3/N5 are closed), so it does not block this PASS, but it is a new egress path of the same class the unit closes and costs a few lines. Fix direction: in the walk, skip a text node whose `parentElement.checkVisibility()` is false (with a fall back to keep when `checkVisibility` is absent), or read `innerText` of a clone with fields removed. Add a planted `display:none` / `hidden` shape to `SHAPES`. A later check needs only `gr/probe_res.py head` (expect no LEAK in the `hidden-*`, `vis-hidden-*`, `details-*`, `noscript-*` cases), the egress test file, doctor and ruff.

### N9 (new, non-blocking) - label quality: adjacent text nodes are joined with a space
`enumerate.js:115` `parts.join(" ")`. Plain labels all still give a useful non-empty label: `Work email`, `Password`, `Full name`, `Board`, `Board Name`, `Choose one`, `Term`, multi-line `Work\n email` -> `Work email`, a `display:none` label target `Hidden Lbl`, `Student Name` (13 real-label cases, 10 identical to the old output). Three differ cosmetically from `textContent`: `First<span>*</span>` -> `First *` (was `First*`), `<span>Date of</span><span>birth</span>` -> `Date of birth` (was `Date ofbirth`, an improvement), `Fi<b>rst</b> name` -> `Fi rst name` (was `First name`; only mid-word inline markup). Ranking-quality cost only, no safety effect.

### N10 (carried, pre-existing) - caption button inside a label
`<label>Class <button type=button>V</button><input></label>`: the button text is sent (old code identical). A plain `<button>` is a caption, not a field; ruled in cycle 3 (`.work/cg-verdict-b-c3.md`, "Role `button`..."). Not changed by this unit.

## G5 - guidance-off byte identity
- `gr/keydiff.py`: the old (`e947c8f2`) and new `enumerate.js` run on 127 pages (all 47 attack cases, 13 real-label cases, every `tests/fixtures/**/*.html`): ZERO differences in any key other than `field_label` (`role, name, selector, enabled, visible, obscured, href, is_form_submit, in_row, target_blank, tag, type`). The only field-ness changes (`field_label` null -> non-null) are the 11 intended shapes (N1 select contents, N5 fallback roles). `name` and `selector` are untouched, so persisted `ElementRef`s are unchanged; `test_the_label_field_is_not_persisted_so_crawl_artifacts_stay_byte_identical` passes.
- Guidance-off crawl byte-identity (seam baseline tests `tests/test_crawl_guidance_seam.py`, `tests/test_crawl_guidance_core.py`): `47 passed`.
- Perf: `enumerate.js` old vs new on 3000 labelled inputs 1093 ms vs 933 ms, 3000 `<option>`s 5 vs 4 ms, 2000 tabindex divs 382 vs 488 ms, a 20000-node labelledby target 41 vs 48 ms (the `closest()` per element is cheap).

## COMMANDS (from `D:/autoTesting/.claude/worktrees/guidance-residuals`, 2 test files per pytest call, `-o addopts=`)
```
uv run python gr/probe_res.py head | revert-js | revert-py | revert-both | mut-closest | mut-roles | mut-tof | mut-tofwalk
uv run python gr/keydiff.py ; uv run python gr/perf.py ; uv run python gr/shadow.py
git archive HEAD (x2) + old enumerate.js / explore_guidance_payload.py from e947c8f2 ; pytest tests/test_crawl_guidance_egress.py   -> 1 failed, 6 passed (each)
uv run pytest tests/test_crawl_guidance_egress.py tests/test_crawl_guidance_payload.py -o addopts=   -> 36 passed
uv run pytest tests/test_crawl_guidance_seam.py tests/test_crawl_guidance_core.py -o addopts=        -> 47 passed
uv run pytest tests/test_crawl_guidance_kg.py tests/test_crawl_guidance_schema.py -o addopts=        -> 22 passed
uv run pytest tests/test_observe.py tests/test_explore_modal.py -o addopts=                          -> 16 passed
uv run pytest tests/test_explore_typing_input_type.py tests/test_marker_blocks.py -o addopts=        -> 23 passed
uv run pytest tests/test_ingest.py -o addopts=                                                        -> 9 passed
uv run ruff check src tests scripts                                                                   -> All checks passed!
uv run autotester doctor                                                                              -> doctor: clean (2 advisory D-087 findings, non-blocking)
```
File sizes (G11): `enumerate.js` 206, `explore_guidance_payload.py` 145, `tests/test_crawl_guidance_egress.py` 166, all <= 300. The full suite was not run (machine memory; another checker running tests).

## Re-check scope
None required for this PASS. N7 is cheap hardening for one small maker commit; N8-N10 are observations.

---

# Cycle 1 - re-check of N7 (maker fix `54dedb4a`)

Cycle checked: 1
Source checked: branch `fix/crawl-guidance-residuals` head `54dedb4a` (`git diff 9371f6dd..54dedb4a -- src tests`: `enumerate.js` +`hiddenBelow` at `:104-119`, `textOutsideFields` at `:121-134`; `tests/test_crawl_guidance_egress.py` +8 shapes, +1 test)
Contract: `qa/contracts/crawl-guidance.md` G3, G5.
VERDICT: PASS
SCOREBOARD: N7 CLOSED for the rule the maker stated (display:none, [hidden], noscript, script, style, template, closed `<details>`, own-parent `visibility:hidden`). Four exotic hidden-text shapes still reach the label (N11, non-blocking, below). No regression elsewhere; cycle-0 closures N1, N2, N3, N5 re-verified.

Method as cycle 0: real `enumerate.js` in headless Chromium, random non-word planted values, `innerText` of the target as an in-page oracle (`gr/hidden2.py`, 33 shapes); reverts in a `git archive` scratch copy or in memory only; no stash, no `src/` or `tests/` edit, no merge or push.

## FINDINGS
No F items.

### N7 - CLOSED
`gr/hidden2.py head`, label vs the `innerText` oracle: no leak and the same visible text for `display:none`; `[hidden]`; nested `display:none` > `display:block`; `display:none` > `display:inline` child; `visibility:hidden` parent; `visibility:hidden` outer with the text in an inner span; `visibility:collapse`; closed `<details>` (body, direct text, nested closed inside open, nested `<b>` in summary: the `<summary>` is kept, `Name Sum`); open `<details>` kept; `<noscript>`; `<template>`; closed `<dialog>`; a shadow host with `display:none` and a slotted child; a slot with an unassigned `slot="nope"` child. Better than the oracle: a `visibility:hidden` outer with a `visibility:visible` child gives `Name Shown`; a hidden root with a `display:none` child gives `Name` (innerText gave the child's text too).
- The root is always read: `display:none` root, `[hidden]` root, `visibility:hidden` root with a visible child, a `display:none` `<label>`: all give the useful label (`Name Lbl`). Labels get the same rule (`label-hidden-child` -> `Name`).
- Kept like the old `innerText`, as the maker stated: `opacity:0`, off-screen (`left:-9999px`), `aria-hidden`. Unchanged from before.
- Cycle-0 probe re-run on `54dedb4a` (`gr/probe_res.py head`, 47 shapes): the previously leaking `noscript`, `display:none`, `hidden`, `visibility:hidden`, closed-details and `hidden-in-label` shapes are now clean. Leaks left are exactly the ones the old code also had by design or by the cycle-0 ruling: `aria-hidden`, off-screen, a hidden WHOLE target (root read), a button caption in a label.
- N1, N2, N3, N5 shapes: still clean (no LEAK in any `n1-*`, `n2-*`, `n3-*`, `n5-*`, shadow, iframe, template case).

### Load-bearing proof
- Scratch `git archive HEAD` with `enumerate.js` from `2e17d653` (the venv python, `PYTHONPATH` = scratch `src;tests`): `tests/test_crawl_guidance_egress.py -o addopts=` fails `test_residual_shapes_never_send_a_planted_value` with `failures` = exactly the 8 new shapes `n7-display-none, n7-hidden-attr, n7-nested-hidden, n7-visibility-hidden, n7-closed-details, n7-noscript, n7-label-display-none, n7-hidden-target-hidden-child`; none of the 23 earlier shapes is in the list.
- In-memory mutation of each clause of `hiddenBelow` (`gr/hidden2.py m-*`): drop `display === "none"` -> 12 shapes leak (`display-none`, `hidden-attr`, `dialog-closed`, `label-hidden-child` among them); drop the `visibility` clause -> `vis-hidden-parent`, `vis-collapse` and others leak; drop the SCRIPT/STYLE/NOSCRIPT/TEMPLATE list -> `noscript` leaks; drop `closed` -> the 4 details shapes leak. Each clause has a planted shape in `SHAPES` (`n7-display-none`, `n7-visibility-hidden`, `n7-noscript`, `n7-closed-details`); the `[hidden]` attribute and the dialog case ride on `display:none`.
- Deviation from `checkVisibility`: accepted. Root-relative `getComputedStyle` keeps a hidden target readable, which an absolute `checkVisibility` would not; probes `root-display-none`, `root-hidden-attr`, `root-vis-hidden-child-ok` confirm.

### N11 (new, non-blocking) - four exotic hidden-text shapes still reach the label
`hiddenBelow` (`enumerate.js:104-119`) reads computed `display` / `visibility` and a few tags, so it cannot see content that is not rendered for another reason. The old `innerText` excluded these; the new code sends them (`gr/hidden2.py head`, 4 FAILs of 33):
- `content-visibility:hidden` on a descendant (`<div style="content-visibility:hidden">V</div>`): label `Name V`.
- `hidden="until-found"` (computes to `content-visibility:hidden`, not `display:none`): label `Name V`.
- Shadow DOM: default-slot text of a host whose shadow root has no `<slot>` (`<x-h2>V</x-h2>`), and a slotted child whose `<slot>` sits inside a `display:none` element of the shadow tree: label `Name V`.
Ruling, as for N7 in cycle 0: hidden page text is not an input value, typed value or option text, so no G3 criterion fails, and each needs unusual markup (an accordion using `content-visibility` or `until-found` is the realistic one). Fix direction if taken: also skip a text node when a descendant's computed `contentVisibility` is `hidden` (same `getComputedStyle(p)` the loop already makes); for the shadow cases skip a text node whose parent has no `assignedSlot` while its host has a shadow root. A later check needs only `gr/hidden2.py head` (expect no FAIL) plus the egress test file.

### G5 and regressions
- `gr/keydiff.py` (old `e947c8f2` vs new `enumerate.js`, 127 pages: all attack cases, real-label cases, every `tests/fixtures/**/*.html`): ZERO differences in any key other than `field_label`; field-ness changes only on the 11 intended shapes.
- 13 real-label cases: unchanged from cycle 0 (10 identical to the old output; `First *`, `Date of birth`, `Fi rst name` are the carried cosmetic N9, which the maker left as is with a reason: joining without a space would turn adjacent blocks into `AB`).
- Perf (`gr/perf.py`, `gr/perf2.py`, old vs new): 3000 labelled inputs 933 vs 910 ms; one 20000-node labelledby target 23 vs 109 ms (a `getComputedStyle` per ancestor); 300 inputs with 20-node targets 58 vs 75 ms. Acceptable.

## COMMANDS (from `D:/autoTesting/.claude/worktrees/guidance-residuals`, 2 files per pytest call, `-o addopts=`)
```
uv run python gr/hidden2.py head | old | m-closed | m-vis | m-tags | m-none      # old = 2e17d653 enumerate.js
uv run python gr/probe_res.py head ; gr/keydiff.py ; gr/perf.py ; gr/perf2.py
git archive HEAD + enumerate.js from 2e17d653 ; pytest tests/test_crawl_guidance_egress.py -vv   -> fails with exactly the 8 n7-* shapes
uv run pytest tests/test_crawl_guidance_egress.py tests/test_crawl_guidance_payload.py -o addopts=   -> 37 passed
uv run pytest tests/test_crawl_guidance_seam.py tests/test_crawl_guidance_core.py -o addopts=        -> 47 passed (see note)
uv run pytest tests/test_crawl_guidance_kg.py tests/test_crawl_guidance_schema.py -o addopts=        -> 22 passed
uv run pytest tests/test_observe.py tests/test_explore_modal.py -o addopts=                          -> 16 passed
uv run pytest tests/test_explore_typing_input_type.py tests/test_marker_blocks.py -o addopts=        -> 23 passed
uv run ruff check src tests scripts                                                                   -> All checks passed!
uv run autotester doctor                                                                              -> doctor: clean
```
Note (flake report): the seam + core pair failed once (`7 failed, 37 passed, 3 errors`, 30 s) on its first run this cycle while the machine was under memory pressure, then passed on re-runs (`47 passed`, about 67 s each). The failing names were not captured. This cycle's delta reaches those tests only through `enumerate.js`, and guidance-off byte identity is shown independently by `keydiff.py` (zero non-`field_label` diffs), so I attribute it to a transient resource failure; a maker run of that pair on a quiet machine should confirm. File sizes (G11): `enumerate.js` 221, egress test 200, both <= 300. Full suite not run.

## Re-check scope
None required. N11 is optional hardening; N9 remains cosmetic.
