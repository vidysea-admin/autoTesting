# Build brief: t205-g10-headroom (goal task T-205, plan unit G1 `g10-0-headroom`)

Written 2026-10-11 by the readiness pass (read-only; nothing was built). Self-contained: a builder needs nothing else but the repo.
Contract: `qa/contracts/team-foundation.md` (TF1-TF8, ACTIVE 2026-10-07). Plan: `docs/plan.md` row G1. Spec: R63, R65 (R54 at the seam).
Dispatchable: YES. The contract exists and covers every acceptance line of the task. Two rulings are open (see section 10, "Open rulings"); neither blocks starting.

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier L.** Trigger: TF2 relocates the D-018 / CN11 live-case consent gate (`src/autotester/ui/routes_runs.py:75` `_require_live_case_approval`) into a new shared launcher that the scheduler and the Test button will call. The contract itself says "Tier M, with TF2 treated as L because it touches the approval gate". Other rows (TF1, TF3, TF5, TF6, TF7, TF8) are M: multi-file behaviour, shared module, schema read.
- `Dual check: no`. There is no new auth, tenancy or prod-write code: the gate is moved, not written, and `auth.md` is not touched. If the checker wants a dual check the only honest trigger is `security src/autotester/ui/routes_runs.py:75`, flagged here, not required.
- Persona walk: skip (section 9).

## 2. Root and base

- Root: `D:/autoTesting`.
- Base: current `master` = `3a16616cf2c99a63c8d763150a1ca6410dfc0acc` (docs-only commit on top of `4f8f5da1`; no `src/` or `tests/` change since). Re-read `git -C D:/autoTesting rev-parse master` before starting and merge master in if it moved.
- Build in a NEW worktree: `D:/autoTesting/.worktrees/t205-g10-headroom`, branch `wave/t205-g10-headroom`, created from that sha. No existing branch holds usable work for this unit:
  - `codex/t202-completion` (worktree `.worktrees/codex-t202-completion`, 12 ahead / 3 behind master, 1 untracked manifest `qa/manifests/t202-completion.md`) contains `stages/run_launcher.py`, `ui/routers.py`, `store/team_store.py`, `schema/team_enums.py` and `auth/policy.py`, but it is a combined Codex branch (123 files, 10251 insertions, mixes T-202/T-203/T-204 work) with no checker verdict. D-080 item 1: Codex worktree changes are NOT canonical. The builder may READ it for ideas; it must not merge or cherry-pick from it.
  - `wave/t204-auth-fix1` (worktree `.worktrees/t204-fix1`, T-204 fix cycle 1 ready-for-check, not landed) already contains `ui/routers.py` (ROUTERS tuple, `include_all(app)`, `ui/app.py` reduced to 222 lines) and `auth/policy.py`. Read it so the shapes match, because TF header says "whichever of T-203, T-204 or G1 lands first creates `ui/routers.py` and `auth/policy.py`; the others extend them in place. A second router list or a second policy table is a defect."

## 3. Acceptance criteria (verbatim from `qa/contracts/team-foundation.md`)

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


## 4. What exists and what is missing

Measured on master `3a16616c` (line counts are `wc -l`):

| Concept | Exists (file:line) | Gap to the criterion |
|---|---|---|
| Run logic | `src/autotester/ui/routes_runs.py` (204 lines): `_is_entry_case` :42, `_require_declared_values` :55, `_require_live_case_approval` :75, `_execute_with_trace` :98, `trigger_run` :139 (POST `/projects/{slug}/run`), `Run(` constructed :173, `_ask_for_what_it_did_not_recognise` :188 | TF1: nothing in `stages/` is callable by a queue worker or the CLI tick. All of it lives in the route. TF2: the consent check is a route helper, not a launcher property. |
| Live-case approval (AT-570) | `_require_live_case_approval` :75-95 already refuses (HTTP 403) before any run id, directory or browser exists; `covering_approval` from `stages/explore_consent.py`, `ApprovalKind.LIVE_CASE` | Closed in code. The stale "AT-570 open" wording is in `.goal/goal.json` (T-201 note) and `docs/plan.md`; correcting it is the orchestrator's edit, not yours. TF2 needs the check re-verified through the launcher for `manual`, `schedule`, `ci`. |
| Router registration | `src/autotester/ui/app.py` (300 lines): 17 `app.include_router(...)` lines at :74-90, module imports :22-43 | TF3: no `ui/routers.py`, no `ROUTERS`, no empty stubs, no golden route snapshot. |
| CLI registration | `src/autotester/cli.py` (295 lines): `app.add_typer(...)` at :28-32 (`ledger`, `flowspec`, `report`, `ingest` = `cli_video.app`, `issues`), imports :10 | TF5: no sub-app list; no golden `--help` snapshot. |
| Run model | `src/autotester/schema/run.py` (121 lines): `Run` :78 already has `trigger: Trigger = Trigger.MANUAL`; `Trigger` enum (`manual`, `ci`, `schedule`) at `schema/enums.py:152` | TF2: no `requested_by`, `slot_key`, `via` fields. |
| Project / Source schema | `schema/project.py` (194 lines): `Source` :105, `Project` :130; `extra="forbid"` | TF6: no `schedule`, no `tracker`. Source provenance fields: see the open ruling in section 10. |
| Vocabulary file | `schema/enums.py` is 300 lines (at the cap, do not touch) | TF8: `schema/team_enums.py` does not exist. |
| Paths | `core/paths.py` is **300 lines (at the cap)**: `repo_root` :15, `ProjectPaths` :23, `work_dir` :212, `RepoDocs` :219-300 | TF7: team-store helpers need paths; there is zero headroom, and T-197 needs +6 lines in this file later. Free room first (see section 5). |
| Team store | `store/` has `filestore.py`, `project_store.py`, `crawl_store.py`, `request_store.py`, `run_store.py` | TF7: `store/team_store.py` does not exist. |
| Policy merge | `src/autotester/auth/` does not exist on master | TF4: `auth/policy.py` merge function; see section 10 for the T-204 collision. |
| Importers of `RepoDocs` (`paths.py:219-300`, the obvious split candidate) | 19 files under `src/`, 10 under `tests/`, 0 under `scripts/` | If you move `RepoDocs` out to make headroom, every `from autotester.core.paths import RepoDocs` must keep working: update all 29 importers, or keep a re-export that costs 1 line. The builder chooses how to free room; the checker judges the 300-line cap. |

## 5. Files the builder will touch

Product files:

| Path | New / existing | Lines now | Note |
|---|---|---|---|
| `src/autotester/stages/run_launcher.py` | new | - | TF1/TF2: the one launcher. No `fastapi` import. No `skip_approval` parameter. |
| `src/autotester/ui/routers.py` | new (or existing if T-204 landed first) | - | TF3: `ROUTERS` ordered tuple + `include_all(app)`; 8 empty `APIRouter()` stubs: `schedule`, `team_run`, `inbox`, `profile`, `tracker`, `video_review`, `video_portal`, `access_requests`. |
| `src/autotester/ui/app.py` | existing | 300 | Replace the 17 `include_router` lines and the router imports with one `include_all(app)`. Must end <= 300 and the registered order must not change. |
| `src/autotester/ui/routes_runs.py` | existing | 204 | `trigger_run` becomes a thin caller. The helper functions move out. |
| `src/autotester/schema/run.py` | existing | 121 | `requested_by`, `slot_key`, `via` optional, default `None`. |
| `src/autotester/schema/project.py` | existing | 194 | `Project.schedule`, `Project.tracker` (default `None`), typed minimal placeholders. Do NOT edit `Source` unless the ruling in section 10 goes the other way. |
| `src/autotester/schema/team_enums.py` | new | - | Group 10 vocabulary file; docstring says `enums.py` stays the home of pre-existing vocabularies. |
| `src/autotester/store/team_store.py` | new | - | TF7: atomic `os.replace` writes, `O_CREAT|O_EXCL` markers, one slug / slot-key validator, no `fcntl`/`pwd`/`grp`/`resource`/`os.fork`. |
| `src/autotester/core/paths.py` | existing | 300 | New helpers under the data root; must end <= 300. This is the hot file (section 10). |
| `src/autotester/cli.py` | existing | 295 | One hook iterating a `(name, typer_app)` list; stays <= 300. |
| CLI sub-app list module | new (name is the maker's choice; unknown) | - | TF5. |
| `src/autotester/auth/__init__.py`, `src/autotester/auth/policy.py` | new on master | - | TF4 merge function only, plus tests. See section 10 for the T-204 add/add collision. |
| `docs/MAP.md` | existing, generated | - | Regenerate with `uv run autotester map` only. Never hand-edit. |
| `docs/ARCHITECTURE.md` | existing | - | Rows for the new modules, only under a DECISIONS entry that names the section (Lab Protocol). That entry is the orchestrator's, not the builder's; leave a note for it. |

Test files:

| Path | New / existing |
|---|---|
| `tests/test_run_launcher.py` | new (TF1: AST/grep single-call-site test; no `fastapi` import) |
| `tests/test_run_launcher_approval.py` | new (TF2: `{manual, schedule, ci}` x `{no approval, covering approval}`; golden pre-change `run.json`) |
| `tests/test_routers_list.py` + `tests/golden/<routes>.json` (the `tests/golden/` directory does not exist yet) | new (TF3) |
| `tests/test_policy_merge.py` | new (TF4) |
| `tests/test_cli_subapp_hook.py` + a golden `--help` file | new (TF5) |
| `tests/test_project_schema_team.py` | new (TF6) |
| `tests/test_team_store.py` | new (TF7) |
| `tests/test_team_enums_home.py` | new (TF8) |
| the existing UI-run tests listed in section 6 | existing, patch-target edits only IF the ruling in section 10 allows it |

## 6. Test scope

Run only these (no directory, no full suite; the full suite is the orchestrator's pre-push check, recorded as `full-suite trigger: router/CLI seam`):

```
uv run pytest tests/test_run_launcher.py tests/test_run_launcher_approval.py tests/test_routers_list.py tests/test_policy_merge.py tests/test_cli_subapp_hook.py tests/test_project_schema_team.py tests/test_team_store.py tests/test_team_enums_home.py
uv run pytest tests/test_ui_runs.py tests/test_ui_runs_live_case_approval.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_serial_entry_mix_live.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_ui_runs_serial_resilience.py tests/test_credential_run_approval.py tests/test_ui_credential_safety.py tests/test_coverage_wiring.py tests/test_cli_surface.py tests/test_ui_origin_guard.py
uv run ruff check src tests scripts
uv run autotester doctor
```

Symbols that leave `ui/routes_runs.py` (`git grep` under `tests/` on master):

- `_is_entry_case`: `tests/test_ui_runs.py:154` (import), `:169`, `:170`; `tests/test_ui_runs_serial_entry_order.py:228`, `:237`; mention in `tests/test_ui_runs_serial_resilience.py:50` (docstring only).
- `_execute_with_trace`: `tests/test_ui_runs_serial_entry_order.py:227` (called directly as `routes._execute_with_trace`).
- `_require_live_case_approval`, `_require_declared_values`, `_ask_for_what_it_did_not_recognise`: no hits under `tests/`.

Monkeypatch targets that look up names in the `routes_runs` module and will stop reaching the code once the logic moves (`monkeypatch.setattr(<routes_runs>, "<name>", ...)`):

- `LangChainFallbackProvider` (17 sites): `tests/test_coverage_wiring.py:100`; `tests/test_credential_run_approval.py:225`; `tests/test_ui_credential_safety.py:163`; `tests/test_ui_runs.py:86,129,220`; `tests/test_ui_runs_live_case_approval.py:80`; `tests/test_ui_runs_parallel_crash_recovery.py:132`; `tests/test_ui_runs_parallel_trace.py:85,145,189,264`; `tests/test_ui_runs_serial_entry_mix_live.py:109`; `tests/test_ui_runs_serial_entry_order.py:65,147`; `tests/test_ui_runs_serial_entry_screenshot_namespace.py:97`; `tests/test_ui_runs_serial_resilience.py:69`.
- `plan_parallel_run` (7 sites): `tests/test_ui_runs_live_case_approval.py:260`; `tests/test_ui_runs_parallel_crash_recovery.py:80,133`; `tests/test_ui_runs_parallel_trace.py:88,267`; `tests/test_ui_runs_serial_entry_order.py:171,223`.
- `ulid` (1 site): `tests/test_ui_runs_serial_entry_order.py:264`.

TF1 says those RU tests pass "with assertions unedited". Retargeting a `setattr` is not an assertion edit, but the contract does not say so. Ruling needed (section 10). Until it is made, the safe design is to keep the seams the tests patch reachable (for example the route passes the judge factory and `plan_parallel_run` into the launcher), and the diff of those files must show zero changed `assert` lines.

## 7. Reachable test cases (happy path first)

- TF1: (1) `POST /projects/{slug}/run` through `TestClient` with two cases, a fake judge and the existing run fakes returns 303 to `/projects/{slug}/report` and saves a `Run` with the same fields as today. (2) A project with no cases returns 400 "has no cases to run"; no provider configured returns 400 in that order. (3) An AST/grep test: exactly one non-test `Run(` and one `_execute_with_trace(` call site in `src/`; `run_launcher.py` imports nothing from `fastapi`. (4) Mutation: paste the run logic back into `trigger_run`, the single-call-site test fails.
- TF2: (1) Live case, covering approval, `trigger=manual`: proceeds. (2) Live case, no covering approval, for each of `manual` / `schedule` (with a `slot_key`) / `ci`: launcher refuses with the same reason today's `trigger_run` gives, before any `BrowserSession` exists, the data-root listing is byte-identical, both counters 0 (asserted at the transport per `consent.md` CN1). (3) A `run.json` written before this unit loads unchanged. (4) AST check: the launcher has no `skip_approval`-style parameter.
- TF3: (1) Route-table snapshot `(methods, path, endpoint qualname)` in order equals the pre-change snapshot for the existing routes. The snapshot must be written so that later units adding routes (T-197, T-198, T-200, T-201, T-199) do NOT break it: compare the existing routes as an ordered prefix or subset, not as an exact full-table equality (otherwise every later unit fails this test). (2) The 8 stubs add zero routes. (3) A throwaway router appended to `ROUTERS` becomes reachable without editing `app.py`. (4) `wc -l app.py` <= 300. (5) Mutation: reorder two routers, snapshot fails.
- TF4: two fake unit dicts merge; each fail-at-import case (duplicate `"<METHOD> <path>"`; key not in the closed catalogue; `public` outside AU16's set; a route that does not exist) raises with a message naming the offender; key set equals the catalogue's. Mutations: last-wins merge; accept an unknown key.
- TF5: golden `autotester --help` command names plus one-line help via `typer.testing.CliRunner`; all existing exit codes unchanged; a throwaway sub-app appended to the list makes `autotester <name> --help` work without editing `cli.py`; `wc -l cli.py` <= 300.
- TF6: load every committed `projects/*/project.json`; a golden file with and without the new keys round-trips (load, save, load equal); an unknown key is still rejected; `Project.schedule` required would fail the old-file load (mutation).
- TF7: hostile names (`..\x`, `a/../../x`, `C:\x`, `CON`, `NUL`, trailing dot or space, 121 characters, both separators) are refused and a sentinel outside the root is untouched; a writer killed mid-write leaves the old content; source grep for forbidden imports; `git check-ignore` and `.dockerignore` assertions for the team-state root.
- TF8: `uv run autotester doctor` and ruff pass; no value defined in both `enums.py` and `team_enums.py`; every new file <= 300 lines.

## 8. Gate answers

- `qa/gates/plan-approved-g10.md` (Group 10 plan, units G1-G10 incl. T-205 as the new G1 row), final section, verbatim: `## Answer` / `Approved -- Umesh, 2026-10-07 (chat), recorded as D-074.`
- New modules: no gate file applies. `docs/DECISIONS.md` D-072 item 2, verbatim: "**New modules: yes to all.** This covers T-176 (...), T-202 (the LiteLLM provider), T-203/T-204 (hosting, auth), the Group 10 split modules, T-190's six paths, and `agents/`. Every file stays at or under 300 lines with a one-job docstring, and the checker judges it." D-074(a): "Build units G1-G10 per `docs/plan.md` and `qa/gates/plan-approved-g10.md` (... T-205 and T-206 as the new rows)."
- Other gate files (`drive-identity`, `email-sender-credentials`, `t199-first-live-write`, `t203-host-and-dns`, `write-policy-tier`): none applies to this unit (no Drive, mail, sheet, host or write-policy change).

## 9. UI surface and persona walk

- UI surface: no. `ui/app.py` and `ui/routes_runs.py` are server code; no `*.html`, `*.css`, page, component or user-facing flow is added or changed. The 8 router stubs register zero routes.
- `Persona walk: skip (refactor with no new screen, navigation path or flow; contract says G1 changes no behaviour; docs/plan.md G1 row says skip)`.

## 10. Dependencies and conflicts

Must land first: nothing. T-205 is the root of Group 10 (`docs/plan.md` waves: "after G1, run G2, G3 and G4 in parallel").

Shared files (one owner each; the others rebase on the owner's merge):

| File | Also wanted by | Proposed owner | Note |
|---|---|---|---|
| `ui/app.py` | T-204 (done on its branch: 222 lines), T-203 | T-205 | If T-204 lands first, T-205 extends its `ui/routers.py`; otherwise the later landing unit reconciles. |
| `ui/routers.py` | T-204 (created on its branch), T-197 (video_review stub), T-198b/G9, T-200, T-201, T-199 | T-205 | They only append to `ROUTERS`. |
| `ui/routes_runs.py` | T-203 (its branch is 252 lines and conflicts with master here), T-201/G7 | T-205 | T-203 must be re-based after (D-080 item 1: its branch goes back through the maker). |
| `core/paths.py` (300 lines) | T-197 (+6 lines: `review_path`, `review_work_dir`), T-203, T-200 | T-205 | T-205 must leave real headroom (at least 30 lines) or T-197's merge breaks the cap (g2 branch merged onto master measures 306). |
| `schema/project.py` | T-198 (Source provenance, already built on `wave/g3-zip-core`), T-200, T-199 | T-205 for the `Project` class; T-198 for the `Source` class | Same import block: expect a trivial textual conflict. |
| `schema/run.py` | T-200, T-201 | T-205 | Adds the three optional fields once. |
| `cli.py` (295) | T-204 (297 on its branch), T-174 | T-205 | |
| `auth/policy.py` | T-204 | whoever lands first creates it; the other extends in place | T-204's branch already has a different `auth/policy.py`: an add/add conflict if both create it. |
| `docs/MAP.md` | every unit | the integrator, regenerated at merge | Generated; the builder regenerates once, at the end. |
| `docs/ARCHITECTURE.md` | every unit | orchestrator, under one DECISIONS entry | |
| `tests/golden/` (new dir) | T-197, T-198 if they add routes | T-205 | Snapshot must tolerate later additions. |

Open rulings (the builder must not decide these; the checker or Umesh does):

1. **TF6 vs plan G3, `Source.uploaded_by / uploaded_at / origin`.** `team-foundation.md` TF6 gives these three fields to G1 (with `origin` a closed enum in `team_enums.py`). `docs/plan.md` G3 and `team-intake.md` TI11 give them to T-198, and `wave/g3-zip-core` already built them as a typed union `SourceOrigin` in `schema/intake.py` (upload / zip / drive with their payloads). The two shapes differ. Proposed: the checker amends TF6 so Source provenance belongs to T-198 and G1 keeps only `Project.schedule` / `Project.tracker`. Until it does, T-205 builds the Project half only.
2. **Patch-target edits in 13 existing test files** (section 6). Proposed: allowed when the diff changes only the `monkeypatch.setattr` target or an import, never an `assert`.
3. **TF4 / T-204 order.** Proposed: land T-205 first (small, M-tier), then T-204 merges master and reconciles `ui/routers.py` and `auth/policy.py`. The alternative (T-204 first) is also valid per the contract header.

## 11. Budget and process rules

- Check budget for tier L: 45 min wall clock. Builder budget: unknown (the repo gives none for a builder; aim for one worktree session).
- The builder runs no full suite. The full suite is the orchestrator's pre-push check.
- Falsification (the mutations named in the criteria) only in a throwaway copy outside the bound tree (`git archive` into the scratchpad); never mutate the worktree.
- Kill only PIDs you started. Headed browser lane max 1; this unit needs no browser.
- Edit in place; no `*_v2.py` / `*_new.py`; files <= 300 lines, functions <= 50, one-job module docstring, `extra="forbid"` models.
- Do not edit `qa/contracts/`, `docs/DECISIONS.md`, `.goal/goal.json`, `qa/issues.jsonl`. Write the manifest at `qa/manifests/t205-g10-headroom.md` with `Status: ready-for-check`, `Fix cycle: 0`, the Policy-Version line and the verbatim criteria.
- Use `git -C <worktree> ...`, never `cd X && ...`.
