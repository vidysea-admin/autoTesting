# Manifest - t209-leak-severity (T-209, G11-3)

**Status:** ready-for-check
**Fix cycle:** 1
**Contract:** qa/contracts/multi-role-platform.md (MP7, MP8, MP9, MP10; invariants MPI1, MPI2, MPI3 held)
**Goal task:** T-209
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now)
**Dual check:** required
dual-trigger: security src/autotester/stages/leak_evidence.py:50 (per-project HMAC-SHA256 key derived from the `.env` server key read through `load_repo_env` at :47)
dual-trigger: security src/autotester/stages/leak_evidence.py:96 (screenshot masked through `core/image_privacy.sanitized_images`; only the masked copy is written at :100, a refusal at :97 writes nothing)
**Persona walk:** skip (no UI surface in this unit; the banner is report HTML drawn by `render_html`, not a route)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** 722bf3df (worktree .worktrees/t209-leak-severity, branch wave/t209-leak-severity)
**Code SHA:** b7370722 (cycle 0 was 7746a2b8; cycle 1 repairs coordinator B's MP9/MPI1 FAIL)

## Criteria (quoted verbatim from the contract)
- **MP7 - Leak and privilege are always P0.** `stages/finding_priority.py` assigns P0 to every finding of class data-leak or privilege-escalation, with no model input and no override argument. Verify: parametrised test over every class plus a mutation that lowers one to P1 turns the test red. serves: intent#O19 - closes T-209
- **MP8 - Banner first.** When any P0 leak or privilege finding exists, the rendered report's first header block is a release-blocking banner with the count and a link to each finding's repro; with none, no banner renders. The banner is built in a new `stages/report_banner.py` and called first by `stages/unified_report_render.py`; `stages/unified_report.py` is not edited by T-209 (A3). Verify: render test on both fixtures, asserting position, not just presence; `git diff --name-only <base>..<candidate>` does not list `stages/unified_report.py`. serves: intent#O19 - closes T-209
- **MP9 - No third-party PII persists.** `LeakEvidence` holds count, field names, at most 5 HMAC-SHA256 hashed ids keyed per project, a masked screenshot path and a URL template; a planted canary name, email and phone in the probed page appear in no file under the run directory, no log line and no provider prompt. Verify: canary sweep over the run dir and captured prompts. serves: intent#O19, intent#O7 - closes T-209
- **MP10 - Repro survives masking.** Each P0 finding carries role, platform, URL template, ordered action steps and the count, enough for a second run to reproduce it. Verify: replay the recorded repro against the fixture and get the same count. serves: intent#O19, intent#O3 - closes T-209
- **MPI1 - Leak evidence stores no third-party personal data.** (checked by MP9; the model, not the caller, refuses value-shaped text.)
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` is not in `git diff --name-only 722bf3df..b7370722`.

## What changed
- `src/autotester/schema/leak_evidence.py` (new, 86 lines): `LeakEvidence` (count, header names, <= 5 hashed ids of the form `^[0-9a-f]{64}$`, masked-screenshot relative path, URL template) plus `validate_url_template`, `contains_personal_shape`, `segment_is_id_like`. A name, email, phone, raw id, userinfo, fragment or query value in any text field fails validation.
- `src/autotester/schema/multi_role_finding.py` (new, 81): `MultiRoleFinding` (role, platform, URL template, ordered `steps`, count, optional oracle/leak_evidence) and the closed `ReproVerb` enum with `parse_repro_step`. It has NO priority field. A data-leak finding must carry evidence whose count equals its own.
- `src/autotester/stages/finding_priority.py` (new, 43): `PRIORITY_BY_CLASS` (every `FindingClass`), `priority_for(finding_class)` (the only parameter), `is_release_blocking(finding)`.
- `src/autotester/stages/leak_evidence.py` (new, 129): `project_key` (:47-51), `hash_id`, `hashed_ids`, `templatise_url`, `store_masked_screenshot` (:96-100), `collect_leak_evidence`, `write_finding` (writes `multi_role_findings/<id>.json`, logs one value-free line).
- `src/autotester/stages/report_banner.py` (new, 58): `render_banner`, `render_repros`, `BANNER_STYLE`.
- `src/autotester/stages/unified_report_render.py` (edited in place, 171 -> 180): `render_html(report, findings=())` builds the banner first (before `<h1>`) and appends the repro sections; with no findings the output is byte-identical to before.
- tests: `tests/test_finding_priority.py`, `tests/test_report_banner.py`, `tests/test_leak_evidence.py`, `tests/test_leak_url_ids.py`, `tests/test_leak_repro_replay.py` (77 cases).
- **Fix cycle 1 (coordinator B FAIL, MP9/MPI1):**
  - `schema/leak_evidence.py`: `segment_is_id_like` is now ONE closed-list predicate: a path segment survives only if it is a `{placeholder}` or a lower-cased member of the closed `ROUTE_WORDS` set (students, profile, settings, api, v1 ...). Everything else (digits, letters mixed with digits, 20+ char runs, `%`/`@` values, nanoid-21, base62-22, `cus_...`, cuid2, ULID, ObjectId, UUID, name slugs) is an id. Both `stages/leak_evidence.templatise_url` and `validate_url_template` call it (no second copy). `LeakEvidence` sets `hide_input_in_errors=True`.
  - `schema/multi_role_finding.py`: `FINDING_ID_PATTERN` constant (one place) and `hide_input_in_errors=True` (same reason: its validators also see `url_template` and `title`).
  - `stages/leak_evidence.py`: `_screenshot_dest` validates `finding_id` against `FINDING_ID_PATTERN` and asserts the resolved destination stays inside the run dir; `collect_leak_evidence` calls it first.
  - tests: new `tests/test_leak_url_ids.py` (41 cases); `tests/test_leak_evidence.py` two fixture templates `/s/{id}` -> `/students/{id}` (`s` is not a route word).
- falsified (unchanged): none.

## Judgement calls for the checker
1. **Priority is not stored.** `MultiRoleFinding` has no `priority` field (extra=forbid rejects one), so no caller can store P1 for a leak; the priority is `priority_for(finding.finding_class)`. This satisfies "no override argument" structurally. Non-leak classes get a fixed P1/P2 row (P2: copy_or_branding, responsive_layout); the contract only fixes the two P0 classes, so those rows are this unit's choice and live in one table.
2. **HMAC key.** `AUTOTESTER_LEAK_EVIDENCE_KEY` (a server key, so `load_repo_env` exports it despite AU21) is the master; the per-project key is HMAC(master, "autotester/leak-evidence/v1\0" + slug). It is separate from `AUTOTESTER_APPROVAL_KEY`. This unit does not create the key in `.env` (nothing here writes `.env`); an operator adds it. With no key the ids are withheld (`ids_withheld_reason="key_missing"`) and the count is still recorded: a missing key never turns into raw ids. Tests use a monkeypatched synthetic key.
3. **Masking.** `store_masked_screenshot` imports only `sanitized_images` from `core/image_privacy.py` (untouched). The raw PNG bytes exist only in a `TemporaryDirectory` outside the run directory. This machine has no Tesseract, so the real engine path is unproven here: tests fake `_local_ocr` (as `tests/test_image_privacy.py` does) and also prove the fail-closed path (engine missing -> no PNG in the run dir, reason `local_ocr_unavailable`).
4. **Residual (named, not fixed).** Cycle 1 narrowed it: name slugs and every opaque id format now become `{id}` because only a closed route-word list is kept literally. What remains is the reverse: a legitimate route word not on `ROUTE_WORDS` is templated to `{id}` (over-masking, never under-masking), and a person's name equal to a listed route word cannot be told apart. `ReproVerb` steps are free-text targets scanned only for email/phone shapes.
5. **MP8 wiring.** `render_html` takes the findings as an argument; `stages/unified_report.py:282` (not editable here, A3) still calls it without findings, so the banner appears once a later unit passes them. CORE-REQUEST: stages/unified_report.py pass the run's multi-role findings (read from `<run_dir>/multi_role_findings/*.json`) to `render_html`, owner = T-218 or the first unit that produces findings.
6. `autotester doctor` reports 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); not hand-edited, merge-queue owner regenerates. Doc registration of the new modules needs a D-entry (contract "Out of scope").

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: L (security: HMAC-keyed ids and a PII-free evidence boundary; dual check required, triggers above)
Round: 11 files (6 src, 4 test, 1 edited src), 4 criteria (+MPI1, MPI3), est 55 min
Owners: OG-SEVERITY
Base / checked state: 722bf3df / b7370722, clean tree
Gate answers: none apply (D-104 opens the build; no gate in qa/gates touches severity or leak evidence).
Affected tests / full-suite trigger: `tests/test_unified_report.py` (consumes `render_html`; 18 passed with the banner tests). The builder ran no full suite.
Tests[MP7]: tests/test_finding_priority.py - 19 cases: parametrised over every FindingClass, table covers every class, signature has one parameter (extra positional/keyword raises TypeError), a finding cannot carry a priority, and the invariant helper goes red when either leak class is lowered.
Tests[MP8]: tests/test_report_banner.py, tests/test_unified_report.py - first-block position (head furniture stripped, banner next, banner index < `<h1>`), count and per-P0 link that resolves to an `id=` in the file, P1 excluded, repro fields and step order, no-banner output byte-identical to the no-findings render, HTML escaping. DC2 (`test_dc2_...`, no arithmetic builtins in the render file) still passes.
Tests[MP9]: tests/test_leak_url_ids.py (cycle 1: one parametrised case per id format - nanoid-21, base62-22, stripe-like, cuid2, ULID, ObjectId, uuid, numeric, letters-only-22, name slug - through `templatise_url`, `validate_url_template`/`LeakEvidence` and the bytes `write_finding` writes; route words students/profile/settings/api/v1 kept; query values never survive; `finding_id` slug and run-dir containment; no raw input echoed in a `ValidationError`), tests/test_leak_evidence.py - evidence shape (7 rows -> count 7, headers, 5 HMAC hashes recomputed in the test, template), per-project keys differ and a missing key withholds ids, model rejects 6 ids / value-shaped text / id-like URLs, masked-before-write pixels and metadata, withheld on missing engine, canary sweep (name, email, phone, raw ids, utf-8 and utf-16) over the whole run dir + caplog + captured prompts, and a positive control proving the sweep detects a planted canary.
Tests[MP10]: tests/test_leak_repro_replay.py - fixture two-tenant app; the recorded finding is read back from disk and replayed: same count (3); a fixed app yields 0; the five repro fields are present.
Tests[MPI1]: tests/test_leak_evidence.py, tests/test_leak_url_ids.py (see MP9).
Tests[MPI3]: none - diff check: `git diff --name-only 722bf3df..b7370722` lists neither `schema/multi_role_enums.py`, `schema/enums.py`, `stages/unified_report.py` nor `core/image_privacy.py`.
Falsification[MP7]: copy-mutant in scratchpad/t209-leak-severity/mut (`DATA_LEAK: P0` -> `P1`): red `test_priority_by_class_over_every_class[data_leak]` (`assert P1 is P0`), `test_table_covers_...`, `test_report_banner.py` banner tests (several failed); restored 36 passed.
Falsification[MP8]: copy-mutant (banner emitted after `</h1>`): red `test_banner_is_the_first_block_when_a_p0_exists` and `test_banner_names_the_count_and_links_every_p0_repro_only` (2 failed, 34 passed); restored 36 passed.
Falsification[MP9]: copy-mutants: a stray run-dir file holding the canary name -> red `test_canary_sweep_over_run_dir_log_and_prompts` (1 failed); raw screenshot written -> red `test_screenshot_is_masked_before_it_is_written` and the sweep (2 failed); raw ids kept -> `ValidationError` string_pattern_mismatch in the evidence build (red); restored 36 passed.
Falsification[MP10]: copy-mutant (count-equals-evidence check disabled) -> red `test_finding_refuses_a_repro_that_cannot_be_replayed_or_leaks` (DID NOT RAISE); restored 36 passed.
Falsification[MP9 cycle 1]: copy-mutants in scratchpad/t209-c1 (pytest run with PYTHONPATH pointing at the copy): (a) predicate reverted to the cycle-0 regex -> 22 failed of 41 in tests/test_leak_url_ids.py (every opaque format); (b) `finding_id` slug check and containment check disabled -> 8 failed (`DID NOT RAISE ValueError`); (c) `hide_input_in_errors` removed -> 1 failed (`cus_Nffrf7JkLm3pQw` echoed in the error); restored 41 passed.
Pre-check[MP7]: b7370722 uv run --directory <worktree> pytest tests/test_finding_priority.py -> 19 passed t=13 blobs=tests/test_finding_priority.py:a2e00bc
Pre-check[MP8]: b7370722 uv run --directory <worktree> pytest tests/test_report_banner.py tests/test_unified_report.py -> 18 passed t=46 blobs=tests/test_report_banner.py:7aec50a,tests/test_unified_report.py:9150701
Pre-check[MP9]: b7370722 uv run --directory <worktree> pytest tests/test_leak_evidence.py tests/test_leak_url_ids.py -> 50 passed t=25 blobs=tests/test_leak_evidence.py:4837e38,tests/test_leak_url_ids.py:bed6e0c
Pre-check[MP10]: b7370722 uv run --directory <worktree> pytest tests/test_leak_repro_replay.py -> 3 passed t=23 blobs=tests/test_leak_repro_replay.py:aaf9f63
Lint: b7370722 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated docs/MAP.md and docs/SNAPSHOT.md (judgement call 6).
Metrics: start=2026-10-18T09:00:00Z end=2026-10-18T10:30:00Z wall_min=90 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=7 cycle=0 resumes=2 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=7 defects_unit=0 defects_6c=0 tests=49 tests_min=2

## How to verify (commands + expected)
- `uv run pytest tests/test_finding_priority.py tests/test_report_banner.py tests/test_leak_evidence.py tests/test_leak_url_ids.py tests/test_leak_repro_replay.py tests/test_unified_report.py` -> expected: 90 passed.
- `git diff --name-only 722bf3df..b7370722` -> expected: no `stages/unified_report.py`, `schema/multi_role_enums.py`, `core/image_privacy.py`.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP7 | leak/privilege classes are P0, no override | tests/test_finding_priority.py::test_priority_by_class_over_every_class | `DATA_LEAK: P0` -> `P1` in finding_priority.py | green on tree; red `assert P1 is P0` on the mutant |
| MP8 | banner first, none without a P0 | tests/test_report_banner.py::test_banner_is_the_first_block_when_a_p0_exists | emit banner after `</h1>` | green; red `test_banner_is_the_first_block...` |
| MP9 | no canary in run dir, log or prompt | tests/test_leak_evidence.py::test_canary_sweep_over_run_dir_log_and_prompts | write the canary name into the run dir | green; red `assert ['Zorblax Quimby'] == []` |
| MP9 (cycle 1) | opaque ids never survive in url_template | tests/test_leak_url_ids.py::test_templatise_turns_every_id_format_into_a_placeholder, ::test_validate_url_template_refuses_every_raw_id_format | cycle-0 id regex restored | green; red 22 failed |
| MP10 | repro replays to the same count | tests/test_leak_repro_replay.py::test_replaying_the_recorded_repro_gives_the_same_count | disable count-vs-evidence check (guard test) | green; red DID NOT RAISE |

## Live browser evidence
Not UI-touching - no surface changed: only report-rendering HTML (`stages/unified_report_render.py`) and stages/schema modules changed; no route, template or static asset.

## Status: ready-for-check
