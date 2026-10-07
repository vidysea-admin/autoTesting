# Intent — Team loop: in-product developer portal (group 10, T-197..T-201)

**Purpose:** the feature-level intent for Group 10: why the team loop exists, its outcomes O8-O15, its user types (admin, subadmin, dev, tester) and the answers Umesh gave on 2026-10-07.
**Open me when:** you are building or checking any of T-197..T-201 and need the reason behind a requirement, or a criterion cites `serves: intent#O8`..`O15`.

**Originator:** Umesh (CEO meeting asks + chat 2026-10-07, D-067, D-070, D-072) · **Date:** 2026-10-07 · **Status:** draft, grill answered (`.work/grill-team-loop-dev-portal.md`, scratch), awaiting plan approval (`qa/gates/plan-approved-g10.md`)

## Problem
Developers record "how it is built and what it is for" videos and send them as Drive zips by mail.
The review happens outside AutoTester: the CEO watches them and writes his notes in a separate doc.
The flows in those videos never reach the product knowledge graph unless someone ingests them by
hand, so AutoTester cannot test against what the developer intended.

In Umesh's words, the portal should give each person a login, the projects mapped to them, a video
upload per project, and a shareable link to mail out (for example from Navnit to Karunn sir and
Radhika). People with access watch the video and the rest request access. The roles follow the
company structure (CEO, developer, Radhika as tester, admin, sub-admin). Comments carry timestamps,
Udemy-style, and everyone with access sees them.

## Proposed outcome
Numbered to continue `docs/intent.md` (O1-O7 there). Each outcome is a feature-level restatement; the
root file carries the same ids.

- **O8** A reviewer gives a recording plus approximate timestamps and 2-3 pointers, and gets a flow summary
  and a 4-5 row confirm-list that cites the exact second (T-197).
- **O9** A developer uploads a video or a zip, or pastes a Google Drive link, inside a project they are
  assigned to, and gets one registered source per video. The video is ingested into the product
  knowledge graph with no human approval step (D-070 part 2) and its flows appear in reports, including
  the "another possibility" divergences (T-198).
- **O10** A failure becomes one tracked bug under a stable key; a re-test updates it, a run of passes closes
  it (T-199).
- **O11** A team sheet is written only after the user confirms the column mapping and the first write (T-199, D-071).
- **O12** A project runs on a button press, at a fixed time, or at a custom time the user selects (T-200).
- **O13** Any member with permission presses Test and reads the report on the website, and also by email if
  they ticked their email preference (T-201).
- **O14** A video has a share link; a person without access sees "request access" and the request reaches
  someone who can approve it; people with access leave timestamped comments everyone with access sees
  (T-198 portal).
- **O15** What a person sees and does is decided by the groups an admin put them in. Groups are sets of
  ticked permissions (AWS-IAM style); a new account has no access until it is in a group (T-204 owns the
  mechanism, D-072; this group consumes it).

## Affected users and systems

### User types
Group names are Umesh's (2026-10-07, "Admin/CEO for all, dev for own"). The per-type fields below are
drafted from them and from the original ask; Umesh confirmed the groups, not each field.

| id | who (default group) | goal | blocks on | patience | mental model | confirmed |
|---|---|---|---|---|---|---|
| `admin` | CEO / Admin group: sees every project and video, can approve anyone | review a video with pointers, approve access, see why a run or schedule did not go | a summary that cannot be traced to a second in the video; not knowing who can see what | 1 | a review doc: time, screen, seen, suggestion, severity | group confirmed by Umesh 2026-10-07; fields drafted |
| `subadmin` | Sub-admin group: manages only the projects assigned to them | add members to their project, approve access, set the schedule, bind the tracker sheet | a screen that shows other projects, or a permission they cannot see the reason for | 3 | user-management screens | group confirmed; fields drafted |
| `dev` | Developer group: records and uploads their own videos, approves access to them | hand over a demo without a terminal, press Test, read the report | a zip that fails with no reason; a report with no failing step | 2 | CI output, stack traces | `dev` confirmed 2026-09-27; group confirmed |
| `tester` | Tester group: sees only what is shared with them, can comment | watch a shared video, comment at a second, read the project's report | finding nothing because nothing was shared and not knowing how to ask | 3 | Excel case sheets, WhatsApp notes | `tester` confirmed 2026-09-27; group confirmed |

`lead` (Umesh or the product lead, confirmed 2026-09-27) normally holds the Admin group. `pm` and `exec`
from the earlier draft are dropped: the CEO is in Admin, and a product-team member is whatever group the
admin gives them.

### Systems
- AutoTester FastAPI UI (`src/autotester/ui/`): the existing source upload is at `ui/routes_sources.py:169`.
- Video ingest: `stages/ingest.py`, `cli_video.py`, `merge_flowspec`.
- Model providers through `providers.base.Provider` (T-202 makes them any-model).
- Login, groups, permissions: **T-204**. Hosting, run queue, concurrency and server settings: **T-203**.
- Mail, to deliver reports by preference. The sender and credentials are not yet provided.

## Constraints
- **Single organisation:** Vidysea only (Umesh 2026-10-07). **Anyone can sign up; an admin can act on any
  account; a new account has no access until an admin puts it in a group** (D-072, replacing the earlier
  "no self sign-up").
- **Data boundary:** sensitive frames are redacted before any video goes to a model. Unredacted
  originals never go to a model. Pathlynks content needs per-use approval before it goes to an
  external model.
- **Public repo:** no video, credential or internal review content is committed.
- **Run safety:** the run approval is the supplied credential (D-068). A button or schedule adds no second
  prompt and refuses, naming the reason, when no credential is declared. AT-570 reads closed in code and
  is re-verified in unit G1.
- **Both platforms:** production is Ubuntu, development is Windows (D-072); new code must run on both.
- **Limits are settings, not literals:** the upload limit is admin-configurable (default 2 GB); the number
  of concurrent browser runs is a server setting (default 2).
- **Replay is graded:** a replayed script run still goes to the judge (D-072).

## Open questions
- [x] Tenancy: Vidysea only (Q1, 2026-10-07).
- [x] Permission matrix: groups with checkbox permissions, defaults per user type above (Q2, D-072).
- [x] Team login mechanism: email and password, open sign-up, admin moderates (D-072; T-204).
- [x] Video storage limit: admin-configurable, default 2 GB; Drive link fetched by the system (D-072).
- [x] Share-link delivery: the developer copies the link. Reports are delivered by the site and by email per preference.
- [ ] PARKED: rows carry an `org_id` (fixed to Vidysea) for a later multi-company move. Not built; one-way door only if a client company asks, and then it is a migration. Plan default: no.
- [ ] Email sender address and SMTP (or Google) credentials. Gates only the email adapter (unit G4).
- [ ] Which Google identity the server uses to fetch Drive links (the file must be shared with it). Gates only the live Drive fetch.
