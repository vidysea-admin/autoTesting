# Contract — team-foundation: headroom and shared seams for Group 10 (G1, `g10-0-headroom`)

**Covers:** unit G1 `g10-0-headroom` (goal task T-205, new); requirements R63, R65 (and R54's "no second runner" at the seam).
**Owner:** /checker. **Status:** ACTIVE (2026-10-07); lands before every other Group 10 unit (`docs/plan.md` waves).
**Criticality:** CRITICAL for TF2 (AT-570 re-verification); MEDIUM elsewhere (a refactor that must change no behaviour). Tier M, with TF2
treated as L because it touches the approval gate (`consent.md`).
**Serves:** `docs/spec.md` R63 (no new permission keys; server-side enforcement), R65 (Windows and Ubuntu), R54; `docs/intent.md` O12, O13, O15;
D-072 items 2 (new split modules authorised) and 7; AT-570.
**Depends on:** `core-invariants.md` (files <= 300 lines, one concept one place), `ui-run.md` RU1-RU4 (behaviour to preserve), `consent.md`,
`auth.md` (AU12, AU14, the closed catalogue), `hosting.md` HO10 (Windows and Linux).
**Consumers:** G2-G9 (`team-schedule.md`, `team-test-button.md`, and the intake, review and tracker contracts) register through these seams;
T-203 and T-204 also use the router list and the policy merge. **Whichever of T-203, T-204 or G1 lands first creates `ui/routers.py` and
`auth/policy.py`; the others extend them in place. A second router list or a second policy table is a defect.**

## Why this unit exists (measured on origin/master)

`ui/app.py` is 300 lines, `cli.py` 295, `schema/enums.py` 300, `core/paths.py` 287: no Group 10 unit can add a router line, a CLI command or a
path helper in place, and `trigger_run` is the only place a run is started. G1 changes **no behaviour**; it makes room and puts the shared
seams in one place so the seven units after it do not collide.

## Criteria

- **TF1 — One run launcher; the UI Run, the Test button and the scheduler all call it (R54, R56).**
  `stages/run_launcher.py` holds the **single** function that, given a project, a trigger, an optional requester and an optional slot key,
  (a) loads the project and cases, (b) applies the 400 pre-checks (no cases; no provider; in that order), (c) resolves secrets and the live-case
  approval (TF2), (d) executes through `_execute_with_trace` / the resilient pipeline, and (e) saves the `Run`. `ui/routes_runs.py`'s `trigger_run`
  becomes a **thin caller** of it (no run logic remains in the route). The extraction is **behaviour-preserving**: `ui-run.md` RU2, RU3 and RU4
  (and the `at044` entry-case isolation) hold, the existing RU tests pass **with assertions unedited**, and `POST /projects/{slug}/run` returns
  the same 303 to the report. Exactly **one** non-test function in `src/` constructs a `Run(...)` for a UI/queue/scheduler run or calls
  `_execute_with_trace`; the CLI scripts that call `run_and_grade_case` directly are unchanged and out of this row. The launcher has no
  FastAPI import (it is callable by a queue worker and the CLI tick). It does **not** itself queue (T-203's), schedule (G5) or authenticate.
  `serves:` spec R54, R56, `ui-run.md` RU1-RU4, `team-schedule.md` TS6, `team-test-button.md` TT4.
  *Evidence (LOCAL):* `uv run pytest tests/test_ui_run*.py` green with `git diff` showing zero changed assertions in those files;
  `tests/test_run_launcher.py` — an AST/grep test that `Run(` and `_execute_with_trace(` each have one call site outside tests, and that
  `run_launcher.py` imports nothing from `fastapi`; `uv run autotester doctor` (duplicate-concept). *Mutation:* paste the run logic back into
  `trigger_run` -> the single-call-site test fails.

- **TF2 — AT-570 live-case approval is re-verified through the launcher, from every entry point (CRITICAL).**
  A live case (one that would enter data or act on the target) cannot run without a **covering approval** (`consent.md`; D-018; AT-570, closed in
  code at `ui/routes_runs.py` `_require_live_case_approval`). After the extraction the check is performed **inside the launcher**, so every
  caller inherits it; a caller cannot skip it by passing a flag. Called with a live case and **no covering approval**: the launcher refuses
  with the same reason `trigger_run` gives today, **before** any `BrowserSession` is constructed, no run directory exists, and zero requests
  reach the network (asserted at the transport, `consent.md` CN1). Called with a covering approval, it proceeds. The same holds when the
  launcher is invoked as the Test button would (`trigger=manual`, a `requested_by`) and as the tick would (`trigger=schedule`, a `slot_key`):
  the three call sites are one parametrised test. The launcher accepts the new keyword arguments `trigger` (the existing `Trigger` enum:
  `manual`, `ci`, `schedule`), `requested_by` and `slot_key`, with defaults that reproduce today's behaviour, and the **`Run`** model gains
  optional `requested_by`, `slot_key` and `via` fields (default `None`; a `run.json` written before this unit loads unchanged) so G5 and G7
  do not each edit `schema/run.py`. The credential-derived approval of D-068 is **not built here**; G1 asserts only that when it lands it is
  consulted at this one place. The stale T-201 note that calls AT-570 "open" in `.goal/goal.json` / `docs/plan.md` is corrected to "closed
  in code, re-verified by G1". `serves:` spec R54, R60, `consent.md`, D-018, D-068, AT-570, `team-schedule.md` TS5, `team-test-button.md` TT6.
  *Evidence (LOCAL):* `tests/test_run_launcher_approval.py` — `{manual, schedule, ci}` x `{no approval, covering approval}`: refusals leave the
  data-root listing byte-identical and both counters 0; a golden pre-change `run.json` loads. *Mutation:* delete the approval call from the
  launcher -> every refusal row fails; accept a `skip_approval=True` argument -> an AST check that the launcher has no such parameter fails.

- **TF3 — Routers register from one ordered list; the stubs are in place and expose nothing (R63, design rule).**
  `ui/routers.py` holds the ordered list of routers (`ROUTERS`) and `ui/app.py` registers them by iterating it; `app.py` has **no per-unit
  `include_router` line** and does not grow (<= its current 300 lines, and ideally fewer). The registered **order is unchanged**: a snapshot of
  `(methods, path, endpoint qualname)` for every route of the app, in order, taken before the change, equals the one after, for the existing
  routes. The Group 10 stubs (`schedule`, `team_run`, `inbox`, `profile`, `tracker`, `video_review`, `video_portal`, `access_requests`, as the
  plan names them) are **registered empty `APIRouter()`s**: they add **zero routes** until their unit fills them. Adding a route to a stub, or
  appending a router to the list, makes it reachable **without editing `app.py`** (tested with a throwaway router). `serves:` spec R63, R65,
  `docs/plan.md` finding 2, `core-invariants.md`. *Evidence (LOCAL):* `tests/test_routers_list.py` — the route-table snapshot test (golden
  file committed under `tests/golden/`), the "stubs add zero routes" test, the throwaway-router test; `wc -l src/autotester/ui/app.py` <= 300.
  *Mutation:* reorder two routers -> the snapshot test fails.

- **TF4 — Each unit contributes its own route-policy dict; `auth/policy.py` merges them; no new key (R63).**
  A unit declares its routes in a **module-level dict** of its own (`ROUTE_POLICY`: `"<METHOD> <path template>"` -> a permission key from the
  **closed catalogue in `auth.md`** plus the resource resolver name, or the marker `public` for `auth.md` AU16's closed set only), and
  `auth/policy.py` **merges** them into the one central table that `auth.md` AU14's enumeration test walks. The merge is deterministic and
  **fails at import** (not silently) on: a duplicate `"<METHOD> <path>"` claimed by two units; a permission key **not** in the catalogue (so no
  Group 10 unit can invent one — R63); a `public` entry outside AU16's set; a unit dict naming a route that does not exist. The stubs of
  TF3 contribute empty dicts. G1 contributes **no new permission key**: `git diff` of the catalogue (`auth/permissions` or `auth.md`'s table as
  encoded) is empty. If T-204 has not landed, G1 adds only the merge function and its tests to `auth/policy.py`; T-204 extends the same file
  in place. `serves:` spec R63, `auth.md` AU12, AU14, the closed catalogue. *Evidence (LOCAL):* `tests/test_policy_merge.py` — two fake unit
  dicts merge; each of the four fail-at-import cases raises with a message naming the offender; a golden check that the key set equals
  the catalogue's. *Mutation:* make the merge last-wins -> the duplicate-route case fails; accept an unknown key -> the catalogue case fails.

- **TF5 — A CLI sub-app hook lets new commands register without editing `cli.py` (design rule).**
  `cli.py` (295 lines) gains **one** hook: a list of `(name, typer_app)` sub-apps defined in a small module (the maker's choice of file) that
  `cli.py` iterates to `add_typer`. After G1, `cli.py` is <= 300 lines, `autotester --help` lists **exactly the same commands** as before
  (a snapshot of command names and one-line help, golden file), every existing command keeps its exit codes, and appending a throwaway
  sub-app to the list makes `autotester <name> --help` work **without editing `cli.py`**. G1 registers no Group 10 sub-app (`schedule`,
  `tracker`, `video review` belong to their units). New commands' conventions (`--output json`, documented exit codes, `--dry-run`, T-174)
  are their units' criteria, not this row's. `serves:` `docs/plan.md` finding 1, `core-invariants.md`, T-174. *Evidence (LOCAL):*
  `tests/test_cli_subapp_hook.py` (golden `--help` snapshot via `typer.testing.CliRunner`; throwaway sub-app test); the existing CLI
  tests green; `wc -l`. *Mutation:* drop a registration -> the snapshot test fails.

- **TF6 — `schema/project.py` gains the schedule, tracker and Source provenance fields, all optional and backward-compatible.**
  `Project` gains `schedule` (default `None`, meaning `manual`) and `tracker` (default `None`); `Source` gains `uploaded_by`, `uploaded_at` and
  `origin` (all default `None`; `origin` is a closed value set when present, e.g. `upload | zip | drive | recording`, defined in the Group 10
  vocabulary home, TF8). Every new field is typed by a **Pydantic model with `extra="forbid"` or a closed enum**; none is a bare `dict`,
  `Any` or free string where a vocabulary exists (the models themselves are built by G5 and G6, so G1 may land minimal typed placeholders
  they extend **in place**). `extra="forbid"` stays on `Project` and `Source`: an unknown key is still rejected. **Back-compat:** every
  existing `projects/*/project.json` and `sources` record in the repo loads unchanged; load then save then load gives an equal model; a file
  **without** the new keys loads, and a file **with** them round-trips. The `Source.id` derivation (`content_id` over `kind` and
  the hash/url/text/path/label) is **unchanged**: adding provenance never changes an existing source's id (idempotent re-ingest). The
  provenance fields hold **no secret** and are set from the session identity, never from a request body (G3's criteria). `serves:` spec R32-R50
  (provenance), R63, `core-invariants.md` (schema in `schema/` only). *Evidence (LOCAL):* `tests/test_project_schema_team.py` — load every
  committed `projects/*/project.json`; a golden file with and without the new keys; an unknown key rejected; the id-stability test over a
  fixed `Source`. *Mutation:* make `Project.schedule` required -> the old-file load fails; fold `uploaded_by` into the id derivation -> the
  id-stability test fails.

- **TF7 — The shared team store and path helpers are portable and safe (R65).**
  `store/team_store.py` (the sibling store for team data: schedule markers and records, delivery records, preferences, and the like) and the
  new `core/paths.py` helpers write **atomically** with `os.replace` over a temp file in the same directory, create markers with
  `O_CREAT | O_EXCL`, and import none of `fcntl`, `pwd`, `grp`, `resource`, or use `os.fork`. All paths come from `core/paths.py` /
  `pathlib` under the **data root** (`repo_root()`, honouring `AUTOTESTER_ROOT`), never a hard-coded drive letter or `/` prefix. A project
  slug, slot key or id used in a path is validated by a single function (the existing slug pattern for slugs; a path-safe encoder for slot keys)
  that **refuses** `..`, an absolute path, either separator, a drive letter, a reserved Windows device name (`CON`, `NUL`, ...), trailing
  dots or spaces, and a name longer than 120 characters. The data root for team state is covered by `git check-ignore` and `.dockerignore`
  (`auth.md` AU23's rule), so no marker, record, preference or outbox file can be committed or baked into an image. `serves:` spec R65,
  `auth.md` AU23, AU24, `hosting.md` HO10. *Evidence (LOCAL):* `tests/test_team_store.py` — table of hostile names with both separators and
  a drive letter (asserting refusal and that a sentinel file outside the root is untouched); an atomic-write test that kills the writer
  mid-write (the old content survives); a source grep over the new modules for the forbidden imports; `git check-ignore` and
  `.dockerignore` assertions; the same file runs on Windows and in T-203's Ubuntu check. *Mutation:* write with `open(..., "w")` in place
  -> the kill-mid-write test fails; accept `..\\x` -> the hostile-names test fails.

- **TF8 — Design rules and vocabulary home hold, and nothing else regresses.**
  `uv run autotester doctor` and `uv run ruff check src tests scripts` pass; every new file is <= 300 lines with a one-job module docstring
  and `extra="forbid"` models (D-072 item 2 authorises the Group 10 split modules); `docs/ARCHITECTURE.md` gains the rows for the new modules
  under a DECISIONS entry that names the section (Lab Protocol), and `docs/MAP.md` is regenerated with `autotester map`. **Vocabulary home:**
  new Group 10 closed vocabularies (slot outcomes, delivery status, source origin, the queue statuses G5 and G7 read) live in **one**
  documented place: `schema/team_enums.py`, whose docstring states it is the Group 10 vocabulary file and that `schema/enums.py` stays the home of
  every pre-existing vocabulary (`enums.py` is at the 300-line cap); a string defined in both files, or a value duplicated as a bare
  literal in a stage, is a defect (one concept, one place). The pre-existing test suite passes with no assertion edited. **Full-suite trigger:**
  a change to `app.py` registration order or to `cli.py` is a pre-push full-suite trigger (recorded as `full-suite trigger: router/CLI
  seam`). `serves:` `core-invariants.md`, CLAUDE.md design rules, D-072#2. *Evidence (LOCAL):* the two commands above plus `uv run pytest`
  at the pre-push check (no CLI `-q`); `tests/test_team_enums_home.py` (no duplicate value across the two vocabulary files; every value used in
  `stages/` for these concepts is imported, not re-typed). *Mutation:* define a slot outcome string in a stage -> the home test or
  doctor fails.

## Out of scope / ignore

- The queue, concurrency cap and workers (T-203); the permission engine, accounts and groups (T-204): G1 only leaves the seams they share.
- The credential-derived approval itself (D-068 implementation, branch `d063-grant-budget`).
- Any Group 10 screen, route, command or model beyond the empty stubs and the minimal typed placeholders TF6 allows.
- Changing `write_policy` semantics (D-053) or consent mechanics.

## No-fire list (must NOT happen)

- No behaviour change: no new route, command, permission key, status code or page on any existing path.
- No second router list, policy table, launcher or vocabulary file beyond the one named here.
- No `skip_approval`-style escape hatch on the launcher.
- No file over 300 lines; no `*_v2.py` / `*_new.py`.

## Amendment log (append-only; git history is the version)

- 2026-10-07 · init · contract created for unit G1 from `docs/plan.md` (G1 row and "Findings that shape the units"), `docs/spec.md` R63 and R65, and
  the maker's headroom measurements. TF8 records the vocabulary-home ruling the plan left to the checker (one documented second file,
  `schema/team_enums.py`); Umesh may overrule it, in which case `enums.py` is split first and TF8 is amended routinely.
