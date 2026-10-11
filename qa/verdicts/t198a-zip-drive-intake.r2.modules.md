# t198a-zip-drive-intake: new-module list (D-082 item 1), addendum to the r2 dual PASS

Bound to `D:/autoTesting`. Checker, read-only. Single-purpose: it judges the 18 new modules only and does not re-check any criterion. The two coordinator verdicts (`.r2.a.md`, `.r2.b.md`) are untouched.

- Head checked: `dba80100307f62847c14a75c08bd674ac81c7f8f`, branch `wave/t198a-zip-drive-intake` (worktree `.worktrees/t198a-zip-drive-intake`, `git status` clean).
- List source: `git diff --diff-filter=A --name-only master...dba80100 -- src` = 18 files, 2,319 lines. I opened every file in full.
- Rule: D-082 item 1 (docs/DECISIONS.md:2357). A new module needs no owner gate when (a) the contract or brief names it, (b) its docstring states one job, (c) `autotester doctor` is clean, (d) the checker lists it.
- Also read: D-072 item 2 (docs/DECISIONS.md:2170, Umesh 2026-10-07, "New modules: yes to all ... the Group 10 split modules ... Every file stays at or under 300 lines with a one-job docstring, and the checker judges it"). It is ACTIVE and D-082 supersedes only D-057, so it stands beside D-082. T-198a is Group 10 (contract `team-intake.md` line 17).

## (a) how "named" was judged

`qa/contracts/team-intake.md` names no new module by path (its only module reference is `zip_intake.py` at line 70). The brief `qa/briefs/t198-video-intake.md` does:
- **B-named (7):** `zip_names`, `bounded_write`, `intake_commit`, `zip_intake`, `drive_verify` (brief lines 259-263, 295), `upload_limit`, `schema/intake` (lines 264-265, 296).
- **B-role (6), the brief requires a new module for this job but says "name unknown":** `cli_intake` (line 278: "the command body must live in a new module registered by a hook"), `drive_link` and `gws_drive` (lines 279, 298: link parser and gws adapter "in a sibling module under 300 lines"), `intake_upload`, `routes_intake`, `upload_stream` (line 302: "split them into a new module, name unknown").
- **D-072 only (5):** `drive_errors`, `gws_runner`, `drive_jobs`, `drive_intake`, `intake_gate`. The contract needs the job (TI8, HO33, TI7, TI10) but neither document names the file. These are Group 10 split modules in the sense of D-072 item 2, which Umesh already answered "yes to all" and which leaves the judging to the checker. I read (a) as met for them through D-072, not through D-082's literal wording. If the owner reads D-082 (a) as file names only, these five rest on D-072 alone.

## The 18 modules

Imports are `src` importers (full list in the evidence file). "One job" is what I found by reading the code.

| # | Module | Lines | (a) named where | (b) docstring, quoted | Does only that job? | Imported by | Result |
|---|---|---|---|---|---|---|---|
| 1 | `core/upload_limit.py` | 48 | B-named, brief :264, :296, :367 | "The ONE accessor for the admin upload limit (`max_upload_bytes`), read at request time." | Yes (`read_max_upload_bytes`, `human_bytes`, `UploadLimit`). One definition of the limit; no second `human_bytes` in src. | 6: drive_verify, gws_drive, zip_intake, intake_upload, routes_sources, upload_stream | OK |
| 2 | `schema/intake.py` | 165 | B-named, brief :265, :296 | "Shapes for video intake: zip limits, the per-member report, and where a source came from." | Yes, all pydantic models, `extra="forbid"`. | 12 (cli_intake, schema/project, 7 sources, 3 ui) | OK |
| 3 | `sources/bounded_write.py` | 64 | B-named, brief :260, :295 | "One bounded, hashing copy for every intake path (zip member, Drive fetch)." | Yes (`copy_bounded`, plus its `read_chunks` feeder). | 6 | OK |
| 4 | `sources/zip_names.py` | 91 | B-named, brief :259, :295; dual-trigger :13 | "Zip member-name vetting that behaves identically under Windows and Ubuntu path rules." | Yes. `ensure_inside` is a path-containment check also used by `intake_commit`, so the name is narrower than its reach. The other `is_relative_to` uses in src are inline, in other contexts, not a shared helper. | 3: intake_commit, zip_intake, intake_upload | OK |
| 5 | `sources/intake_commit.py` | 169 | B-named, brief :261, :295 | "Atomic video registration, the per-project intake lock, staging and orphan sweep." | Yes: lock, sweep, session and commit are one mechanism (file first, row second). | 4: cli_intake, drive_intake, zip_intake, intake_upload | OK |
| 6 | `sources/zip_intake.py` | 291 | B-named, brief :262, :295; dual-trigger :13 | "Safe zip expansion: one video source per video member, everything else accounted for." | Yes. It also holds `overall_status`, which `drive_intake` reuses. One definition, in the right job family. No second suffix list; it calls `require_recording_suffix`. 291 lines, 9 under the cap. | 3: cli_intake, drive_intake, intake_upload | OK |
| 7 | `sources/drive_verify.py` | 110 | B-named, brief :263, :295 | "Drive fetch verification: bound the download, check size and md5, stage it, or remove it." | Yes (`fetch_and_verify` plus the `DriveFetcher` seam it checks). One sentence is stale: it says the real fetcher "belongs to the integration slice", but `gws_drive.GwsDrive` now exists. Wording only. | 2: drive_intake, gws_drive | OK (docstring note 1) |
| 8 | `sources/drive_link.py` | 71 | B-role, brief :279, :298 (link parser) | "Parse a pasted Google Drive link (or a bare id) into a `DriveRef`: only an id survives." | Yes. `DRIVE_ID` is defined here once. | 4: cli_intake, drive_verify, gws_drive, routes_intake | OK |
| 9 | `sources/gws_drive.py` | 160 | B-role, brief :279, :298 (gws adapter) | "The real Drive seam: the existing `gws` CLI login behind `DriveFetcher` (metadata, list, fetch)." | Yes. It implements the one existing `DriveFetcher` and defines no third interface (brief :280). `_require_id` repeats the id check that `fetch_and_verify` also makes, with the same `DRIVE_ID` and message: two call sites of one rule, not two definitions. | 1: drive_intake | OK |
| 10 | `sources/gws_runner.py` | 128 | D-072 only (split of the gws adapter) | "Run the `gws` CLI as a subprocess: an argument list, a timeout, a size watch, no shell." | Yes (argument-list subprocess, shim resolution, byte-cap kill). | 1: gws_drive | OK |
| 11 | `sources/drive_errors.py` | 90 | D-072 only (contract TI8 requires the five messages; no file named) | "The ways a Drive fetch fails, each with its own fixed, human message (TI8, HO33)." | Yes (kind table, `DriveError`, `classify_gws_failure`). | 3: drive_intake, gws_drive, gws_runner | OK |
| 12 | `sources/drive_jobs.py` | 71 | D-072 only (hosting HO33 needs a polled job; no file named) | "Persist one Drive fetch job so the page can poll it and a restart cannot lose its result." | Yes. The job id is checked against the ULID shape before it touches a path. | 1: routes_intake | OK |
| 13 | `sources/drive_intake.py` | 196 | D-072 only (TI7 folder/zip/file handoff; no file named) | "Drive intake: one pasted link or id becomes registered sources, or an honest typed failure." | Yes (`intake_drive`, the file/zip/folder orchestrator, its own stale-fetch cleanup). `_MIME_SUFFIX` repeats the five suffixes of `RECORDING_SUFFIXES` as a mime map, but every value is re-run through `require_recording_suffix`, so it cannot widen the allowlist (docstring note 2). | 2: cli_intake, routes_intake | OK |
| 14 | `cli_intake.py` | 83 | B-role, brief :278 ("a new module registered by a hook") | "`autotester ingest zip` and `ingest fetch-drive`: hand over recordings without the browser." | Yes. `render_report` is the CLI text table; the HTML table is a different medium. Registered by a 2-line hook, `cli_video.py:14,295`. | 1: cli_video | OK |
| 15 | `ui/intake_gate.py` | 62 | D-072 only (TI10 seam; no file named) | "The one seam where sign-in and project permission plug into video intake." | Yes (`IntakeGate` protocol, `OpenGate`, `get_gate`/`set_gate`). TI10 itself stays HELD on T-204; that is for the unit's close-out and not a module question. | 2: intake_upload, routes_intake | OK |
| 16 | `ui/upload_stream.py` | 229 | B-role, brief :302 | "Read one multipart upload from the wire into a staged file, stopping at the admin limit." | Yes (`stream_upload`, the parser callbacks). `read_small_form` is the bounded Drive-box form reader; small, same bounded-read concern. | 2: intake_upload, routes_intake | OK |
| 17 | `ui/routes_intake.py` | 118 | B-role, brief :302 | "The Google Drive door of Add-videos: paste a link, get a background job and its result page." | Yes (two routes, the worker thread, the job card). | 1: routes_sources (`include_router`, line 38) | OK |
| 18 | `ui/intake_upload.py` | 143 | B-role, brief :302 | "The Add-videos upload door: one form field takes a recording or a zip of them." | **No: two jobs.** The docstring states the upload handler (`handle_upload`, `_commit_recording`). The file also holds the page fragments both doors render: `refusal_page`, `gate_refusal`, `report_table`, `report_page`, and `intake_forms`, which includes the Google Drive link form. Five of its seven functions are presentation. `routes_intake` imports `gate_refusal`, `refusal_page` and `report_table` from it for the Drive door, and `routes_sources` imports `refusal_page` and `intake_forms`. | 2: routes_intake, routes_sources | **FAIL (b)** |

## Doctor (c)

`uv run --project D:/autoTesting/.worktrees/t198a-zip-drive-intake autotester doctor` at `dba80100`: **`doctor: clean`** run from the repo root with `--project`, and again from inside the worktree; both exit 0 (the `VIRTUAL_ENV` mismatch warning is environmental). Output in `qa/evidence/t198a-zip-drive-intake-r2-modules/doctor.txt`. Largest file is 291 lines; no module is orphaned (every one has at least one `src` importer, table above).

## What I checked and found clean

- Every new module has a `src` importer; none is dead.
- "One concept, one place": no class or function in the 18 files is defined a second time in `src/` under the same name, apart from private helpers with different jobs (`_finish`, `_label`, `_report`, `_refusal`). The limit is read in one place (`upload_limit.py`); the Drive id charset in one place (`drive_link.DRIVE_ID`). Scan output: `qa/evidence/t198a-zip-drive-intake-r2-modules/importers-and-duplicate-scan.txt`.
- Two Drive seams exist, as the brief says (`DriveClient` in the existing `drive.py`, `DriveFetcher` in `drive_verify.py`, both with a `list_folder`). The unit added no third.

## Non-blocking notes (wording, not rulings)

1. `drive_verify.py` docstring: "the real fetcher ... belongs to the integration slice" is stale; `GwsDrive` implements the seam now.
2. `drive_intake._MIME_SUFFIX` is a second spelling of the five allowed suffixes; if `RECORDING_SUFFIXES` ever changes, the map will not follow. It fails closed (values are re-validated), so this is a low ledger row at most.

## Ruling

New-module rule (D-082 item 1): NOT SATISFIED for: `src/autotester/ui/intake_upload.py` - fails the one-job test in (b): its docstring states only the upload door, but the file also hosts the shared refusal/report page fragments and the Google Drive link form that the Drive door and `routes_sources` import. The other 17 modules satisfy (a) through (d); 11 of them are not named by file in the contract or brief, and that is covered by the brief's role description or D-072 item 2 as set out above.

So the unit does not merge on this addendum. This module needs the owner's gate, or a fix that makes it one job (for example, state the real single job in the docstring, or move the five page fragments and the Drive form into one sibling UI module, which would then also need listing). The two dual-check verdicts and every criterion result stand; this addendum changes none of them.

Evidence: `qa/evidence/t198a-zip-drive-intake-r2-modules/`.

Metrics: start=2026-10-11T04:40:00Z end=2026-10-11T05:10:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=0 cycle=2 resumes=0 tokens=unavailable policy=addendum lane=normal check_s=unavailable mutants=0 defects_unit=1 defects_6c=0
