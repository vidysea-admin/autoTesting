# Contract — team intake and developer portal: zip and Drive intake (G3, T-198a) and the share / access-request / comment portal (G9, T-198b)

**Covers:** the two T-198 units of Group 10. **G3 `t198a-zip-drive-intake`** (rows TI1-TI11; spec R39-R42 and R65) and **G9
`t198b-dev-portal`** (rows TP1-TP6; spec R61-R63). **Owner:** /checker. **Status:** ACTIVE (2026-10-07).
**Criticality:** HIGH. **CRITICAL** rows: TI1, TI2, TI9, TI10, TP1, TP4 (a hosted attack surface: untrusted archives, untrusted
links, and the byte route). Tier L (security/auth/tenancy plus filesystem writes from untrusted input), so each unit gets a **dual
check**; the falsification floor is per row, and every row below names its mutation.
**Serves:** D-072 items 2, 3, 4, 7 and 10; D-066 (Origin guard); intent O9, O14, O15 (O7 for the byte route); spec R39-R42, R61-R63, R65;
`core-invariants.md` C1-C5.
**Depends on:** `auth.md` (the permission catalogue, the default groups, `authorize()`, AU11-AU14), `hosting.md` (HO15, HO30-HO33),
`ingest.md`, `source-adapters.md` (SA1, SA2), `consent.md`.

## Unit ownership (nothing here duplicates another contract)

| unit | rows | note |
|---|---|---|
| **G3 / T-198a** | TI1-TI11 | zip expansion, Drive link intake, provenance, `video.upload` gating |
| **G9 / T-198b** | TP1-TP6 | share link, request-access flow, timestamped comments, route-by-route permissions |
| `hosting.md` HO30-HO33 | already exist | the **streaming upload limit** on the HTTP route (HO30), the proxy ceiling (HO31), the Drive host allow-list and redirect rules (HO32), the Drive fetch bound and honest failure states (HO33). G3 **references** them and is judged on them there; this file never restates a row. TI9 adds only what they do not say (one limit, three paths) |
| `auth.md` AU11-AU14 | already exist | default groups, the single `authorize()`, visibility without leakage, default-deny routes. G9 is judged on them through TP4; this file adds the Group 10 routes to their enumeration |

**Permission keys used (all exist in `auth.md`; this contract adds none):** `video.upload` (G3); `video.view`, `video.share`,
`access.approve`, `comment.create`, `project.view` (G9). A route or action that seems to need a key outside that catalogue is a contract
gap to raise with the checker (spec R63), never a reason to invent one.

**Roles (D-072 group answer, `auth.md` default groups):** Admin/CEO acts on everything (`@all`); a Developer acts on their own projects
and videos (`@own`) and approves access only to their own videos; a Sub-admin manages the projects assigned to them (`@assigned`); a
Tester sees only what was shared with them (`@shared`) and may comment. For a **video** resource, `owner_email` is the video's uploader
(`Source.uploaded_by`, TI11); for a **project** resource it is the project's creator, as `auth.md` defines. A source with no recorded
uploader matches only `@all` (fails closed).

## Verification classes

`LOCAL` = the checker runs it on the dev host (Windows), with fakes: a fake `DriveClient` and fake HTTP transport, an injected clock, a
small configured limit (for example 5 MiB) instead of 2 GiB, no real Google call and no model call. `BROWSER` = Mode D with the checker's
own browser and the named persona. `SERVER-GATED` = needs the real Ubuntu server, the proxy or a real Drive file; it gates go-live
(the T-203 rehearsal), not the unit's code PASS. **R65 (Windows and Ubuntu):** every row below that touches a path, a staging directory,
a lock or a marker is judged on Windows by the checker and must also pass on Linux; the Linux run is recorded in
`qa/evidence/t198-linux-run.md` (it may come from T-203's Ubuntu check, as in `auth.md` AU24). TI1 and TI6 carry the R65 assertions.

## A. Intake (unit G3, T-198a)

- **TI1 — A zip member cannot escape staging, on Windows and Ubuntu path rules (CRITICAL; R39, R65).** Refused, by name with a reason,
  and never written: a name with `..` in any position (`../x`, `..\x`, `a/../../x`, `a\..\..\x`), an absolute path (`/abs`,
  `\abs`), a drive letter (`C:\x`, `C:x`), a UNC path (`\\host\share\x`), a Windows alternate data stream (`a.mp4:evil`), a Windows
  reserved device name (`CON`, `NUL`, `AUX`, `COM1`, `LPT1`, with or without an extension), a name with a NUL byte or a bidi/control
  character, and any entry whose mode marks it as a symlink, hardlink, device, FIFO or socket. **The same hostile zip gives the same
  refusals on Windows and Linux**: both separators are treated as separators on both hosts. Nothing is extracted with `ZipFile.extractall`
  or `extract`; each destination is built by the code from a generated name (TI4), then resolved and verified to lie inside the staging
  directory (`pathlib`, `Path.resolve()` and `is_relative_to`, never a `startswith` on a string).
  *Re-derive:* one fixture zip per hostile name above plus one benign video; plant a sentinel file one level above staging and another at
  the host's temp root; after the run the sentinels are byte-identical, the staging tree holds no entry outside it, the report names
  each refused member and the reason, and the benign video is still registered (TI5). *Mutation:* replace the containment check with
  `str(dest).startswith(str(staging))` on an unresolved path -> the `..\x` and `a/../../x` cases fail; split only on `/` -> the
  `..\x` and `C:\x` cases fail. `serves:` O9, R39, R65, D-072#7. *LOCAL.*
- **TI2 — Bomb limits refuse before extraction and hold while streaming (CRITICAL; R39).** Caps on: total entries, video count, per-file
  uncompressed bytes, total uncompressed bytes, the archive's own size, and compression ratio; nesting is depth 0 only (a member named
  `*.zip`, `*.7z`, `*.rar`, `*.tar`, `*.gz`, `*.tgz`, or whose first bytes are a zip signature, is refused as a nested archive). A
  violation visible in the central directory is refused **before any byte is written** and names which limit it hit. A header that lies
  about a size is caught **while inflating**: bytes written for a member never exceed its cap plus one chunk, and the whole expansion
  never exceeds the total cap plus one chunk; the offending member is removed, not left half-written. The per-file cap is the admin
  `max_upload_bytes` (`hosting.md` HO15, default 2 GiB); the other caps are named defaults in one place (checker-chosen: 1000 entries,
  20 videos, 10 GB uncompressed, 5 GB archive, ratio 100:1) and are not literals scattered through the code; a missing or corrupt
  settings value falls back to them and says so. *Re-derive:* with caps injected small, a zip of zeros claiming a huge size
  (zero bytes written, limit named); a zip whose central directory understates a member (stops at cap + one chunk); an
  over-ratio member; a nested zip; more entries than the cap. *Mutation:* trust the declared `file_size` only -> the lying-header case
  fails; remove the ratio check -> the ratio case fails. `serves:` O9, R39, D-072#10. *LOCAL.*
- **TI3 — One source per video; everything else is accounted for; the file-type allowlist (R39).** A zip of 3 videos, 1 PDF and 1 text
  file registers exactly 3 `VIDEO` sources, and the other 2 appear in `skipped[]` with a reason. The allowlist is the existing
  `ingest.require_recording_suffix` / `RECORDING_SUFFIXES` (one definition; a second suffix list in `zip_intake.py` is a defect, `core-invariants.md`
  "one concept, one place"). A member with no suffix, a dotfile (`.env`), an executable or script (`.exe`, `.bat`, `.ps1`, `.sh`, `.js`) or a
  directory entry is never registered, never copied out of staging, and appears in `skipped[]` (directories are not listed). A skipped
  member's bytes are not kept past the run. The result, as JSON from the CLI and as the per-member table on the Add-videos page, gives each
  member exactly one of `registered | duplicate | skipped | failed` with its reason. *Re-derive:* the 5-member fixture; a `.env` and a
  `run.ps1` member; the page in a live browser as `dev` (the table is readable without the log). *Mutation:* register every member ->
  the count test fails. `serves:` O9, R39. *LOCAL* + *BROWSER* (persona `dev`).
- **TI4 — Dedupe, and no stored path comes from a member name (R39; SA2).** The same bytes (sha256) already registered in the project are
  not registered again and are reported `duplicate` with `duplicate_of=<source id>`; two members with the same basename get distinct
  stored names and neither overwrites the other; the stored path is built only from the generated source id and the vetted suffix, never
  from the member name, the Drive file name or any other supplied text (unicode, spaces, trailing dots and very long names are
  irrelevant to the stored path). The member's name is kept as the label after the same redaction a label already gets. Nothing already on
  disk is overwritten. *Re-derive:* the same video twice in one zip and again in a second upload; two `a/clip.mp4` and `b/clip.mp4`;
  a 300-character name; a name of `con.mp4`. *Mutation:* build the stored name from `member.filename` -> the traversal and collision tests
  fail. `serves:` O9, R39, source-adapters.md SA2. *LOCAL.*
- **TI5 — A partial failure is partial, never success (R39).** A corrupt member (bad CRC, truncated, an encrypted member, a member that
  fails to inflate) is `failed` with a reason and the others still register; the overall status is `partial` and the CLI exit code is
  non-zero (2), never `ok` / 0. A refused hostile member (TI1, TI2) counts as `failed`/refused in the same table. An archive that is not a
  zip at all gives one `failed` and registers nothing. *Re-derive:* a zip with one flipped byte in the middle member, one with a password-protected
  member, a renamed `.txt`; assert status, exit code and which rows registered. *Mutation:* return `ok` whenever at least one member
  registered -> fails. `serves:` O9, R39, D-070. *LOCAL.*
- **TI6 — Registration is atomic and staging is cleaned (R39, R65).** A process killed or an exception raised after member N has
  been copied leaves **no source row without its file and matching sha256, and no file without its row**; staging for that run is removed
  on the next intake (or immediately on a normal exit and on an exception) and is under the project's working area, never in the repo
  tree or the system temp root by an unchecked name. The commit step uses portable primitives only (write to a temp name in the destination
  directory, `os.replace`; no `fcntl`, no `flock` as the only guard, no POSIX-only call at module top level), so it behaves the same on
  Windows and Linux. *Re-derive:* fault injection after member 2 of 3 (rows and files agree; a re-run converges to 3 sources, no duplicates);
  an exception inside the copy; two intakes into one project at the same time (no row lost, no row duplicated). *Mutation:* write the row
  before the copy -> the crash test fails. `serves:` O9, R39, R65. *LOCAL.*
- **TI7 — Drive intake lands on a stable path through the existing `gws` auth (R40).** `ingest fetch-drive <file-id-or-link>`, and the
  same from a pasted link on the Add-videos form, parse the link into a Drive id (the file, `open?id=`, `uc?id=`, folder and bare-id
  forms are accepted and the id must match the Drive id character set; every other shape is refused). Which hosts and redirects are
  allowed is `hosting.md` HO32 and is not restated or loosened here. The fetch goes through the existing `gws` authentication (no second
  credential store), stages under the working directory, **verifies the byte count and md5 against Drive's metadata when Drive supplies them
  (a mismatch refuses, nothing is registered, staging is removed)**, copies to the project's stable source path (TI4 naming), then registers
  exactly as an upload does (same size limit, TI9; same owner, TI11). A **folder** id lists the folder and fetches each video (video count cap
  from TI2); non-video files are listed as `skipped` with a reason and **are not downloaded**. A **zip** id goes through TI1-TI6 after the
  fetch. The Drive file name is untrusted and is never used in a path (TI4). `serves:` O9, R40, D-072#10. *Re-derive:* fake `DriveClient`:
  a file with a good md5 (registers, path under the project), a wrong md5 and a short read (refused, no row, no staging), a folder with
  2 videos and a PDF, a zip id with a hostile member. *Mutation:* skip the md5 compare -> the wrong-md5 case fails. *LOCAL* (real Drive is
  *SERVER-GATED* and needs an approved, synthetic, non-student video, `hosting.md` HO33).
- **TI8 — Drive failures are five distinct messages, and no token is ever printed (R40).** Not authenticated, permission denied, not found,
  quota exceeded and network error each give a different, typed, human-readable message that says what to do next (HO33 states the
  "make it viewable / share it with the server's Google identity" text; this row requires the five to be told apart, not collapsed into
  one). No access token, refresh token, device code, `Authorization` header or signed URL appears in stdout, stderr, any log line, the audit
  file (`auth.md` AU22), the failure message, the source row or the page. *Re-derive:* one fake `DriveClient` response per class asserting
  five distinct messages; plant a canary token in the fake credential and in each error body, then grep captured stdout, stderr,
  `caplog`, the audit file and `sources.jsonl` for the canary. *Mutation:* include `repr(exc)` of the transport error in the message ->
  the canary grep fails. `serves:` O9, R40, O7, `browser-and-secrets.md` B5-B9. *LOCAL.*
- **TI9 — One upload limit, read at request time, for all three intake paths, enforced by streaming (CRITICAL; R41; D-072#10).** The
  upload limit is the admin setting `max_upload_bytes` (default **2 GiB**, `hosting.md` HO15), configurable without a restart. The
  HTTP upload (judged in detail by HO30: exact-limit succeeds, limit + 1 gets 413 with no partial file and no row, a lying or missing
  `Content-Length` changes nothing), the Drive fetch (HO33) and the zip member inflation (TI2) **all call the same accessor**; there is no
  second copy of the limit and no literal `2 * 1024**3` outside the settings default. Whichever path hits it, the read stops at limit + at
  most one chunk, the partial file is removed and the message names the limit in human units. The Add-videos page shows the current
  limit. Changing the setting from 2 GiB to a small value changes the behaviour of all three paths on their next request. A body with no
  end (an endless generator) cannot hold a worker: it ends at the limit. *Re-derive:* with the setting at 5 MiB, exactly 5 MiB succeeds
  and 5 MiB + 1 byte is refused on each of the three paths; change the setting between two requests and watch the second obey it; an
  endless generator body bounded by limit + one chunk; `grep` of `src/` for a second limit. *Mutation:* hard-code a different limit in
  the Drive path -> the change-the-setting test fails; trust `Content-Length` only -> the endless-body test fails. `serves:` O9, R41,
  D-072#10, hosting.md HO15/HO30/HO33. *LOCAL* (one real >= 1 GiB upload through the proxy is *SERVER-GATED*, HO30).
- **TI10 — Intake needs a signed-in member holding `video.upload` on that project (CRITICAL; R42).** The upload, zip and Drive-link routes
  and the `fetch-drive` background job: an unauthenticated request is refused (302 to sign-in for a browser, 401 otherwise) and no file is
  written and no row created; a signed-in user without `video.upload` on **that** project gets 403 naming the permission; a project the
  user may not view answers as one that does not exist (404, `auth.md` AU13), so intake cannot probe project names. Scope follows
  `auth.md`: a Developer holds `video.upload@own` (their own projects only), a Sub-admin `@assigned`, Admin `@all`, a Tester and a
  signed-up user in no group hold none. Permission is checked when the request arrives **and again when the queued Drive fetch starts**
  (a user disabled in between gets `refused`, no bytes fetched), as `hosting.md` HO19 does for runs. The Origin/CSRF guard (D-066) still runs
  before authentication on every state-changing route. Every intake route is declared in the central policy table (`auth.md` AU14).
  *Re-derive:* the matrix (Admin, Sub-admin assigned and not, Developer own and not, Tester, no-group, anonymous) x (upload, zip, Drive
  link) with the sentinel/row checks; a cross-origin POST with a valid session cookie. *Mutation:* delete the `video.upload` decorator from the zip
  route -> the Tester case fails. `serves:` O9, O15, R42, R64, D-072#3, D-072#4. *LOCAL.* A loopback-only stub is **not** evidence for this
  row: if G3 is built before T-204's `authorize()` exists, TI10 stays `HELD` and the unit cannot close the task.
- **TI11 — Every source records who supplied it, when, and from where (R42).** `Source` (`schema/project.py`, `extra="forbid"`)
  gains `uploaded_by` (the authenticated user's email, taken from the session, **never from a form field or a request body**: a
  client-supplied value is ignored), `uploaded_at` (server UTC ISO timestamp) and `origin` (typed, exactly one of an upload with its
  original file name, a zip with the archive name and the member path, or Drive with the file id). The stored path/label rules of TI4
  still hold. `uploaded_by` is the video's owner for `@own` scoping in G9 (`TP4`, `TP5`). A `sources.jsonl` written before this change still loads (the new
  fields default to none, and such a source is owned by nobody and so matches only `@all`); the content-derived source id is unchanged by the new fields, so
  existing ids and dedupe (TI4, SA2) do not move. `origin` and `label` pass `Redactor.scrub` before they are stored. *Re-derive:* upload as
  user A while sending `uploaded_by=B` in the form (stored as A); a zip member and a Drive file give the two other `origin` shapes; load a
  fixture `sources.jsonl` from before the change and assert ids are unchanged; model test for `extra="forbid"`. *Mutation:* read
  `uploaded_by` from the request -> the spoof test fails. `serves:` O9, O15, R42. *LOCAL.*

## B. Portal (unit G9, T-198b; depends on G3 and T-204)

All G9 routes are state-changing or data-bearing and so are subject to `auth.md` AU14 (declared in the policy table), AU13 (visibility
without leakage) and AU18 (Origin guard before authentication). Where this section says "route-by-route" it means every method of
every Group 10 route added by G9: the video page, the video byte route, share-link create/revoke, request-access create/list/approve/
decline, and comment create/list/edit/delete/promote.

- **TP1 — The bytes are behind the membership check, not only the page (CRITICAL; R61).** A signed-in user with no access to a video
  (not in its `shared_with`, no scope that covers it) receives the **request-access page** and **no video bytes**: the media/byte route
  (including range requests, the thumbnail and the transcript if one is served) returns 403/404 with no body from the file, asserted at the byte
  route itself, not only on the page. An unauthenticated request to the video page or the byte route redirects to sign-in (the
  same-site `next` rule of `auth.md` AU16) and returns no bytes. Access is `video.view` at a scope that covers the video: `@all`, `@assigned` (the
  video's project is assigned), `@own` (the uploader, TI11) or `@shared`. Revoking access (removing the share, un-assigning the user, disabling the account) stops the **next** request, including one with a live
  cookie and a cached player URL. Bytes are served from a path resolved by id inside the project's sources directory, never from a
  client-supplied path. *Re-derive:* the matrix (Admin, Sub-admin assigned and not, Developer owner and non-owner, Tester shared and
  not, no-group, anonymous) x (page, full GET, `Range` GET) with the sentinel bytes asserted absent for every denied case; revoke
  then re-request. *Mutation:* check membership on the page route only -> the byte-route case fails; a path-traversal id (`../x`) returns nothing. `serves:` O14, O15, O7, R61. *LOCAL* +
  *BROWSER* (persona `tester`: the non-shared video is absent from "Shared with me", the direct URL shows request access, no player).
- **TP2 — Timestamped comments (R62; permission `comment.create`).** A comment has `at_s` within `[0, duration_s]` (a source without a known
  duration accepts only a non-negative finite number and is refused above the file's probed length once known), text (1 to 2000 characters after
  trim), the author (taken from the session, not from the body) and `created_at`; it is visible to everyone who can view that video
  (TP1); its author may edit it (an `edited` marker and `edited_at` are kept) and delete it, and a holder of `comment.create@all` or an
  admin may delete anyone's. Refused with 4xx and nothing stored: `at_s` negative, NaN, infinite, above the duration or not a number;
  empty or oversize text; creating a comment without `comment.create` at a scope covering that video. A **Tester** with `comment.create@shared`
  can comment on a shared video and on no other. Text is stored as given and **rendered escaped everywhere** (page, list, email or export):
  `<script>alert(1)</script>` and `"><img onerror=...>` never execute. A comment's second jumps the player to that second for every viewer.
  *Re-derive:* boundary values `at_s` = -0.001, 0, duration, duration + 0.001, `nan`; a script comment loaded in the checker's browser with
  the console watched; author spoof (`author=admin` in the body); a Tester commenting on a shared and an unshared video. *Mutation:*
  render text with `|safe`/raw -> the script test fails; accept `at_s > duration` -> fails. `serves:` O14, R62. *LOCAL* + *BROWSER*
  (personas `dev` and `tester`: a comment click seeks the player).
- **TP3 — The share link is non-guessable, needs sign-in, and carries no capability (R61).** A holder of `video.share` (scope `@own` for a
  Developer, `@assigned` for a Sub-admin, `@all` for Admin) can create and revoke a video's share link and add or remove people in
  `shared_with`. The link's token is at least 128 bits from `secrets` (not derived from the video id, the project name, a counter or a
  timestamp), is unique per link, and is compared in constant time. **Possession of the URL grants nothing by itself**: opening it
  while signed out goes to sign-in, then applies TP1 (a signed-in non-member gets request access, never the bytes). Revoking the link
  stops it on the next request; deleting the video or project removes its links. A token is never written to a log line or the audit file
  (`auth.md` AU22: path templates, not values), and a revoked, unknown, truncated or oversized token returns the same response as any
  unknown video (no existence leak). A user without `video.share` on that video gets 403 from create and revoke. *Re-derive:* create a link,
  assert token length and entropy shape, 1000 links are distinct; open it signed out (redirect, no bytes), as non-member (request-access
  page, no bytes), as a member (the player); revoke and re-open; canary-grep logs and the audit file for the token. *Mutation:* make the link
  itself grant access -> the non-member case fails; derive the token from the video id -> the uniqueness test fails.
  `serves:` O14, O15, R61. *LOCAL.*
- **TP4 — Permissions are enforced server-side, route by route, with the UI ignored (CRITICAL; R63; `auth.md` AU11-AU14 apply).**
  A table-driven test iterates **every Group 10 route G9 adds**, every method, against the default groups and relations in `auth.md`
  (Admin/CEO, Sub-admin, Developer, Tester, and a user in no group, each against the relations own / assigned / shared / none) and
  calls the routes directly, never through the UI. Expected: a user without the permission, or outside its scope, gets 403, and a project
  or video the user may not view is **absent** (the 404 of a resource that does not exist, `auth.md` AU13), not "forbidden"; Admin reaches every
  route; a Sub-admin only assigned projects; a Developer their own and what was shared; a Tester only shared items, with read and comment
  only (no share, no approve, no upload); a signed-up user in no group reaches only the waiting-for-access page (`auth.md` AU6).
  Every G9 route is declared in the central policy table and the route-enumeration test (`auth.md` AU14) fails on one that is not.
  **No permission key outside `auth.md`'s catalogue is introduced** (the test diffs the keys the G9 routes declare against the
  catalogue). No route compares an email or a group name itself (`auth.md` AU12): every decision goes through `authorize()`. *Mutation:*
  delete one permission declaration -> the table test fails; widen `@shared` to `@all` -> fails. `serves:` O15, R63, R64, D-072#4. *LOCAL.*
- **TP5 — The request-access flow: a developer approves access to their own videos (R61; permission `access.approve`).** A signed-in
  user without access who asks for it on the request-access page creates an `AccessRequest` that records requester (from the session),
  video, time and status `pending`; asking twice for the same video is one pending request. The request page tells the requester **who will
  be asked in role terms**, not a list of emails. The request is delivered to everyone who may approve it: the video's uploader (a
  Developer, `access.approve@own`), a Sub-admin of that project (`@assigned`), and any Admin (`@all`), and appears on their Access requests
  page; if SMTP is configured, a notification mail is sent only through the shared transport (`hosting.md` HO27-HO29: it carries a link
  and no video, thumbnail or comment text, and a mail failure never blocks the request). **Approving creates exactly one `Share` on that
  video for that requester, once** (a second approve, a double click or a replay changes nothing); declining records the decision and
  creates no `Share`. **A Developer cannot approve or decline a request for someone else's video**, and cannot approve for a project they
  do not own; a Sub-admin cannot act outside assigned projects; the requester cannot approve their own request even if they also hold
  `access.approve` elsewhere. The requester sees the outcome on the next page load, and an approved requester then passes TP1. Approvers
  see only the requests they may act on (TP4, absence not 403). *Re-derive:* Tester-B requests a video uploaded by Dev-A; Dev-A approves
  (one `Share`, the video now opens for B); Dev-C attempts to approve (404/403, no `Share`); the Sub-admin of that project and an Admin
  approve a second request; a double POST of one approval; a decline. *Mutation:* make approve non-idempotent -> the double-POST test
  fails; scope `access.approve@own` as `@all` -> Dev-C's attempt succeeds and the test fails. `serves:` O14, O15, R61, D-072 group answer. *LOCAL* + *BROWSER*
  (persona `dev`: finds and approves the request; persona `tester`: asks, then gets in).
- **TP6 — A comment can be promoted to a pointer, and the comment stays (R62).** Promoting a comment (by someone holding `project.edit` on
  the video's project, since a pointer steers a review; scope as in `auth.md`) creates a `Pointer` in the format the pointer parser of the
  review unit (G2, proposed `team-video-review.md` TV1) accepts, with the comment's second as its timestamp and the comment text as its free
  text; the original comment is unchanged; promoting twice creates one pointer. A user without `project.edit` gets 403 and creates
  nothing. The pointer text passes the parser **the same way a typed one does**: a comment whose text cannot parse is promoted as free
  text, never dropped or crashing. If the G2 `Pointer` type does not exist when G9 is checked, TP6 is `NOT MET`, not vacuous.
  *Re-derive:* a comment at 754 s promoted -> the parser returns a pointer at `12:34`; the comment still lists; a second promotion is a no-op;
  a Tester's attempt is refused. *Mutation:* delete the comment on promotion -> fails. `serves:` O14, R62. *LOCAL.*

## Persona walks (Mode D)

G3: persona `dev` (upload a zip with a bad member, read the outcome table, paste a Drive link, hit the limit message). G9: personas
`dev` (share, approve a request for their own video, promote a comment) and `tester` (reach a shared video in two clicks from sign-in,
comment, ask for access to a video that was not shared). `lead`/Admin controls must not be shown to `tester`. Every form control has a
visible label and is keyboard-operable (as `auth.md` AU26). Zero unexplained console errors. Evidence under
`qa/evidence/browser-t198a-*-checker/` and `qa/evidence/browser-t198b-*-checker/`.

## Out of scope / ignore

- Streaming-limit mechanics on the HTTP upload route (HO30), the proxy ceiling (HO31), the Drive host allow-list and redirect rules
  (HO32) and the Drive fetch bound (HO33): judged in `hosting.md`, not here.
- The permission engine, accounts, groups, sign-up and the waiting page (T-204, `auth.md`); the server settings store (T-203, HO15).
- The pointer parser and the review itself (G2), the bug tracker and sheet sync (G6-G8), the schedule and Test button (G5, G7), report
  delivery (`hosting.md` HO25-HO29).
- Inspecting a video's content (a codec/container probe beyond the suffix allowlist), antivirus scanning of uploads, transcoding.
- Public (no sign-in) sharing, expiring links, per-comment permissions, threaded comments, reactions, mentions, a comment-edit history.
- Wording, colours and layout beyond the labelled, keyboard-operable controls.

## No-fire list (must NOT happen)

- No file written outside the staging directory by an archive member; no sentinel changed; no use of `ZipFile.extractall`.
- No member name, Drive file name, `Content-Disposition` or other supplied text used to build a stored path.
- No source row without its file and hash, and no file without its row, after a crash or a refused intake.
- No token, device code or credential in stdout, stderr, a log, the audit file, a source row, a page, or a mail.
- No video byte, thumbnail or transcript served to someone without access, on any route, range request or method.
- No share URL, request token or comment text that executes in a browser; no access granted by possessing a URL alone.
- No approval of an access request by a person who may not approve it; no second `Share` from one approval.
- No new permission key; no route reachable without a declared permission; no check done only in the UI.
- No second copy of the upload limit, the video suffix list or the permission catalogue.
- No real Google, SMTP or model call in the default test suite; no real student or Vidysea video used as a fixture.
- No Windows-only or POSIX-only primitive that makes a test pass on one host and fail on the other.

## Amendment log (append-only; git history is the version)

- 2026-10-07 · init · contract created for G3 (`t198a-zip-drive-intake`) and G9 (`t198b-dev-portal`) from the maker's proposal
  (`.work/plan-g10/contract-proposal-T-198.md`, refreshed for D-072) and the spec rows R39-R42, R61-R63 and R65. Folded: TI7 and TI8
  keep only what `hosting.md` HO32-HO33 does not state (the `gws` stable path, md5 verification, folder and zip ids, the five failure
  classes, token hygiene); TI9 states one limit across the three intake paths and leaves the HTTP streaming mechanics to HO30; TI12
  (outcome table, live browser) folded into TI3; TI13 (Windows and Ubuntu, R65) folded into TI1 and TI6 and the verification-class
  paragraph; TP7 (sign-up is not access) folded into TP4 and `auth.md` AU6. Added by the checker (not in the proposal): the encrypted-member
  and non-zip cases (TI5), the nested-archive signature sniff and the archive-size cap (TI2), the re-check of `video.upload` when a queued
  Drive fetch starts (TI10), the byte-route range and revoke-on-next-request cases (TP1), and the requester-cannot-self-approve and
  idempotent-approval cases (TP5). The zip cap defaults other than the 2 GiB per-file limit are checker-chosen and editable by a routine amendment.
