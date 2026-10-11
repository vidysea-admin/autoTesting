# t198a-zip-drive-intake - sub-checker A, round 1: diff-scope and rulings (findings only, no verdict)

Bound: branch wave/t198a-zip-drive-intake head 894549ee, worktree D:/autoTesting/.worktrees/t198a-zip-drive-intake; diff `git diff 81f63ce9..894549ee` (43 files, +5001/-73). Nothing was run except git, grep, file reads and one AST line-count script (scratchpad lens.py, worktree venv `-I`). No pytest.

## A. Diff-scope

Only six existing files are modified (`git diff --diff-filter=DRM --name-status`): `.env.example`, `docs/MAP.md`, `cli_video.py`, `schema/project.py`, `stages/ingest.py`, `ui/routes_sources.py`. Nothing deleted or renamed at file level. All 18 test files are ADDED (tests: 18 files changed, 2572 insertions, 0 deletions) - no existing test, conftest, fixture or test-data file is edited.

Removed / renamed symbols (quoted from the diff):
1. `stages/ingest.py` `def _project_redactor(slug: str) -> Redactor:` -> `def project_redactor(...)`; call site in `ingest_video` updated (`redactor = project_redactor(project_slug) if redactor is None else redactor`). `git grep _project_redactor` in the worktree: only `qa/manifests/at779-ingest-narration.md:21` and `qa/verdicts/at779-ingest-narration.md:9` (historical prose) and the t198a manifest. No src/, tests/, scripts/ reference to the old name. New importer: `ui/intake_upload.py:29`.
2. `ui/routes_sources.py` `_link(href, text)` helper removed. `git grep "def _link\|_link("` hits only `stages/knowledge_graph.py` (its own, different `_link`) and `drive_link`/`parse_drive_link` substrings. No dangling use.
3. `ui/routes_sources.py` `def upload_source(slug, recording: Annotated[UploadFile, File()], label: str = Form(""))` (sync, copyfileobj + `_reserved_temp_path`) -> `async def upload_source(request: Request, slug: str)` delegating to `intake_upload.handle_upload`. Name and route path `/projects/{slug}/sources/upload` kept. Removed imports from routes_sources: `shutil`, `Annotated`, `File`, `UploadFile`, `SecretStore`... (SecretStore still imported), `file_sha256`, `work_dir`, `require_recording_suffix`, `_reserved_temp_path`. `_reserved_temp_path` is still used by routes_crawls.py:35/218, routes_issues.py:38/91, routes_report.py:28/282/295 - not orphaned. `core.ids.file_sha256` still used by providers/gemini_files.py:22 and sources/adapters.py:29.
4. `_refusal(slug, message, *, title="Recording not found")` kept with the same signature, now `return refusal_page(slug, message, title=title)` (routes_sources.py:41-42). Still used by the path form (`routes_sources.py:137` title "Not a recording", `:139` "Recording not found") and routes_learn etc. Default link text "Try another path" preserved in `refusal_page` (intake_upload.py:39-40). `refusal_page` does `theme.page(escape(title), ...)` (intake_upload.py:46) where the old `_refusal` passed the title unescaped; titles are static strings, so no visible change.
5. The old inline upload form in `sources_page` (`<form ... action=".../sources/upload">` with `accept="video/*"`) replaced by `intake_forms(...)` (new form accepts `video/*,.zip`; id `recording` and field name `recording` kept, intake_upload.py:82-83). Page card title "Upload a recording" is gone (now inside `intake_forms`).

Files changed that the manifest "What changed" does not name explicitly: `.env.example` (named later, "Integration with master"), `tests/*` (18 files; only some named in prose: the manifest names tests/asgi_helpers.py and tests/ui_intake_support.py; the others appear only in the pre-check commands), `docs/MAP.md` (named). `qa/manifests/t198a-zip-drive-intake.md` is the manifest. `scripts/`, `qa/contracts`, `uv.lock`, `pyproject.toml`: untouched. No unlisted src file.

Weakened or deleted assertion, skip/xfail, threshold, conftest/fixture/test-data edits in existing tests: none (zero deletions under tests/; conftest.py not in the diff).

Manifest accuracy nits: manifest says `ui/upload_stream.py (198)`, actual 216 lines (also at the code commit 642575ce); `routes_intake.py` said 116, actual 118. Not a rule breach (cap 300).

## B. Ruling 4 (old title "Not a recording", 422, old message)

- No existing test pins the old upload title or a 422 on the upload route. Master's upload tests: `tests/test_source_is_a_recording.py:119-130` (unknown suffix upload) asserts `status_code == 400`, content-type text/html, `"not a recording" in response.text` (lowercase), `store.list_sources() == []`, no `recording.video`. It still holds: the new message is `f"{exc}, or a .zip of them"` (ui/upload_stream.py:70) and `NotARecording`'s text starts "that is not a recording - add a video file ending in ..." (stages/ingest.py:96), so the lowercase string is present. The title assertion does not exist ("Not a recording" capital N appears in tests/ nowhere).
- `tests/test_source_is_a_recording.py:110` asserts "Try another path" - that is the path form, not upload; unchanged.
- `tests/test_ui_sources.py:97` asserts "Recording not found" - path form; unchanged. `tests/test_ui_sources.py:127` (upload happy path) and `test_source_is_a_recording.py:134-142` (mp4 upload `in (200, 303)`, path endswith `recording.mp4`) are consistent with the new handler.
- `tests/test_ui.py:114` `status_code in (400, 422)` is `/onboard`, unrelated. `qa/contracts/team-video-review.md:44` "HTTP 422" is about the label-paste route, unrelated.
- No contract line (hosting.md, ingest.md, source-adapters.md, browser-and-secrets.md) names the upload title, the 422 or the old message (grep of qa/contracts for `Not a recording` = no hits; HO30 pins 413 which the new code gives).
- Historic prose that does pin the old title, none executable: `qa/manifests/at433-source-is-a-recording.md:85` ("Upload form, notes.txt -> 400 'Not a recording'"), `qa/manifests/at446-...md:37,73`, `qa/verdicts/at433-...md:23,29`, `at446-...md:67-69` (browser observations of the path form and upload). They are closed records, not live assertions; but the browser claim for the UPLOAD form title is now stale.
- docs/, scripts/, src/: no e2e script or doc names the upload title. Only src hit: routes_sources.py:137, the path form (title unchanged).
- Behaviour change confirmed in code: upload non-recording -> `UploadRefused(400)` rendered by `refusal_page(..., title="Upload refused")` (intake_upload.py:133); non-multipart -> `UploadRefused(400, "That request is not a file upload form.")` (upload_stream.py:170-171) instead of FastAPI's 422. The manifest states both. Nothing found that breaks or is weakened.

## C. Ruling 5 (tests/asgi_helpers.py)

- NEW in this unit: `git ls-tree 81f63ce9 tests/asgi_helpers.py` returns nothing (only conftest.py exists at master with that path filter). Importers: tests/test_ui_intake.py:16 and tests/ui_intake_support.py:8 only. Not a shared master helper.
- conftest.py is NOT in the unit's diff. Its session autouse fixture `_ui_test_host` (tests/conftest.py:93-102, master's AT-758) sets `AUTOTESTER_ALLOWED_HOSTS=testserver` for the whole session; tests/test_ui_origin_guard.py:160-190 `monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS")` to see the real default and asserts `get("testserver") == 403 and get("autotester.example.org") == 403` (:183).
- Master's guard: `ui/helpers.py` `_host_allowed` (:218-241) and `_OriginGuard.__call__` (:268-290): refuses with an empty 403 when `host` header count != 1, origin count > 1, or `not _host_allowed(host)`, before any handler. Unchanged by this unit.
- Default `host="testserver"` in `post_stream` (asgi_helpers.py:80-86) is overridable per call (`host=` kwarg; `""` sends an empty Host header). It mirrors what TestClient does anyway, and `testserver` is already allowed for every UI test by the master conftest, so it hides no guard regression that every other UI test (TestClient, same `testserver` host) would not equally hide; the guard itself stays covered by test_ui_origin_guard.py.
- Hostile-Host tests exist and assert the claim:
  - tests/test_ui_intake.py:215-220 `test_at758_a_hostile_host_on_the_upload_route_is_403_before_any_body_byte`: loops hosts `evil.example`, `localhost:8000.evil.com`, `""`; each `post_stream(UPLOAD, endless(multipart_head("a.mp4")), host=host)` must give `status == 403 and page == b"" and served.bytes == 0`; then `gate.checks == [] and store.list_sources() == []`. That is exactly "403, zero body bytes read, gate not called".
  - tests/test_ui_intake_drive.py:116-121 `test_at758_a_hostile_host_on_the_drive_route_is_403_and_makes_no_job`: TestClient with `headers={"Host": "evil.example"}` -> 403, empty content, `gate.checks == []`, no `.work/drive-jobs` directory.
  - FINDING (low): in tests/test_ui_intake.py the first function is defined TWICE with the identical name and identical body (lines 215 and 223). The second shadows the first, so one is dead. No coverage lost (identical), but it is copy-paste residue hidden by the file-level `# ruff: noqa: F811` (line 7). Not run, not executed by me.
  - Gap (info): the harness builds the headers from a dict, so it cannot send a duplicate Host (AT-761); the duplicate-Host case is only covered by master's test_ui_origin_guard.py.
- Protected-test-change in the policy sense (editing conftest guards / weakening an assertion)? NO. asgi_helpers.py is a new file, conftest.py and every existing test are untouched, no assertion removed or relaxed, the helper's default Host matches what the already-allowed `testserver` conftest permits and the host stays overridable.

## D. Ruling 6 (new modules, one job; duplication)

Line counts and longest functions (AST, threshold > 40 lines listed): all new src modules <= 253 lines, none has a function over 40 lines. Every new module has a docstring.
- cli_intake.py (83): `ingest zip` / `ingest fetch-drive` commands.
- core/upload_limit.py (48): the ONE accessor for the admin upload limit; delegates to store/server_settings (`effective_max_upload_bytes`, `load_server_settings`) and `schema/server_settings.DEFAULT_MAX_UPLOAD_BYTES`. No second 2 GiB literal (only `schema/server_settings.py:12-18`).
- schema/intake.py (165): zip limits, per-member report, origins, Drive shapes, `IntakeActor`.
- sources/bounded_write.py (64): one bounded hashing copy for zip member and Drive fetch.
- sources/drive_errors.py (90): Drive failure kinds with fixed messages.
- sources/drive_intake.py (196): link/id -> registered sources.
- sources/drive_jobs.py (71): persist one Drive job file.
- sources/drive_link.py (71): parse pasted link into `DriveRef`.
- sources/drive_verify.py (110): bound, size+md5 check, stage a download.
- sources/gws_drive.py (160): `DriveFetcher` over the `gws` CLI.
- sources/gws_runner.py (128): run `gws` as subprocess.
- sources/intake_commit.py (169): atomic registration, per-project lock, staging.
- sources/zip_intake.py (253): safe zip expansion.
- sources/zip_names.py (91): member-name vetting.
- ui/intake_gate.py (62): the sign-in/permission seam.
- ui/intake_upload.py (143): upload door.
- ui/routes_intake.py (118): Drive door and job page.
- ui/upload_stream.py (216): streaming multipart read under the limit.

Duplication check against master:
- Suffix list: NO second list. `stages/ingest.py:74 RECORDING_SUFFIXES` + `require_recording_suffix` are called by zip_intake.py:97, intake_commit.py:153, drive_intake.py:64/69, upload_stream.py:68, intake_upload.py:103. `drive_intake._MIME_SUFFIX` (line 44) is a mime->suffix map re-checked through `require_recording_suffix`. `zip_names.NESTED_SUFFIXES` (line 23) is an archive-suffix refusal list, a different concept. The ".zip" literal is tested in upload_stream.py:65 and `gws_drive.ZIP_MIMES` (mime), mild.
- Size limit: NO second literal; `schema/intake.py ZipLimits` holds the zip caps (defaults 1000/20/10e9/5e9/100/1MiB at schema/intake.py:45-54); `ServerSettings` has no zip fields (schema/server_settings.py has only `max_concurrent_runs`, `max_upload_bytes`), so ZipLimits is the only declaration. Note spec R41 says "zip limits likewise" an admin setting; TI2 only requires named defaults in one place, so this meets the contract.
- sha256: `core/ids.py:112 file_sha256` (file-based, master) is not reused; the new code hashes on the stream in two places: `sources/bounded_write.py:37` (`copy_bounded`, sha256 + optional md5) and `ui/upload_stream.py:83` (`self.sha = hashlib.sha256()`, incremental over the wire). Both are incremental-while-copying (needed to bound), so not a clear duplicate of the file-based helper; but two streaming hashers exist (low). Master's `drive_register.py:171/194` and `email_register.py` also hash independently.
- Atomic write: `store/filestore.py:21 _atomic_write` (text, private, mkstemp+os.replace) vs `sources/drive_jobs.py:save_job` (fixed `path.with_suffix(".tmp")` + `os.replace` retry loop for Windows, :40-52) vs `sources/intake_commit.py:_copy_in/_place` (binary, EXDEV fallback). drive_jobs is a second small JSON atomic writer (it adds a PermissionError retry that filestore lacks); `filestore` helper is private, so reuse would need an edit. Low, and note a fixed `.tmp` name is shared by concurrent savers of the same job.
- Temp-file helper: `ui/helpers.py:174 _reserved_temp_path` no longer used by the upload route; the new route stages under `work_dir(root)/uploads/<slug>/<ulid>` (intake_upload.py:~117) and `intake_commit.staging_root`. Two staging notions in the new code (upload staging in intake_upload, intake staging in intake_commit); no conflict with master.
- Drive: `sources/drive.py` (`DriveClient`, `HttpDriveClient`, OAuth device flow, `list_folder`/`fetch_file`) and `sources/drive_register.py` remain; the new `DriveFetcher` protocol (drive_verify.py:45) + `GwsDrive` (gws_drive.py:100) is a SECOND Drive transport and a second register path (intake_commit vs drive_register). The manifest admits it ("a second DriveFetcher, not a replacement"); justified by D-081 (docs/DECISIONS.md:2332, shell out to gws). A concept-level duplication to rule on. Error taxonomy: drive.py has no typed taxonomy (it degrades on bare `except Exception`, drive.py:203), so `drive_errors.DriveFailure` is not a second taxonomy, but `DriveVerifyError` (drive_verify.py) and `LimitExceeded` (bounded_write) sit beside `DriveError`; three Drive-adjacent exception types.
- Redaction: `project_redactor` reused (renamed public); no second redactor.

## E. Design-rule sweep

- No new/changed src file over 300 lines (largest new: zip_intake.py 253; modified: stages/ingest.py exactly 300, cli_video.py 295).
- No function over 40 lines in any new or modified src module except two PRE-EXISTING in cli_video.py (`run_cmd` 42 at :184, `analyze_cmd` 45 at :229), both under 50 and not touched by this diff. So no function over 50.
- Every new test file is under 300 lines (test_drive_intake.py 230 is the largest by stat).
- `# ruff: noqa: F811` file-level suppressions in tests/test_ui_intake.py:7 and test_ui_intake_drive.py:6 hid the duplicate function definition noted in C.
