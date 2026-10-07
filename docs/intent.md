# Intent — AutoTester

**Purpose:** why AutoTester exists, in the originator's words — the problem, the numbered outcomes (O1-O15), who uses it, and the constraints every contract inherits.
**Open me when:** you are about to add a capability and need to know which outcome it serves, or a contract criterion cites `serves: intent#O*`.

<!-- PLAN phase step 1, written as a BACKFILL (maker SKILL.md init step 2b backfill clause):
     this project shipped M0–M6 before the PLAN rule existed. Drafted from target.md, .goal/goal.json,
     docs/ARCHITECTURE.md and qa/contracts/, not from a fresh interview. -->

**Originator:** Umesh · **Date:** 2026-09-27 (O8-O15 and the Group 10 rows added 2026-10-07) · **Status:** draft (backfill; Group 10 additions await `qa/gates/plan-approved-g10.md`)

## Problem

Regression testing of Vidysea's web products is done by hand. A tester is given a product, learns
it by using it, writes cases, and re-runs them after every dev cycle. That does not scale, it is
not reproducible, and a feature can silently break an old one between releases with nobody
noticing until a student hits it.

Existing tools need a test script written first. Umesh's framing, kept in his words:
**"give AutoTester a product, not a test script."** And when it meets a screen it does not
understand, it must **ask for a video instead of guessing** — a confident wrong test is worse
than an honest gap.

## Proposed outcome

- **O1** — Given only a URL and scoped test credentials, AutoTester builds and keeps a model of
  the product's screens, states and actions, and can say what it has and has not exercised.
- **O2** — It generates best / worst / edge cases per flow and runs them in a **real visible
  browser** after every dev cycle, so a regression is caught by a run, not by a user.
- **O3** — Every finding carries evidence (what was attempted, prior state, what changed, why it
  was classified that way) and an honest label — AI suspicion is never dressed as confirmed fact.
- **O4** — Coverage is honest: an unexplored branch is reported as unexplored, never as passed.
  Any bound (time, depth, safety) names what it left unreached.
- **O5** — When the model is insufficient for a screen, AutoTester raises a VideoRequest rather
  than inventing behaviour.
- **O6** — On a real product, AutoTester is measured against an expert human tester on bugs found,
  false-positive rate, coverage and time — and wins on those numbers.
- **O7** — Credentials never leak: a secret exists only as a `SecretRef` plus a value in a
  gitignored `.env`, substituted at `page.fill()` time inside the project's allowed domains, and
  masked in every screenshot, log, video and model prompt.

### Team loop (Group 10, T-197..T-201; D-067, D-070, D-072; feature file `docs/features/team-loop/intent.md`)

- **O8** — Teach by video with a human's pointers. A reviewer gives a recording plus approximate
  timestamps and 2-3 free-text pointers; AutoTester returns a flow summary and a 4-5 row confirm-list
  (`time | screen | seen | suggestion | severity`), each citing the exact second. Pointers raise
  attention and never hide the rest; the output names every span nobody looked at. Human oracle: the 13
  high-severity rows in `.work/pathlynks-dev-videos-oracle-2026-10-07.md`.
- **O9** — A developer hands over a demo without a terminal: a file, a zip, or a pasted Google Drive link
  becomes one registered source per video inside one of their own projects (or one they are assigned to). The upload limit is an
  admin setting (default 2 GB). A hostile or broken archive cannot write outside its staging area, and
  any member skipped or failed is listed by name with the reason. The video is ingested into the product
  knowledge graph with no human approval step (D-070 part 2).
- **O10** — A failure becomes one tracked bug, once, and stays honest: a stable key survives re-runs, a
  re-test updates it, a run of passes closes it, and a run that could not judge neither closes nor opens.
- **O11** — The team's own sheet is written only with the team's consent (D-071): proposed mapping,
  user-confirmed, first write shown cell by cell and confirmed, then append/update of own rows only.
- **O12** — Regression runs without anyone remembering to: per project, by button press, at a fixed time,
  or at a custom time the user selects; same path and same consent as a manual run; never overlapping; an
  unrunnable slot is reported, never skipped quietly.
- **O13** — Any member with permission presses Test and gets the report themselves, attributed to them:
  on the website, and by email if they ticked their email preference. A blocked, failed or thin-coverage
  run is delivered with that label.
- **O14** — A video has a share link. A person without access sees "request access" and the request
  reaches someone who may approve it; people with access leave timestamped comments that all with access
  see. (D-070 part 3)
- **O15** — What a person sees and does is decided by the groups an admin put them in: AWS-IAM-style
  groups of ticked permissions, a new account having none. Default groups: CEO/Admin (everything,
  every project), Sub-admin (assigned projects), Developer (own videos, approves access to them),
  Tester (only what is shared, can comment). (D-072; T-204 owns the mechanism.)

## Affected users and systems

### Audience
**`internal-tool`**, now **hosted**: the Vidysea development and product teams reach AutoTester as a
website on an Ubuntu server (development stays on Windows) and sign in (T-203, T-204). Q1 is answered
(Umesh, 2026-10-07: "Vidysea only"): it stays internal to Vidysea; external teams remain out of scope.
It has a web UI, so UI units still get a live browser run; persona walks stay limited to 1–2 of the
user types below per unit (cost gate).

### User types (`dev`, `tester`, `lead` confirmed by Umesh 2026-09-27; `admin` and `subadmin` are Umesh's default group names, 2026-10-07; the rest still drafted)
| id | who | goal | blocks on | patience | mental model | confirmed |
|---|---|---|---|---|---|---|
| `dev` | Vidysea developer who just pushed a commit | know within minutes whether the push broke an existing flow | a report that says FAIL without the failing step, the judge's reason or a repro | 2 | CI output, stack traces | Umesh, 2026-09-27 |
| `tester` | the human tester AutoTester is measured against | onboard a product, review the learned FlowSpec, prune bad cases before they cost tokens | cases generated with no way to tell which are actually runnable | 4 | manual test plans, Excel case sheets | Umesh, 2026-09-27 |
| `lead` | Umesh / product lead | see the trust number and the damage-control report; decide ship / no-ship | coverage that looks green because the unexplored part is invisible | 2 | dashboards, one-screen summaries | Umesh, 2026-09-27 |
| `admin` | CEO / Admin group: every project and video, approves anyone, reviews videos with pointers | review a video in minutes, approve access, see why a run or schedule did not go | a summary that cannot be traced to a second; not knowing who can see what | 1 | a review doc: time, screen, seen, suggestion, severity | group confirmed 2026-10-07; fields drafted |
| `subadmin` | Sub-admin group: manages only the projects assigned to them | add members, approve access, set the schedule, bind the tracker sheet for their projects | a screen showing other projects | 3 | user-management screens | group confirmed 2026-10-07; fields drafted |
| `trainer` | domain expert supplying recordings | teach a flow by recording it once; confirm a reported bug is real | being asked for a video with no indication of which screen is missing | 3 | screen recordings, WhatsApp, Excel issue sheets | drafted — not confirmed |
| `release-manager` | whoever runs the release | trigger the approved suite against a release and get a pass/fail with consent respected | a run that writes to production, or one that cannot be resumed after a crash | 1 | release checklists, approval gates | drafted — not confirmed |

### Systems
`src/autotester/` (stages · schema · browser · providers · ui) · Playwright/Chromium · the
provider seam (Anthropic → Gemini → Ollama → ChatGPT) · the filestore under `projects/<slug>/` ·
Pathlynks and the Vidysea ERP as acceptance targets · production Mongo, **read-only by
construction**. Team loop adds: the hosted site and run queue (T-203), login and groups (T-204), mail
for report delivery, Google Drive and Sheets through `gws`.

## Constraints

- **Credential boundary** (`CLAUDE.md`, hard): values only in the gitignored repo-root `.env`;
  `SecretRef` carries the key and its domain scope, never a value; `assert_no_raw_secrets` gates
  every model call; screenshots mask secret inputs before capture.
- **`write_policy` defaults to `read_only`.** Testing a real product needs a **test account** and
  explicit per-run approval — never a live user's credentials.
- **Production Mongo is never written.** Backend assertions are read-only.
- **Lab Protocol:** `docs/DECISIONS.md` is append-only via `scripts/append_decision.ps1`;
  `docs/ARCHITECTURE.md` prose changes need an authorizing entry first.
- **Design rules** (`uv run autotester doctor`): file ≤ 300 lines, function ≤ 50, one concept one
  place, every domain shape a Pydantic model in `schema/` with `extra="forbid"`, no `*_v2.py`.
- **Vendor independence:** all model calls go through `providers.base.Provider`; prompts are files.
- **Team data stays on the company server** (Group 10): videos, comments, bugs and reports live under
  `projects/<slug>/` on the host. A video goes to an external model only under a recorded per-use
  approval for that project and provider, after redaction windows are applied; the unredacted original
  is never sent.
- **Identity comes from the session, never from a form field** (Group 10): "report to whoever clicked"
  means the authenticated identity; a recipient typed into a request is ignored. Access is by group
  permission, enforced server-side on every route (D-072). Anyone can sign up; a new account has no
  access until an admin adds it to a group.
- **Outward writes are shown first** (Group 10): the first write to any team sheet is previewed and
  confirmed by a named user, bound to the exact plan shown.
- **Run approval is the supplied credential** (D-068): schedules and the Test button add no second
  prompt, and refuse with a named reason and zero requests when no credential pair is declared.
- **Windows and Ubuntu** (D-072): new code runs on both. Limits (upload size, concurrent runs) are admin
  settings, not literals.
- **Honesty rule:** a capability counts as shipped only when the code exists AND a checker proved
  it. Fixture-proven is stated as fixture-proven.

## Open questions

- [x] **Q1** — ANSWERED 2026-10-07 (Umesh, grill): Vidysea only; stays `internal-tool`. `org_id`
      future-proofing is PARKED (not built).
- [x] **Q2** — ANSWERED 2026-09-27 (partial): `dev`, `tester`, `lead` confirmed. `trainer` and
      `release-manager` remain drafted and do not seed personas yet — see qa/gates/plan-approved.md.
- [ ] **Q3 (carried, AT-281)** — The real two-mode acceptance thresholds for O6/T-169: what recall,
      false-positive rate and time actually count as beating the human? Open since 2026-09-11.
- [ ] **Q4 (carried, AT-218)** — The policy on vacuous guards: what makes a test admissible as
      proof, given the recurring class of guards that cannot fail.
- [ ] **Q5 (Group 10)** — Email sender address and credentials for report delivery (website delivery needs
      neither). Gates only the email adapter. Detail in `docs/features/team-loop/intent.md`.
- [ ] **Q6 (Group 10)** — Which Google identity the server uses to fetch pasted Drive links. Gates only
      the live Drive fetch.
- [ ] PARKED: `org_id` on every row for a later multi-company move (Q1 follow-up; default: not built).
- [ ] PARKED: which second product supplies the trust number — until Pathlynks is proven
      (Umesh 2026-09-24: "not only erp").
