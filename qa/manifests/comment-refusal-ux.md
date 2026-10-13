# Manifest — comment-refusal-ux

**Unit:** A refused video comment keeps the user on the video page (T-198 G9 walk, defect D2).
**Contract:** `qa/contracts/team-intake.md` TP2 (refused with 4xx, nothing stored; text rendered escaped)
**Date:** 2026-10-13
**Status:** checked-PASS
**Fix cycle:** 1 of max 3
**Issues addressed:** see qa/issues.jsonl (AT-996, D2; renumbered from AT-994 by the checker)

## Change
- `routes_video_comments.comment_create`: on `CommentError`, a browser (Accept text/html) gets the video page
  re-rendered with status 400 (refusal unchanged, nothing stored), the message inline (`role='alert'`) and the
  typed time and text put back, escaped. Non-HTML clients still get the JSON 400.
- `routes_video_portal.render_player` extracted from `video_page`; `video_portal_view._comment_form` takes `refused`.

## Tests
`tests/test_portal_comments.py`: two new tests (text kept + escaped + message shown + 400 + nothing stored);
existing portal comment/access/persona tests pass (62).
