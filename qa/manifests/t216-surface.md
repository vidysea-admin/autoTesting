# Manifest - t216-surface (T-216, G11 W5)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP25, MP26; invariants MPI1, MPI2, MPI3, MPI6 held). The criteria are in the contract (checker fold-in done 2026-10-18); no "contract pending" note applies.
**Goal task:** T-216
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now; Umesh 2026-10-18: "build all remaining features")
**Dual check:** no (no security, auth, tenancy or production-write trigger: both oracles read text and measured widths through an injected port, call no model, store no page text, and write only a masked screenshot under the run directory)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** cff3ffe6 (worktree .worktrees/t216-surface, branch wave/t216-surface; the T-211 head, stacked on T-209 36a87037 and T-207)
**Code SHA:** d601de49

## Criteria (quoted verbatim from the contract)
- **MP25 - Copy, branding and timezone lint.** Declared lint rules (brand terms, forbidden strings, expected display timezone) run over visible DOM text and mail bodies; each hit cites screen or message and the rule. Verify (A1, replaces the earlier text): a synthetic rule matrix: each declared brand term misspelt once, each forbidden string present once, and a timestamp rendered in each of two arbitrary zones other than the declared display zone; every cell is reported, and a control page with none is clean. serves: intent#O20 - closes T-216
- **MP26 - Responsive sweep.** Each visited screen is checked at the declared viewports; horizontal overflow or a control off-screen is a finding with a masked screenshot. Verify: fixture overflowing at 375 px. serves: intent#O20 - closes T-216
- **MPI1 - Leak evidence stores no third-party personal data.** (held: a finding carries a rule id, a slug of the screen or message and a count, never matched text or a control's text; screenshots only through `store_masked_screenshot`, withheld when masking fails.)
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` and `schema/enums.py` are not in `git diff --name-only cff3ffe6..d601de49`.

## What changed
- `src/autotester/schema/lint_rule.py` (new, 196 lines): the only schema file OG-SURFACE owns, so it holds the surface shapes together (docstring states the one job): `LintRule` (id, `LintKind` brand_term / forbidden_string / display_timezone, value, optional `case_sensitive`; a personal-shaped value or an unknown display zone is refused), `Viewport`, `SurfaceChecks` (the declaration, loaded from `<run_dir>/surface_checks.json`), `SurfaceText` and `ScreenLayout`/`ControlBox` (what a role session hands an oracle, in memory only), the optional port capabilities `TextSurface` (`surface_texts()`) and `LayoutSurface` (`layouts(viewport)`, `screenshot(...)`), `SurfaceUnavailable`, `SurfaceDeclarationMissing`, `load_surface_checks`, and the closed zone vocabulary `ZONE_OFFSETS_MIN` / `zone_key` (zones compare by offset: `IST` = `+05:30`).
- `src/autotester/stages/oracle_copy_lint.py` (new, 170): `lint_texts(rules, texts)`, `run_copy_lint` (exposed as `run`). Brand term: exact occurrences are cut out, then word windows within edit distance 0/1/2 (by term length) that are not the term are hits (case and spacing variants included). Forbidden string: counted substring. Timezone: every timestamp whose written zone (ISO offset after seconds, `Z`, `UTC+5:30`, table abbreviation) differs in offset from the display zone, one finding per (rule, source, zone). One finding per (rule, source); the title cites rule id, source slug and kind; no matched text.
- `src/autotester/stages/oracle_responsive.py` (new, 122): `run_responsive` (exposed as `run`), `case_class_for` (width <= `browser.conditions.MOBILE_VIEWPORT["width"]` -> `CaseClass.VIEWPORT_MOBILE`). Per declared viewport (default: the mobile viewport) and per measured screen: page wider than the viewport + 1 px, or a control with `right > width + 1` or `left < -1`, is a `RESPONSIVE_LAYOUT` finding (count = off-screen controls, else 1). Masked screenshot through `stages/leak_evidence.py::store_masked_screenshot` to `responsive/<finding_id>.png`; failure or cap (20 per run) is withheld with a fixed reason in the title.
- Test files: `tests/test_oracle_copy_lint.py` (19 cases incl. parametrised), `tests/test_oracle_responsive.py` (10), shared double module `tests/surface_fakes.py` (`SurfacePort`, `PlainPort`).
- No T-207/T-209/T-211 file, `schema/multi_role_enums.py`, `schema/enums.py`, `schema/project.py`, `browser/session.py` or the registry touched (`git diff --name-only cff3ffe6..d601de49` lists the 6 files above).

## Judgement calls for the checker
1. **How an oracle gets text and widths.** `RoleSessionPort` has only `perform` and `observe` (a matched flag and 200 characters), which cannot carry a page or a layout. I defined two optional capabilities in `lint_rule.py` that T-210's session may implement. A port without them makes the oracle raise `SurfaceUnavailable`, which the registry reports `errored: SurfaceUnavailable` (tested), never a clean result. CORE-REQUEST: stages/multi_role_session.py (T-210 owner) implement `TextSurface` and `LayoutSurface`.
2. **Where rules and viewports are declared.** `OracleContext` and `Project` carry no such field and both are off limits, so the declaration is `<run_dir>/surface_checks.json`. No rules declared: `SurfaceDeclarationMissing` (errored, not clean). No viewports declared: the mobile viewport the executor already enacts. CORE-REQUEST: schema/project.py (T-207 owner) a project-level `surface_checks` field and `OracleContext` carrying it.
3. **Masked screenshot has no field.** `MultiRoleFinding` has no screenshot path (only `LeakEvidence` does), so the file is `responsive/<finding_id>.png` and the title says so. CORE-REQUEST: schema/multi_role_finding.py (T-209 owner) optional `screenshot_path` for non-leak findings.
4. **Doctor `drift-filename` on `oracle_copy_lint.py` is a false positive I cannot remove.** `doctor.py:25` bans the substring `_copy`, but the module name is fixed by `OracleName.COPY_LINT = "copy_lint"` (T-207) and the registry's `oracle_<value>` rule. CORE-REQUEST: src/autotester/doctor.py:106 match the banned hints as a suffix (or exempt `oracle_*`). Until then `autotester doctor` is red on this one rule.
5. **`run` is an alias.** The registry needs a public `run`, and `doctor.py` already defines `run`, so a `def run` in each of the 13 oracle modules trips `duplicate-concept`. Each module defines `run_<name>` and sets `run = run_<name>`. Every other oracle unit will meet the same collision.
6. **"Reuse ux_advisory evidence reading" is not done as an import.** Its readers (`_screenshots`, `_evidence_lines`) are private and bound to provider, persona and `RawResult`; importing them would couple a deterministic oracle to a model stage. What is reused is the principle (a second reader of already-captured text, never re-driving the product) and `CaseClass.VIEWPORT_MOBILE` plus `MOBILE_VIEWPORT`.
7. **Known limits of the timezone lint, by design.** A timestamp with no written zone, and an abbreviation outside `ZONE_OFFSETS_MIN`, say nothing and are ignored; `09:00-12:00` (a range) is not read as an offset (a signed offset needs seconds or a leading space); `IST`/`BST`/`AST` mean India/UK/Atlantic. The brand lint can false-positive on an ordinary word within one edit of a short brand term (terms under 5 letters allow case/spacing variants only).
8. **TDD note.** The tests were written before the modules in the same sitting, but I did not run them red first; the falsifications below are the evidence that each one bites.
9. `autotester doctor`: 3 violations: `drift-filename` (call 4) and the two stale-generated docs (docs/MAP.md, docs/SNAPSHOT.md), not hand-edited; the merge-queue owner regenerates.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: M (new public oracle modules and a new shared schema file; no L trigger)
Round: 3 new src files + 3 test files, 2 criteria, est 40 min
slow-plan: two independent detectors families (fuzzy brand match plus zone parsing; layout measure plus masked screenshot) share one new schema file and need their own fixtures, so the round cannot be split below two oracles without splitting one schema file across builders (OG-SURFACE owns a single schema file).
mutant-cap-raise: src/autotester/stages/oracle_copy_lint.py:116 three independent detectors in one module (zone, brand, forbidden) each need their own mutant so one dead detector cannot hide behind the others; the three MP26 edits are the same shape in oracle_responsive.py
Owners: OG-SURFACE
Base / checked state: cff3ffe6 / d601de49, clean tree
Gate answers: none apply (D-104 opens the build; no gate in qa/gates touches the surface oracles).
Affected tests / full-suite trigger: `tests/test_oracle_registry.py` (the registry imports these modules by name; 12 passed together with the new files); no existing module edited; the builder ran no full suite.
Tests[MP25]: tests/test_oracle_copy_lint.py - `test_every_cell_of_the_rule_matrix_is_reported` (2 brand terms misspelt once, 2 forbidden strings once, two foreign zones; exactly those 6 (rule, screen) cells, class COPY_OR_BRANDING, oracle COPY_LINT, P2); `test_control_page_is_clean` (correct brands, display-zone timestamps, `10:30 AM`, `09:00-12:00`, mail); `test_timezone_rule_compares_zones_not_names` (7 declared/written zone pairs incl. `UTC+5:30` vs `IST`, `Z`, `PM JST`); `test_mail_bodies_are_linted_and_cited_as_a_message`; `test_occurrences_are_counted_per_cell`; `test_an_undeclared_rule_set_is_an_error_not_a_clean_pass`; `test_a_port_without_text_access_is_reported_errored`; `test_the_registry_runs_the_oracle_end_to_end`; `test_rule_shapes_are_closed` (4 bad rules).
Tests[MP26]: tests/test_oracle_responsive.py - `test_overflow_at_375_is_a_finding_with_a_masked_screenshot` (520 px page at 375: one finding, masked file exists, differs from the raw capture); `test_a_clean_screen_is_not_a_finding`; `test_a_control_past_the_edge_is_a_finding_even_when_the_page_does_not_scroll`; `test_every_declared_viewport_is_swept`; `test_the_default_viewport_is_the_mobile_one`; `test_without_a_masking_engine_the_screenshot_is_withheld_not_written_raw`; `test_a_failing_screenshot_does_not_lose_the_finding_or_leak_its_error`; `test_screenshots_are_bounded`; `test_a_port_that_cannot_measure_is_reported_errored_not_clean`; `test_the_registry_runs_the_oracle_end_to_end`.
Tests[MPI1]: tests/test_oracle_copy_lint.py::test_no_page_text_reaches_a_finding_or_a_file (planted canary email, phone and name in the page: absent from every finding, and the run directory holds only the declaration file); tests/test_oracle_responsive.py::test_a_failing_screenshot_does_not_lose_the_finding_or_leak_its_error.
Tests[MPI3]: none - diff check: `git diff --name-only cff3ffe6..d601de49` lists only the 6 files above.
Falsification[MP25]: copies in scratchpad/t216-surface (src+tests+scripts, `python -I -m pytest` with that PYTHONPATH; green before: 29 passed): foreign-zone comparison `key != shown` -> never true: red (5 failed, 14 passed); brand hit not counted (`hits + 1` -> `hits`): red (2 failed, 17 passed); forbidden count -> 0: red (4 failed, 15 passed); each restored.
Falsification[MP26]: same copy: page-overflow test `content_width > limit` -> `False`: red (7 failed, 3 passed); off-screen control count -> 0: red (1 failed, 9 passed); sweep only the first viewport: red (1 failed, 9 passed); each restored.
Pre-check[MP25]: d601de49 uv run pytest tests/test_oracle_copy_lint.py -> 19 passed t=4 blobs=tests/test_oracle_copy_lint.py:7832648
Pre-check[MP26]: d601de49 uv run pytest tests/test_oracle_responsive.py -> 10 passed t=4 blobs=tests/test_oracle_responsive.py:528189d
Lint: d601de49 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 3 violations (judgement calls 4 and 9).
Metrics: start=2026-10-19T08:00:00Z end=2026-10-19T09:10:00Z wall_min=70 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=4 defects_unit=0 defects_6c=0 tests=29 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_oracle_copy_lint.py tests/test_oracle_responsive.py tests/test_oracle_registry.py` -> expected: 41 passed.
- `git diff --name-only cff3ffe6..d601de49` -> expected: the 6 files listed, nothing else.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP25 | foreign-zone timestamps reported, any zone, by offset | tests/test_oracle_copy_lint.py::test_every_cell_of_the_rule_matrix_is_reported, ::test_timezone_rule_compares_zones_not_names | `key != shown` -> never | green on tree; red (5 failed) |
| MP25 | misspelt brand term reported, correct use clean | ::test_every_cell_of_the_rule_matrix_is_reported, ::test_control_page_is_clean | hit not counted | green; red (2 failed) |
| MP25 | forbidden string reported with count | ::test_occurrences_are_counted_per_cell | count -> 0 | green; red (4 failed) |
| MP26 | overflow at 375 px is a finding with masked screenshot | tests/test_oracle_responsive.py::test_overflow_at_375_is_a_finding_with_a_masked_screenshot | page-width test -> False | green; red (7 failed) |
| MP26 | off-screen control is a finding | ::test_a_control_past_the_edge_is_a_finding_even_when_the_page_does_not_scroll | off count -> 0 | green; red (1 failed) |
| MP26 | every declared viewport is swept | ::test_every_declared_viewport_is_swept | first viewport only | green; red (1 failed) |

## Live browser evidence
Not UI-touching - no surface changed: only schema and stage modules plus tests; no route, template or static asset. The oracles are driven by fakes through the port capabilities until T-210 merges.

## Status: ready-for-check
