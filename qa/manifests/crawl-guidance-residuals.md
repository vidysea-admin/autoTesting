# Manifest — crawl-guidance-residuals

Status: ready-for-check
Fix cycle: 0
Unit: crawl-guidance-residuals: the non-blocking G3 egress residuals N1, N2, N3, N5 from checker B's cycle-3 PASS (`.work/cg-verdict-b-c3.md`, "NON-BLOCKING RESIDUALS"). N4 (aria-labelledby target that only displays a value: inherent, checker recommends no fix) and N6 (path-segment PII, grids of <=3 rows) are left as the checker ruled.
Contract: qa/contracts/crawl-guidance.md G3 (egress); G5 (guidance-off byte-identity) must stay green. G12 stays HELD. Contract not edited.
Branch: fix/crawl-guidance-residuals (worktree D:/autoTesting/.claude/worktrees/guidance-residuals), cut from feat/crawl-guidance e947c8f2
Code/test SHA: the commit that carries this manifest (see `git log -1` on the branch)

## Criteria (all under G3: no control value, shown text or option text reaches the prompt)

- **N1** elements inside a `<select>` / `<datalist>` are fields: `enumerate.js:92-100` `isFieldEl` ends in `el.closest("select, datalist")`, so the options, the customizable-select `<button><selectedcontent>` and any clickable / tabindex option send a label or `<field:KIND>`, never their text. Python half unchanged: `field_label is not None` already routes to `<field:KIND>` (`explore_guidance_payload.py:67`).
- **N2** `<label>` text excludes ARIA widgets and contenteditables: `enumerate.js:104-116` `textOutsideFields` walks the label's text nodes and drops any under a field (`isFieldEl`); used at `:127`. (The old clone only removed `input, select, textarea, option`.)
- **N3** an `aria-labelledby` target contributes no field text: `enumerate.js:124` `.map(textOutsideFields)`; a target that is itself a field (e.g. a `role=listbox`) contributes nothing (`:105`). N4 (a plain sibling that displays a value) is unchanged by design.
- **N5** every token of a role fallback list is read: JS `enumerate.js:97,99` (`roles.some(...)`), Python `explore_guidance_payload.py:71-74` `_field_role` (first token that is a field role; used by `is_field` `:67` and `_kind` `:82`), so an old stored graph with `role="foo combobox"` also sends `<field:combobox>`.
- `nameOf`, selectors, every other `enumerate.js` output key and the persisted artifacts are unchanged (G5).

## Files changed (edited in place; no new module)

- `src/autotester/browser/enumerate.js` (206 lines): `fieldLabelOf(el, tag, type)` split into `isFieldEl`, `textOutsideFields`, `fieldLabelOf(el)`; call site `:183`-area updated to `fieldLabelOf(el)`.
- `src/autotester/stages/explore_guidance_payload.py` (145 lines): `_role` replaced by `_field_role`; `is_field`, `_kind` use it; module docstring notes the label rule.
- `tests/test_crawl_guidance_egress.py` (166 lines): `SHAPES` (15 planted markups), `test_residual_shapes_never_send_a_planted_value`, `test_a_role_fallback_list_is_read_token_by_token_for_an_old_stored_graph`.

## Tests written first and seen RED, then GREEN

`test_residual_shapes_never_send_a_planted_value` runs the REAL `enumerate.js` in headless Chromium 151 (`page.set_content` -> `enumerate_elements` -> `Guidance.order` -> captured prompt of a `FakeProvider`). Each of the 15 shapes plants a random non-word value (`Q` + 11 chars of `bcdfghjklmnpqrstvwxz0123456789`, seeded `random.Random(20261029)`) and asserts neither the full value nor any 5-character slice appears in the prompt; each page also carries an `<a href="/reports">` so there are two candidates and the model call really happens (`assert model.calls == 1`). Shapes: n1-base-select-button, n1-select-button, n1-select-option-onclick, n1-select-option-tabindex, n1-datalist-option-tabindex, n2-label-combobox, n2-label-contenteditable, n2-label-listbox, n3-target-select, n3-target-listbox, n3-target-editable, n3-target-is-listbox, n5-fallback-combobox, n5-fallback-textbox, n5-fallback-padded-upper.

- RED before the fix (`uv run pytest tests/test_crawl_guidance_egress.py -o addopts= -k residual_shapes -vv`): `failures == []` failed with all 15 shapes listed; `test_a_role_fallback_list_...` failed (`'Zq91xv-secret' != '<field:combobox>'`).
- GREEN after the fix: `tests/test_crawl_guidance_egress.py` -> `7 passed` (the 5 earlier tests, incl. `test_prefilled_values_and_option_text_never_leave_the_machine` and its label expectations Work email / Password / Country / Search students / Find student / Term / Board, still pass).

## Verify commands run (from the worktree; machine low on memory: 2 files per pytest call, `-o addopts=`)

```
uv run pytest tests/test_crawl_guidance_egress.py tests/test_crawl_guidance_payload.py -o addopts=   -> 36 passed
uv run pytest tests/test_crawl_guidance_seam.py tests/test_crawl_guidance_core.py -o addopts=        -> 47 passed   (G5 byte-identity: seam baseline tests, support.baseline)
uv run pytest tests/test_crawl_guidance_kg.py tests/test_crawl_guidance_schema.py -o addopts=        -> 22 passed
uv run pytest tests/test_observe.py tests/test_explore_modal.py -o addopts=                          -> 16 passed
uv run pytest tests/test_explore_typing_input_type.py tests/test_marker_blocks.py -o addopts=        -> 23 passed
uv run ruff check src tests scripts                                                                   -> All checks passed!
uv run autotester doctor                                                                              -> doctor: clean (2 advisory D-087 findings, non-blocking)
```

The full suite was NOT run (machine memory; another agent is running tests).

## Known limits / for the checker

- `textOutsideFields` reads text nodes (no `innerText`), so a label / labelledby text no longer depends on CSS visibility and whitespace is collapsed (`Name \nQQQ` style newlines are gone). `aria-labelledby` may reference hidden elements by spec, so this is intended.
- N1's `base-select` shape depends on Chromium supporting customizable select; it was RED before the fix on Chromium 151, and on an older browser it is simply inert (passes without proving).
- A later check needs only: the new egress tests, the five guidance test files, doctor and ruff, plus `probe_aria.py head` from the cycle-3 scratchpad if available.
