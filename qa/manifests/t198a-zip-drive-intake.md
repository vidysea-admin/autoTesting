# Manifest - t198a-zip-drive-intake (Group 10 unit G3 / T-198a: zip and Drive intake)

## Status: ready-for-check

**Contract:** qa/contracts/team-intake.md TI1-TI11, qa/contracts/hosting.md HO15, HO30-HO33 (referenced, not restated)
**Goal task:** T-198 slice G3. The developer-portal slice t198b is NOT in this unit.
**Authority:** D-072 (group answers), D-081 (Drive identity: the live fetch shells out to the existing `gws` login; no token is copied into the repo), D-066 (Origin guard, unchanged and still first)
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (untrusted archives and links write to the filesystem; a request-body limit; an auth seam)
Fix cycle: 0
Branch: wave/t198a-zip-drive-intake, based on master 3d8f7d5a. Earlier work of branch wave/g3-zip-core (slice 1, not landed) was carried in by file copy; that branch and its worktree are untouched. Master was not merged.
Code commit under check: 5cfd9eb0
Executor: claude-sonnet-subagent (maker build subagent)
Dual check: required
dual-trigger: security src/autotester/sources/zip_names.py:77 (`ensure_inside`), security src/autotester/sources/zip_intake.py:214 (`expand_zip`), security src/autotester/ui/upload_stream.py:175 (`stream_upload`, the streaming body limit), auth src/autotester/ui/intake_upload.py:111 (`handle_upload`, the gate seam)
Persona walk: required (persona `dev`: the Add-videos page with the zip result table and the Drive job page). Not run by me: no browser was used.
Round cap: SECURITY CLASS (untrusted archive and link intake), the 2-PASS cap for non-security seams does not apply

## Acceptance criteria

The criteria are rows TI1-TI11 of qa/contracts/team-intake.md plus hosting.md HO30, HO32, HO33 as the brief copies them (qa/briefs/t198-video-intake.md section 3). TI10 is HELD (below).

## What changed (existing files edited in place; new modules are the ones the brief and contract name)

Carried from wave/g3-zip-core and adapted (zip core): `sources/zip_names.py` (TI1), `sources/bounded_write.py`, `sources/intake_commit.py` (TI4/TI6), `sources/zip_intake.py` (TI1-TI6), `sources/drive_verify.py`. Master's `ServerSettings` replaced the branch's JSON-file limit source, so there is one limit.
- `core/upload_limit.py` (48): `read_max_upload_bytes` now delegates to `store/server_settings.py` (T-203); the one accessor for the HTTP upload, the Drive fetch and zip inflation. The only 2 GiB literal stays in `schema/server_settings.py`.
- `schema/intake.py` (165): `ZipLimits` (TI2 caps, the only place they are declared), `IntakeReport`, origins, plus `DriveRef`, `DriveItem`, `IntakeActor` (the gate's answer), `DriveJob`. `schema/project.py`: `Source` gained `uploaded_by`, `uploaded_at`, `origin` (master's `user_persona` fields kept).
- Drive: `sources/drive_link.py` (71, TI7 / HO32 link parsing: https, exact host, no userinfo, id charset, never echoes the input), `sources/drive_errors.py` (90, TI8 five typed failures plus gws-missing, fixed messages, raw gws text dropped), `sources/gws_runner.py` (128, argument-list subprocess, shim resolved to `gws.exe`, timeouts, kills the process at the byte cap), `sources/gws_drive.py` (160, the `DriveFetcher` over gws), `sources/drive_intake.py` (196, file / zip / folder), `sources/drive_jobs.py` (job file store).
- CLI: `cli_intake.py` (83: `ingest zip`, `ingest fetch-drive`, exit 2 on partial); `cli_video.py` (295) gained a 2-line registration hook.
- UI: `ui/intake_gate.py` (62, the TI10 seam), `ui/upload_stream.py` (198, streaming multipart read with the limit), `ui/intake_upload.py` (143, the upload handler, per-member table, the two forms), `ui/routes_intake.py` (116, Drive link job and job page). `ui/routes_sources.py` (202): `upload_source` rewritten in place as the async delegate; the page shows the limit and the zip and Drive controls; `_refusal` now calls the shared page; the router includes `routes_intake` (so `ui/app.py` stays at 300 lines). `stages/ingest.py`: `_project_redactor` renamed `project_redactor`.
- `docs/MAP.md` regenerated.

## Bounds, and where each is declared

| bound | value | declared |
|---|---|---|
| per-file bytes (upload, Drive file, zip member) | admin `max_upload_bytes`, default 2 GiB, 1 MiB..64 GiB, re-read each request | `schema/server_settings.py`, read through `core/upload_limit.py::read_max_upload_bytes` only |
| entries / videos / total uncompressed / archive / ratio | 1000 / 20 / 10 GB / 5 GB / 100:1 (ratio only above 1 MiB declared) | `schema/intake.py::ZipLimits` |
| body overhead beyond the file limit | 256 KiB; field 16 KiB; part header 8 KiB; small form 64 KiB | `ui/upload_stream.py` constants |
| Drive metadata timeout / download timeout / folder pages | 60 s / 3600 s / 10 | `sources/gws_drive.py` |
| stale job | 2 h | `sources/drive_jobs.py` |

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L. No builder full suite; scoped files only, one pytest process at a time with `-p no:xdist`.
Pre-check: 5cfd9eb0 uv run ruff check src tests scripts -> All checks passed!
Pre-check: 5cfd9eb0 uv run autotester doctor -> doctor: clean (worktree; the three root-clutter violations exist only in the root checkout); `uv run autotester map` run
Pre-check[TI1]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_zip_intake_names.py tests/test_zip_intake_limits.py tests/test_zip_intake_register.py tests/test_zip_intake_atomic.py -> 93 passed (names, limits, register, atomic files; the same four files serve TI1, TI2, TI4, TI5, TI6)
Pre-check[TI2]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_zip_intake_names.py tests/test_zip_intake_limits.py tests/test_zip_intake_register.py tests/test_zip_intake_atomic.py -> 93 passed (limits file: ratio, lying header, entries, nested, total)
Pre-check[TI3]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_ui_intake.py tests/test_cli_intake.py -> 27 passed (5-member zip table, .env and .ps1 skipped, CLI JSON one outcome per member)
Pre-check[TI4]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_zip_intake_names.py tests/test_zip_intake_limits.py tests/test_zip_intake_register.py tests/test_zip_intake_atomic.py tests/test_drive_intake.py -> 114 passed (duplicates, hostile Drive names never reach a path)
Pre-check[TI5]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_zip_intake_names.py tests/test_zip_intake_limits.py tests/test_zip_intake_register.py tests/test_zip_intake_atomic.py tests/test_cli_intake.py -> 101 passed (partial is exit 2, not ok)
Pre-check[TI6]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_zip_intake_names.py tests/test_zip_intake_limits.py tests/test_zip_intake_register.py tests/test_zip_intake_atomic.py -> 93 passed (atomic file: crash after member N, concurrent intakes)
Pre-check[TI7]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_drive_link.py tests/test_drive_verify.py tests/test_drive_intake.py tests/test_ui_intake_drive.py -> 83 passed (good md5, wrong md5, short read, folder with PDF, zip id with hostile member, hostile link)
Pre-check[TI8]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_gws_drive.py tests/test_gws_runner.py -> 49 passed (five distinct messages, canary token absent from stdout, stderr, caplog, messages)
Pre-check[TI9]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_ui_intake.py tests/test_drive_intake.py -> 40 passed (5 MiB exact ok, +1 refused, setting changed between requests, endless body stopped, lying Content-Length)
Pre-check[TI10]: HELD on T-204 (no authorize()); seam proved: 5cfd9eb0 uv run pytest -p no:xdist tests/test_ui_intake.py tests/test_ui_intake_drive.py -> 30 passed (gate before the first body byte, re-check at job start, refusal writes nothing)
Pre-check[TI11]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_ui_intake.py tests/test_ui_intake_drive.py tests/test_drive_intake.py -> 51 passed (uploaded_by from the gate only, origin shapes, form field ignored)
Pre-check[HO30]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_ui_intake.py -> 19 passed (streaming limit at the ASGI level)
Pre-check[HO32]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_drive_link.py tests/test_ui_intake_drive.py -> 44 passed (hostile hosts and schemes refused, not echoed, no job)
Pre-check[HO33]: 5cfd9eb0 uv run pytest -p no:xdist tests/test_ui_intake_drive.py tests/test_gws_runner.py -> 21 passed (fetching page, typed failure on the page, timeouts)
Pre-check: 5cfd9eb0 uv run pytest -p no:xdist tests/test_ui_sources.py tests/test_source_is_a_recording.py tests/test_cli_advice_resolves.py tests/test_ensemble_honesty.py tests/test_merge_flowspec_cli.py tests/test_server_settings.py tests/test_drive_verify.py tests/test_intake_schema.py -> 164 passed (existing neighbours of the touched files plus the schema and verify files)
mutant-cap-raise: security-class unit with 12 contract rows plus 3 review-found defects; one mutation per row, each recorded in the table below
Metrics: start=2026-10-11 end=2026-10-11 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=19 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9

## Falsification (throwaway copy of src, tests, scripts under the scratchpad, outside the worktree; run with the worktree venv and `PYTHONPATH=<copy>/src`; the originals restored after each; the copy is discarded)

Each row: scoped tests green on the copy before the edit, then red after it.

| Row | edit in the copy | before | after |
|---|---|---|---|
| TI1 | `ensure_inside` containment -> `str(resolved).startswith(str(base))` | 65 passed | 1 failed |
| TI1 | member name split only on `/` | 65 passed | 12 failed |
| TI2 | ratio check removed | 9 passed | 1 failed |
| TI2 | inflate cap removed (header lies about size) | 9 passed | 2 failed |
| TI5 | overall status `OK` when any member registered | 22 passed | 4 failed |
| TI7 | md5 compare skipped | 39 passed | 3 failed |
| TI8 | raw gws stderr printed before the typed error | 39 passed | 9 failed |
| TI9 | limit hard-coded to 2 GiB instead of the accessor | 37 passed | 8 failed |
| TI9/HO30 | streaming limit check removed in the upload parser | 16 passed | 3 failed |
| TI10 seam | gate runs after the body is drained | 1 passed | 1 failed |
| TI10 seam | no gate re-check when the queued job starts | 10 passed | 2 failed |
| TI11 | `uploaded_by` taken from a form field | 16 passed | 1 failed |
| HO32 | the pasted link echoed in the refusal page | 10 passed | 1 failed |
| review fix | archive name in the heading unescaped | 19 passed | 1 failed |
| review fix | a cut-off multipart body accepted | 19 passed | 1 failed |

Two mutations SURVIVED and are stated, not hidden:
- TI2 "trust the declared size" (removing only the central-directory pre-check `if info.file_size > per_file`) stays green: the inflate cap refuses the same member with the same message, so the pre-check is observable only as "zero bytes written", which no test measures. The lying-header mutation (the inflate cap) is caught. PROPOSED-ISSUE below.
- Part-header cap removed (`HEADER_CAP`): the 40 KiB header test is refused with 400 either way; only the memory bound differs. PROPOSED-ISSUE below.
Not mutated by me: row-before-copy (TI6), the register-everything and name-in-stored-path mutations (TI3/TI4); the inherited tests of wave/g3-zip-core carry those, and I did not re-run those mutations here.

## Held and left to others

- **TI10 is HELD on T-204** (accounts, groups, `authorize()`, the `video.upload` permission). What is built and proved is the seam: `ui/intake_gate.py` (`check` before any body byte is read, `recheck` when the queued Drive job starts, a refusal creates no job and writes nothing), `uploaded_by` only from the gate. The default gate is open and records nobody, so on a live host intake is as open as the old upload route was until T-204 installs a gate. The unit cannot close T-198 on its own.
- **SERVER-GATED / not run:** one real Drive fetch (needs the owner's approved synthetic video and the server's `gws` login, D-081), a real >= 1 GiB upload through the proxy (HO30/HO31), the Linux run of the R65 assertions (`qa/evidence/t198-linux-run.md` not written).
- **BROWSER checks not run:** the persona walk for TI3 (zip result table as `dev`) and the Drive job page polling. The page is exercised only through TestClient and an ASGI harness.
- t198b (share link, access requests, comments) is untouched.

## How to verify
- `uv run pytest -p no:xdist tests/test_ui_intake.py tests/test_ui_intake_drive.py tests/test_drive_intake.py tests/test_cli_intake.py tests/test_gws_drive.py tests/test_gws_runner.py tests/test_drive_link.py tests/test_drive_verify.py tests/test_intake_schema.py tests/test_zip_intake_names.py tests/test_zip_intake_limits.py tests/test_zip_intake_register.py tests/test_zip_intake_atomic.py tests/test_ui_sources.py tests/test_source_is_a_recording.py`
- `uv run ruff check src tests scripts`; `uv run autotester doctor`.
- The ASGI-level endless-body and lying-Content-Length tests are in `tests/test_ui_intake.py` (helper `tests/asgi_helpers.py`); a `TestClient` cannot show that the server stops reading.

## Review
A fresh `senior-software-engineer` read of the new UI files found: HTML injection through the archive name in the result heading (FIXED, with a test), a cut-off multipart body accepted as complete (FIXED, test), an unbounded part header (FIXED), a Windows `os.replace` race on the job file and an unguarded save in the failure path (FIXED), a project-slug length mismatch (FIXED), `parse_qs` raising on more than 50 fields (FIXED, test). Not fixed, listed below. Behaviour changes noticed: a non-recording upload now answers 400 titled "Upload refused" (was "Not a recording"); a non-multipart body answers 400 (was 422). No existing test pinned either.

## Not claimed / gaps stated
- The checker must run the full suite; I ran none. The neighbours I ran are listed above.
- Windows only. Nothing here was run on Linux.
- `tests/test_ui_intake*.py` import fixtures from `tests/ui_intake_support.py` (file-level `ruff: noqa: F811`), to stay under 300 lines per file.
- `sources/drive.py` (`DriveClient`, `HttpDriveClient`) is untouched; the gws path is a second `DriveFetcher`, not a replacement.

PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":"No test shows the zip central-directory per-file size pre-check writes zero bytes; removing the pre-check leaves every test green","file":"tests/test_zip_intake_limits.py","fix":"assert the staging folder holds no bytes after a declared-oversize member is refused"}
PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":"The multipart part-header cap (HEADER_CAP) is not observable through the status code; removing it keeps the suite green","file":"src/autotester/ui/upload_stream.py","fix":"measure bytes buffered, or assert the cap constant in a unit test of _Reader"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"No cap on concurrent Drive worker threads: one member can start unlimited fetches","file":"src/autotester/ui/routes_intake.py","fix":"refuse with 429 when more than N drive-job threads are alive, once T-204 gives a per-member identity"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"Until T-204 the default intake gate is open and uploaded_by stays empty, so on a hosted server anyone who can reach the page can add videos","file":"src/autotester/ui/intake_gate.py","fix":"T-204 installs its gate with set_gate; consider refusing intake on a non-loopback host while the open gate is installed"}
