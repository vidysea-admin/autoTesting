# t198a-zip-drive-intake r2 - Q7 credentials / gws stderr (findings only, no verdict)

Head 894549ee, worktree D:/autoTesting/.worktrees/t198a-zip-drive-intake. Read-only. No pytest, no gws run.
Paths below are relative to src/autotester/ unless they start with tests/.
Executed once: `classify_gws_failure('', '{"error":{"code":403,"errors":null}}')` (python, PYTHONPATH=worktree src) -> TypeError; `"errors":5` -> TypeError.

## 1. No credential read into the process - CONFIRMED (with two PARTIAL notes)
- grep of environ|getenv|credentials|.config|token|authorization|expanduser|appdata|env= over gws_runner, gws_drive,
  drive_errors, drive_intake, drive_jobs, drive_verify, drive_link, cli_intake, ui/routes_intake, ui/intake_upload,
  ui/upload_stream: the only environment read is gws_runner.py:52 `env.get(GWS_BIN_ENV) or which("gws")` (a path).
  No code opens ~/.config/gws, credentials.json or any token file. `token` in gws_drive.py:116-126 is Drive's
  `nextPageToken` (a pagination cursor, not a credential), passed inside the --params JSON.
- Subprocess env: NOT scrubbed. gws_runner.py:88-90 (`subprocess.run`, no env=) and :104-106 (`Popen`, no env=) inherit
  os.environ. The docstring says so (gws_runner.py:5). core/env.py:46-68 `load_repo_env` copies the whole repo `.env`
  into os.environ at CLI/UI start (cli.py:47, ui/app.py:67), so the `gws` child also receives every project secret and
  provider key the server holds (PATHLYNKS_*, AUTOTESTER_APPROVAL_KEY, ...). Not a Drive token leak, but least-privilege
  is not applied; gws is trusted. [PARTIAL on "env scrubbed" - it is inherited by design]
- No token on a command line: argv is `["drive","files","get","--params",<json>, ("-o","download.part")]`
  (gws_drive.py:109-111, 141-142). Only fileId, fields, supportsAllDrives, q, pageSize, pageToken, alt are in the JSON.
- AUTOTESTER_GWS_BIN: path only (gws_runner.py:52-61), `.env.example:96`. Not validated: no existence, basename or
  allowlist check beyond the shim redirect. It is a server env var, but it is also writable from the web UI: the
  Credentials page declares any `^[A-Z][A-Z0-9_]*$` key (schema/project.py SecretRef.key; ui/routes_project_edit.py:45-62
  build_secret_ref has no reserved-name denylist) and ui/routes_credentials.py:136-157 `set_env_value(repo_root()/".env", ...)`
  writes it. After the next restart (load_repo_env only fills unset vars) the Drive route would exec that path. This needs
  credentials-page access (open until T-204's gate) and a restart, so I rate it a question/Low, but the unit adds a new
  consumer of an unvalidated executable path. A relative AUTOTESTER_GWS_BIN is also passed as-is to Popen with cwd=<dl folder>.
- shell=False everywhere (gws_runner.py:90, 106). Windows `.cmd/.bat/.ps1` or suffix-less shim is redirected to the real
  gws.exe or refused (gws_runner.py:56-60), so cmd.exe is never in the path.
- Id injection: `_require_id` (gws_drive.py:47-51) -> `DRIVE_ID.fullmatch(r"[A-Za-z0-9_-]{6,128}")` (drive_link.py:17).
  fullmatch, so a trailing "\n" fails (tests/test_gws_drive.py:87 covers it). An id such as "-abcdef" DOES pass the charset
  (leading '-' allowed) but it is never a standalone argv element: it sits inside the `--params` JSON string
  (`{"fileId":"-abcdef",...}`), so no flag injection. The list query is `f"'{id}' in parents and trashed=false"` after the
  same check (gws_drive.py:114). Gap: `item.id` used at gws_drive.py:141 (`fileId=item.id`) comes from gws output and is not
  re-run through `_require_id` there (the id passed to open() was checked at drive_verify.py:88 / :132 metadata call); it is in
  JSON either way. Low.
- parse_drive_link never fetches a URL, only an id survives (drive_link.py:50-71).

## 2. gws stdout/stderr never reaches page/log/exception/job/source row - CONFIRMED for the real path
- Capture points: gws_runner.py:88-95 (run: capture_output text) and :102-118 (download: two TemporaryFile, read back).
  Both only return GwsResult to gws_drive; nothing logs it.
- Only consumers: `_json` gws_drive.py:72-81 and open() gws_drive.py:145-146, both ONLY call
  `classify_gws_failure(stdout, stderr)` (drive_errors.py:79-90) -> returns an enum; `DriveError(kind)` message is the fixed
  table MESSAGES[kind] (drive_errors.py:25-52). `json.loads` failure -> `raise DriveError(NETWORK_ERROR) from None`
  (gws_drive.py:77-78), `from None` drops the chained ValueError (which would hold a stdout fragment).
  TimeoutExpired / OSError mapped with `from None` (gws_runner.py:91-94, 107-108).
- Logging: grep of logging|logger|log.|print(|typer.echo|secho|warnings over the listed modules: only
  ui/routes_intake.py:13,35,59 `log.exception("drive job %s failed", job.id)` (traceback of an UNEXPECTED exception; DriveError
  text is fixed; no locals) and cli_intake.py:39,45,55,61,74 (project name, report, DriveLinkError message which never echoes
  the link - drive_link.py:25). typer 0.27.2 `pretty_exceptions_show_locals` default False (checked), and no override in repo.
- Job file (sources/drive_jobs.py:37-53) stores DriveJob (schema/intake.py:152-): id, project, state, drive_id, message, report
  (IntakeReport: member = scrubbed label, reason = fixed text or str(DriveError/DriveVerifyError/IntakeBusy), notes), timestamps.
  Never the link or any gws text. Job id regex JOB_ID and SLUG checked before the path is built (drive_jobs.py:23-34).
- HTML: ui/routes_intake.py:89-100 escapes state, slug, message; report_table (ui/intake_upload.py:53-62) escapes member,
  outcome, reason, notes, counts; report_page heading escapes archive (:66); forms escape slug and the limit (:76,84).
  refusal_page escapes message/slug/link_text and the <title>; card title is raw (theme.py:102) but every caller passes a
  constant. A Drive file name/mime/id cannot inject HTML. (`slug` in redirects is regex-validated by _require_slug.)
- Exception text to page: DriveJob.message is `_FAILED` constant or IntakeRefused.message (routes_intake.py:40,51,61).
  The page string for unknown exceptions never carries str(exc).
- Not leaking but fragile: classify_gws_failure crashes on odd error bodies (see D1).

## 3. Drive-supplied text -> filesystem path / log - CONFIRMED none
- Names/paths generated: dl-<ulid>/download.part (gws_drive.py:140,31), drive-<ulid>.part (drive_verify.py:93),
  fetch_root/<ulid> (drive_intake.py:108,136), final `sources/<id>/recording<suffix>` (intake_commit.py:141-169, ensure_inside).
  Suffix comes only from `require_recording_suffix` allowlist, or a mime table fallback re-vetted (drive_intake.py:44-69).
  File name only becomes `label` (scrubbed, [:200]) and a table cell (escaped). `member`/md5/mime never reach a path or a log.

## 4. Redactor on origin/label - CONFIRMED for Drive; PARTIAL for browser upload
- Drive: label = `scrub(base)[:200]` (drive_intake.py:56-58) used at :107,113-115; origin = `DriveOrigin(file_id=item.id)` only
  (id validated by drive_verify.py:88 before commit). CLI/UI pass `project_redactor(slug).scrub` (cli_intake.py:77,
  routes_intake.py:56). Default scrub is identity (drive_intake.py:174) - fine, both callers pass the real one.
- Drive zip: archive_name = scrubbed label, then expand_zip scrubs again (zip_intake.py:231); member_path scrubbed (:81).
- Upload (ui/intake_upload.py): origin.file_name scrubbed (:108); label stored RAW but first run through
  `_refuse_unsafe_submission` (:124), i.e. refused rather than scrubbed if it contains a secret. Behaviourally safe, different mechanism.
- `_skipped` reason embeds Drive `item.mime_type` unscrubbed (drive_intake.py:167): Drive text, escaped on the page, stored in the job file. Low.

## 5. Tests - PARTIAL
- tests/gws_fakes.py:13 CANARY = "ya29.CANARY-TOKEN-do-not-print-0123456789"; planted in every error BODY of
  tests/test_gws_drive.py:130-145 FAILURES (9 cases incl. 401, 403, 404, 429, dns error) and unparseable stdout (:174).
  Test :148-159 asserts canary absent from `str|repr|args` of the DriveError, capsys out+err and caplog.text, and exact
  message == MESSAGES[kind]. This does give the "repr(exc) in the message" mutation a failing test.
- NOT covered: (a) there is no fake CREDENTIAL (no token in env / credential file) - the canary is only in error bodies;
  (b) the canary is not run end to end through intake_drive -> job file -> job page -> sources.jsonl. UI tests
  (tests/test_ui_intake_drive.py:33-37, 60-70) inject a pre-typed `DriveError(PERMISSION_DENIED)` with no canary;
  :99-106 plants CANARY-USP in the pasted LINK, not in gws output; (c) no audit-file grep - this unit writes no audit file
  (grep "audit" over sources/drive*.py and ui/*intake* finds only a docstring), TI8's "the audit file (AU22)" is untested here;
  (d) the failed-download canary test tests/test_gws_drive.py:181-188 asserts kind and cleanup, not canary absence;
  (e) tests/test_drive_verify.py:104-117 is named "never carries a token" but only asserts the staging folder is empty (the
  ConnectionError carrying "Authorization: Bearer CANARY-TOKEN" propagates by design); (f) log.exception path of _run_job with
  a canary-bearing unexpected exception is untested; (g) a canary in a successful response's file name vs logs untested;
  (h) tests/test_gws_runner.py:99-102 shows the real runner DOES hand raw stderr (with CANARY-123) to the caller - the drop is
  only in drive_errors/gws_drive, so a future caller that logs GwsResult would leak; no test pins that.

## 6. Resource bounds - PARTIAL
- Timeouts: run() timeout 60 s (gws_drive.py:34,111,123; subprocess.run kills the child on timeout), download total 3600 s
  (gws_drive.py:35; gws_runner.py:101,126-127); on any BaseException the child is killed, waited, partial file removed
  (gws_runner.py:111-115). Over-limit: watch every poll_s=0.1 s, `written > max_bytes` -> kill -> LimitExceeded
  (gws_runner.py:120-128) -> rmtree (gws_drive.py:149-152).
- Unbounded: `run()` uses capture_output=True with no cap (gws_runner.py:88-90): metadata/list stdout is held entirely in
  memory (list: pageSize 1000 x up to 10 pages). download() sends stdout/stderr to TemporaryFile in the SYSTEM temp dir (not
  the project work area), unwatched and uncapped, then `.read()` them entirely into memory (gws_runner.py:116-118). With `-o`
  gws prints small JSON, so this needs a misbehaving/hostile gws binary. Low.
- Watch gap: the loop only checks while the process is alive (`while proc.poll() is None`, :122); a file that crosses the limit
  between the last poll and process exit is never size-checked there, and one poll interval of writes can overshoot the limit
  on disk. The downstream copy_bounded (drive_verify.py:98, bounded_write.py:33-53) then refuses it, so registered data is
  bounded; the staging file can exceed the limit transiently. Peak disk about 2x limit (gws folder + drive-fetch copy).
- Download file is under work_dir/gws/<slug>/dl-<ulid> (drive_intake.py:51-53, gws_drive.py:140), removed on every exit
  (gws_drive.py:95-96,150,154; drive_intake.py:128,145); stale sweep after 24 h (drive_intake.py:82-87).

## Defects / questions (own file:line)
D1 (Medium, >80%) drive_errors.py:74-75 `for e in err.get("errors", [])` raises TypeError when error.errors is null/int
   (reproduced). Not caught by `except (DriveError, DriveVerifyError)` (drive_intake.py:120,142,195; cli_intake.py has none).
   Effects: web job ends "failed" with the generic text instead of a typed Drive message (routes_intake.py:58-61); CLI
   `ingest fetch-drive` exits with a Python traceback (no locals, typer 0.27.2) instead of a typed message; TI8 asks for
   typed output for every failure class. No raw text leaks. Fix: guard `isinstance(errors, list)`; or catch in classify and
   return NETWORK_ERROR.
D2 (Medium, >80%) routes_intake.py:40 `_FAILED` says "Nothing was added." but a folder job registers videos one at a time
   (drive_intake.py:157, each commit_video independent) - any exception outside the caught set (D1's TypeError, ValueError at
   intake_commit.py:127 on cross-volume sha mismatch, a pydantic error) on video N aborts the job via routes_intake.py:58
   after videos 1..N-1 are already registered. The page then claims nothing was added and shows no per-member table.
D3 (Low-Medium) routes_intake.py:80-84 one thread per POST, no cap or per-project/global limit; each can hold a download up to
   the limit (x2 on disk) for up to 3600 s per file, serialised only by the 600 s intake lock for the commit step. Authenticated
   (or, until T-204, OpenGate = anyone, intake_gate.py:41-48).
D4 (Low) drive_intake.py:181 / 82-87 `_sweep_stale` runs outside the try and not under any lock: `folder.stat()` on a folder a
   concurrent job's `finally: rmtree` just removed raises FileNotFoundError (OSError) -> job "failed". Narrow race.
D5 (Low) gws_drive.py:32,117 `_MAX_PAGES = 10` x 1000: a folder with more than 10,000 children is silently truncated, no note
   in the report (drive_intake.py:148-161).
D6 (Low/question) GwsDrive's limit and fetch_and_verify read `read_max_upload_bytes()` with NO root (gws_drive.py:106,
   drive_verify.py:91) while upload/zip pass `store.paths.root` (intake_upload.py:118, zip_intake.py:227). Same value when root
   is the default repo root; differs for any non-default root (tests, multi-root). Question.
D7 (Low, <80%, question) upload_stream.py `_Reader`: caps exist per header/field value (HEADER_CAP, FIELD_CAP) and for total
   bytes, but no count cap on part headers (`_head` dict, :116) or on text fields (`fields`, :154); memory is bounded only by
   limit + FORM_OVERHEAD (default 2 GiB). Needs a gated member; python-multipart may bound header counts itself - not verified.
D8 (Note) confused deputy by design: until T-204 installs a gate (intake_gate.py:41-48) anyone who can reach the server can
   make the server's Google login fetch any Drive file/folder id it can read (video or zip only). HO33/TI10 seam, held.

## Candidate PROPOSED-ISSUE lines
- classify_gws_failure raises TypeError on a gws error body with null/non-list `errors` (drive_errors.py:74); fetch-drive CLI
  traceback / web job "failed" instead of a typed Drive message; guard and return NETWORK_ERROR + test with a canary body.
- Drive job `_FAILED` "Nothing was added" is false for a folder job that registered earlier videos before an unexpected
  exception (routes_intake.py:40,58; drive_intake.py:157); catch per item or report partial.
- gws child inherits the full server environment incl. all .env secrets (gws_runner.py:88-90,104-106); pass an allowlisted env
  (PATH, HOME/USERPROFILE/APPDATA, GOOGLE_*/GWS_*) or document it as accepted.
- AUTOTESTER_GWS_BIN is an unvalidated executable path writable through the Credentials page (routes_project_edit.py:45-62,
  routes_credentials.py:136-157); add a reserved-key denylist (AUTOTESTER_*) or validate basename/existence.
- TI8 canary coverage: add an end-to-end test (canary in fake credential env + each error body + a successful file name) grepping
  stdout, stderr, caplog, drive-jobs/*.json, sources.jsonl and the page; tests/test_gws_drive.py:181 and test_drive_verify.py:104
  assert nothing about the canary.
- Cap gws stdout/stderr (run(): capture_output; download(): TemporaryFile read) and re-check the staged file size after the
  process exits (gws_runner.py:88-95,116-122).
- Bound concurrent Drive jobs (routes_intake.py:80-84).
