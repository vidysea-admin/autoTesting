# t198a-zip-drive-intake, sub-checker t3: gate seam + provenance (findings only, no verdict)

Worktree head 894549ee (read-only; I edited nothing in it). All lines below were opened by me.
Paths relative to `.worktrees/t198a-zip-drive-intake/src/autotester/`.

## 1. TI10 seam, from the code

TI10 is HELD on T-204 by the builder and I do not judge it met. What the seam proves:

(i) Gate before any body byte.
- Upload and zip share ONE route, `POST /projects/{slug}/sources/upload` (ui/routes_sources.py:143-146) -> `handle_upload`.
  `get_gate().check(request, slug)` is at ui/intake_upload.py:114; the first body read is `stream_upload` at :121; a refusal returns at :116. There is no separate zip route.
  `_load_project_or_404` (:117) sits between them but reads no body.
- Drive-link route `POST /projects/{slug}/sources/drive`: `check` at ui/routes_intake.py:68, body read (`read_small_form`) at :73, refusal returns at :70. Gate is first.
- Nothing before the gate reads the body: `_OriginGuard` (ui/helpers.py:266-287) only reads `scope["headers"]`.
- Test proving the upload ordering: tests/test_ui_intake.py:163 (served.bytes == 0).

(ii) Recheck at job start.
- `_run_job` (ui/routes_intake.py:44) calls `get_gate().recheck(actor, slug)` at :49 BEFORE `job.state = fetching` (:53) and before `intake_drive(...)` (:55).
- On `IntakeRefused` it saves `state="refused"` with the gate's message (:51) and returns. Nothing is fetched or written (test tests/test_ui_intake_drive.py:73 asserts `drive.opened == []` and no sources).
- The worker thread is started at :82-84.

(iii) `uploaded_by` provenance. grep of src/ for uploaded_by/uploaded_at/origin=:
- UI upload: intake_upload.py:106 `uploaded_by=actor.email`, :129 `uploaded_by=actor.email`; `actor` comes only from `get_gate().check` (:114).
- Drive: routes_intake.py:55 `uploaded_by=actor.email` (actor passed as a thread arg from :68). Down in sources/drive_intake.py:115/140 and sources/zip_intake.py:152 it is only passed through.
- sources/intake_commit.py:154-155 stamps Source with the value it was given, and `uploaded_at or utc_now()` is server time.
- No place reads `uploaded_by` from a form, body, query or header. `staged.fields` is read only for `label` (intake_upload.py:122).
- EXCEPTION, the CLI: cli_intake.py:22,51,58,68,76 take `--uploaded-by` as a typer option. This is the local operator, not a request, but it is a self-declared, unauthenticated string.

(iv) Default gate. `OpenGate` (ui/intake_gate.py:41-48): `check` returns `IntakeActor(email=None)`, `recheck` returns None. `_gate = OpenGate()` at :51.
- grep `set_gate` across src/: the only hit is its definition (intake_gate.py:58) and `__all__`.
- Nothing in settings, env or server config installs a different gate. Only tests call `set_gate`.
- So today the hosted routes are open and record nobody (test_ti11_with_no_sign_in_yet_nobody_is_recorded..., test_ui_intake.py:184).

(v) CLI bypass. `ingest zip` / `ingest fetch-drive` (cli_intake.py:49-78) never call `get_gate`. The module docstring does not say so. Contract TI10 lists the "fetch-drive background job", not the CLI, and a local CLI user already holds filesystem access. I read this as acceptable but UNSTATED; the builder should say it. `--uploaded-by` lets the CLI stamp any identity.

(vi) Origin/CSRF before the gate. `app = FastAPI(..., middleware=origin_guard_middleware())` (ui/app.py:72); `_OriginGuard.__call__` (ui/helpers.py:273-287) runs `origin_refusal` for unsafe methods and returns 403 before any handler. It therefore runs before `check` on both intake POST routes. Tests: test_d066_a_cross_origin_post_is_refused_before_the_gate_or_any_write (test_ui_intake.py:190) and the AT-758 host tests.
- Not Origin-related but note: it is an ASGI middleware, not a per-route check. The "before authentication" ordering holds because the gate runs inside the handler.

(vii) Central policy table (auth.md AU14). It does NOT exist in the tree: grep for `app.routes`, "policy table", `route_policy`, `authorize` across src/ finds nothing. The intake routes are declared only by their own `get_gate().check` call. The GET `/projects/{slug}/sources/drive/{job_id}` (routes_intake.py:103-118) has NO gate call at all (read of a job report, ULID-shaped id).

NOT proven by this unit: the 302/401/403/404 matrix (Admin, Sub-admin, Developer, Tester, no-group, anonymous), `video.upload` scopes (@own/@assigned/@all), the policy table / default-deny enumeration (AU14), real session-derived identity, and the "cross-origin POST with a valid session cookie" case. Only a fake gate is exercised.

## 2. The four `dual-trigger` lines

| Cited | Line text | Real seam? |
|---|---|---|
| ui/upload_stream.py:175 | `async def stream_upload(request: Request, staging: Path, limit: int) -> StagedUpload:` | yes, security (streaming body limit) |
| sources/zip_names.py:77 | `def ensure_inside(path: Path, root: Path) -> Path:` | yes, security (path containment) |
| sources/zip_intake.py:214 | `def expand_zip(store: ProjectStore, archive: Path, *, archive_name: str | None = None,` | yes, security (untrusted archive expansion) |
| ui/intake_upload.py:111 | `async def handle_upload(request: Request, slug: str) -> Response:` | yes, auth gate seam |
| ui/intake_gate.py (no line cited) | `class IntakeGate(Protocol):` is at :33, `check` at :34 | the seam definition; the manifest cites intake_upload.py:111 for this entry |

## 3. TI11 + re-run + falsification

Pre-check run (once, lock held): `tests/test_ui_intake.py tests/test_ui_intake_drive.py tests/test_drive_intake.py` -> **53 passed, 1 warning** (22.5 s). Log: t3-pytest-run1.log (this dir). Python = worktree venv, `-p no:xdist -o addopts=`, no -q.

TI11 evidence, located (not all in the three files above):
- spoof: tests/test_ui_intake.py:175 (form `uploaded_by=attacker@evil.test`, stored `dev@vidysea.test`).
- three origin shapes: upload test_ui_intake.py:181 (UploadOrigin), zip tests/test_intake_schema.py:225 (ZipOrigin) and test_zip_intake_register, Drive test_ui_intake_drive.py:36 and test_drive_intake.py:54 (DriveOrigin).
- `extra="forbid"`: test_intake_schema.py:181. Origin exactly-one-of: :195.
- old sources.jsonl loads, id unchanged: test_intake_schema.py:169 (`test_ti11_a_sources_jsonl_written_before_the_change_still_loads_with_the_same_id`). Source id is `content_id` of kind + sha256 (schema/project.py:136-141); the new fields are not in the key.
- scrub before storage: tests/test_zip_intake_register.py:118 (canary in a member name). Zip and Drive labels go through `scrub` (drive_intake.py:107 `_label(item, scrub)`; intake_upload.py:108 scrubs `file_name`).
- GAP/NOTE: on the UPLOAD route the user-typed `label` is NOT scrubbed; it is passed raw (intake_upload.py:105-106) after `_refuse_unsafe_submission` (:124) REFUSES a secret-bearing label (ui/credential_guard.py:122). That is a different mechanism from "pass Redactor.scrub" in TI11; I did not find a test of it on this route. Judgement for the checker.
- Duplicate test name: tests/test_ui_intake.py defines `test_at758_a_hostile_host_on_the_upload_route_is_403_before_any_body_byte` twice (:215 and :223, identical bodies); the second shadows the first (ruff F811 candidate; I did not run ruff).

Falsification (throwaway copies of src/ tests/ pyproject.toml + scripts/regression_proof.py, which tests/conftest.py imports, under scratchpad `t3-m1-ti11-form`, `t3-m2-ti10-recheck`, `t3-m3-ti10-bodyfirst`; PYTHONPATH=copy; `autotester.__file__` printed inside each copy; baseline run GREEN first, logs `t3-m*-base.log`, `t3-m*-mut.log` in scratchpad):
- M1 (TI11): intake_upload.py:106 `uploaded_by=actor.email` -> `uploaded_by=staged.fields.get("uploaded_by", actor.email)`. Node `test_ti11_uploaded_by_comes_from_the_gate_and_a_form_field_is_ignored` -> RED on `assert source.uploaded_by == "dev@vidysea.test"` (got `'attacker@evil.test'`).
- M2 (TI10 recheck): routes_intake.py:49 `get_gate().recheck(actor, slug)` -> `pass`. Node `test_ti10_seam_the_queued_fetch_checks_again_and_a_refusal_fetches_no_bytes` -> RED on `assert "refused" in text.lower() and "disabled" in text`.
- M3 (TI10 gate-before-body): added `async for _chunk in request.stream(): break` before the gate in handle_upload. Node `test_ti10_seam_a_refused_member_is_stopped_before_a_single_body_byte_is_read` -> RED on `assert served.bytes == 0` (got 205).
All three failed on the named assertions, not on import errors. Worktree untouched.

## 4. Concurrency / abuse note

routes_intake.py:82-85: every accepted Drive POST starts a new `threading.Thread` (daemon) with no semaphore, no per-project or global cap, no rate limit, and `save_job` (:81) writes a job file per request (unbounded files under `.work/drive-jobs/<project>/`). `asyncio.to_thread(worker.join, 3.0)` (:85) also holds a default-executor thread for up to 3 s per request. Per-fetch size/count limits exist (TI2/TI9), and commits are serialised by `intake_session` (sources/intake_commit.py, `IntakeBusy`), but the fetches themselves are parallel and unbounded in number.
- With the open gate (today, nothing installed) any client that can reach the server and passes the Origin/Host guard can start unlimited fetches against the server's Google login: resource exhaustion plus use of the server's Drive credentials.
- My read: a HARDENING note, not a defect against TI10/TI11 text (the contract has no concurrency criterion and the open gate is the declared interim state), but it is new attack surface in changed code and becomes member-only abuse once T-204 installs a gate. Recommend a bounded semaphore / per-project queue under T-204 or a follow-up issue.
