# Manifest - run-review-route

**Status:** checked-PASS
**Fix cycle:** 1
**Unit:** TA5 "Run review" button and route (team-video-review.md TV7, TV10; team-loop-acceptance.md TA5)
**Branch:** wave/run-review-route
**Contract:** qa/contracts/team-loop-acceptance.md TA5; qa/contracts/team-video-review.md TV2-TV5, TV7, TV10

## Changes
- ui/routes_video_review.py: `POST /projects/{slug}/videos/{video_id}/review` (form `pointers`) calls the same `stages.video_review.run_review` and `cli_video_review.build_gate` as `autotester ingest review`; 303 to the video page on success, 403 on missing permission or approval (zero provider calls), 400 on pointer errors, 422 unreadable.
- auth/policy.py: `video` rule, key `video.upload` (404 unseen, 403 view-only). tests/test_ui_auth_policy_table.py: additive row.
- ui/video_review_view.py + video_portal_view.py + routes_video_portal.py: a "Review" card on the video page with the latest stored review (any `video.view` holder) and the Run review form (only with `video.upload`).
- stages/video_review_store.py: list stored reviews of a source, newest first.
- Test seams in the route module: `provider_factory`, `probe_fn`, `frames_fn` (the TA5 xfail in tests/acceptance on wave/t206-runbook should be turned into a real test using them).

## Verify
uv run pytest tests/test_video_review_route.py tests/test_ui_auth_policy_table.py tests/test_routers_list.py tests/test_portal_access.py tests/test_portal_share.py tests/test_portal_comments.py ; uv run ruff check src tests scripts ; uv run autotester doctor
