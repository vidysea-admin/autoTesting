# Contract — Web UI (T-100)

**Covers:** goal task T-100. **Owner:** /checker. **Criticality:** HIGH — T-100's own note:
"full onboarding → report without touching the CLI."
**Depends on:** `core-invariants.md` (all), `browser-and-secrets.md` (B1-B9 — the credential
boundary this UI's `.env` editor must respect), `execute.md`/`grade.md` (the `RawResult`/`Verdict`
shapes the report/run views read).

## Purpose

A thin FastAPI viewer/editor over the same project files the CLI reads and writes — design
principle 8: "the UI is a viewer/editor over those files, not a second source of truth." Every
route goes through `ProjectStore`/`SecretStore`, never a parallel store.

## Criteria

### U1 — Onboarding creates a real, CLI-compatible project
`POST /onboard` builds a `schema.project.Project` from form fields and persists it via
`ProjectStore.save_project` — the same file (`projects/<slug>/project.json`) and format the CLI
and every stage already read. No UI-only project representation exists.

### U2 — Project detail reflects real state, no caching/duplication
`GET /projects/{slug}` reads the project's actual `FlowSpec` (`review.status`) and case count
live via `ProjectStore` on every request — never a cached or UI-maintained copy. An unknown slug
is a 404, not a silently empty page.

### U3 — The env editor never renders a real secret value
`GET /projects/{slug}/env` shows, per declared `SecretRef`, only whether `.env` currently has a
non-empty value for that key (`"set"`/`"not set"`) — the actual value is never present anywhere
in the rendered HTML. `POST /projects/{slug}/env` writes a new value via
`ui/env_editor.py::set_env_value` (the one legitimate write path to the repo-root `.env`) and
never echoes the submitted value back in its response. Posting a key the project does not declare
is refused (400), never silently written.

### U4 — Run/report views read real persisted evidence, never invent it
`GET /projects/{slug}/runs/{run_id}` and `GET /projects/{slug}/report` read actual
`RawResult`/`Verdict` files via `ProjectStore.load_results`/`load_verdicts` — the outcome/result
values shown are exactly what was persisted by `execute.py`/`grade.py`, not recomputed or
guessed. A project with no runs yet reports that plainly (200 with a "no runs yet" message), not
an error.

### U5 — User-supplied values are HTML-escaped
Every string derived from user input or project data (`name`, `base_url`, slugs, case ids,
outcome/result values) is passed through `html.escape` before being placed in a response —
verified by reading `ui/app.py` in full, not merely tested against one payload.

### U6 — A test case is creatable from the UI, as a real CLI-compatible `Case`
`GET /projects/{slug}/cases/new` renders a plain server-rendered form and
`POST /projects/{slug}/cases` persists the result via `ProjectStore.add_case` as a
genuine `schema.case.Case` in `projects/<slug>/cases.jsonl` — the same file and format
`stages/expand.py` and every stage already read; no UI-only case representation exists.
`kind` is **derived** from `case_class` (`KIND_BY_CLASS`) and is never a form field, so
the two can never disagree. `rationale` is left `None`: it is a *claim*, not provenance
— `stages/run_case_pipeline.default_rubric` feeds it to the grader verbatim as the claim
to judge evidence against (AT-057 cycle, 2026-09-07) — and provenance lives in
`flow_id="manual"`. A blank title, zero surviving steps, an unknown `case_class`, an
unknown `action`, and an unknown project are each **refused (400/400/400/400/404) with
nothing written to disk**. A project with zero cases says so on its detail page and
offers the route to fix it, rather than showing only a disabled Run control.

### U7 — A project cannot be created or edited into a state where it can never run
Every route that writes `project.json` (`POST /onboard`, `POST /projects/{slug}/edit`) first calls
`ui/helpers.py::_require_reachable_base_url`, which **composes the same two functions the real
navigation gate uses** — `browser.secrets.host_of` and `Project.allows_domain`, exactly as
`browser/session.py::check_destination` does — so the validator can never be stricter or looser
than the boundary it guards (a subdomain of an allowed domain must still be accepted). A project
whose own `base_url` host falls outside its `allowed_domains` is refused **400 with the host named**
and **nothing is written to disk**. The edit route is not a back door: it runs the same validator,
refuses a blank name and an empty domain list, and **cannot change the slug** — the slug names the
directory every run, case, rubric and browser profile is already filed under. Editing preserves
every field the form does not offer (`secrets`, `write_policy`, `providers`) — the edit form reads
and writes `project.json` only and touches no `SecretRef` value and no `.env` (U3 boundary).
`allowed_domains` gets **no wildcard**: widening the browser's hard boundary is a decision for the
Approver, not a validation fix, and the user's real intent stays expressible because the refusal
names the exact host to add.

### U8 — The case form cannot commit a raw credential to a git-tracked file
Every user-supplied text of a case — the `title` and every `step_target`, `step_value` and
`step_expected` — passes `ui/helpers.py::_refuse_unsafe_submission` **before any `Case` is
built**, on both doors into a title (`POST /projects/{slug}/cases` and
`POST /projects/{slug}/cases/{case_id}/rename`). A `{{SECRET:KEY}}` placeholder naming an
undeclared key is refused (400); a raw `.env` value in any one of those fields is refused (400);
and their **concatenation** is checked too, so a value split across two or more rows — or across
two different field types — cannot reassemble byte-for-byte in `projects/<slug>/cases.jsonl`,
which is git-tracked in a public repo. Nothing is written to disk on a refusal. A refusal that
reaches the grading prompt anyway (a credential already inside a rubric) yields a
`Result.BLOCKED` `Verdict` naming no value — `stages/grade.py` never raises out of
`SecretStore.guard_prompt`, because crashing every subsequent run leaves no way back.
This criterion pins the *case form only*. The equivalent hole on the three routes that write
`project.json` is **not** covered here and is tracked as **AT-073**.

### U9 — The three routes that write `project.json` cannot commit a raw credential either
`POST /onboard` (`name`, `base_url`, `allowed_domains`), `POST /projects/{slug}/edit` (the same
three) and `POST /projects/{slug}/secrets` (`description`, `domains`) each pass their
user-supplied text through `ui/helpers.py::_refuse_unsafe_submission` **before** `project.json`
is written — the same guard U8 pins on the case form, on the file that a project *name* renders
from on every page including the home index. Matching runs against **every** value in the shared
`.env`, declared as a `SecretRef` or not: an undeclared provider key is still a credential and
this repo is public (AT-083 — scoping input matching to declared values only was a real hole and
is the one thing this criterion must never be softened back to).
The guard must **not** brick a project's own data. A field is exempt **only** when its submitted
text is byte-identical to what is already persisted for that project — data the system itself
stored, never fresh input, and never anything derived from the same request (AT-078: `pathlynks`'s
`base_url` is byte-identical to the non-secret `.env` entry `PATHLYNKS_USER_LOGIN_URL`, and
without this every project whose config collides with a `.env` value became uneditable with no
fix the user could express). Every on-disk project must be able to re-save its own unmodified
`name` / `base_url` / `allowed_domains`, and to be renamed while keeping a colliding base URL.
Two residuals are deliberately **outside** this criterion and tracked instead, because closing
either is a scope decision rather than a bug fix: **AT-087** — exempt fields are excluded from
the *concatenation* check and the exempt set is flat rather than per-field, so a credential
straddling an exempt field and a fresh one is not caught (the case form is unaffected: it passes
no exempt set at all); and **AT-086** — a project whose `base_url` is byte-identical to an `.env`
value cannot be created through the UI at all, by onboarding or by editing a placeholder. Both
fail closed.

### U10 — The cold start has a way out, and the gate over it swings both ways
A project with **zero cases and no `FlowSpec`** — the state every newly onboarded product is in —
has a route out of that state that a person can reach by clicking, and the person, not the
machine, decides whether what the machine learned is true.

- **The dead end is closed.** `ui/project_view.py::_actions_card`'s zero-case empty state offers a
  link to `GET /projects/{slug}/flowspec` beside "+ Add the first case". Hand-writing cases one at
  a time was previously the only remedy offered, which made the product's own generator invisible
  to the operator it was built for.
- **The no-FlowSpec page says so and is not itself a dead end.** `ui/routes_learn.py::flowspec_page`
  renders a page that states no FlowSpec exists for this project and carries **at least one** onward
  link. A page that only reports the absence would move the dead end, not close it.
- **The gate moves in both directions from the UI.** `POST …/flowspec/approve` and
  `POST …/flowspec/request-edit` both exist and both persist through
  `ProjectStore.save_flowspec` after `stages/review.py::approve`/`request_edit` — the same file
  (`projects/<slug>/flowspec.json`), the same functions the CLI uses (R2/R3/R4), no parallel state.
  **A review page carrying only an Approve button is a rubber stamp, and this criterion pins the
  second button so a later unit cannot quietly delete it.**
- **An unsigned approval is refused and changes nothing.** A blank or whitespace-only signer is
  refused (400) and `flowspec.json` is left **byte-identical** — R2's "there is no such thing as an
  anonymous approval" holds on the UI door too, and the refusal must not be a partial write.
- **The review free text goes through the same credential guard as the case form.** Both routes pass
  their `by` and `note` through `ui/helpers.py::_refuse_unsafe_submission` **before** any save, with
  the project's `SecretStore` loaded exactly as every other route loads it. `flowspec.json` is
  git-tracked in a public repo; the reason U8/U9 exist does not stop at the case form.
- **The queue is visible.** `GET /projects/{slug}/requests` renders the open `VideoRequest`s, and an
  empty queue gets an honest empty state rather than a blank page. A request written to a file
  nothing renders is, from the human's side, not asking at all.
- **U5 covers the new surfaces.** Every project-derived string on both new GET routes — including
  the `<title>`, which `theme.page` does not escape for you, and the labels handed to
  `theme.breadcrumb`/`theme.empty_state`, which do not escape for you either — is `html.escape`d at
  the call site.

**Deliberately not claimed here:** that refusals from these routes are themed pages. Only the three
`POST …/cases/generate` refusals are (expand.md X6); `approve`/`request-edit` still answer with a raw
`{"detail": …}` blob, tracked as AT-259. Writing that into this criterion would be crediting an
intention.

### U11 — An operator can authorize and bound a crawl without the CLI
The UI exposes a crawl-approval form whose target is the project's exact persisted `base_url` and
is displayed read-only: the browser never supplies or widens the target. The operator supplies the
signer, scope, expiry, and the approval's action/time bounds; the server persists a real
`schema.approval.RunApproval` through `ProjectStore.add_approval`. The browser converts the selected
local expiry instant with the UTC offset for that selected date (not today's offset), so a future
date across a daylight-saving boundary remains the instant the operator chose.

The crawl-start form displays all four operator-facing `CrawlBounds` controls (`max_screens`,
`max_actions`, `wall_clock_s`, `max_depth`), and the exact parsed object is used for both consent
preflight and `run_crawl`; invalid or non-positive bounds fail closed. Missing, expired, malformed,
or too-narrow consent returns a themed refusal with an in-UI recovery link and no CLI instruction.
Unknown crawl ids return a themed HTTP 404. Review-gate refusals reached through
`approve`/`request-edit` likewise remain inside the themed UI and give the operator a route onward.
These behaviours require an independent interactive Mode-D run with zero unexplained console errors;
route tests or screenshots supplied by the maker are not sufficient evidence.

### U12 — One intake form preserves typed truth in both bare and taught modes
`GET /onboard` presents one usable form containing the project's URL/domain boundary, repeatable
test-account credential rows (key, masked optional value, typing domains and description), optional
evals, conditions/business rules, use cases, and repeatable URL/video/document/text source rows.
`POST /onboard` accepts both a URL/account-only submission and a richly taught submission without
requiring CLI or JSON editing. It writes the existing canonical shapes only: `Project` through
`ProjectStore.save_project`, domain-scoped `SecretRef`s in `project.json`, non-secret teaching and
source declarations as content-addressed `Source` rows, and raw credential values only through the
repo-root `.env` writer. Repeated identical statements/source rows are idempotent, and only video
sources offer video analysis.

Every repeated row and non-secret field is parsed and validated before any project, source or secret
write. A malformed later row leaves no partial project/source/`.env` state; re-onboarding cannot
overwrite an existing project; and a key already present in the root `.env` or declared by another
project is refused even when that other declaration is currently unset. Security of the submitted
values themselves is additionally governed by B10 and C5; U12 does not weaken U1-U11.


### U13 — The credential guard's spelling threat model is written down, and its edge does not move
The guard that U8, U9, U10 and U12 each invoke (`ui/helpers.py::_refuse_unsafe_submission`)
defends against **ACCIDENTAL exposure**: a hurried human pasting a credential into a text box, or
an agent writing one into a git-tracked file. It does **not** defend against a party who already
holds the value. That distinction is load-bearing rather than convenient — every spelling declared
out of scope below must be *constructed* from the credential, so whoever built it read the value
out of `.env` first, and no guard can protect a secret from someone who has it. This is
`consent.md` CN3's tamper-evidence-not-tamper-proofing posture (AT-110) on a second boundary.

**In scope.** These are the transforms that arrive by accident — a paste out of a terminal or a
PDF carrying stray marks, a re-type with different punctuation, a value copied through a URL bar.
A finding in any of them is a FAIL against U8/U9, not a filing:
case; separator substitution across the punctuation set in `core.redact._FOLD_STRIP`; single
percent-encoding and `+`-decoding (`ui.helpers._credential_variants`); whitespace of every kind,
including interleaved; zero-width and default-ignorable code points (`core.redact._DEFAULT_IGNORABLE`);
format characters (category `Cf`); control characters (category `Cc`, `U+0000` included); the
curated homoglyph set in `core.redact.ASCII_CONFUSABLES`; and the bidi **overrides**
`U+202D`/`U+202E`, which are **refused outright rather than folded away** — subtracting them
deletes the character that causes the reordering and then compares a string that is not the
credential, so the deny-list's usual widen-to-see-more move makes this one class strictly worse
(AT-355). This list is a **floor, not a ceiling**: removing any strip or refusal named here is a
CRITICAL amendment, never a simplification a later unit may make on its own.

**Out of scope, by name.** Each of these needs deliberate construction by someone holding the
value, and all but the first need a decoding step the reader must take on purpose: bidi handling
beyond the override refusal (`U+200E`/`U+200F` and the embeddings and isolates are ordinary
punctuation in Hebrew and Arabic text and do not reverse a pure-ASCII run — refusing them costs
real input, and false-positive rate is a term in the north star); base64, base32 and hex;
HTML numeric and named entities; double percent-encoding; plain reversal with no direction
control; homoglyphs outside the curated map (AT-349); and visible combining marks (AT-356).
Out of scope means **filed, never charged** — it does not mean closed and it does not mean
forgotten: AT-349, AT-352 and AT-356 stay open at their recorded severities, and this criterion is
not a licence to close them.

**Moving a class from FILED to CHARGED is an amendment, not a measurement.** A checker may file a
new spelling class at any time, at whatever severity the evidence supports. **Charging** one
against a unit requires this criterion to name it first; moving a class in or out is a contract
amendment under the criticality gate, decided away from any pending verdict. A fresh measurement
proving an out-of-scope class real is evidence *for* such an amendment, never a substitute for one.
This clause exists because the opposite happened: three fix cycles and three FAILs on one line of
`fold_credential`, each charging a class no written criterion covered, with the boundary redrawn at
cycle 3 on a fresh measurement (`qa/debug/at345-346-fold-coverage-cycle3.md`, gate
`qa/gates/at355-guard-shape.md`). A loop whose acceptance line the judge moves mid-cycle cannot
terminate, whatever the maker builds.

**Two things this criterion does not do.** It does not adopt an allow-list of readable characters:
that is unbounded with the sign flipped, its failure mode is refusing legitimate input, and AT-078
and AT-086 are two measured occasions when this guard made a real project uneditable — reopening
it needs a written character inventory and its own gate, not a quiet retry. And an enumeration is
itself a deny-list, so this criterion does not discharge the positive rendering detector
(`visualOrder`, the only instrument that caught AT-355 and still living in a checker's evidence
directory) — that port is tracked as **AT-358** and is owed regardless of anything written here.

### U14 — The positive rendering detector has a written acceptance line
`src/autotester/browser/visual_order.js` (`visual_text`, the port AT-358 owed) is the instrument that
answers "what text did a reader see". Until this criterion it had **no** criterion: U13 names it only
to say it is not covered, yet checker verdicts charged U13 against it three cycles running (at379) and
again at at438 cycle 1. A module whose acceptance line is invented per verdict cannot terminate
(`qa/debug/at379-scrollable-pane-reachability-cycle3.md`). This criterion is that line.

- **(a) Scroll-invariance floor — charged.** The multiset of glyphs `visual_text` reports must not
  change when the window or any scrollable container is scrolled anywhere in its range. The scrolls
  are performed in a real browser, never computed from rects.
- **(b) No new false negative on visible text — charged.** A change to the detector must not stop
  reporting text a reader can see on a page where the pre-change detector reported it, and must not
  visibly change the page it observes (a probe that restarts an animation, reflows, or leaves a node
  behind). **Pre-change detector, defined (D-048, D-049):** the detector as it stood at the unit's
  branch point, meaning the parent commit on master before the unit's first cycle. It is never a
  failed or committed earlier cycle of the same unit. A unit is judged against the code that existed
  before it began, not against its own earlier draft. A later cycle that falls behind an earlier cycle
  of the same unit is not, by itself, a U14(b) failure. **North-star tie-break, written down:** where suppressing a false positive and keeping a
  true positive conflict, keeping the visible text wins — a missed leak is the failure this detector
  exists to prevent (AT-355), and a false positive costs a reviewer a look, not a bug.
- **(c) What this does not see — contract-owned.** The list below is the detector's disclosed blind
  set. A class on it is **filed, never charged** (U13's rule applies unchanged: moving a class from
  filed to charged is an amendment, not a measurement). Widening or narrowing it is an amendment to
  this file, not a docstring edit in `visual_order.js`. As of this amendment: the scroll/clip
  interaction classes held by gate `qa/gates/at416-clip-vs-reach-direction.md` (AT-379, AT-408,
  AT-416, AT-417 — the strict-xfail rows of the invariance probe), AT-440 (five display types
  missing from `HIDES_ON`), and AT-454 (D-049). AT-454 is a `display:contents` child slotted through
  a `mode:"closed"` shadow root, reported although it does not paint. `assignedSlot` is `null`
  across a closed root's boundary, so the flat-tree walk falls back to `parentElement` and cannot see
  the hiding box inside. A real fix needs CDP-level shadow inspection and would be its own unit.
- **Scope in time.** Charged against manifests whose `Fix cycle` is submitted after the commit that
  adds this criterion. The at438-display-contents cycle-1 verdict and the classes it filed (AT-442 to
  AT-445) are that verdict's to own; this criterion neither discharges nor adds to them.
- **Verify:** `uv run pytest tests/test_browser_scroll_invariance.py tests/test_browser_visual_order.py`
  exits 0 with every xfail strict and each xfail's reason naming a class listed in (c); the checker's
  Mode D run drives its own browser over the unit's changed shape and one shape from each fixture the
  change touches, and records a before/after report count for (b).

### U15 - The home page answers "can I test with this?" before any project is opened
Umesh, verbatim (`qa/feedback-inbox.md:353`, 2026-09-06, watching the live UI): *"bhai ye kessa ui
bnaya hai na dashboard na kuch user kese testing krr payegaa"*. `/` is a bare project-card grid; U2
covers project DETAIL and nothing covered the landing surface. AT-664.

- **`/` renders portfolio-level state, not only a list of projects.** At minimum: how many projects
  exist, how many have ever had a run, and per project the outcome and age of its most recent run.
  A person arriving cold can tell which project needs attention without opening one.
- **Every number is read from persisted evidence.** U4's rule, unchanged and load-bearing here
  because an aggregate is the easiest place to invent one: a project with no runs renders `no runs`,
  never `0 failures`, and a run whose evidence cannot be read renders `unreadable`, never a zero.
  An aggregate never sums over projects it could not read without saying how many it skipped.
- **Stale is visible.** A most-recent run older than the project's last change is labelled stale
  rather than shown as a current result.
- **It reuses the existing components.** Stat tiles and status vocabulary come from `theme.py` and
  the project's status vocabulary (AT-116/AT-119), so a new spelling of PASS/FAIL/NOT_RUN is not
  introduced on the busiest page.
- **Verify:** with two projects, one never run and one with a failed run, `/` shows the run outcome
  and its age for the second and `no runs` for the first, and shows neither as `0`; a project whose
  run evidence is unreadable is counted as skipped in the aggregate and named.
  **Links:** AT-664; AT-552 (the shadowed row this ask was filed on); U2; U4; AT-116; AT-119.

## No-fire list

- Authentication/authorization — this is a local, single-operator tool for now (matches the
  plan's "Out of scope v1: multi-tenant SaaS").
- A JS framework or HTMX wiring — plain server-rendered HTML strings for this cycle; the plan
  names HTMX as a future refinement, not required to satisfy this contract.
- Live-updating run views (polling/websockets) — `GET /projects/{slug}/runs/{run_id}` is a
  point-in-time snapshot; "live" in T-100's title is satisfied by reading current persisted state
  on every request, not by push updates.
- Triggering a run or an onboarding video from the UI — this contract covers viewing/editing
  existing project state and creating a bare project record; kicking off `execute.py`/
  `ingest.py` from a UI button is a future enhancement.
- CSRF protection on the POST forms — acceptable for a local single-operator tool; flagged as a
  known gap if this UI is ever exposed beyond localhost.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for T-100 — no contract existed before this cycle.
- 2026-09-03 · /checker (docker-live-ui unit) · shared-layout invariant: every route in
  `ui/app.py` now returns its HTML fragment wrapped by `ui/theme.py::page(title, body)` — a
  shared nav + stylesheet, visual only. U1-U5 are unaffected: `page()` prepends/wraps the
  caller's already-escaped fragment and never removes, reorders, or unescapes it (verified —
  see `qa/verdicts/docker-live-ui.md` D5). A new presentation-only route, `GET /live` (renders
  an iframe onto the container's noVNC client; no `ProjectStore`/`SecretStore` call, triggers no
  run), now exists alongside U1-U5's routes — covered by `qa/contracts/docker.md` D4, not a U-item
  itself since it reads no project state. Routine, non-weakening; folds the flagged
  `qa/feedback-inbox.md` 2026-09-03 "Docker + live-watch + UI polish" entry.
- 2026-09-07 · /checker (ui-back-nav-and-live-clarity unit) · shared back-navigation invariant:
  every route that is not the home page now builds its trail with
  `ui/theme.py::breadcrumb(*crumbs)` — one helper replacing 8 hand-written
  `<div class='breadcrumb'>` blocks across 5 modules — which renders a real `← Back` anchor
  targeting the **last crumb carrying an href** (the natural parent), plus the same trail as
  before. U5 is unaffected and re-verified: `breadcrumb()` adds no escaping of its own (same
  caller-escaping discipline as `page()`), all 8 call sites pass `escape()`d labels, and every
  href is a literal or `/projects/{escape(slug)}` where the slug is already `_require_slug`
  regex-validated — so no user-controlled string reaches an `href=`. Verified live against a
  project named `<script>alert(1)</script>&'"` on 5 routes (see
  `qa/verdicts/ui-back-nav-and-live-clarity.md` U5). Also in this unit: `GET /live`'s tip text
  replaced — the stale `scripts/regression_proof.py` instruction (which predated the ▶ Run tests
  button) is gone, replaced by the honest "a black screen is normal, it is the container's real
  and idle display" note plus the AT-054 `AUTOTESTER_SLOW_MO_MS` opt-in; presentation-only, no
  `ProjectStore`/`SecretStore` call added. Routine, non-weakening. Known gap deliberately NOT
  covered by any criterion here and now tracked as ledger issue **AT-057**: an onboarded project
  with zero cases has no UI path to add one, so its ▶ Run tests button is permanently disabled —
  it needs its own contract-scoped cycle and a scoping decision (add-a-case flow vs explicit
  next-step prompt) before a criterion can be written for it.
- 2026-09-07 · /checker (ui-add-case unit) · **new criterion U6 added** — the contract-scoped
  cycle the AT-057 row above demanded has now happened, and the scoping decision came back
  "both": `ui/routes_cases.py` adds the add-a-case form AND `app.py::_actions_card` adds the
  empty-state prompt, so the criterion is finally writable. Routine, non-weakening (adds a
  criterion, softens none). U1-U5 re-verified in the same check and unaffected: the new routes
  go through `ProjectStore` only (U1's no-second-store rule), read live state per request (U2),
  touch no `SecretStore`/`.env` (U3), touch no run/report code (U4), and escape every
  user-derived value — probed hostilely against a project whose `name` and `base_url` carried
  `<script>`, `'` and `"`, with zero raw tags in the response (U5). Two real defects found
  during that cycle were correctly filed rather than folded in here, because neither is a
  U-criterion: **AT-058** (onboarding accepts an `allowed_domains` that excludes the project's
  own `base_url` host, and no route can edit it afterwards — a security-model decision, not a
  bug fix) and **AT-059** (a case's persisted rubric is keyed on a case id that deliberately
  excludes `rationale`, so a changed claim keeps grading against the stale one — a `grade`
  bug the UI flow can no longer trigger now that `rationale` is `None`). Also filed:
  **AT-060** — the form silently discards a submission whose steps duplicate an existing case
  (`add_case` is idempotent on the content id and `create_case` never checks the return), so a
  user cannot correct a mistyped title and gets no feedback. See
  `qa/verdicts/ui-add-case.md`.
- 2026-09-07 · /checker (ui-project-edit-and-domain-validation unit) · **new criterion U7 added**
  — the AT-058 row above named a defect no U-criterion covered; the unit fixed both halves
  (validate at onboarding, and an edit route to recover a project already broken), so the
  criterion is now writable. Routine, non-weakening (adds a criterion, softens none). The
  criterion deliberately pins the *composition* (`host_of` + `allows_domain`, the same pair
  `browser/session.py::check_destination` uses) rather than the validation behaviour, because the
  real risk here is a validator that drifts stricter than the boundary and bricks a legitimate
  project — verified live: a subdomain still onboards, and all four on-disk projects
  (`pathlynks`, `vidysea-erp`, `regression-demo`, `erp`) still pass. U1-U6 re-verified in the same
  check and unaffected: the edit route goes through `ProjectStore` only (U1), reads live per
  request and 404s an unknown slug (U2), imports no `SecretStore` and preserves `secrets` through
  `model_copy` (U3), touches no run/report code (U4), escapes every rendered value — probed with a
  project whose `name` and `base_url` carried `<script>`, `'` and `"`, zero raw tags and every
  `value='…'` attribute escaped including `'`→`&#x27;` (U5), and leaves the add-a-case flow
  untouched (U6). The refused wildcard is recorded as correct: `allowed_domains` stays a hard
  boundary. Two low-severity gaps found in the same probe were filed rather than folded in, since
  neither violates a criterion: **AT-061** (`host_of` returns a pseudo-host for garbage, so a
  schemeless or nonsense `base_url` still onboards) and **AT-062** (onboarding stores `name`/
  `base_url` unstripped while the edit form strips them). See
  `qa/verdicts/ui-project-edit-and-domain-validation.md`.
- 2026-09-07 · /checker (ui-credential-safety-all-fields unit) · **new criterion U8 added** —
  the credential guard the two previous units built had no criterion at all, so a later unit
  could have deleted it and no check would have noticed. Routine, non-weakening (adds a
  criterion, softens none). U8 records exactly what this checker re-derived live against a real
  `.env` value: title / target / expect / value each refuse (closing **AT-070**), and a value
  split across two rows, three rows, or two *different* field types is refused by the
  concatenation check (closing **AT-071**). U1–U7 re-verified in the same check and unaffected:
  onboarding and edit still go through `ProjectStore` only (U1), unknown slug still 404s (U2),
  the env editor is untouched and imports nothing new (U3), no run/report code changed (U4),
  escaping unchanged (U5), all five U6 refusals still fire and the duplicate-check 400 was
  confirmed to be the duplicate check and not the guard misfiring (U6), and
  `_require_reachable_base_url` is byte-unchanged (U7). Five defects found in the same probe were
  filed rather than folded in, because none is a U-criterion violation by this unit:
  **AT-073** (high — `POST /onboard`, `POST /projects/{slug}/edit` and
  `POST /projects/{slug}/secrets` still write a raw `.env` value in cleartext to git-tracked
  `project.json`, breaching core-invariants C5; this is the next unit),
  **AT-074** (a URL-encoded or whitespace-split value still gets through, recoverable in one
  step), **AT-075** (the `unknown case class` / `unknown action` 400s echo raw form input, the
  AT-068 pattern), **AT-076** (any `.env` value — including another project's undeclared one —
  blocks its own literal text, so a login URL in `.env` cannot be a navigate target and the
  suggested `{{SECRET:KEY}}` remedy does not work there because only `session.fill` resolves
  placeholders) and **AT-077** (the concatenation refusal names no field, so an innocent
  straddle across 15 artificial boundaries leaves the user with nothing to change). See
  `qa/verdicts/ui-credential-safety-all-fields.md`.
- 2026-09-07 · /checker (ui-credential-guard-project-routes unit, cycle 3) · **new criterion U9
  added** — the U8 amendment above named AT-073 as "the next unit"; this was it, and it took
  three cycles because the two obvious fixes each broke the other half. U9 records what finally
  held, and pins **both** directions so neither regression can recur silently: matching over the
  **full** `.env` (cycle 2 was FAILed for scoping it to declared values — proved with the
  operator's live `GEMINI_API_KEY` landing in a git-tracked `cases.jsonl` and `project.json`),
  **and** a byte-identical-to-stored exemption (cycle 1 was FAILed for refusing `pathlynks`'s own
  unmodified `base_url` and making the project uneditable). Routine, non-weakening — it adds a
  criterion, softens none, and the two residuals it names are recorded as tracked issues rather
  than written out of the rule. U1–U8 re-verified in the same check and unaffected: onboarding
  and edit still go through `ProjectStore` only and a subdomain still onboards (U1/U7), unknown
  slug still 404s (U2), no declared `SecretRef` value appears in any of 35 rendered routes and
  the env editor is unchanged (U3), no run/report code touched and every `report`/`.html`/`.xlsx`
  is 200 (U4), escaping re-probed live against a project named `<script>alert(1)</script>&'"`
  with zero raw tags on 6 routes (U5), all five case-form refusals still fire with no raw echo
  (U6), and the case form's own concatenation check is **structurally** unexemptable because
  `routes_cases._guard_submitted_case` passes no `exempt` set — 32 hostile probes against a
  declared *and* an undeclared live credential all refused (U8). Three defects found in the same
  probe were filed rather than folded in, none a criterion violation: **AT-087** (medium — the
  exemption hollows out the concatenation check on the project routes; isolated against a
  control), **AT-088** (medium — `_require_reachable_base_url` runs before the guard and echoes a
  credential pasted into Base URL back in its 400, the AT-068/AT-075 pattern's fourth occurrence)
  and **AT-086** raised low→medium (the manifest's "has workarounds" was tested and is wrong —
  onboarding a placeholder then editing is refused too). See
  `qa/verdicts/ui-credential-guard-project-routes.md`.

- 2026-09-09 · /checker (at241-cold-start unit, cycle 1) · **new criterion U10 added** — the
  business-truth campaign proved T-100's own acceptance note ("full onboarding → report without
  touching the CLI") false by driving this UI in a real browser, and no U-criterion covered the
  hole, so nothing was failing while the product's promise was. U10 pins the cold-start exit, the
  two-way gate, the unsigned-approval refusal and the credential guard on review free text.
  Routine, non-weakening: it adds a criterion and softens none. Everything in it was re-derived by
  this checker's own Playwright script against its own `uvicorn` on a scratch `AUTOTESTER_ROOT`
  (18/18 interactions, evidence
  `qa/evidence/browser-at241-cold-start-2026-09-09-checker/report.json`), not read from the maker's
  report: a project named `<script>alert(1)</script>&'"` was onboarded through the real form, its
  zero-case page **clicked** through to `/flowspec`, the gate driven draft → `needs_edit` →
  `approved` with `review.status` and `review.by` **read back off disk each time**, and a
  whitespace-only signer confirmed to leave `flowspec.json` byte-identical. U5 was re-probed on the
  raw HTTP source rather than the DOM (`page.title()` re-decodes entities and reports a false leak):
  both new routes emit `&lt;script&gt;…` in the body **and in `<title>`**, zero raw payloads — the
  fourth escaping site this checker went looking for does not exist. Two residuals filed rather than
  folded in, because neither violates a criterion: **AT-259** (the module's own
  `approve`/`request-edit` refusals are raw JSON — the manifest's "refusals from *these* routes are
  pages" is true only of `generate`, 4 of ~6 refusal paths on these routes are raw, and this checker
  saw one rendered as a bare `<pre>` blob in Chromium) and **AT-262** (Generate is a ~2-minute
  synchronous POST with no progress feedback). U1–U9 are **not** re-verified by this unit and are not
  claimed to be; AT-243's finding that 24 UI-touching PASS verdicts carry zero `LIVE-BROWSER` lines
  is untouched by this cycle. See `qa/verdicts/at241-cold-start.md`.
- 2026-09-10 · routine · **new criterion U11 added** — folds the T-100 real-browser re-close
  feedback: an outward-facing crawl started from the UI must expose its exact target, approval and
  four execution bounds in the UI; use the selected date's browser offset; fail through themed,
  recoverable pages; return 404 for an unknown crawl; and survive an independent interactive run
  without unexplained console errors. Tightening only: U1–U10 are unchanged. The previous U10
  disclaimer about raw review refusals remains historical evidence of AT-259, while U11 makes its
  repair part of the acceptance bar for this re-close.
- 2026-09-10 · /checker (t161-unified-project-intake cycle 1) · **new criterion U12 added** — folds
  D-025/T-161's one-form intake, canonical typed persistence, repeated-row atomic validation,
  idempotent sources, re-onboarding refusal and cross-project credential-key ownership into the
  living UI contract before judging the unit. Tightening only: U1-U11 are unchanged; raw-value
  confidentiality is pinned separately by B10/C5 so a product-flow criterion cannot soften it.
- 2026-09-11 · /checker (contract maintenance, no unit in flight) · **new criterion U13 added** —
  folds the 2026-09-11 maker inbox entry (*"a guard with no written threat model cannot
  terminate"*) and the answered gate `qa/gates/at355-guard-shape.md` (option C plus the narrow
  half of A, decided by the maker under Umesh's delegation). **Criticality: ROUTINE, and the
  judgement was close enough to state.** The proposal reads as a NARROWING — it declares spelling
  classes out of scope — and a narrowing of a safety boundary is the one amendment a checker may
  not apply alone. It is not one, on three pieces of evidence. (i) **Nothing written is removed.**
  U8/U9 pin *raw* values and byte-for-byte reassembly; none of AT-345/AT-349/AT-351/AT-352/AT-353/
  AT-355/AT-356 is a raw value, which is exactly why the checker who first met this class **filed
  rather than charged** it. The standard three cycles later charged against — rendering
  equivalence — was written in verdict prose and nowhere in this contract, so out-of-scope text
  subtracts nothing that a criterion ever said. (ii) **No shipped defence is authorised away.**
  Every in-scope class named here is defended in code today (`core/redact.py::fold_credential`,
  `_is_ignorable`, `_DEFAULT_IGNORABLE`, `ASCII_CONFUSABLES`; `ui/helpers.py::_credential_variants`,
  `_refuse_direction_override`), and U13 makes that set a floor whose removal is CRITICAL — so the
  criterion ends **stronger** than the silence it replaces: the AT-345/AT-351/AT-353 fixes and the
  bidi-override refusal are contract-bound for the first time. (iii) **The out-of-scope classes
  stay open in the ledger at their filed severities** (AT-349 low, AT-352 medium, AT-356 medium);
  out of scope means *not charged*, not *closed*. This documents a boundary the contract already
  had rather than moving one, which is the routine lane. The one genuine change in what may be
  enforced — a future checker can no longer charge an unlisted class — is the amendment-not-a-
  measurement rule, and it is procedural, reversible by a gated amendment, and the direct remedy
  for the non-termination measured in `qa/debug/at345-346-fold-coverage-cycle3.md`.
  **Independent judgement on the two calls the maker made:** option B (allow-list) was **rightly
  rejected** — it is unbounded on the false-positive axis, `false-positive rate` is a scored term
  in the north star, AT-078/AT-086 are measured precedents of this guard bricking a real project,
  the product ingests arbitrary third-party selectors/JWTs/multilingual expectation text so "the
  scripts the product actually stores" cannot be enumerated in advance, and it would not close
  AT-349 at all since homoglyphs live *inside* an allow-list. The narrow half of A is **upheld**
  as the in-scope bidi-override refusal. **Not discharged by this amendment:** the `visualOrder`
  positive detector, filed as **AT-358** (medium). U1-U12 are unchanged and none is softened;
  `at355-refuse-bidi-overrides` is `ready-for-check` as this is written and U13 **tightens**
  against it (it makes that refusal a criterion), so the "never amend toward a pending verdict"
  rule is satisfied in the safe direction. Numbered U13 because U11 (crawl authorisation) and U12
  (unified intake) already exist — the inbox entry's "fold as U11" is a stale number, not a stale
  proposal.
- 2026-09-16 · routine · added **U14** — the positive rendering detector (`visual_order.js`) gets a
  written acceptance line: (a) scroll-invariance floor, (b) no new false negative on visible text with
  the north-star tie-break written down, (c) a contract-owned does-not-see list · why: folded from
  `qa/feedback-inbox.md` (at379 stall diagnosis, 2026-09-16) by the Mode B sweep of 2026-09-16 18:09.
  Routine, not critical: a new criterion over a module no criterion covered — it narrows nothing U1-U13
  say, and U13's own precedent (a criterion added to stop a moving acceptance line) is the lane.
  Re-derived before folding: `grep -rn "visual_text\|visual_order" qa/contracts/` returned only U13's
  two "not covered" mentions, while `qa/verdicts/at438-display-contents.md` cycle 1 charged U13
  against the detector — the pattern the inbox entry names, recurring the same day. The invariance
  property is already a committed, checker-PASSed test (`tests/test_browser_scroll_invariance.py`,
  at423 cycle 2). **Pending verdict rule:** at438 is live at cycle 1 FAIL; U14 is explicitly
  scoped to later submissions and does not re-rule AT-442..AT-445, so it amends neither toward nor
  against that verdict. The (c) list names only classes already filed and gated, so nothing is
  closed by being listed.
- 2026-09-16 · routine · Mode D live-browser duty restated from Umesh's direct instruction ("sabb live
  browser mai validate krna hai", inbox 2026-09-16T16:05) · no criterion text changed: a UI-touching
  unit already cannot PASS without a checker-driven browser run (D-024, checker Mode D) and a maker
  smoke report is never cited as that run; a unit with no browser surface states `not-applicable`
  with its changed paths. The proposed "each session ends with a live-browser pass" was **not**
  adopted as a criterion: a session leaves no on-disk boundary a checker can re-derive, so it would
  be a criterion no verdict can judge (AT-218's vacuous class). Its intent is served instead by the
  standing live UI validation verdicts (`qa/verdicts/live-2026-09-16-ui.md`), which the queue keeps
  scheduling.
- 2026-09-26 · /checker (at438-display-contents, D-048 gate answer a+b+c, D-049) · U14(b)'s
  baseline is defined: "pre-change detector" means the detector at the unit's branch point, never an
  earlier cycle of the same unit. Why: cycles 2 and 3 were charged against the cycle-1 probe
  c687b73, which itself FAILED (AT-442). Against the pre-unit detector c687b73^, cycle 3 (9fc937d)
  drops zero reported texts. Re-measured in real Chromium, 70 layouts (qa/evidence/browser-at438-
  rerule-2026-09-26-checker/): false negatives OLD 26, C3 2, MASTER 2. U14(c) gains AT-454 as a
  disclosed false-positive class. **Weakening, named:** U14(b) no longer charges a cycle for losing
  ground a rejected earlier cycle had gained, only for falling behind pre-unit master. AT-453 (the
  ::details-content display:contents/inline miss) is NOT added to (c). It stays charged and open as
  its own unit, capped at 2 cycles (gate option b).
- 2026-09-28 - routine (add) - U15 added: the home page answers "can I test with this?" before any
  project is opened. Cause: AT-664, found in the overdue Mode B sweep's feedback-inbox fold. Umesh
  said this watching the live UI on 2026-09-06; it was filed as a ledger row and never encoded, and
  the row it was filed on carries a DUPLICATE id (AT-552, shared with an unrelated fixed defect), so
  an id-keyed read of open work cannot see it - the first measured case of AT-656 losing a human
  instruction rather than a status. U15 states the outcome and the honesty rules and does NOT
  prescribe a layout; the aggregate-honesty clauses are U4's rule applied where inventing a zero is
  easiest. Additive; no criterion weakened. **Changes-authorized:** qa/contracts/ui.md U15 +
  Amendment log (this entry). No enforcement-path file touched. **Links:** AT-664; AT-656; AT-552.
