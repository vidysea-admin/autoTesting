# Build brief: t198-video-intake (goal task T-198, plan unit G3 `t198a-zip-drive-intake`)

Written 2026-10-11 by the readiness pass (read-only; nothing was built). Self-contained.
Contract: `qa/contracts/team-intake.md` section A, rows TI1-TI11 (ACTIVE 2026-10-07), plus the rows it defers to in `qa/contracts/hosting.md` (HO15, HO30-HO33), copied below. Spec: R39-R42, R65. Intent: O9, O14, O15.
Dispatchable: YES, as a CONTINUATION of the existing branch `wave/g3-zip-core` (slice 1, the pure core, is built). The remaining slice does not need T-205 and can start now.

Scope note: goal task T-198 covers two plan units. This brief is **G3 only** (zip and Drive intake, rows TI1-TI11). G9 `t198b-dev-portal` (share link, access requests, comments, rows TP1-TP6 of the same contract file) needs G3 and T-204 first and gets its own brief later; it is deliberately NOT in this one. The goal task stays open until both units have a checker PASS (`done_check`: `qa/verdicts/t-198-team-loop.md`).

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier L.** Triggers: security (untrusted archives and untrusted links writing to the filesystem: zip-slip, symlinks, bombs, nested archives), auth (intake routes require `video.upload`, TI10), data writes (source rows plus files must be atomic, TI6). The contract itself names "Tier L ... each unit gets a dual check".
- `Dual check: required`, triggers `security src/autotester/sources/zip_names.py:77` (`ensure_inside`, the containment check) and `security src/autotester/sources/zip_intake.py:214` (`expand_zip`, the untrusted-archive entry point), both on branch `wave/g3-zip-core`; `auth src/autotester/ui/routes_sources.py:169` (`upload_source`, the route that gains the `video.upload` gate and the session-derived `uploaded_by`).
- Persona walk: required (section 9).

## 2. Root and base

- Root: `D:/autoTesting`. Current `master` = `3a16616cf2c99a63c8d763150a1ca6410dfc0acc`.
- **Continue on the existing branch `wave/g3-zip-core`** (worktree `D:/autoTesting/.worktrees/g3-zip-core`, clean, tip `ac7df298`, 1 commit ahead, 57 behind master). Reasons: it holds slice 1 whole (7 new source modules, 7 test files, a manifest at `Fix cycle: 0`, 154 tests passing per the manifest). Starting over would repeat about 2200 lines.
- Bringing it current: MERGE master into the branch (not a rebase; keeps the commit the manifest cites). `git merge-tree` shows two touch points: `docs/MAP.md` (generated: take master's and rerun `uv run autotester map`) and `src/autotester/schema/project.py` (one import-block conflict: master added `from autotester.schema.user_persona import PERSONA_ID_PATTERN, UXPolicy`, the branch added `from autotester.schema.intake import SourceOrigin`; keep both). Nothing else conflicts.
- The manifest `qa/manifests/g3-zip-core.md` exists only on the branch; there is no verdict for it. Not landed. Under D-080 item 1 it reaches master only by the exact commit a checker PASS reviewed.
- Slice 1 is claimed as: TI1, TI2, TI4, TI5, TI6 full (LOCAL); TI3, TI7, TI9, TI11 partial; TI8 and TI10 not started.

## 3. Acceptance criteria (verbatim)

Source: `qa/contracts/team-intake.md` (header, ownership table, verification classes, section A rows TI1-TI11, persona walks, out of scope, no-fire list), then `qa/contracts/hosting.md` HO15 and HO30-HO33, which TI7 and TI9 say this unit is judged on. Section B (rows TP1-TP6) belongs to G9 and is left out on purpose.

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


### hosting.md HO15

- **HO15 — Server settings are an admin setting, validated, audited.** A `ServerSettings` model (`schema/`, `extra="forbid"`) stored
  under the data root holds `max_concurrent_runs` (default **2**) and `max_upload_bytes` (default **2 GiB** = 2147483648). A page
  reachable only with `settings.manage` edits them. Validation: concurrency is an integer 1..64, upload limit an integer between 1 MiB and
  64 GiB; anything else (0, negative, text, float, empty, overflow) is refused with a message that does not echo secret data and stores
  nothing. A change applies to the next dispatch / next upload **without a restart**, and writes an audit line (`auth.md` AU22). Missing
  or corrupt settings fall back to the defaults and say so. `serves:` D-072#6, D-072#10. *LOCAL.*
  *Re-derive:* boundary-value tests (0, 1, 64, 65, "2", "x", 2^63); change 2 -> 1 with two queued runs and see the next start obey it.

### hosting.md HO30-HO33

### E. Video intake (Group 10 / T-198; the limit is T-203's HO15)

- **HO30 — The upload limit is enforced while streaming.** The upload route reads the body in chunks to disk (memory does not grow with
  the file) and stops at `max_upload_bytes` read from the setting at request time: a file of exactly the limit succeeds; limit + 1 byte
  gets 413, leaves no partial file and no source row; a lying or missing `Content-Length` changes nothing. The upload page shows the
  current limit. Tested with a small limit (for example 5 MiB), not a 2 GiB file; one real >= 1 GiB upload through the proxy is
  *SERVER-GATED*. Requires `video.upload` on the project. `serves:` D-072#10. *LOCAL.* Mutation: trust `Content-Length` only -> fails.
- **HO31 — The proxy does not undercut the setting.** The prod proxy config takes its body-size ceiling from the same value (or a
  documented larger one) so a file within the admin's limit is not refused with 413 by Caddy/nginx; the guide says to raise both together.
  *LOCAL* (config test) + *SERVER-GATED.* `serves:` D-072#10.
- **HO32 — A Google Drive link is fetched by the server, and only Google hosts.** The user pastes a Drive link; the server resolves the
  file id and fetches it itself, as a queued background job, then registers it exactly as an upload (same limit, same ownership). The URL
  must be `https`, with a host exactly `drive.google.com` or `docs.google.com` (and the Google download host the API returns); each
  redirect hop is re-checked against the same rule and may not resolve to a loopback, private or link-local address. Refused, with a
  typed message that does not echo tokens: `http://127.0.0.1/x`, `file:///etc/passwd`, `https://drive.google.com.evil.io/file/d/x`,
  `https://evil.io/?u=https://drive.google.com/...`, a redirect to `169.254.169.254`, a non-Drive path. Requires `video.upload`.
  `serves:` D-072#10, O7. *LOCAL* with a fake HTTP transport (no real Google call in tests).
- **HO33 — The fetch is bounded and honest.** The fetch stops at the same `max_upload_bytes` (partial file removed), has a connect and a
  total timeout, accepts only a video content type, and surfaces its state on the page (`fetching`, `done`, or a typed failure). A link
  the server cannot read (private, deleted, quota page) gives a message saying how to make it viewable or share it with the server's
  Google identity, and never a stack trace. The credential the server uses for non-public files is a server-side secret under
  `auth.md` AU21 rules, never rendered. *Real* Drive fetch of an actual file is *SERVER-GATED* and needs an approved,
  synthetic, non-student video. `serves:` D-072#10. *LOCAL.*


## 4. What exists and what is missing

Exists on branch `wave/g3-zip-core` (NOT on master). Line counts are from the branch tip:

| Module | Lines | Job / key symbols |
|---|---|---|
| `src/autotester/sources/zip_names.py` | 91 | `vet_member_name` :38 (string-only, both separators on every host; takes `ZipInfo.orig_filename`), `ensure_inside` :77 (resolved `is_relative_to`), `special_mode_kind`, `is_nested_archive_name`, `looks_like_archive`, `display_name` |
| `src/autotester/sources/bounded_write.py` | 64 | `copy_bounded`: chunked, hashing, refuses before a chunk that would pass the cap, removes the partial |
| `src/autotester/sources/intake_commit.py` | 169 | `intake_lock` :54 (`O_CREAT\|O_EXCL`, stale takeover), `sweep_orphans` :85, `intake_session` :108, `commit_video` :141 (file first via `os.replace`, row second, file removed if the row fails; stored path `sources/<id>/recording<suffix>`) |
| `src/autotester/sources/zip_intake.py` | 253 | `expand_zip` :214 (plans every member from the central directory before any write; returns an `IntakeReport` with status ok/partial/failed, exit_code 0/2, one outcome per member) |
| `src/autotester/sources/drive_verify.py` | 102 | `DriveFetcher` / `DriveDownload` protocols, `fetch_and_verify` :75 (Drive-id charset, declared-size pre-check, bounded stream, size and md5 compare, partial removed, `verified=False` when Drive gave neither) |
| `src/autotester/core/upload_limit.py` | 75 | `read_max_upload_bytes` :61 (the ONE accessor, read on every call, 1 MiB..64 GiB, falls back to 2 GiB and says why), `human_bytes` :38. Until T-203 lands `ServerSettings` it reads `max_upload_bytes` from the JSON file named by `AUTOTESTER_SERVER_SETTINGS` |
| `src/autotester/schema/intake.py` | 117 | `DEFAULT_MAX_UPLOAD_BYTES` (the only 2 GiB literal), `ZipLimits`, `IntakeOutcome`, `IntakeStatus`, `MemberResult`, `IntakeReport`, `UploadOrigin\|ZipOrigin\|DriveOrigin` union (`SourceOrigin`) |
| `schema/project.py::Source` | edit | `uploaded_by`, `uploaded_at`, `origin` (default None, id still derived from kind + sha256 only) |
| tests | - | `tests/test_zip_intake_names.py`, `_limits.py`, `_register.py`, `_atomic.py`, `tests/test_intake_schema.py`, `tests/test_drive_verify.py`, helper `tests/zip_fixtures.py` |

Exists on master and must be reused:
- `src/autotester/sources/drive.py` (204 lines): `DriveFile` :40, `DriveFetch` :48 (`content: bytes | None`, whole file in memory), `DriveClient` Protocol :55 (`list_folder`, `fetch_file`), OAuth **device-flow** helpers `request_device_code` :76 and `exchange_device_code` :99, and `HttpDriveClient` :125 (httpx plus a refresh token). `src/autotester/sources/drive_register.py` (197): `register_drive` :51 (folder plus each file). `src/autotester/sources/__init__.py` (63) exports `DriveClient`, `HttpDriveClient`, `exchange_device_code`, `request_device_code`, `register_drive`. Tests: `tests/test_source_adapters_drive.py` (188 lines) uses `FakeDriveClient` and the real `HttpDriveClient`.
- `src/autotester/stages/ingest.py` (300 lines): `RECORDING_SUFFIXES` :74 and `require_recording_suffix` :84 are the one allowlist (TI3: a second suffix list is a defect); `register_source` :101 records a path in place and does not copy.
- `src/autotester/ui/routes_sources.py` (261 lines): `sources_page` :114 (register-by-path form plus an upload form), `add_source` :154, `upload_source` :169 (copies the whole body with `shutil.copyfileobj` into `work_dir`, no size limit, no streaming cap, no auth, no `uploaded_by`), `analyze_source` :222.
- `src/autotester/cli_video.py` (291 lines): the `ingest` typer app.
- No reference to `gws` exists anywhere under `src/`. The `gws` CLI is installed on this host (`gws 0.22.5`, `C:/Users/Lenovo/AppData/Roaming/npm/gws`).

Missing (the gap to each criterion):
- TI3 page half: the per-member outcome table on the Add-videos page (BROWSER, persona dev). `registered | duplicate | skipped | failed` per member exists in the report model, not on a page.
- TI5 CLI half: a command returning `report.exit_code` (exit 2 on partial). `manifest` notes it "needs G1's hook"; cli_video.py has room for about 8 lines, so the command body must live in a new module registered by a hook of <= 4 lines.
- TI7: Drive link parsing (file `/d/<id>`, `open?id=`, `uc?id=`, folder, bare id; id charset; every other shape refused), folder listing with non-videos listed `skipped` and not downloaded, zip-id handoff to `expand_zip`, and the real adapter that implements `DriveFetcher` by shelling out to `gws`. **D-081 item 6 / `qa/gates/drive-identity.md`: the live fetch uses the existing `gws` CLI login; no token is copied into the repo.** The existing `HttpDriveClient` / device-flow code in `sources/drive.py` is a different mechanism (a stored refresh token). Do not remove it (it is exported and tested); do not use it for this path. The T-198 goal note records the measured constraint: `gws drive files get -o` only writes under the current working directory, so the adapter must stage under a directory it controls and then copy to the stable project path (this is what `commit_video` already does). The exact `gws` flags are unknown here; the builder must read `gws drive files get --help` itself.
- Two Drive seams now exist (`DriveClient` in `drive.py`, `DriveFetcher` in `drive_verify.py`). "One concept, one place": the builder must make the `gws` adapter serve both listing and bounded fetch without defining a third interface.
- TI8: the five typed failure messages (not authenticated, permission denied, not found, quota exceeded, network error) and the canary-token grep over stdout, stderr, `caplog`, the audit file (`auth.md` AU22) and `sources.jsonl`. Not started.
- TI9 route half: the HTTP upload route streaming to disk with the limit read from the accessor (exact limit succeeds, limit + 1 gets 413 with no partial file and no row, a lying or missing `Content-Length` changes nothing), the page showing the current limit, and an endless body bounded at limit + one chunk. HO31 (proxy ceiling) and the admin page (HO15) belong to T-203.
- TI10: not startable until T-204's `authorize()` exists (NOT on master; `src/autotester/auth/` does not exist). The contract is explicit: a loopback stub is not evidence; TI10 stays HELD and the unit cannot close the task. Build the seam (a callable the route calls first, refusing before any byte is read) and report HELD.
- TI11 route half: `uploaded_by` from the authenticated session, never from a form field (the form-spoof test), and the plain upload-origin write on the HTTP route. Needs T-204.
- HO32 text vs a `gws` shell-out: HO32 speaks of redirect hops re-checked against loopback/private/link-local addresses, which assumes our own HTTP client. With `gws` doing the transfer, the host allow-list on the pasted URL still applies, but the redirect rule may not be checkable. Ruling needed (section 10).
- Linux run record `qa/evidence/t198-linux-run.md` (R65), reusing T-203's Ubuntu run if it covers these tests.
- The independent `senior-software-engineer` review (mandatory on this unit per `docs/plan.md` risk 2) and the dual check.

## 5. Files the builder will touch

Product files:

| Path | New / existing | Lines now |
|---|---|---|
| `src/autotester/sources/zip_names.py`, `bounded_write.py`, `intake_commit.py`, `zip_intake.py`, `drive_verify.py` | new on master (exist on the branch) | 91, 64, 169, 253, 102 |
| `src/autotester/core/upload_limit.py`, `src/autotester/schema/intake.py` | new on master (exist on the branch) | 75, 117 |
| `src/autotester/schema/project.py` (`Source` class only) | existing | 194 on master (201 on the branch) |
| `src/autotester/sources/drive.py` | existing | 204 (the `gws` adapter and link parser land here or in a sibling module under 300 lines; a sibling is the safer reading of "no new module" in the T-198 goal note, which D-072 item 2 overrides for Group 10 split modules) |
| `src/autotester/sources/__init__.py` | existing | 63 (exports) |
| `src/autotester/cli_video.py` | existing | 291 (hook of <= 4 lines; shared with T-197) |
| CLI module for `ingest fetch-drive` and the zip command | new, name unknown | - |
| `src/autotester/ui/routes_sources.py` | existing | 261 (will exceed 300 if the streaming upload, zip branch, Drive-link branch and outcome table are added inline: split them into a new module, name unknown) |
| `src/autotester/ui/` new module for the intake branches and outcome table | new, name unknown | - |
| `docs/MAP.md` | existing, generated | regenerate with `uv run autotester map` only |

Test files:

| Path | New / existing |
|---|---|
| the 7 test files and helper listed in section 4 | new on master (exist on the branch) |
| `gws` adapter tests with a fake runner (no real Google call): link forms, good md5, wrong md5, short read, folder with 2 videos and a PDF, zip id with a hostile member, five failure classes plus the canary-token grep | new, name unknown |
| CLI tests (exit 2 on partial, `fetch-drive`) | new, name unknown |
| route tests (streaming limit 413, zip branch, Drive-link branch, outcome table) | new, name unknown |
| `tests/test_ui_sources.py` (upload at :127), `tests/test_source_is_a_recording.py` (upload at :122, :137), `tests/test_source_adapters_drive.py` | existing; must stay green with assertions unedited |

## 6. Test scope

```
uv run pytest tests/test_zip_intake_names.py tests/test_zip_intake_limits.py tests/test_zip_intake_register.py tests/test_zip_intake_atomic.py tests/test_intake_schema.py tests/test_drive_verify.py
uv run pytest <the new gws-adapter, CLI and route test files named above>
uv run pytest tests/test_ui_sources.py tests/test_source_is_a_recording.py tests/test_source_adapters_drive.py tests/test_ingest.py tests/test_cli_surface.py
uv run ruff check src tests scripts
uv run autotester doctor
```

Symbols removed or renamed: none planned. Do not remove `HttpDriveClient`, `request_device_code`, `exchange_device_code` (exported at `sources/__init__.py:20-25` and tested in `tests/test_source_adapters_drive.py`). `git grep -n "upload_source\|/sources/upload" -- tests`: `tests/test_source_is_a_recording.py:122,137`, `tests/test_ui_sources.py:127`; `git grep -ln routes_sources -- tests`: `tests/test_ensemble_honesty.py`, `tests/test_ui_sources.py`. Pre-existing red on base per the slice manifest: `tests/test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen` (fails identically on the base; verify on current master before blaming it on this unit).

## 7. Reachable test cases (happy path first)

- TI3/TI4: a dev uploads a zip of 3 videos, 1 PDF, 1 text file: 3 `VIDEO` sources, 2 `skipped` with reasons, outcome table readable on the page; a `.env` and a `run.ps1` member skipped; the same video twice in one zip and again in a second upload is `duplicate` with `duplicate_of`; `a/clip.mp4` and `b/clip.mp4` get distinct stored names; a 300-character name and `con.mp4` are harmless to the stored path.
- TI1: one hostile fixture per name (`../x`, `..\x`, `a/../../x`, `/abs`, `C:\x`, `\\host\share\x`, `a.mp4:evil`, `CON`, NUL byte, bidi char, symlink, hardlink, device) plus a benign video, sentinel files above staging and at the temp root unchanged, benign video still registered; same refusals with `os.sep` patched to both separators.
- TI2: caps injected small: zeros claiming a huge size (nothing written, limit named); a header that understates a member (stops at cap + one chunk); over-ratio member; nested zip by name and by signature; too many entries.
- TI5: a flipped byte, an encrypted member, a renamed `.txt`: status `partial`, exit 2, others registered; a non-zip file: one `failed`, nothing registered.
- TI6: fault injection after member 2 of 3 (rows and files agree; a re-run converges to 3, no duplicates); a real `os._exit` kill; two intakes at once.
- TI7: fake runner for `gws`: good md5 registers under the project's stable path; wrong md5 and short read refuse with no row and no staging; folder with 2 videos and a PDF (PDF listed, not downloaded); a zip id with a hostile member goes through TI1-TI6.
- TI8: one fake response per failure class gives five distinct messages; a canary token planted in the fake credential and in each error body never appears in stdout, stderr, `caplog`, the audit file or `sources.jsonl`.
- TI9: with the setting at 5 MiB, exactly 5 MiB succeeds and 5 MiB + 1 byte is refused on the HTTP upload, the Drive fetch and zip-member inflation; change the setting between two requests; an endless generator body ends at limit + one chunk; a grep of `src/` finds no second limit or `2 * 1024**3` literal.
- TI10 (HELD until T-204): the matrix (Admin, Sub-admin assigned and not, Developer own and not, Tester, no-group, anonymous) x (upload, zip, Drive link); re-check at queued-fetch start; cross-origin POST with a valid cookie. Report HELD, do not fake it.
- TI11: old `sources.jsonl` loads with ids unchanged; `uploaded_by=B` in the form stores A (needs T-204); `extra="forbid"` rejects unknown keys.

## 8. Gate answers

- `qa/gates/drive-identity.md`, verbatim: `Answered: 2026-10-10 - A (existing gws CLI login) - D-081`. Scope line in the same file: "Blocks: only the live Drive fetch in T-198 (`ingest fetch-drive`, `sources/drive.py`)." Answer text: "the existing gws CLI login. The live Drive fetch shells out to gws; no token is copied into this repo."
- `qa/gates/plan-approved-g10.md`, final section, verbatim: `Approved -- Umesh, 2026-10-07 (chat), recorded as D-074.` Its assumptions include "Zip caps 5 GB, 20 videos".
- `qa/gates/email-sender-credentials.md` (`Answered: 2026-10-10 - A (credentials from d:/erp, AutoTester-prefixed keys) - D-081`): does not apply; it gates delivery email only (the T-198 goal note says the same).
- New modules: `docs/DECISIONS.md` D-072 item 2, verbatim: "New modules: yes to all. This covers ... the Group 10 split modules ... Every file stays at or under 300 lines with a one-job docstring, and the checker judges it." The T-198 goal note says "No new module"; D-072 item 2 post-dates nothing but is broader, and slice 1 already added seven modules on that reading. A ruling is owed (section 10).
- Real Drive fetch of an actual file: SERVER-GATED and needs "an approved, synthetic, non-student video" (HO33). No such approval is recorded; the builder uses a fake only. `qa/gates/t203-host-and-dns.md` is open but gates only the hosted check, not this unit.

## 9. UI surface and persona walk

- UI surface: yes (`ui/routes_sources.py`: the Add-videos page gains a zip option, a Drive-link field, the current limit, and the per-member outcome table).
- `Persona walk: required (dev: uploads a zip with a bad member, reads the outcome table, pastes a Drive link, hits the limit message; no lead/Admin controls shown to a tester)`. Controls need visible labels and keyboard operation; zero unexplained console errors. Evidence under `qa/evidence/browser-t198a-*-checker/`. Browser lane max 1; the builder runs no browser.

## 10. Dependencies and conflicts

Must land first: nothing for the code that remains. TI10 and the route half of TI11 are blocked on T-204 (outside this pass); TI9's admin page and HO31 on T-203. Both are reported HELD, so the unit cannot CLOSE the task until T-204 lands, but it can be built and checked for every other row now.

Shared files (one owner each):

| File | Also wanted by | Proposed owner |
|---|---|---|
| `schema/project.py` | T-205 (`Project` class, and TF6's Source fields), T-200, T-199 | T-198 owns the `Source` class edit; T-205 owns the `Project` class. Same import block: expect a trivial conflict. Needs the TF6 ruling in the T-205 brief (section 10, item 1) |
| `cli_video.py` (291) | T-197 (`--pointers`, `ingest review`) | T-197 first, then T-198 adds <= 4 lines after merging master |
| `ui/routes_sources.py` (261) | T-204 (permission gate), T-203, G9 | T-198 |
| `ui/routers.py`, `ui/app.py` | T-205 | T-205; this unit registers no new router unless it adds a route module (then append to `ROUTERS` after T-205 lands) |
| `sources/drive.py`, `sources/drive_register.py`, `sources/__init__.py` | G9 (the portal reads sources) | T-198 |
| `core/upload_limit.py` | T-203 (replaces the file source with `ServerSettings`) | T-198 keeps the accessor signature; T-203 swaps the source |
| `docs/MAP.md` | every unit | integrator regenerates at merge |
| `docs/ARCHITECTURE.md` | every unit | orchestrator, under one D-entry that names the section |
| `qa/manifests/g3-zip-core.md` | none | this unit (lives on the branch; bump `Fix cycle`/slice, do not create a second manifest) |

Open rulings (builder must not decide):
1. HO32's redirect-hop rule when the transfer is done by the `gws` CLI rather than our HTTP client (does the contract still require a redirect check, or only the pasted-URL host allow-list plus gws's own behaviour?). HO33's "connect and total timeout, accepts only a video content type" maps to a subprocess timeout and the Drive metadata mimeType; confirm.
2. Whether `HttpDriveClient` and the device-flow helpers are to be deprecated now that D-081 item 6 chose `gws`. Proposed: leave them untouched in this unit.
3. New modules for the CLI command and the route split (D-072 item 2 versus the T-198 goal note "No new module").

## 11. Budget and process rules

- Check budget for tier L: 45 min wall clock per checker (two checkers for the dual check). Builder budget: unknown (no figure in the repo).
- The builder runs no full suite (the checker's one combined G-core run, then the orchestrator's pre-push full suite). Note the repo's own measure: the full suite takes about 31 minutes and has been killed by memory pressure on this 24 GB machine; code lane max 4, browser lane max 1.
- Falsification (each row's named mutation) only in a throwaway copy outside the bound tree; never mutate the worktree. Kill only PIDs you started (the TI6 test starts a real subprocess and kills it).
- No real Google, SMTP or model call in the default test suite; no real student or Vidysea video as a fixture. No token in any output.
- Edit in place; no `*_v2.py` / `*_new.py`; files <= 300 lines, functions <= 50, one-job docstring, `extra="forbid"` models; no `ZipFile.extractall` / `extract`; no second suffix list; no `fcntl` / `flock` / POSIX-only call at import.
- Do not edit `qa/contracts/`, `docs/DECISIONS.md`, `.goal/goal.json`, `qa/issues.jsonl`.
- Use `git -C <worktree> ...`, never `cd X && ...`.
