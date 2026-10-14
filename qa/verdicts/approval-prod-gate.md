# Verdict - approval-prod-gate

Cycle checked: 1
Verdict: FAIL
Checker: independent security review of wave/approval-prod-gate (b6336876). Tests: 62 passed (prod_gate, explore_consent, explore, credential_run_approval, secret_scrubbing); ruff clean; doctor clean.

## Probes
1. Enforced production gate (project.production): crawl/explore (stages/explore.py:263 via cli_crawl) and release scope creation (stages/release.py:64, covering_approval). NOT enforced: UI case runs (ui/routes_runs trigger_run has no approval check, AT-570 open); orchestrate_gate.py:46 (re-check omits production, so a hand-edited scope.json naming a production:false or derived row passes); agents/guards.py:65,72; stages/adversarial.py:108; stages/discover.py:49. The unit does not claim these, but the manifest does not say so either.
2. production is not settable via UI: routes_project_edit.py:213 model_copy touches name/base_url/domains only; new projects default False (ui/app.py:161). Flipping is a raw project.json edit: no admin check, no audit entry. A new slug pointing at a production URL is non-production by default (declared, not inferred).
3. Only pathlynks was a production target in tree; it is set true. Other prod-looking projects (erp, vidysea-erp at www.vidysea.com/erp) stay False: they silently remain ungated. Needs Umesh's call.
4. CrawlSummary: ids, approval id, bounds, counters only. stop_reason (<=200 chars, scrubbed) can carry page text or a URL; minor.
5. DEFECT: scripts/check_crawl_approval.py:73-78 passes a production project with "signature NOT verified" when the key is absent; row.is_intact is a content hash, forgeable by anyone who can edit approvals.jsonl. Must fail closed for production projects.
6. Redaction: planted email masked in nodes/edges/issues, ids preserved (test_crawl_artifacts_mask_the_test_account_email).

## Required fixes
- D1: fail closed (exit 1) when project.production or summary.project_production and no key.
- D2: pass production through orchestrate_gate.py:46 (and state which other paths remain open).

---

# Cycle 2

Cycle checked: 2
Verdict: PASS (with notes)
Head checked: be2f0bd3. Tests: 118 passed (test_approval_prod_gate, _paths, test_release_gate, test_consent, test_explore_consent, test_approval_signing) with AUTOTESTER_APPROVAL_KEY unset; ruff clean; doctor clean.

## Cycle-1 defects
- D1 PASS: scripts/check_crawl_approval.py:68-72 exits 1 for a production project when the key is unset ("cannot be verified"). Covered by tests/test_approval_prod_gate_paths.py::test_done_check_fails_closed_for_production_without_the_key (asserts exit 1 and the message) and ::..._forged_signature. Live run of `check_crawl_approval.py pathlynks` with the key unset exits 1, but in this worktree only because no tracked projects/pathlynks/crawl_summaries/ exists (clean checkout); the key branch is proven by the test, not that live run.
- D2 PASS: orchestrate_gate.py:46 calls core.consent.require_project_approval(project=...), the same function explore_consent.covering_approval uses (production => non-account-derived production:true row). test_hand_edited_scope_naming_a_non_production_row_does_not_pass_release expects ApprovalRequired for a production project; the valid human row passes.
- stop_reason PASS: explore_summary.safe_stop_reason yields an enumerated code plus <=80-char URL-free detail; parametrized tests cover URLs and None.

## Path audit
Enforcing require_project_approval: covering_approval (crawl, release scope, UI trigger_run via run_launcher.require_live_case_approval:154), release_preflight, agents/guards.py:66,73, stages/adversarial.py:108. AT-570 gap is closed in this path (trigger_run -> prepare_run -> covering_approval); the table in the path test covers it.
Remaining raw require_approval (not production-aware):
- stages/ai_capture.py:95 (caller-stated production flag, project slug only).
- stages/discover.py:49 (filesystem read gate, not a live target).
- cli_video_review.py:76 (video review; not examined for live target use).
The manifest discloses the first two; cli_video_review.py:76 is not disclosed. These are non-blocking notes, not criteria failures.
