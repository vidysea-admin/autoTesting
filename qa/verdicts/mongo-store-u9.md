# Verdict - mongo-store-u9

**Verdict:** PASS
**Cycle checked:** 1
**Checker:** checker-A (fresh context; did not read any other checker's verdict; the cycle 0 FAIL is `2f8d6708` in git)
**Code SHA checked:** `1c9e65727e27f0dbbe3abad9b78fab1a866f428c` (manifest commit `8d61b57e`), branch `feat/mongo-store-u9`
**Contract:** `qa/contracts/mongo-store.md`, U9 row: M9, M11, M13, M26, M27. M26 is CRITICAL; finding 6 states what is and is not proven by this unit.

## Result per criterion

| Crit | Result | Evidence |
|---|---|---|
| M26 fail closed (HTML 503, F1) | MET for the U9 scope | finding 1 |
| M9 URI never echoed (incl. W3) | MET | findings 2, 3 |
| M27 startup check | MET | finding 4 |
| M13 backend is configuration | MET | finding 4 |
| M11 marker | MET (unchanged; U9 starts through it) | finding 4 |

## Findings

1. **F1 closed (M26).** `src/autotester/ui/error_pages.py:137-150` `_store_down_html()` builds the page from `theme.card` + `PAGE_STYLE` with no sidebar and no project read; any exception returns `_STATIC_503` (`:134`); the gate (`:175`) sends it as `HTMLResponse(..., 503)`.
   My own scratch reproduction (not the maker's tests; scratchpad `test_scratch_u9.py`, run with the repo conftest as a plugin): fake server opened while up, then taken down. Selections `AUTOTESTER_STORE_AREAS=runs=mongo,projects=mongo`, `AUTOTESTER_STORE=mongo`, `AUTOTESTER_STORE_AREAS=projects=mongo`; Accept `text/html`, a browser Accept string, and `application/json`; project `demo` seeded while up. Nine requests per combination: `GET /`, `/projects/demo`, `/projects/demo/cases`, `/admin/users`, `/admin/groups`, `/settings/providers`, and `POST /projects/demo/run`, `/admin/groups`, `/settings/providers`.
   Result: 9/9 combinations pass. Every request is 503 except `POST /settings/providers`, which is 422 (form validation fires before any store read; the body is still canary-free). Every 503 carries the fixed text; HTML ones are `text/html`, contain `class='card'` and `<style`, and no `<aside` in the markup; JSON ones are exactly `{"detail": "State store unavailable, nothing was changed"}`. The canary password, `mongodb` and `db.example` appear in no body, stdout, stderr or log record.
   Per-request tree hash of the data root: the only changes are `.auth/auth.sqlite3` on every request (the test harness `tests/auth_login_fixture.py:44` runs `INSERT OR REPLACE INTO sessions` with `now` before each request; auth is still SQLite until U6b) and, only when the `audit` area is a file area (never with `AUTOTESTER_STORE=mongo`), `.work/audit.jsonl` on POSTs. No file belonging to a mongo area is created or changed.
   Fallback probes (each answered 503, body equal to `_STATIC_503` exactly, no leak): `theme.card` raising `RuntimeError("boom <uri>")`; `theme.card` raising `StoreUnavailable("x <uri>")`; `theme.card` raising `KeyError`; `PAGE_STYLE` replaced by an object whose `__format__` and `__str__` raise with the URI.
2. **W3 closed (M9).** `src/autotester/store/mongo_routes.py:249-261` raises `type(exc)(f"state store unreachable ({type(exc).__name__}); areas on {name}: {areas}") from None`. Own probes: a canary-bearing `StoreDown("cannot reach <uri>")` and a `StoreDown` subclass: text, repr and full traceback contain no canary, no `mongodb`, no `cannot reach`; `__cause__` is `None` and `__suppress_context__` is true; only areas on the failing backend are listed (`runs, projects`, not `settings`). A non-`StoreDown` exception (`ValueError` quoting the URI) is not caught by `ping_backends` and propagates with its own message: unchanged behaviour (the guard only raises `StoreUnavailable`, a `StoreDown`, from `ping`), so the path is not reachable through the real backend. Real startup against a down fake with `runs,projects=mongo`: `StoreUnavailable: state store unreachable (StoreUnavailable); areas on mongo: projects, runs`; canary absent from text, stdout, stderr and log.
3. **Behaviour change judged: acceptable.** The refusal now names `StoreUnavailable` instead of the driver class (`AutoReconnect`). M27 requires naming the area and the exception class, never the URI (M9); both hold (area names plus the class of the raised exception), and M9 outranks diagnostic detail because the driver message is exactly where a URI can hide. Cost: an operator no longer sees the driver class. Non-blocking.
4. **No regression of cycle-0 criteria.** M13: fresh `-I` interpreter importing `autotester.cli` and `autotester.ui.app` and calling `validate_store_env()` in file mode: `pymongo in sys.modules` False, `gridfs in sys.modules` False, all nine areas `file`. M27: against an up fake with `runs,projects=mongo` the server log holds exactly one `('autotester', 'command:ping')` (one ping per backend, on the configured database only). M11: `tests/test_mongo_guard.py` marker tests pass unchanged and U9 adds no marker code. M9: guard chain and URI tests pass unchanged.
5. **Diff is fix files only.** `git diff --stat 117fecf7..HEAD` (the merge `117fecf7` is the only other content in `2f8d6708..HEAD`): `src/autotester/ui/error_pages.py` (+18/-1), `src/autotester/store/mongo_routes.py` (+5/-3), `tests/test_store_outage_u9.py` (new, 193 lines), `tests/test_store_startup_u9.py` (-105, tests moved), `qa/evidence/mongo-store-u9/{mutations.json,mutation-run-cycle1.txt}`, `qa/manifests/mongo-store-u9.md`. Test-name diff old vs new: no test removed; three added (`..._falls_back_to_a_fixed_body`, `..._never_relays_the_source_message`, `..._renders_without_reading_the_down_store`). The only assertion changed in moved tests is `"AutoReconnect"` -> `"StoreUnavailable"` (finding 3). Sizes: `error_pages.py` 182, `mongo_routes.py` 288, `test_store_startup_u9.py` 180, `test_store_outage_u9.py` 193; all under 300.
6. **What this PASS does not prove (carry into the G1 readiness table, M52).**
   (a) M26's clauses "a run in progress ends `interrupted`" and auth denial at the auth *store* level are not reachable in U9: auth is still SQLite (U6b) and run-queue state is U7/U3c. The gate-level denial (a `StoreDown` inside the auth gate becomes a 503, never an allowed request) is proven here. The unit that owns each clause must re-judge it before any area flip.
   (b) `/healthz` returns the `store` readiness block only to `settings.manage` callers; an anonymous probe sees `{"ok": true}` (AU16). M26's "a readiness field reports the store" is met for administrators only; making it anonymous is a contract decision, not a defect here.
   (c) `/healthz` pings Mongo per detail request (5 s selection timeout when down); admin-only, accepted.
   (d) `PATHLYNKS_MONGO_URI` is also the product DB-assertion variable (`browser/db.py:6`): a naming question for Umesh, not code.
   All four are carried unchanged from the manifest's judgement list.
7. **Manifest evidence misstatement (non-blocking).** `qa/manifests/mongo-store-u9.md` records `test_store_startup_u9.py + test_state_selection.py -> 52 passed`; I measure 38 passed (12 + 26). 52 equals outage 26 + selection 26, so it looks mis-transcribed. The tests pass; no verdict depends on the figure. The maker should correct the line at close-out.

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u9`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, two files per call, `env -u ANTHROPIC_BASE_URL`)

```
pytest tests/test_store_startup_u9.py tests/test_store_outage_u9.py        -> 26 passed
pytest tests/test_store_startup_u9.py tests/test_state_selection.py        -> 38 passed
pytest tests/test_ui_healthz.py tests/test_ui_error_pages.py               -> 18 passed
pytest tests/test_ui_error_page_headers.py tests/test_mongo_guard_scan.py  -> 35 passed
pytest tests/test_state_sweep_u3b.py tests/test_state_wrappers.py          -> 90 passed
pytest tests/test_state_sweep_u3c.py tests/test_state_bypass_rule.py       -> 67 passed
pytest tests/test_mongo_guard_chain.py tests/test_ui_auth_surface.py       -> 34 passed
pytest tests/test_state_selection.py tests/test_ui_healthz.py              -> 32 passed
pytest tests/test_mongo_guard.py tests/test_mongo_guard_uri.py             -> 87 passed
pytest <scratchpad>/test_scratch_u9.py -p conftest (own reproduction)      -> 14 passed
pytest <scratchpad>/test_probe2.py -p conftest (startup refusal, ping log) -> 1 passed
uv run ruff check src tests scripts                                        -> All checks passed!
uv run autotester doctor > .work/doctor-chk-u9.txt                         -> exit 0, "doctor: clean" (D-087 non-blocking advisories only)
uv run python scripts/mutation_check.py qa/evidence/mongo-store-u9/mutations.json --repo .  -> 21/21 mutations killed (exit 0)
python -I: import autotester.cli, ui.app; validate_store_env()             -> pymongo False, gridfs False
```

No live server, no network, no `.env` value read or printed. No `src/` or `tests/` file edited. The full suite was not run (low-memory rule); not needed for this unit's scope.
