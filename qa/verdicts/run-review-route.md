# Verdict - run-review-route

**Verdict:** PASS
**Cycle checked:** 1
**Branch checked:** wave/run-review-route @ 96a96384

## Criteria
- TV7 permission: `POST .../review` is in PORTAL_POLICY via `_video(VIDEO_UPLOAD)` (auth/policy.py:58) and the gate re-checks `authorize()`. 404 unseen, 403 view-only. PASS.
- TV7 approval: `build_gate` -> `require_approval` for (project, provider, plan call count) runs inside `run_review` before the first call. Missing or too-small approval gives 403 and zero provider calls (tests 64, 70). PASS.
- Redaction/secrets: the stage scrubs with `SecretStore.scrub_values()`; test 83 shows a secret in pointers never reaches the provider. PASS.
- Model calls only via `providers.base.Provider` (provider_factory seam); no inline prompts in the route (prompts stay in stage files). PASS.
- TA5: tester reads a stored review when shared and has no Run control (test 96); 401/404 covered (test 111). PASS.
- Design rules: all new files <=300 lines (max 169), functions <=50; ruff clean; `autotester doctor` clean.
- Tests: 76 passed (route, policy table, routers list, portal access/share/comments).
- `git merge-tree master wave/run-review-route`: no conflicts (master at check time).

## Notes (non-blocking)
- `_lines/_row` are private helpers imported across modules from video_review_render.
- Real TA5 acceptance test (tests/acceptance/test_ta05_review_of_intake.py) lives on wave/t206-runbook and is not checked here.
