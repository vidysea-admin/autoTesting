# 6c integration check r4 - int/1017 @ 345c1606

Verdict: FAIL
Cycle checked: 0
Head tested: 345c1606ae03abd8c8dcf4b6cda8193e7ba31cf5 (int/1017 head, unchanged during the run). Base: fcedc9f4.
Policy: proportional-verification/2026-10-18.15; full suite (.13-2: tests/conftest.py edit; tier-L security units).

## Commands run (real detached worktree .worktrees/int-6c-345c1606, TMP/TEMP=D:/autoTesting/.work/tmp)
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: clean (advisory D-087 findings only).
- Full suite, no -x/--maxfail, run as r3 did (single-process run hangs): 526 test files, 5 in parallel, `pytest-timeout --timeout=240`.
  First pass: passed=8653 failed=61 skipped=10 errors=0. Red files rerun serially: 1 pyc artifact cleared (docker/__pycache__ removed),
  3 mutation_check load reds cleared. After rerun: passed=8658 failed=56 skipped=10. Of the 56, 14 are baseline and 42 are NEW.
- `tick.mjs --push-gate` (run in int-1017): `no green stamp` (expected). No stamp written (FAIL).

## Baseline reds (14, match qa/checkpoints/baseline-reds.md; test_mutation_check 9th test also red on fcedc9f4, shown)
test_cli_advice_resolves (AT-1024) x1, test_goal_contract_registration (92 != 106, AT-743) x1, test_infra_trio x2 (WSL bash),
test_mutation_check x9 and test_mutation_check_judgement x1 (TMP inside repo). The r3 fix 99acda50 holds: test_hosting_deploy is green.

## NEW reds (42, files absent or green on base; deterministic on serial rerun)
1. url_template closed route-word predicate (T-209 fix b7370722, `schema/leak_evidence.py:62` `segment_is_id_like`) rejects ordinary route words
   used by other merged G11 units' tests/code ("/inbox", quiz/answer-key paths, "/api/fast", "/api/status", "/items/..."):
   - tests/test_oracle_state_after.py x12 and tests/test_state_probe_schema.py x3 (T-220 StateProbe.reader_url `/inbox`)
   - tests/test_oracle_answer_key.py x19 (AnswerKey url_template), tests/test_oracle_copy_lint.py x1 (MultiRoleFinding)
   - tests/test_network_oracles.py x3 (MP22 polled endpoints collapse to `{id}`; expectation `/api/fast` etc.)
   Owner: T-209 (leak-severity) interacting with T-220 / answer-key / network-oracle units. Either ROUTE_WORDS is too narrow or those tests/code must use `{id}`.
2. Windows-install fallback in image-privacy-mask (`core/image_privacy.py:37,63`, WINDOWS_TESSERACT) makes the tests that stub only `shutil.which -> None`
   no longer simulate "no OCR": tests/test_leak_evidence.py::test_unmaskable_screenshot_is_withheld_never_written_raw and
   tests/test_oracle_responsive.py::test_without_a_masking_engine_the_screenshot_is_withheld_not_written_raw get `no_recognized_text`, not `local_ocr_unavailable`.
   Owner: image-privacy-mask vs T-209/responsive tests (machine has Tesseract at the Windows path).
3. tests/test_network_assertions.py::test_na6_exactly_one_response_listener_exists_in_browser: 2 listeners (`observe.py:68`, `role_probe.py:74`).
   Owner: g11-port-wiring (cdc199e7/2e3c5c8e, `browser/role_probe.py`).
4. tests/test_actuator_chokepoint.py::test_no_direct_page_or_playwright_access_outside_browser_package: raw page access in
   `stages/platform_links.py:120,155,156,184` (T-210, 42fc8dc9). Owner: T-210 / g11-port-wiring (reported earlier by that checker; not in baseline).

Not done: no merge, no push (FAIL). Logs: .work/6c-r4/files/, .work/6c-r4/serial/.

Metrics: start=2026-10-19T02:00 end=2026-10-19T02:45 wall_min=45 agent_min=unavailable blocked_min=0 suite_runs=2 repeat_runs=1 mutations=0 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=2700 mutants=0 defects_unit=0 defects_6c=4
