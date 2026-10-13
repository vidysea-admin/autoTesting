# Manifest — t198b-developer-portal
**Contract:** qa/contracts/team-intake.md (section B, TP1-TP6)
**Goal task:** T-198 (plan unit G9, the share / access-request / comment developer portal)
**Date:** 2026-10-12
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** yes
**Persona walk:** required (developer, tester)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Executor rationale:** one multi-file build unit sized for a single agent; auth/permission touch, so Tier L.

dual-trigger: auth src/autotester/ui/auth_middleware.py:79
dual-trigger: auth src/autotester/auth/policy.py:44

## What changed
- src/autotester/schema/video_share.py:1-77 (new) — `Share`, `ShareLink`, `AccessRequest`, `VideoComment` models (`extra="forbid"`), token and comment length constants.
- src/autotester/schema/team_enums.py — appended `AccessRequestStatus` (pending / approved / declined).
- src/autotester/schema/auth.py — `RouteRule.kind` gained `"video"` (video-scoped rule: 404 when the account may not view the video, 403 when it may view but lacks the key).
- src/autotester/auth/db.py — `_SCHEMA` gained `video_shares`, `video_links` (hash only, `revoked_at`), `access_requests` (unique partial index = one pending request per requester and video) and `video_comments` (`pointer_line`).
- src/autotester/stages/video_access.py (new) — video lookup by validated id, share and link store, `resolve_link` (charset, length, sha256, `hmac.compare_digest`), `media_path` (resolved path must stay inside the project dir; the path comes from the id only), purge on video or project delete.
- src/autotester/stages/video_requests.py (new) — request, atomic decide (the Share is inserted only if the UPDATE won), approver list through `authorize`, optional mail through `delivery/email.py`.
- src/autotester/stages/video_comments.py (new) — `parse_at_s`, `clean_text`, comment CRUD, `pointer_line` (G2 parser format with fallbacks), `promote`, `pointer_text`.
- src/autotester/ui/auth_middleware.py:79,118 — `_video_refusal` and the `video` rule branch.
- src/autotester/auth/policy.py:44-103 — `PORTAL_POLICY` (17 rows, spread into `ROUTE_POLICY`). No new permission key; no route compares an email or a group.
- src/autotester/ui/routes_video_portal.py, routes_access_requests.py, routes_video_comments.py, video_portal_view.py (new) — pages, media (inline, nosniff, generated filename, Range via `FileResponse`), share-link, shares, request-access, approvals, comments, promote. Every human string is escaped in `video_portal_view.esc`.
- src/autotester/ui/routers.py, theme.py — three routers appended (the stubs stay); nav links `/shared` (video.view) and `/access-requests` (access.approve), shown only to holders.
- tests/test_ui_auth_escalation.py — added the 17 portal rows to the pinned `EXPECTED` table of AU14 (add only; the test still compares the whole table).
- tests/portal_support.py, test_portal_access.py, test_portal_share.py, test_portal_requests.py, test_portal_comments.py (new) — 75 tests.
- docs/MAP.md — regenerated with `autotester map`. docs/SNAPSHOT.md not regenerated here (the orchestrator owns it on merge).
- falsified (unchanged): none — every falsifying edit hit a file listed above, in a throwaway copy outside the worktree.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (auth / permission: a new middleware rule kind, 17 route-policy rows, share and approval decisions)
Base / checked state: 7e1aec04 / code commit 06d86f93 (clean tree apart from this manifest)
Gate answers: `qa/gates/plan-approved-g10.md`: "Approved -- Umesh, 2026-10-07 (chat), recorded as D-074." D-072 item 2: "New modules: yes to all. This covers ... the Group 10 split modules ... Every file stays at or under 300 lines with a one-job docstring, and the checker judges it." `qa/gates/drive-identity.md` and `qa/gates/email-sender-credentials.md` do not apply to G9 (no Drive call, no new sender credential; the optional mail goes through the existing shared transport and is skipped when SMTP is not configured).
Affected tests / full-suite trigger: new tests/test_portal_*.py (4 files). Existing nodes touched by the change and run green on this code: tests/test_routers_list.py, test_ui_auth_groups.py (route walk), test_ui_auth_surface.py, test_ui_auth_escalation.py (AU14 pinned table, nav), test_ui_auth_refusal_audit.py, test_ui_auth_survivors.py, test_team_enums_home.py, test_policy_merge.py, test_ui_sources.py, test_ui_intake.py, test_ui_video_route.py, test_ui_video_route_traversal.py, test_ui_project_intake.py. Full-suite trigger: none named; the builder ran no full suite.
Pre-check[TP1]: 06d86f93 `uv --directory . run pytest tests/test_portal_access.py -o addopts= -m "not harness"` -> 20 passed t=190 blobs=tests/test_portal_access.py:93333e4,tests/portal_support.py:966876d
Pre-check[TP2]: 06d86f93 `uv --directory . run pytest tests/test_portal_comments.py -o addopts= -m "not harness"` -> 33 passed t=258 blobs=tests/test_portal_comments.py:c2f56eb,tests/portal_support.py:966876d
Pre-check[TP3]: 06d86f93 `uv --directory . run pytest tests/test_portal_share.py -o addopts= -m "not harness"` -> 8 passed t=233 blobs=tests/test_portal_share.py:74c9f6c,tests/portal_support.py:966876d
Pre-check[TP4]: 06d86f93 `uv --directory . run pytest tests/test_portal_access.py tests/test_ui_auth_escalation.py -o addopts= -m "not harness"` -> 20 + 22 passed (AU14 table, 22 passed t=164 on identical content, run before the commit) t=354 blobs=tests/test_portal_access.py:93333e4,tests/test_ui_auth_escalation.py:f6df017
Pre-check[TP5]: 06d86f93 `uv --directory . run pytest tests/test_portal_requests.py -o addopts= -m "not harness"` -> 14 passed t=184 blobs=tests/test_portal_requests.py:3a374ce,tests/portal_support.py:966876d
Pre-check[TP6]: 06d86f93 `uv --directory . run pytest tests/test_portal_comments.py -o addopts= -m "not harness"` -> 33 passed (TP6 tests are in the same file as TP2) t=258 blobs=tests/test_portal_comments.py:c2f56eb,tests/portal_support.py:966876d
Pre-check: 06d86f93 `uv --directory . run pytest tests/test_portal_access.py tests/test_portal_share.py tests/test_portal_requests.py tests/test_portal_comments.py -o addopts= -m "not harness"` (run file by file, the six tagged lines above) -> 75 passed t=865 blobs=tests/test_portal_access.py:93333e4,tests/test_portal_share.py:74c9f6c,tests/test_portal_requests.py:3a374ce,tests/test_portal_comments.py:c2f56eb,tests/portal_support.py:966876d
Metrics: start=2026-10-12T00:00:00Z end=2026-10-12T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=6 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=0 mutants=6 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv --directory D:/autoTesting/.worktrees/t198b-video-intake run pytest tests/test_portal_access.py -o addopts= -m "not harness"` -> expected: 20 passed
- same for `test_portal_share.py` (8), `test_portal_requests.py` (14), `test_portal_comments.py` (33) -> expected: all passed
- `... run pytest tests/test_ui_auth_escalation.py tests/test_ui_auth_groups.py tests/test_routers_list.py -o addopts= -m "not harness"` -> expected: passed (AU14 pins all 17 portal rows; the route walk covers every route)
- `... run ruff check src tests scripts` -> expected: All checks passed
- `... run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- ruff: `All checks passed!`; doctor: `doctor: clean` (after the final edit, before the commit).
- Existing tests touched by the change, file-scoped: 48 passed (routers_list, ui_auth_groups, team_enums_home, policy_merge); 59 passed + AU14 fixed then 22 passed (ui_auth_surface, escalation, ui_sources, refusal_audit, survivors); 55 passed (ui_intake, ui_video_route, ui_video_route_traversal, ui_project_intake).
- AU14 first went red because the pinned table did not know the 17 new rows; the rows were added to the table (not derived from `PORTAL_POLICY`), then green.
- Timings are slow on this host (uv start-up dominates, 75-80 s per file).

## Capability coverage (each new claim -> its isolating falsification)
Each edit ran on a throwaway copy of src/tests/docs/scripts/pyproject outside the worktree (`falsify.py` in the scratchpad), the worktree venv python with `PYTHONPATH=<copy>/src`. Same node green before and red after.

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| TP1 | bytes are served only behind the membership check; non-member gets request-access and no bytes | tests/test_portal_access.py::test_tp1_a_signed_in_non_member_gets_request_access_and_no_bytes; policy.py:51 (`media` is a `video` rule) | policy.py: `("GET", _V + "/media"): _video(K.VIDEO_VIEW)` -> `_key(K.VIDEO_VIEW)` (page-level check only) | before `3 passed`, after `3 failed` (the media request returns the bytes to the non-member) |
| TP2 | comment text is escaped on every page | tests/test_portal_comments.py::test_tp2_a_script_comment_is_text_on_the_page | video_portal_view.py `esc`: `escape(str(value), quote=True)` -> `str(value)` | before `1 passed`, after `1 failed` (`<script>alert(1)` found in the page) |
| TP3 | a share link grants nothing by itself | tests/test_portal_share.py::test_tp3_possessing_the_url_grants_nothing | routes_access_requests.py `open_share_link`: drop `and authorize(who, K.VIDEO_VIEW, res)` (the link redirects to the video) | before `1 passed`, after `1 failed` (tester gets 303, expected 404 + Request access) |
| TP4 | share routes need `video.share`, not just view | tests/test_portal_access.py::test_tp4_a_tester_with_a_share_can_read_and_comment_but_not_share_or_promote (and AU14 pins every row) | policy.py: `_video(K.VIDEO_SHARE)` -> `_video(K.VIDEO_VIEW)` for the three share routes | before `1 passed`, after `1 failed` (tester's share POST is not refused) |
| TP5 | approving is idempotent and creates exactly one Share | tests/test_portal_requests.py::test_tp5_the_uploader_approves_and_the_requester_gets_in_exactly_once | video_requests.py `decide`: drop the `status = pending` guard and `INSERT OR IGNORE` -> `INSERT` | before `1 passed`, after `1 failed` (second approve breaks on the share primary key). A first edit that dropped only the guard stayed green because `INSERT OR IGNORE` alone also holds the invariant: two layers, not one |
| TP6 | promoting keeps the comment | tests/test_portal_comments.py::test_tp6_promoting_a_comment_gives_the_pointer_the_parser_accepts | video_comments.py `promote`: add `DELETE FROM video_comments WHERE id = ?` | before `1 passed`, after `1 failed` (the comment is gone after promoting) |

Raw runner lines are in the scratchpad: `falsify.out` (TP1-TP4, TP6) and `falsify5.out` (TP5). Other mutations the contract names (accept `at_s` > duration, derive the token from the video id, widen `@shared` to `@all`, scope `access.approve@own` as `@all`) are covered by parametrised tests (`test_tp2_the_second_must_be_inside_the_video` etc.) but were not separately mutated.

## Live browser evidence
UI-touching. The checker runs Mode D (the maker runs no browser on this host). Surface to walk, personas developer (uploader) and tester (gets a share):
- `/shared` (Videos list and "My access requests"); the video page `/projects/<slug>/videos/<video_id>` (player, comment form, "Use current time", seek buttons, edit / delete / "Make a pointer", share panel for the uploader only); the request-access page (no title and no player, role-terms text); `/access-requests` (approve / decline); the share-link page (link shown once); nav links "Videos" and "Access requests" (only for holders of video.view / access.approve).
- Check in the browser: a comment button jumps the player to its second; a `<script>` comment stays text; controls the viewer cannot use are absent; keyboard operation and visible labels on every form.
Evidence directory: not yet created (`qa/evidence/browser-t198b-developer-portal-2026-10-12/` is the checker's).

## Findings and HELD items
- HELD (TP5 own-scope on real data): the default intake gate (`ui/intake_gate.py` `OpenGate`) records `uploaded_by=None` for a real upload, and no gate is installed by T-204 (`set_gate` has no caller). So "a developer approves only their own videos" and the uploader as approver hold in the tests (which record the uploader), but on real uploads the only approvers today are admins and the project's sub-admin. Question for Umesh: may the default gate become session-aware (record the signed-in email as `uploaded_by`)? It is T-198a's TI10/TI11 HELD item; it is not changed here.
- Decision taken (fails closed): a project-level share does not cover videos; only video-level shares grant access to a video.
- Not served: thumbnail and transcript endpoints. The portal serves the media file only.
- Residual: uvicorn's own access log writes the request line, so a token in `/v/<token>` reaches that log; the app's own logs and the audit file store the route template only (tested). Fix, if wanted, is a log filter at the server level.
- Authorship and self-approval compare the lower-cased account email (no group or name compare).
- The T-204 stubs for the portal routes stay beside the real routers (nothing deleted). T-205's `merge_route_policies` is not wired.
- Linux/CI note: the tests use a cheap argon2 hasher via monkeypatch and `TestClient`; nothing is Windows-specific except path separators handled by `pathlib`.

## Status: checked-PASS
