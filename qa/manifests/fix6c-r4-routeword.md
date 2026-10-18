# Manifest - fix6c-r4-routeword (6c integration r4 FAIL on int/1017@345c1606, reds group 1 and 2)

**Status:** checked-PASS
**Fix cycle:** 0
**Contract:** none new; repairs qa/verdicts/integration-6c-int1017-r4.md items 1 and 2 (T-209 leak-evidence predicate vs T-220 / answer-key / MP22 tests; image-privacy Windows-install fallback vs two no-OCR tests)
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now)
**Dual check:** required
dual-trigger: security src/autotester/schema/leak_evidence.py:53 (`segment_is_id_like` decides which literal path segments may reach disk in a leak finding; the closed `ROUTE_WORDS` set at :22-36 grows by 11 words, so what counts as an id-like segment changes in a dual-checked MP9/MPI1 path)
**Persona walk:** skip (no UI surface)
**Issues addressed:** none (AT-1033 stays open: the per-project route vocabulary is still wanted; no ledger row edited)
**Executor:** claude-sonnet-subagent (maker, fix6c-r4-routeword), 2026-10-19
**Base SHA:** 58e13d6b (worktree .worktrees/fix6c-r4-routeword, branch wave/fix6c-r4-routeword)
**Code SHA:** 58c0361e

## Criteria
- **F1 - the route-word reds (38 test ids in the r4 logs) go green, root cause named.** Root cause: the PRODUCT predicate was too narrow, not the tests. T-209 cycle 1 (b7370722) made `segment_is_id_like` (schema/leak_evidence.py:46-53) keep only a closed list of route words; the list never held the ordinary words other merged units already use (`inbox`, `mail`, `quiz`, `status`, `items`, `fast`, `slow`, `cart`, `me`), so StateProbe.reader_url `/inbox`, AnswerKey `/quiz/{id}` and MultiRoleFinding `/mail/{id}` were refused, and MP22 endpoints (`/api/status`, `/api/fast`, `/api/items/{id}`) collapsed to `{id}`. Fix: 11 words added to `ROUTE_WORDS` (:34-35). Real ids, emails, tokens and name slugs still become `{id}` (the list stays closed). Failing files: tests/test_oracle_state_after.py (12), test_state_probe_schema (3), test_oracle_answer_key (19), test_oracle_copy_lint (1), test_network_oracles (3).
- **F2 - the 2 no-OCR reds go green, root cause named.** Root cause: the TESTS were not hermetic. They stubbed only `shutil.which`, but `core/image_privacy.py:59-65` `_find_tesseract` also consults `AUTOTESTER_TESSERACT`, the repo .env and `WINDOWS_TESSERACT` (:37); this machine has Tesseract at the Windows path, so OCR ran and gave `no_recognized_text`. Fix: tests/test_leak_evidence.py::test_unmaskable_screenshot_is_withheld_never_written_raw and tests/test_oracle_responsive.py::test_without_a_masking_engine_the_screenshot_is_withheld_not_written_raw now also patch `WINDOWS_TESSERACT`, delete the env key and point `repo_root` at tmp_path, exactly as tests/test_image_privacy.py:59-65 `no_engine` does. `core/image_privacy.py` is untouched (it is right). Assertions unchanged.
- **F3 - T-209 leak criteria intact.** tests/test_leak_url_ids.py (41 original cases, unchanged) stays green; one test added (`test_ordinary_route_words_other_units_use_are_kept_but_names_still_are_not`): the new words survive, `/inbox/alice` and `/inbox/zorblax-quimby` are refused.

## What changed
- src/autotester/schema/leak_evidence.py:34-35 - +2 lines in `ROUTE_WORDS` (comment + 11 words: cart fast inbox item items mail me quiz quizzes slow status). 104 lines.
- tests/test_leak_evidence.py, tests/test_oracle_responsive.py - +4 lines each: hermetic no-engine patches.
- tests/test_leak_url_ids.py - +8 lines: the F3 test (additive; no assertion changed or removed).
- Protected test change: yes, additive hermeticity patches and one new test in existing T-209-owned test files; no assertion weakened, no skip/xfail, no threshold lowered. Hence Tier L.
- Not done (out of scope, named): r4 verdict items 3 and 4 (test_network_assertions NA6 listeners; test_actuator_chokepoint raw page access) belong to other units. AT-1033 per-project vocabulary is not built.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: L (changes the id-like predicate of a dual-checked security path; protected T-209 test file edited)
Round: 4 files (1 src, 3 tests), 3 criteria, est 15 min
Base / checked state: 58e13d6b / 58c0361e, clean tree
Gate answers: none apply (D-104 opens the build; qa/gates holds nothing on route words).
Affected tests / full-suite trigger: every test file that imports the predicate or image_privacy (platform_links, credential_policy, entity_reading, negative_input, request_budget, multi-role schema): run below; the full suite is the 6c r5 job, not this unit.
Tests[F1]: tests/test_oracle_state_after.py tests/test_state_probe_schema.py tests/test_oracle_answer_key.py tests/test_oracle_copy_lint.py tests/test_network_oracles.py tests/test_leak_url_ids.py - the 38 reds plus the T-209 id formats.
Tests[F2]: tests/test_leak_evidence.py::test_unmaskable_screenshot_is_withheld_never_written_raw, tests/test_oracle_responsive.py::test_without_a_masking_engine_the_screenshot_is_withheld_not_written_raw.
Tests[F3]: tests/test_leak_url_ids.py (42 cases), tests/test_leak_evidence.py, tests/test_leak_repro_replay.py.
Falsification[F1]: copy in scratchpad/fix6c-r4-routeword (src copy with the 11 words removed; tests, scripts and pyproject copied; PYTHONPATH to the copy): tests/test_state_probe_schema.py tests/test_oracle_answer_key.py tests/test_network_oracles.py tests/test_leak_url_ids.py -> 26 failed, 120 passed (ValueError "url_template path holds an id-like segment"); real tree 146 passed.
Falsification[F2]: base versions (git show HEAD~1) of the two test files run as tests/_mut_*.py (deleted after): 2 failed (the two named tests), 17 passed; the fixed tests pass.
Falsification[F3]: the F1 copy (words absent) fails the new F3 test's keep half; the name-slug half is held by the unchanged 41-case id-format tests, which stay green on both trees.
Pre-check[F1]: 58c0361e uv run --directory <worktree> pytest tests/test_oracle_state_after.py tests/test_state_probe_schema.py tests/test_oracle_answer_key.py tests/test_oracle_copy_lint.py tests/test_network_oracles.py tests/test_leak_evidence.py tests/test_oracle_responsive.py tests/test_leak_url_ids.py tests/test_leak_repro_replay.py tests/test_role_session_port.py -> 213 passed t=88 blobs=tests/test_leak_url_ids.py:bed6e0c
Pre-check[F3]: 58c0361e uv run --directory <worktree> pytest tests/test_leak_url_ids.py tests/test_grade_evidence.py tests/test_grade_visual.py tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_multi_role_schema.py tests/test_negative_input_oracle.py tests/test_oracle_consistency.py tests/test_oracle_credential_mail.py tests/test_oracle_credential_policy.py tests/test_platform_links.py tests/test_role_session_port.py tests/test_run_case_pipeline.py tests/test_video_frames.py tests/test_vision_probe.py -> 386 passed t=105
Lint: 58c0361e `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> clean.
Metrics: start=2026-10-19T03:00:00Z end=2026-10-19T03:25:00Z wall_min=25 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=2 defects_unit=0 defects_6c=2

## How to verify
- `uv run pytest tests/test_oracle_state_after.py tests/test_state_probe_schema.py tests/test_oracle_answer_key.py tests/test_oracle_copy_lint.py tests/test_network_oracles.py tests/test_leak_evidence.py tests/test_oracle_responsive.py tests/test_leak_url_ids.py` -> expected: all pass (no -q).
- `git diff --name-only 58e13d6b..58c0361e` -> expected: exactly the 4 files above; no core/image_privacy.py, no qa/contracts.

## Status: ready-for-check
