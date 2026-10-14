# Verdict - t169-real-driver

**Cycle checked:** 1
**Commit:** c375161f
**Verdict:** FAIL (fix cycle 2 needed; two small items)

## Passed
- (a) Refusal: `preflight` -> `require_project_approval` -> `_reject_reason` fails closed on unsigned, edited, expired or missing-key rows; production projects accept only human `production:true` rows. Test covers the no-approval case (message names grant command, nothing written). Gap: no test for an unsigned/forged row or a production project; the gate is shared code so risk is low.
- (c) Reuses run_mode, bench and comparison code; no scorer duplicated.
- (d) `--dry-run` returns after preflight; `_real_seams` (providers, browser, crawl) is built only after that. Nothing live.
- (e) real_acceptance.py 107 lines, script 80, docstrings present, ruff clean.
- (f) pytest test_real_acceptance + test_generic_acceptance: 9 passed. ruff: clean. doctor: clean. merge-tree vs master: clean.

## Failures
1. (b) No Redactor / assert_no_raw_secrets anywhere in the driver. evidence.json writes the first failure reason (80 chars) from verdicts and comparison.json is a raw model dump, both unscrubbed, into a committed-path directory (qa/evidence/). Required: pass these through `Redactor.scrub` / `assert_no_raw_secrets` before writing, plus a test with a token-bearing URL in a failure reason.
2. False GR4 claim. checklist line "[x] GR4: ... the UI run enforces a LIVE_CASE approval" is untrue: `ui/routes_runs.py` has no approval check on master or this branch (AT-570 still open). The driver's own gate does not make the UI run gated.

## Contract amendment for /checker (not edited here)
GR4 in qa/contracts/generic-acceptance.md says: "a UI case run enforces no signed approval today; the report states what the run did." That is STILL CURRENT; it is not stale. The maker's manifest note ("UI runs now enforce LIVE_CASE") is wrong. Fix the checklist line to `[ ]` / state that the driver gates, the UI run does not (AT-570), and the report lists what the run did. Amend the contract only when AT-570 actually lands.

## Cycle 2 (head c6d8dd65, rebased on 4b7b5989)

**Cycle checked:** 2
**Verdict:** PASS

- Correction to cycle 1 finding 2: routes_runs.py itself has no check, but `trigger_run` calls the launcher gates (`authorize`), which return 400/403 at once. The new test posts to the real route `/projects/demo/run` via TestClient and gets 403 with no browser; it is not a stub. The cycle 1 claim "UI run enforces no approval" was based on a grep of routes_runs.py alone and was wrong for production projects; the contract GR4 wording (AT-570) should be re-checked by /checker against that launcher gate.
- Redaction: SecretStore Redactor + `mask_pii_obj` (both existing) then a local `_scrub_urls` regex. No existing URL-parameter scrub in core/redact (only secrets.py userinfo validation), so not a duplicate. Minor nit: the substitution drops the `key=` prefix (no group reference); harmless.
- Unsigned and production:false rows refused (test). pytest 13 passed, ruff clean, doctor clean, merge-tree vs master clean. Files within size limits.
