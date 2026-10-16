# Verdict - run-approval-grant-budget

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** 1dc74b2b0818e8bb90c86dc9efeca760f9bedc9c (base c4d48ad109f1ef77f73ee9172866cc5feeca7063, branch worktree-agent-a70bbe56d22416ba9)

## Scope
ISS-d063-grant-budget-1, -2, -3 / AT-675, AT-570 claim. Consent contract CN5, CN10, CN11; core-invariants C12.
Changed: stages/explore_consent.py, stages/run_budget.py, stages/run_launcher.py (299 lines),
core/consent.py, ui/routes_crawl_approval.py, tests/test_run_approval_grant_budget.py (12 tests).

## Independent checks (outputs and exit codes in .work/checker-rab/)
- Preflight (review_budget.py, PYTHONPATH=src, main .venv python 3.11.16): PREFLIGHT_OK, import from worktree src.
- pytest (22 files: new file, ui_crawl_approval(+_list), explore_consent, run_launcher(+_approval, +_priorities_approval),
  run_budget_judge_time, consent, credential_run_approval, approval_prod_gate(+_paths), approval_residual_callers,
  approval_revoke, approval_signing, parallel_run_approval, team_run_approval, ui_auth_host_and_consent,
  ui_origin_guard, ui_production_approval, ui_runs_live_case_approval, schedule_gate): 403 passed, rc 0 (pytest.txt).
- ruff check on the 6 changed paths: clean, rc 0.
- doctor: candidate clean rc 0; base (git archive of c4d48ad1 into .work) clean rc 0; same advisory warnings.
- Probe .work/checker-rab/probe_budget.py (rc 0, probe_budget.txt).

## Findings
1. BLOCKING (ISS-d063-grant-budget-3 not fixed as claimed). `run_budget.probe_request` says it counts the
   probes a run is KNOWN to spend, but it counts only 2 per FILL and 1 per ASSERT. At runtime
   (`stages/execute.py::_run_steps`, `browser/assertions.py`) every step with a declared expectation
   spends probes: `assert_expected` spends at least 2 (one `met()` plus the final `_probe`), and
   CLICK/NAVIGATE/BACK with an expectation also spend `settle` polls. Probe results:
   - ASSERT with the expectation already met: counted 1, spends 2. A row with max_probes=1 passes
     preflight and then stops with `run budget exhausted: max_probes`.
   - NAVIGATE with expected.url: counted 0, spends 3. `require_live_case_approval` with a human row
     max_probes=0 PASSES preflight. The run then stops at its first probe after the browser opens.
     That is the exact failure ISS-3 records.
   - Real projects/pathlynks/cases.jsonl: probe_request=20, with 4 non-FILL/ASSERT steps that declare
     expectations and are not counted.
   This is not a budget bypass: RunBudget still brakes at runtime, and C12 holds. But the preflight
   floor is below the known minimum, so the ISS-3 outcome ("refuse in preflight when max_probes
   cannot cover the run") is not delivered. The test pins the wrong count (`_case(Action.CLICK)` == 0
   only because its steps declare no expectation).
   Fix: count probes for every step that declares an expectation (and for each ASSERT) using the
   executor's real minimum, and add a test that pins it against the runtime spend.
2. Non-blocking. tests/run_approval_fixture.py docstring still says a case run "spends actions, never
   probes" and that the form has no max_probes field. Both are now false.

## Hunt results (no bypass found)
- Scope match (-1): the scope is canonical JSON with sorted keys. SecretRef lowercases domains and
  strips leading dots, so a case variant reuses the row (same scope). A trailing dot,
  include_subdomains, or an extra or reordered domain list mints a NEW signed row and does not reuse.
  A domain of only evil.demo.test is refused before any write. An empty or legacy scope never equals
  the validated JSON. The production path and the human fallback still see human rows only. The
  credential VALUE is not part of the scope: a rotated value under the same key reuses the row. This
  is per the CN11 definition; noted, not a violation.
- -2: test_ui_origin_guard and the new cross-site test pass. A foreign Origin gets 403 and nothing is written.
- max_probes form field: -1, 40001, abc and 1e3 return 400. A huge int fails the server-side range check.
  A missing field defaults to 0, which grants none (fail closed). The range check is server-side in `_capped`.
- schedule_gate and release do not pass a floor. This is not a bypass: release EXECUTE re-gates
  through `orchestrate_execute -> require_live_case_approval`, and `trigger_run -> prepare_run`
  gates too, so it is only a pre-check disagreement.
- AT-570: `ui/routes_runs.py::trigger_run -> run_launcher.prepare_run -> require_live_case_approval`. Gated.
- Back-compat: a max_probes=0 row is refused with "probes N > approved 0" plus a grant command. No crash.
- HMAC: schema/approval.py is unchanged, so the bound payload is unchanged. Edited rows are refused (test passes).

## Evidence provenance
Everything above was produced independently by this checker. No maker receipts were reused.

## Accounting
Mode BOOTSTRAP_REVIEW (maker usage unknown) plus the standing escalation (limit 480 s, 120000 tokens).
Measured active time (wall, waits not separated) was 929 s, including 209 s of pytest and two doctor
runs. This BREACHES the 480 s limit: assess p2-final returned NEEDS_EXTRA_REVIEW, exceeded active_s.
The breach is recorded, not waived. Tokens: actual null, debit 60000. Ratios unverified.
Inputs and results: .work/checker-rab/p1-review.*, p2-final.*.

## Remaining gates
Maker fix cycle 1 for finding 1. Then a full suite at integration.
