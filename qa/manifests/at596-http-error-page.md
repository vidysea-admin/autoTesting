# Manifest — at596-http-error-page

**Unit:** every `HTTPException` raised anywhere under `ui/app.py`'s routers gets a themed HTML page
for a browser, and the exact JSON body FastAPI's default handler already produced for everyone
else — status codes unchanged.
**Contract:** `qa/contracts/ui.md` U5 (escaping discipline) — no criterion yet names this app-wide
handler by number; flagged for the checker to decide whether a new U-item is warranted. Also
`browser-and-secrets.md` C5 ("one concept, one place") for the secret-loader revision below.
**Date:** 2026-09-26
**Fix cycle:** 2 of 3
**Dual check:** no
**Issues addressed:** AT-596, AT-605

**Revision history within this manifest:** a checker pre-check (before dispatching a full check)
read the cycle-1 diff and sent back two findings, addressed below without opening a new fix cycle:
(1) the handler was registered on `fastapi.HTTPException` rather than its Starlette base class, so
Starlette's own unmatched-route 404 fell through uncovered; (2) `_repo_redactor()` hand-rolled a
second `.env` read-and-parse instead of calling the same `SecretStore` loader every other consumer
in this codebase uses (C5). Both are fixed in commit `6b52c12`, described under "What changed."

**Fix cycle 2:** the checker then ran its full check (Mode A + Mode D, verdict `7b9727d`) against
`6b52c12` and returned FAIL on one medium finding, **AT-605**: `_error_page` (`error_pages.py:84-95`
at that commit) rebuilt the `HTMLResponse` without `exc.headers`, so a browser-negotiated 405 lost
its `Allow` header (RFC 9110 SS15.5.6: a 405 response "MUST generate an Allow header field"), while
the same route's JSON caller kept it (FastAPI's own default handler already forwards `exc.headers`).
The other five claims the checker scored all held (U5 escaping, C5 one-loader, status codes, both
pre-check fixes, live in a real browser). Fixed below.

## The gap (AT-596, as filed)

`src/autotester/ui/app.py` registered no `HTTPException` handler, so every 4xx raised by any route
— the ordinary 400s, `_load_project_or_404`'s 404s, and T-184/AT-585's new 409 on deleting a
pinned case — fell through FastAPI's default handler as a raw `{"detail": ...}` JSON body. A
browser hitting that route (not a client asking for JSON) got Chrome's own built-in JSON viewer:
no styling, no nav, no link back to the app. Evidence: the checker's own screenshot from the T-184
cycle, `qa/evidence/browser-t184-pinned-regression-2026-09-26-checker/02-after-pinned-delete-attempt.png`.

## What changed

**Commit `d9a4182` (original cycle-1 fix):**

- `src/autotester/ui/error_pages.py` (new) — split out of `app.py` rather than added inline because
  `app.py` was already at 295/300 lines (the design cap) before this unit; adding the handler in
  place would have pushed it to ~305.
  - `_wants_html(request)` — `"text/html" in request.headers.get("accept", "")`. A real browser
    sends `Accept: text/html,application/xhtml+xml,...`; httpx's `TestClient` sends `Accept: */*`
    when a test sets no header at all (confirmed live, see "Actual outputs"), so every pre-existing
    test in this suite that never sets `Accept` keeps seeing JSON, unchanged.
  - `_error_page(status_code, detail)` — redacts `detail`, THEN `html.escape`s it (redact-then-
    escape, not the other way round, or a scrubbed value would need to match against already-
    escaped secret bytes), and renders it inside `theme.card(...)` / `theme.page(...)` — the same
    wrap/card primitives every other themed page in this app already uses
    (`ui/routes_learn.py::_refusal` is the closest existing precedent for "a themed refusal with a
    way onward").
  - `http_exception_handler(request, exc)` — the registered handler: JSON/no-`Accept` callers are
    handed straight to FastAPI's own `fastapi.exception_handlers.http_exception_handler` (so the
    204/304-body-suppression edge case and the JSON shape are exactly FastAPI's, not reimplemented);
    HTML-accepting callers get `_error_page`, with the same `is_body_allowed_for_status_code` guard
    FastAPI's own default handler uses.
  - `register_exception_handler(app)` — `app.add_exception_handler(HTTPException, ...)`. (Named
    this, not `register`, after `autotester doctor`'s `duplicate-concept` check flagged the first
    name against the unrelated `providers/__init__.py::register` — a real name collision, not a
    real duplicate concept; renaming was cheaper than arguing with the linter.)
- `src/autotester/ui/app.py:25-27,72` — `error_pages` added to the shared `from autotester.ui
  import (...)` tuple; `error_pages.register_exception_handler(app)` called once, right after
  `app = FastAPI(...)`, before any router is included. Net +2 lines (295 -> 297; still under 300).
- `tests/test_ui_error_pages.py` (new, 9 tests) — see "Actual outputs" and "Capability coverage."
- `docs/MAP.md` — regenerated (`uv run autotester map`) to list the new module; no hand edits.

**Commit `6b52c12` (this pre-check revision, same Fix cycle 1):**

- `src/autotester/ui/error_pages.py:34` — `from fastapi import ... HTTPException` replaced by
  `from starlette.exceptions import HTTPException` (FastAPI's own base class). Starlette's
  exception middleware looks a handler up by walking `type(exc).__mro__`
  (`starlette/exceptions.py::ExceptionMiddleware._lookup_exception_handler`), so registering on the
  base class still matches every route's `fastapi.HTTPException` (a subclass, unchanged) **and**
  now also Starlette's own bare `HTTPException(404, "Not Found")` for a URL matching no route at
  all — confirmed live via a throwaway `TestClient` probe before writing the fix (see "Actual
  outputs"). `register_exception_handler` (`error_pages.py:109`, unchanged signature) now registers
  against this wider type. `http_exception_handler`'s own `exc` annotation follows the same import.
- `src/autotester/ui/error_pages.py:42-67` — `_repo_redactor()` rewritten. **Before:** `Redactor(
  parse_env(path.read_text(encoding="utf-8")))` against `repo_root() / ENV_FILE` — a second,
  independent read-and-parse of `.env`, alongside the one every other secret consumer in this
  codebase already goes through. **After:** `SecretStore.load(_NO_PROJECT_SCOPE, env_path,
  strict=False).redactor()` — the identical two calls every one of the 15 other `SecretStore.load`
  call sites in this codebase makes (`grep -rn "SecretStore\.load(" src/autotester` — e.g.
  `ui/routes_cases.py:164,274`, `ui/routes_runs.py:115`, `cli_orchestrate.py:241`), landing on
  `.redactor()` (`browser/secrets.py:223-235`), the same method `ui/credential_guard.py:109,154`,
  `browser/evidence.py:58` and `stages/orchestrate.py:85` all call to turn a `SecretStore` into a
  `Redactor`. `SecretStore.load` itself is `browser/secrets.py:117-131`. `env_path` is
  `ProjectPaths(_NO_PROJECT_SCOPE.slug).env_file` (`core/paths.py:44-50`) — the exact same
  `ProjectPaths(...).env_file` property every route already calls, which always resolves to the
  repo-root `.env` regardless of slug ("one credential file for the whole repo").
  `_NO_PROJECT_SCOPE` (`error_pages.py:42`) is a minimal, non-onboarded `Project(slug="error-pages",
  name="error-pages", base_url="")` — a pure data carrier: `SecretStore.load` reads only
  `project.secrets` off it (empty, so every `.env` key lands in the "shadow"/undeclared bucket
  rather than "declared"), and `.redactor()` remerges declared and undeclared values into one mask
  list regardless of that split (AT-004's "masks every secret value" rule) — so the `Redactor` this
  produces is **provably identical** to the old direct-`parse_env` implementation's, not merely
  assumed so (see "Capability coverage" — the redaction falsification was re-run against this new
  code path and still isolates the same test).
- `tests/test_ui_error_pages.py` — 3 tests added (12 total): `test_unmatched_route_with_html_accept
  _renders_a_themed_page`, `test_unmatched_route_with_json_accept_is_unchanged`, and
  `test_approve_flowspec_unknown_slug_renders_a_themed_page` (the confirmed AT-259 path — see
  "Known limits" for what AT-259 does and does not cover). The two secret/escaping tests'
  `throwaway_app` fixture was changed to depend on the file's existing `scratch_root` fixture
  (`AUTOTESTER_ROOT` env-var isolation, the same mechanism every other test in this suite already
  uses) instead of `monkeypatch.setattr(error_pages, "repo_root", ...)`, which no longer exists as
  an attribute on the module now that `repo_root` isn't imported there at all.

**Commit `fef6c3b` (Fix cycle 2 — AT-605, checker verdict `7b9727d`):**

- `src/autotester/ui/error_pages.py:1` (`from collections.abc import Mapping`) — new import,
  needed for the `_error_page` signature below; `typing.Mapping` was tried first and rejected by
  `ruff`'s `UP035` (`collections.abc` is the currently-correct import site).
- `src/autotester/ui/error_pages.py::_error_page` — signature changed from `(status_code: int,
  detail: str) -> HTMLResponse` to `(status_code: int, detail: str, headers: Mapping[str, str] |
  None = None) -> HTMLResponse`; the final line changed from `return HTMLResponse(theme.page(title,
  body), status_code=status_code)` to `return HTMLResponse(theme.page(title, body),
  status_code=status_code, headers=headers)`. `HTMLResponse`/`Response` already accept `headers=None`
  (Starlette's own `Response.__init__` treats `None` as "no extra headers"), so this is None-safe by
  construction — no `if headers is not None` branch needed. Docstring extended (not trimmed) to
  explain the `Allow`/`WWW-Authenticate` cases and the FastAPI-default-handler parity this restores.
- `src/autotester/ui/error_pages.py::http_exception_handler` — the one call site,
  `return _error_page(exc.status_code, detail)`, changed to `return _error_page(exc.status_code,
  detail, exc.headers)`. `exc.headers` is Starlette's own `HTTPException.headers` attribute
  (`None` for the common case, a `dict`/`Mapping` when the raiser supplied one — e.g. Starlette's own
  routing sets `{"Allow": ", ".join(sorted(methods))}` on a 405 before this handler ever sees it).
- `tests/test_ui_error_pages.py` — module docstring's last paragraph extended (not trimmed) to note
  the AT-605 split described next, rather than silently going stale once the tests moved out.
- `tests/test_ui_error_page_headers.py` (new, 3 tests) — split out of `test_ui_error_pages.py` once
  that file reached 308 lines against `autotester doctor`'s 300-line cap (the project's own
  established convention for this — `test_ui_case_management.py`'s docstring: "Split from
  test_ui_cases.py once that file passed doctor's 300-line cap"). Carries its own local
  `scratch_root`/`client`/`throwaway_app` fixtures (duplicated, per the same convention, not
  imported from the sibling file) plus the three AT-605 tests: `test_405_with_html_accept_keeps
  _the_allow_header` and `test_405_with_json_accept_keeps_the_allow_header` (both against
  `/projects/{slug}/flowspec/approve`, `routes_learn.py:176`, `@router.post`-only — a `GET` never
  reaches route code, so Starlette's own routing raises the bare 405 with `Allow` before any view
  runs), and `test_other_exception_headers_survive_the_html_branch_too` (a throwaway `/locked` route
  raising `HTTPException(401, "nope", headers={"WWW-Authenticate": "Bearer"})`, proving the fix is
  "any header," not a special case for `Allow` alone).

## How to verify (commands + expected)

- `uv run pytest tests/test_ui_error_pages.py tests/test_ui_error_page_headers.py` -> all pass
  (12 + 3 = 15 tests as of Fix cycle 2; the AT-605 tests now live in the second file)
- `uv run pytest tests/test_ui_error_pages.py tests/test_ui.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_ui_project_name.py tests/test_ui_case_navigate_reachability.py tests/test_ui_learn.py tests/test_pinned_regression.py tests/test_ui_error_page_headers.py` -> all pass (the shared `app` fixture + every route this unit's handler now sits in front of, plus the pinned-case 409 this bug was filed against) — **not re-run in full this cycle**, see the RAM note below
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> only `ledger-row-lost` for AT-605 (the branch's ledger predates the
  row filed on master in `f9d9e7b`; clears on merge — the checker's own cycle-1 re-run note said the
  same about AT-605's own row before it existed on this branch at all)

## Actual outputs (from maker's own run)

**Original cycle-1 run** (commit `d9a4182`, RAM ~0.9GB free at the time):
```
$ uv run pytest tests/test_ui_error_pages.py
.........
9 passed, 1 warning in 3.47s

$ uv run pytest tests/test_ui_error_pages.py tests/test_ui.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_ui_project_name.py tests/test_ui_case_navigate_reachability.py tests/test_ui_learn.py tests/test_pinned_regression.py
........................................................................ [ 94%]
....                                                                     [100%]
76 passed, 1 warning in 11.32s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

**Red before the fix.** `tests/test_ui_error_pages.py` was copied into a throwaway checkout OUTSIDE
the worktree (`git archive f5dc842 -- src tests scripts pyproject.toml uv.lock` — the parent commit,
before any of this unit's edits — extracted to the session scratchpad, own `uv sync`'d venv, the
tracked worktree never touched):

```
$ uv run pytest tests/test_ui_error_pages.py -v
ImportError while importing test module '...\tests\test_ui_error_pages.py'.
E   ImportError: cannot import name 'error_pages' from 'autotester.ui' (...\src\autotester\ui\__init__.py)
1 error during collection
```

The whole module failed to collect — `ui/error_pages.py` did not exist, which is the bug itself
(no handler, anywhere).

**First doctor run was not clean.** Before the rename below, `autotester doctor` reported:
```
duplicate-concept: src\autotester\ui\error_pages.py:85 — 'register' also defined in src\autotester\providers\__init__.py
```
Fixed by renaming `register` -> `register_exception_handler` (both the definition and its two call
sites, in `app.py` and this unit's own test file); re-ran clean (see run above).

**Pre-check revision run** (commit `6b52c12`; RAM critical, ~0.12GB free confirmed via
`Get-CimInstance Win32_OperatingSystem` — the checker was running a browser concurrently). Per the
coordinator's explicit instruction, no uvicorn or browser was started this round, and only the
targeted set below was run, in the tracked worktree's own already-synced venv (no new `uv sync`):
```
$ uv run pytest tests/test_ui_error_pages.py -v
............
12 passed, 1 warning in 2.14s

$ uv run pytest tests/test_ui_case_management.py tests/test_ui_project_name.py
..................
18 passed, 1 warning in 4.10s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

**Red before this revision.** With RAM this tight, a second full `uv sync` (a new venv) was judged
too risky — `uv run pytest` inside such a checkout had already thrown a transient `MemoryError`
importing `openpyxl` mid-collection on the first attempt (retried once, succeeded the second time;
noted here rather than hidden, since it is itself evidence of how little headroom there was).
Instead, red-first and every falsification below reused the **already-synced worktree venv**,
pointed at a throwaway `git archive HEAD` checkout via `PYTHONPATH=<throwaway>/src` on the venv's
own `python.exe` (no `uv run`, no new dependency resolution, no second venv) — still a throwaway
copy outside the worktree per the hard rule, just a cheaper way to run it under critical memory
pressure. Against the checkout taken **before** this revision's two fixes:
```
$ PYTHONPATH=<throwaway>/src <worktree>/.venv/Scripts/python.exe -m pytest tests/test_ui_error_pages.py -v
tests\test_ui_error_pages.py .........F..                                [100%]
FAILED tests/test_ui_error_pages.py::test_unmatched_route_with_html_accept_renders_a_themed_page
AssertionError: assert False
 +  where False = <built-in method startswith...>('text/html')
 +    where ... = 'application/json'.startswith
1 failed, 11 passed, 1 warning in 5.72s
```
Exactly the one new test tied to the base-class registration failed (still JSON for an unmatched
route); `test_approve_flowspec_unknown_slug_renders_a_themed_page` **already passed** at this point
— see "Known limits" for why (it was already covered by cycle 1's narrower registration, since
`fastapi.HTTPException` is what that route actually raises).

**Fix cycle 2 run** (commit `fef6c3b`; RAM still constrained, same lightweight `PYTHONPATH`-on-the-
existing-venv discipline, no uvicorn, no browser, per the coordinator's explicit instruction this
cycle too):
```
$ uv run pytest tests/test_ui_error_pages.py tests/test_ui_error_page_headers.py -v
...............
15 passed, 1 warning in 2.30s

$ uv run pytest tests/test_ui_case_management.py tests/test_ui_project_name.py
..................
18 passed, 1 warning in 1.92s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-lost: qa/verdicts/at596-http-error-page.md — AT-605 is named here but has no row in
qa/issues.jsonl
1 violation(s)
```
The `ledger-row-lost` line is expected and not this unit's to fix (the brief forbids touching
`qa/issues.jsonl`) — it disappears once this branch merges past `f9d9e7b`, the commit on `master`
that filed AT-605's row.

**Splitting the test file.** After adding the three AT-605 tests directly to
`test_ui_error_pages.py` first, `autotester doctor` flagged `file-too-long: 308 lines > 300`. Per
the hard rule against trimming pre-existing docstrings, the fix was to split by responsibility
(the project's own convention, cited above) rather than shorten anything: the three new tests plus
their fixtures moved to `test_ui_error_page_headers.py` (93 lines), leaving the original file at
260 and `error_pages.py` itself at 123 — both re-confirmed clean by `ruff` and `doctor` above.

**Red before this fix, then green after — and one environmental flake along the way.** A throwaway
copy of `src`/`tests`/`scripts` was made OUTSIDE the worktree (plain file copy of the tracked
working tree at the point right after `_error_page` gained the `headers` parameter, before this
cycle's commit — not `git archive`, since the fix was not yet committed; still never touching the
tracked worktree itself), run via the same lightweight `PYTHONPATH`-on-the-existing-venv method:
```
$ PYTHONPATH=<throwaway>/src;<throwaway>/scripts <worktree>/.venv/Scripts/python.exe -m pytest <throwaway>/tests/test_ui_error_page_headers.py -v
[baseline, all fixes in place] ... 3 passed in 5.78s
```
Single-hunk falsifying edit in the throwaway copy only (line 105 of its `error_pages.py`,
`return HTMLResponse(theme.page(title, body), status_code=status_code, headers=headers)` ->
`return HTMLResponse(theme.page(title, body), status_code=status_code)`):
```
FAILED test_405_with_html_accept_keeps_the_allow_header - KeyError: 'allow'
FAILED test_other_exception_headers_survive_the_html_branch_too - KeyError: 'www-authenticate'
2 failed, 1 passed in 5.03s
```
`test_405_with_json_accept_keeps_the_allow_header` correctly stayed green — that path never reaches
`_error_page` at all (JSON callers go straight to FastAPI's own default handler), so the edit could
not have affected it; seeing it PASS both before and after is itself evidence the falsification is
isolating the right code path.

Reverted the throwaway copy's `error_pages.py` back to the `headers=headers` line; `diff` against
the tracked worktree's copy came back empty (byte-identical). Re-running the throwaway copy after
the revert then hit a **transient, environmental** collection-time error, repeatedly, unrelated to
this fix:
```
FileNotFoundError: [WinError 2] The system cannot find the file specified: '...\Temp\mutation-check-<random>'
```
— a different random `mutation-check-<random>` (and once `playwright-artifacts-<random>`) directory
each time, i.e. some other concurrently-running process on this machine (plausibly another
maker/checker session, or the checker's own Mode D browser) creating and deleting its own temp
directories under the same shared `%TEMP%` while pytest's collection walks it. This is the same
class of pre-existing flake the checker's own re-run already flagged for an unrelated test
(`test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild`,
ISS-t164-1/AT-518) — not something this unit's code touches or introduced. The revert-to-green step
was instead confirmed via the **tracked worktree's own real run**, above (`15 passed` for both
files together, including all three AT-605 tests, immediately after `fef6c3b`'s commit) — i.e. the
actual shipped code, not a copy, is green; only the *extra*, belt-and-suspenders re-confirmation in
the disposable copy hit the environmental race.

## Capability coverage (each claim -> its isolating falsification)

**Cycle-1 rows** (re-verified this revision against the current code — see the new rows below for
what's specific to the pre-check fixes): throwaway copy built OUTSIDE the worktree from the fixed
commit, own `uv sync`'d venv, confirmed green before any falsification. Every falsifying edit is a
single hunk in `error_pages.py`, applied, run, then reverted — confirmed byte-identical to the
tracked worktree's copy (`diff` empty) and green again before the next row. The tracked worktree
itself was never edited for this purpose.

| claim | falsifying edit (single hunk) | check | observed |
|---|---|---|---|
| a browser (`Accept: text/html`) gets the themed HTML page | `_wants_html`: `return "text/html" in request.headers.get("accept", "")` -> `return False` | `test_{400,404,409}_with_html_accept_renders_a_themed_page`, `test_html_error_page_escapes_the_detail`, `test_html_error_page_redacts_a_known_secret_from_the_repo_env` | PASS before. FAIL after: all 5 fail — every HTML-accepting request instead gets the raw JSON body |
| a JSON/no-`Accept` client's response is byte-for-byte what FastAPI's default handler already produced | `_wants_html`: same function -> `return True` (unconditional) | `test_{400,404,409}_with_json_accept_is_unchanged`, `test_400_with_no_accept_header_stays_json` | PASS before. FAIL after: all 4 fail — `response.json()` raises `JSONDecodeError` on the HTML body it now gets instead |
| the detail is HTML-escaped before it reaches the page | `_error_page`: `safe_detail = escape(_repo_redactor().scrub(detail))` -> `safe_detail = _repo_redactor().scrub(detail)` (drop `escape`) | `test_html_error_page_escapes_the_detail` | PASS before. FAIL after: `assert '<script>alert(1)</script>' not in response.text` fails — the raw tag is on the page |
| a known secret in the detail is redacted before it reaches the page | `_error_page`: same line -> `safe_detail = escape(detail)` (drop `.scrub()`, keep `escape`) | `test_html_error_page_redacts_a_known_secret_from_the_repo_env` | PASS before. FAIL after: `assert 'sk-supersecretvalue123' not in response.text` fails — the raw secret is on the page |
| the exception's original status code reaches the response unchanged | `_error_page`: `return HTMLResponse(theme.page(title, body), status_code=status_code)` -> `status_code=200` | `test_{400,404,409}_with_html_accept_renders_a_themed_page`, `test_html_error_page_escapes_the_detail`, `test_html_error_page_redacts_a_known_secret_from_the_repo_env` | PASS before. FAIL after: all 5 fail — every themed page comes back `200` instead of its real status |

**Pre-check-revision rows** (falsified against commit `6b52c12`, using the lightweight
`PYTHONPATH`-on-the-existing-venv method described under "Actual outputs" — RAM was too tight for a
second `uv sync`'d scratch venv this round). Each edit applied, run, reverted, and confirmed
byte-identical to the tracked file before the next row:

| claim | falsifying edit (single hunk) | check | observed |
|---|---|---|---|
| registering on `starlette.exceptions.HTTPException` covers Starlette's own unmatched-route 404, not just `fastapi.HTTPException` | `from starlette.exceptions import HTTPException` -> `from fastapi import HTTPException` | `test_unmatched_route_with_html_accept_renders_a_themed_page` | PASS before (12/12). FAIL after: exactly this one test fails (`content-type` is `application/json`, not `text/html`) — the other 11, including the AT-259 test, stay green |
| the new `SecretStore`-routed redaction still masks a known secret (re-derived against the new loader, not assumed carried over) | `_error_page`: `safe_detail = escape(_repo_redactor().scrub(detail))` -> `safe_detail = escape(detail)` | `test_html_error_page_redacts_a_known_secret_from_the_repo_env` | PASS before. FAIL after: exactly this one test fails, same as the cycle-1 row — confirms the loader swap didn't quietly change (or lose) the masking behavior |

**Not falsifiable by a test, verified by citation instead:** "the redaction goes through the SAME
loader every other consumer uses, not a second one" is a code-structure claim, not a behavioral one
— `SecretStore.load(_NO_PROJECT_SCOPE, ...).redactor()` and the old `Redactor(parse_env(...))`
produce a **byte-identical** `Redactor` for this call site (reasoned and confirmed above: `.redactor()`
remerges declared/undeclared regardless of which `Project.secrets` was passed in), so no test can
ever distinguish "calls the shared loader" from "duplicates its logic locally" — reverting to the
old implementation would still pass every test in this file. This claim is instead verified by
direct citation (see "What changed"): `error_pages.py:67` calls `browser/secrets.py:117`
(`SecretStore.load`) then `browser/secrets.py:223` (`.redactor()`), and `grep -rn "parse_env"
src/autotester/ui/error_pages.py` returns no call site, only the prose explaining what was removed.

**Fix cycle 2 row** (AT-605, falsified in a throwaway plain-copy checkout, method described above
under "Actual outputs"; the tracked worktree was never edited):

| claim | falsifying edit (single hunk) | check | observed |
|---|---|---|---|
| a header the raised `HTTPException` carried (e.g. a 405's `Allow`, a 401's `WWW-Authenticate`) survives on the HTML branch, not just the JSON one | `_error_page`: `return HTMLResponse(theme.page(title, body), status_code=status_code, headers=headers)` -> drop `, headers=headers` | `test_405_with_html_accept_keeps_the_allow_header`, `test_other_exception_headers_survive_the_html_branch_too` | PASS before. FAIL after: both fail (`KeyError: 'allow'`, `KeyError: 'www-authenticate'` — the header is simply absent). `test_405_with_json_accept_keeps_the_allow_header` correctly stays PASS both times, since that path never calls `_error_page` at all |

Eight distinct behaviors across the three rounds, each isolated by its own single-hunk falsification
and leaving every other test green — confirming the tests are pinned to the claims they name, not
incidentally passing.

## Live browser evidence

`uv run uvicorn autotester.ui.app:app --host 127.0.0.1 --port 8069` (scratch `AUTOTESTER_ROOT`),
driven with `curl` sending real header sets rather than `TestClient` (a genuinely separate process,
real HTTP, not the in-process ASGI transport `TestClient` uses):

- `curl -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" .../projects/does-not-exist`
  (Chrome's actual default `Accept` header, byte for byte) -> full themed page: doctype, `<title>404
  Not Found — AutoTester</title>`, the shared stylesheet + topbar + sidebar, and
  `<div class='card'><h2>404 Not Found</h2><p>no project &#x27;does-not-exist&#x27;</p><p
  style='margin-top:14px'><a class='btn' href='/'>&larr; Back to projects</a></p></div>` — escaped
  apostrophe, real nav, a way back.
- Same URL with `Accept: application/json` -> `{"detail":"no project 'does-not-exist'"}`.
- Same URL with no `Accept` header at all -> identical JSON body — confirms the negotiation default
  matches what every existing JSON-asserting test already assumed.
- `curl -X POST -H "Accept: text/html" .../projects/demo/cases/nope/delete` (409/404 path) -> same
  themed shell, `<h2>404 Not Found</h2>` (no `demo` project existed in that scratch root, which is
  itself the expected 404 behavior along the same handler path the 409 also travels).

**This is a real browser-facing behavior change** (not merely a `TestClient`-observed one) and the
checker's own Mode D recipe is below for an independent run. Server was killed after
(`taskkill /F` on the uvicorn PID; confirmed via `netstat` that port 8069 has no `LISTENING` entry
left, only expiring `TIME_WAIT` remnants from already-closed connections) — no monitor left running.

**This live run predates the pre-check revision.** It exercised the 404/409 project-route paths,
not the two things `6b52c12` added (Starlette's own unmatched-route 404, and the AT-259 approve
path) — those are `TestClient`-verified only (see "Actual outputs" and "Capability coverage"). No
new uvicorn/browser run was made this revision, per the coordinator's explicit instruction (RAM
critical, ~0.12GB free, the checker itself running a browser concurrently). Flagged under "Known
limits" rather than silently left for the checker to discover.

### Checker Mode D recipe

1. `uv run uvicorn autotester.ui.app:app --host 127.0.0.1 --port 8069` against a scratch
   `AUTOTESTER_ROOT`.
2. In a real browser (not `curl`, not `TestClient`): onboard a project, add a case, pin it (there is
   no UI button for pinning yet — AT-585's own gap — so seed `pinned=True` via `ProjectStore`
   directly against the scratch root, same as `tests/test_ui_case_management.py`'s
   `test_deleting_a_pinned_case_through_the_ui_is_refused_with_409` does), then click the case's
   delete control.
3. Expect: a page in this app's own visual language (topbar, sidebar, card, heading naming the
   status), not Chrome's built-in JSON viewer; a working "Back to projects" link; zero unexplained
   console errors.
4. Repeat for a plain 404 (visit an unknown `/projects/<slug>`) and a plain 400 (submit `/onboard`
   with a blank name) to confirm the same page shape across all three status codes this unit's
   tests cover.
5. Confirm an API-style request (e.g. `curl -H "Accept: application/json"` against any of the three
   URLs above) still gets the plain `{"detail": ...}` JSON it got before this unit.

## Known limits / gaps (disclosed, not claimed)

- **Full suite not re-run in cycles 1 or 2** (RAM critical throughout — ~0.12GB free while the
  checker ran a browser) — only the targeted files named under "How to verify," plus ruff and
  doctor, were run each round, per the coordinator's explicit instruction both times. The original
  cycle-1 76-test broader run (see "Actual outputs") predates every fix after `d9a4182`; it was not
  re-run against `6b52c12` or `fef6c3b`. The checker's own cycle-1 full-suite run (`1774 passed`,
  verdict `7b9727d`) is the most recent full-suite evidence on record for this branch.
- **No new live-browser run in cycles 1 (pre-check revision) or 2** (same RAM constraint both
  times; no uvicorn/browser started, per instruction). The checker's own Mode D run already
  reproduced AT-605 live (scenario G: "GET on a POST-only route (405) — themed page renders, but
  `Allow` is missing") and independently reproduced the fix's target behavior via `TestClient`
  (`text/html,... -> 405 text/html allow= None`) in its verdict — a follow-up Mode D pass confirming
  `Allow: POST` now appears live in the browser's network tab would close the loop, but was not run
  by the maker this cycle (no uvicorn/browser permitted).
- **One environmental, non-reproducing flake during this cycle's extra revert-confirmation step**
  (not the actual fix verification, which passed cleanly against the tracked worktree) — see "Actual
  outputs": a throwaway copy's pytest collection hit `FileNotFoundError` against a different
  `mutation-check-<random>`/`playwright-artifacts-<random>` temp directory on each of several
  retries, consistent with another concurrently-running process on the same machine racing pytest's
  collection-time filesystem walk over the shared `%TEMP%`. Same class of issue as the pre-existing,
  already-tracked `test_flake_probe_real_process.py` flake (ISS-t164-1/AT-518) the checker noted in
  its cycle-1 re-run — not something `error_pages.py` or this cycle's tests touch or introduce.
- **AT-259, precisely scoped now (was previously mis-stated as fully untouched).** On
  `routes_learn.py`'s `approve_flowspec`/`request_edit_flowspec`: the unknown-slug 404
  (`_signed` -> `_load_project_or_404`) raises a plain `fastapi.HTTPException` that nothing there
  catches, so it **is** covered by this handler — and was already covered by cycle 1's narrower
  registration too, since the exception's actual runtime type is `fastapi.HTTPException`, a
  `starlette.exceptions.HTTPException` subclass either way (test added, see "Capability coverage").
  The route's **other** refusals — unsigned (`by.strip()` empty), the credential-guard 400
  (`_refuse_unsafe_submission`, caught inside `_signed`), and "nothing to approve"/"nothing to send
  back" — all return a hand-built `HTMLResponse` via `_refusal()` directly and never raise
  `HTTPException` at all, so they never reach this handler and are unaffected by either revision.
  Whether the wider historical AT-259 filing (U10 amendment log: "4 of ~6 refusal paths ... are
  raw") named other, different raw-JSON paths elsewhere in this codebase was not re-investigated
  beyond these two routes — out of scope for this narrow pre-check revision.
- **No new `qa/contracts/ui.md` criterion added** — flagged above under "Contract" for the checker
  to decide (my brief said do not edit `qa/contracts/`).
- **The "one loader" claim is verified by citation, not by a failing test** — see "Capability
  coverage": `SecretStore.load(...).redactor()` and the old direct-`parse_env` implementation
  produce byte-identical output for this call site, so no test can distinguish "reuses the shared
  loader" from "duplicates it" — that distinction only exists in the source, and is cited by
  file:line instead.
- **The redactor is rebuilt (SecretStore loaded fresh) on every themed error render.** Cheap for a
  local single-operator tool serving error pages, not a hot path; not cached, since caching a
  credential file's contents in memory across requests felt like the wrong tradeoff to make
  silently in a fix-cycle-1 unit — flagged rather than assumed fine.
- **One transient `MemoryError`** was hit and resolved by retrying once, importing `openpyxl`
  mid-`pytest`-collection in a throwaway checkout, during this revision's red-first step (see
  "Actual outputs") — recorded as direct evidence of how constrained RAM was, not hidden as a
  non-event.

## Status: checked-PASS (cycle 2, qa/verdicts/at596-http-error-page.md 67989ea)
