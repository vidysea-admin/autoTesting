# Manifest - at887-learn-guard-test (test-only integration repair of at887-crawl-to-flows)

Contract: qa/contracts/expand.md (X6); core-invariants.md C5 (unchanged; the criterion the repaired test proves)
Issues: none new. Follow-up to qa/manifests/at887-crawl-to-flows.md (merged 4f806daa), whose manifest named this integration risk ("re-run tests/test_ui_learn_guard.py after the merge").
Authority: no D-entry needed; test-only edit, no contract, product, conftest or fixture touched.
Status: ready-for-merge (test-lane)
Fix cycle: 0
Policy-Version: proportional-verification/2026-10-10.9
Tier: S
Dual check: no - test-only change (one line in one test file); no security, auth, tenancy or prod-write product code is edited, so no dual-trigger applies
Base: master a773f972, branch wave/at887-learn-guard-test (worktree .worktrees/at887-learn-guard-test)
Test commit: b343ae20 (the manifest cannot name its own commit; the pre-checks below ran on the identical content of that test change)
Executor: claude-sonnet-subagent (maker builder), 2026-10-12.

## What broke and why

`tests/test_ui_learn_guard.py::test_a_guard_refusal_is_a_themed_400_with_nothing_written_sent_or_echoed` was green on the at887 branch and red on master with `AttributeError: module 'autotester.ui.routes_learn' has no attribute 'LangChainFallbackProvider'` (test line 49). Cause confirmed by reading master: the T-202 LiteLLM change replaced the hard-coded `LangChainFallbackProvider()` in `ui/routes_learn.py` with the one factory call `why_unavailable(provider := for_role(project, "agent"))` (routes_learn.py:246), and the module imports `for_role` (line 36) and no longer imports the old class. The at887 branch was cut before that change, so the test patched a name that no longer exists on master. The product is correct: with the seam repaired the route returns the 400 themed page, the spy sees no prompt, no case is written and the secret is not echoed (see Falsification for the proof the test still bites).

## Test diff (the whole change)

```
tests/test_ui_learn_guard.py:49
-    monkeypatch.setattr(routes_learn_module, "LangChainFallbackProvider", lambda: spy)
+    monkeypatch.setattr(routes_learn_module, "for_role", lambda project, role: spy)
```

Files changed: `tests/test_ui_learn_guard.py` only (1 line). Plus this manifest. No product file, `conftest.py`, fixture, contract or assertion changed; no skip or xfail added. The patch shape `lambda project, role: spy` is the one every sibling learn test already uses (`tests/test_ui_learn.py:78`, `tests/test_ui_learn_vendor_echo.py:31`, `tests/test_provider_factory.py:215`).

Other tests patching `LangChainFallbackProvider` on `routes_learn` (grep of `tests/`): none. Remaining mentions are `tests/test_langchain_fallback.py` and `tests/test_provider_factory.py`, which test the class or assert it is absent from route calls; none patches `routes_learn`. No other at887 test depends on the old seam.

## Pre-checks (final test content; every run `uv --directory D:/autoTesting/.worktrees/at887-learn-guard-test run ...`, `autotester.__file__` confirmed inside the worktree; `-p no:xdist -o addopts=`; no full suite)

Pre-check[X6]: b343ae20 pytest tests/test_ui_learn_guard.py -> red before the edit (1 failed, AttributeError at line 49), 1 passed after.
Pre-check[AT887-GROUP]: b343ae20 pytest tests/test_explore_flows.py tests/test_explore_flows_doors.py tests/test_expand.py tests/test_expand_cli.py tests/test_expand_redaction.py tests/test_explore_merge.py tests/test_eval_compiler.py tests/test_ui_learn.py tests/test_ui_learn_guard.py tests/test_ui_crawls.py tests/test_orchestrate_runners.py tests/test_cli_orchestrate_resume.py tests/test_coverage_wiring.py tests/test_merge_flowspec.py tests/test_ui_learn_vendor_echo.py tests/test_provider_factory.py -> 207 passed in 96.11s (the 14 files of the at887 DOORS group plus the two other tests that patch `routes_learn.for_role`).
Pre-check[LINT]: b343ae20 ruff check src tests scripts -> All checks passed.
Pre-check[DOCTOR]: b343ae20 autotester doctor -> 1 violation, `stale-generated: docs/SNAPSHOT.md`. Not caused by this change: it is identical with the test edit stashed (clean master checkout), and no `root-clutter` row appears. It is a generated-doc staleness on master that `autotester snapshot` regenerates; left alone because regenerating it would put a non-test file in this test-only diff. Reported to the coordinator, not hidden.

## Falsification

Throwaway copy of src, tests, scripts and pyproject on C: (`C:\Users\Lenovo\AppData\Local\Temp\claude\fz-at887lg-c6n4idvh`), `PYTHONPATH` at the copy, `autotester.__file__` printed inside the copy.

- Falsify[X6]: bypass the prompt guard (`stages/expand.py` line 185 `guard_expand_prompt(build_expand_prompt(...), secrets)` reduced to `build_expand_prompt(...)`). Green before: 1 passed. Red after: `assert response.status_code == 400` -> `assert 303 == 400` (the route generated and redirected instead of refusing; an assertion failure, not an import or setup error). Restored `expand.py` from the worktree: 1 passed. Copy deleted (path no longer exists).

## Notes

- Tier S, test lane: no product behaviour changed, so no checker was invoked and nothing was pushed or merged into master.
