# Verdict: ts6-auth-store

**Cycle checked:** 0
**Verdict:** PASS
**Checked code SHA:** 7682c1e0 (base 0a2cbe45)
**Checker:** fresh independent checker; read-only toward src/ and tests/; scratch copies under .work/ deleted afterwards.

## Findings

1. **Failure reproduced on base for exactly the claimed reason.** `git archive 0a2cbe45` (src, tests, scripts, pyproject) into a scratch dir, `PYTHONPATH=<scratch>/src`, `autotester.__file__` confirmed to resolve inside the scratch copy:
   `pytest tests/test_schedule_tick.py -k transitively` -> `1 failed, 20 deselected`;
   `scheduler_side_violations()` returned exactly
   `['autotester.auth.access -> autotester.auth.store', 'autotester.auth.store -> autotester.auth.store_sqlite']`.
   Nothing else, so no other regression is hidden behind it.
2. **Fix only widens ALLOWED_OUTSIDE by those two modules.** `git diff 0a2cbe45 HEAD -- tests src`: one hunk, `tests/test_schedule_tick.py:157-159` (the `auth.loopback` set member gets a trailing comma-line plus `"autotester.auth.store", "autotester.auth.store_sqlite"` and a comment). `git diff 0a2cbe45 HEAD -- src | wc -l` = 0 (no src change). Other changed file: `qa/manifests/ts6-auth-store.md` only.
3. **The walk still descends into the new entries.** `tests/test_schedule_tick.py:218-221`: the allow check only gates what is appended to `problems`; `todo.append(dep)` runs unconditionally. Proven by mutation on a scratch copy of HEAD (pre-mutation: `1 passed`):
   - Mutant 1 (requested): `from autotester.browser import session` added to `auth/store_sqlite.py` -> `1 failed`, first extra item `'autotester.auth.store_sqlite -> autotester.browser.session'` (17 violations, the browser's own closure).
   - Mutant 2 (extra): `from autotester.stages.execute import run_case` added to `auth/store.py` -> `1 failed`, first extra item `'autotester.auth.store -> autotester.stages.execute'`.
   Both scratch copies deleted (`ls .work | grep chk` empty).
4. **auth/store.py and auth/store_sqlite.py import nothing browser- or pipeline-side today.** `grep` of imports: store.py:15-18 contextlib, typing, `autotester.schema.auth`; store.py:93 lazy `from autotester.auth.store_sqlite import SqliteAuthStore` (counted by the AST walk, which is why it is listed); store_sqlite.py:12-18 sqlite3, collections.abc, contextlib, datetime, `autotester.auth.db` (already allowed), `autotester.schema.auth`. No `import_module`/`__import__` in either.
5. **Branch test file green.** `uv run pytest tests/test_schedule_tick.py -o addopts=` -> `21 passed, 10 warnings in 17.92s`.
6. **Ruff clean.** `uv run ruff check tests/test_schedule_tick.py src/autotester/auth` -> `All checks passed!`

## Residual notes (non-blocking)
- Only `tests/test_schedule_tick.py` was run (memory cap: at most 2 test files per call); doctor and the full suite were not run, and no src changed, so they cannot be affected by this diff.
- No .env value was read or printed.
