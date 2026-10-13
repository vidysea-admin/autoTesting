# Verdict - t145-prod-project

**Verdict:** FAIL
**Cycle checked:** 1
**Checker:** independent, 2026-10-13

## Passed
- Both project.json files load via ProjectStore: pathlynks = ["pathlynks.vidysea.com"], read_only, PATHLYNKS_USER_* only; pathlynks-prepod = ["dev-new.vidysea.com"], read_only, PATHLYNKS_COUNSELLOR_* only.
- Login case case_cfa40e6b95c2 uses only PATHLYNKS_USER_EMAIL/PASSWORD (cases.jsonl); no knowledge file uses removed refs. No secret values in changed files (.env.example keys are empty).
- Slug pathlynks-prepod matches D-087 item 1 wording; prod keeps slug `pathlynks` (D-087 says "for example", acceptable).
- Approve command: every flag exists in `autotester approve --help` (--kind crawl, --target, --scope, --granted-by, --expires, --max-actions, --max-probes, --wall-clock, --production); values match D-088 item 3-4 (production true, 150 actions, 600 s, read-only scope). No correction needed.
- Doctor: clean.

## Defect D1 (blocking)
tests/test_browser_navigation_secrets.py::test_saved_pathlynks_config_isolates_each_role_host (4 params) now fails: it reads projects/pathlynks/project.json and expects the COUNSELLOR refs and `allowed_domains == ["vidysea.com"]`. The unit moved those refs and tightened the domain, so the test is stale (4 failed, 67 passed). Fix: update the test to assert USER refs against projects/pathlynks and COUNSELLOR refs against projects/pathlynks-prepod, with allowed_domains equal to each exact host. Resubmit at Fix cycle 2.
