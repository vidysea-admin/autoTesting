# Verdict - mongo-store-u9 (checker A)

**Cycle checked:** 0
**Verdict:** FAIL (one blocking finding on M26; everything else PASS)
**Checker:** chk-mongo-u9-a, fresh context, read-only toward `src/` and `tests/`. Did not read any other checker's verdict.
**Reviewed:** `git diff 23eb4af2..HEAD` on `feat/mongo-store-u9` (code commit `ee4889dc`, manifest `591b4cbf`), contract `qa/contracts/mongo-store.md` M9, M11, M13, M26, M27 (and M28, which U10 owns).

## Blocking finding

**F1 (M26, CRITICAL) - a browser request during an outage is a plain 500, not the themed 503, in every Mongo configuration.**
`_StoreDownGate.__call__` builds the HTML reply with `_error_page(503, STORE_DOWN)` (`src/autotester/ui/error_pages.py:157-158`). `_error_page` calls `theme.page(...)` (`error_pages.py:108`), whose sidebar calls `_project_slugs()` (`ui/theme.py:135` -> `ui/helpers.py:161` -> `store/filestore.py:292` `list_children` -> `_holders` `:276-281` -> `mongo_backend.py:170` `children` -> `keys`). That is a read of the store that is down, so it raises `StoreUnavailable` again, **inside the `except StoreDown:` handler**, and nothing catches it. The result is `ServerErrorMiddleware`'s plain `Internal Server Error`.

Reproduced with a scratch test in the checker scratchpad (fake server, `TestClient(app, raise_server_exceptions=False)`; a route does one write, then the server goes down, then a second write raises `StoreUnavailable`):

```
RESULT 'runs=mongo' text/html        500 'Internal Server Error'
RESULT 'runs=mongo' application/json 503 '{"detail":"State store unavailable, nothing was changed"}'
(same two lines for AUTOTESTER_STORE_AREAS=projects=mongo and AUTOTESTER_STORE=mongo)
```

With `raise_server_exceptions=True` the second `StoreUnavailable` surfaces at `error_pages.py:158 -> theme.py:135 -> filestore.py:292 -> mongo_backend.py:170`. It is still fail-closed (nothing allowed, no URI or canary in either body or in the exception repr), but the M26 falsifier "the UI renders a themed 503 ('State store unavailable, nothing was changed')" fails for every real browser (`Accept: text/html`) when any area is on Mongo.

The manifest's tests miss it because the 503 tests run in file mode: `test_a_store_outage_in_a_route_is_a_503_with_a_fixed_body[html]` patches `ui.app._project_slugs`, not `ui.helpers._project_slugs` that the theme actually calls, and never selects a Mongo area while rendering. The 17 mutants do not cover it.

Expected fix (maker's call, not prescribed): the outage page must not touch the store (render without the sidebar, or catch a second `StoreDown` and fall back to a bare fixed-body `HTMLResponse`), plus a test with `AUTOTESTER_STORE=mongo`, `Accept: text/html`, the fake down, asserting 503 and the fixed body, plus a mutant for it.

## Non-blocking findings

**W1 (judge flag: readiness hidden from anonymous).** `/healthz` returns the `store` block only to `settings.manage` callers (`ui/routes_live.py:132-146`); anonymous still gets exactly `{"ok": true}` (AU16; `test_healthz_stays_200_and_anonymous_learns_nothing_new` passes). This honours AU16 but the container health probe cannot see store readiness. Acceptable for U9; a decision for Umesh if an anonymous readiness bit is wanted (it would amend AU16).

**W2 (healthz cost).** `store_readiness()` (`routes_live.py:111-124`) calls `validate_store_env()`, which opens the backend (marker check, index creation on first open) and pings on every detail GET, up to the 5 s selection timeout when down. Sync route, `settings.manage` only; noted.

**W3 (ping_backends trusts the source message).** `ping_backends` re-raises `type(exc)(f"{exc}; areas on ...")` (`store/mongo_routes.py:249-260`). With a stub `StoreDown(f"cannot reach {URI}")` the URI is relayed verbatim. Today the only source is the guard, whose messages carry the exception class only (`mongo_guard.py:72,235`), and a down fake whose driver message holds the URI produced no canary in the traceback, so M9 holds; but it rests on every `StoreDown` raiser staying URI-free.

**W4 (collision, judge flag).** `PATHLYNKS_MONGO_URI` is also the product read-only DB-assertion `SecretRef` (`browser/db.py:6`, `tests/test_db.py:99`). It is the name Umesh gave (D-120, `docs/DECISIONS.md:2926,2935`; M28/M36) and D-120 states the store sits on the same server; no `projects/` file declares it. M10 (`browser/db.py:35`) still refuses the store database on the read side. No code defect; a naming risk only if the two ever point at different servers. Not a failure.

**W5 (contract-owned file edits, judge flag).** `mongo_guard.py` (U1) and `mongo_routes.py` (U4) were touched only to add the driver-free `StoreDown` base (`mongo_routes.py:123-125`, `mongo_guard.py:24,52`); public surface and guard tests unchanged (`test_mongo_guard*.py`, `test_mongo_backend_fence.py` pass). `mongo_guard.py` is exactly 300 lines, paid by deleting the blank line after the module docstring's first line (cosmetic, doctor clean). `filestore.py` is 298 lines. Justified.

**W6 (wording).** `STORE_DOWN` says "nothing was changed"; a request that wrote before the outage cannot honour that. It is the contract's fixed wording (M26), so this is not a finding against U9. I could not demonstrate a persisted partial write with the fake (my scratch run showed only `server_state` docs), so I make no claim either way.

## Criteria

| Crit | Result | Evidence |
|---|---|---|
| M9 URI never echoed | PASS | `core/env.py:218-231` only returns the value; no log, print or raise carries it. Adversarial: canary URI in the process env AND the repo `.env` -> env wins, nothing logged (DEBUG buffer has no canary); down server whose driver message holds the URI -> `StoreUnavailable`, canary absent from the full traceback and the JSON 503 body; `AUTOTESTER_MONGO_URI` appears nowhere under `src/`, `scripts/`, `docker/` (grep empty). |
| M13 backend is configuration | PASS | `mongo_routes.py`, `error_pages.py`, `routes_live.py` import no driver; fresh interpreter `import autotester.cli, autotester.ui.app` -> `pymongo` loaded: False, `gridfs` loaded: False; `test_a_file_mode_workload_never_imports_a_database_driver` and `test_an_unknown_store_value_stops_startup` pass. |
| M27 startup check | PASS | `filestore.py:159-161` -> `mongo_routes.py:249-260`; one `command:ping` on the configured database per backend; the refusal names area and exception class only; `_lifespan` aborts (`test_the_server_refuses_to_start_when_the_store_is_down`). |
| M11 marker | PASS (unchanged) | U9 adds no marker code; startup constructs through `GuardedStore._verify_identity`; `test_mongo_guard.py` marker tests pass. |
| M26 fail closed | **FAIL** | F1. JSON path, auth-gate path, `/healthz` 200 and the anonymous shape are fine. HTML is a 500 when a Mongo area is selected. |
| M28 | out of scope | U10 owns `docker/DEPLOY.md` and `entrypoint.sh`; `PATHLYNKS_MONGO_URI` is the name M28 lists, consistent. |

## Commands run

Worktree `D:/autoTesting/.claude/worktrees/mongo-u9`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, two files per call, `env -u ANTHROPIC_BASE_URL`.

```
tests/test_store_startup_u9.py tests/test_state_selection.py        -> 48 passed
tests/test_state_sweep_u3b.py tests/test_state_wrappers.py          -> 90 passed
tests/test_ui_healthz.py tests/test_mongo_guard_scan.py             -> 38 passed
tests/test_ui_error_pages.py tests/test_ui_error_page_headers.py    -> 15 passed
tests/test_mongo_guard.py tests/test_mongo_guard_surface.py         -> 40 passed
tests/test_mongo_guard_chain.py tests/test_mongo_guard_spec.py      -> 14 passed
tests/test_mongo_guard_uri.py tests/test_mongo_backend_fence.py     -> 88 passed
tests/test_mongo_backend_layout.py tests/test_blobs_mongo.py        -> 81 passed
tests/test_ui_auth_surface.py tests/test_ui_auth_policy_table.py    -> 25 passed
tests/test_hosting_config.py tests/test_env_loading.py              -> 17 passed
tests/test_env_dollar_warning.py tests/test_state_backend_contract.py -> 339 passed, 1 skipped
tests/test_state_signatures.py tests/test_ui_auth_accounts.py       -> 27 passed
uv run ruff check src tests scripts                                  -> All checks passed!
uv run autotester doctor > .work/doctor-chkA.txt                     -> exit 0, "doctor: clean" (D-087 advisories only)
uv run python scripts/mutation_check.py qa/evidence/mongo-store-u9/mutations.json --repo .  -> 17/17 mutations killed
scratch adversarial test (fake server, canary URI)                   -> F1, W3, M9 results above
```

The manifest's test claims reproduce. The passing suite does not exercise the HTML outage page with a Mongo area selected, which is why F1 survives 17/17 mutants.

## For the maker (cycle 1)

Fix F1 in place (`ui/error_pages.py`: the 503 page must render without a store read), add the Mongo-selected HTML test and a mutant for it. W3 is optional hardening (scrub or replace the relayed message in `ping_backends`).
