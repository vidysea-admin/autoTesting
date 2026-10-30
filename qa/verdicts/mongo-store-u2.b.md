# Verdict (checker B, adversarial security) - mongo-store-u2

**Cycle checked:** 0
**Verdict:** PASS (with 5 warnings, none blocks a U2 criterion M13, M14, M15, M17, M19)
**Unit:** U2, branch `feat/mongo-store-u2`, code SHA `42e1fae1`, manifest SHA `0b19a96e` (checked there; `7d80b16e` only adds checker A's verdict, `git diff --stat 0b19a96e HEAD` = that one file). I did not read checker A's verdict.
**Worktree:** `D:/autoTesting/.claude/worktrees/mongo-u2` (the shared brief named `mongo-u6a`; that was wrong, nothing from it was used).
**Scope:** attack `safe_key` (M17), area routing, `AUTOTESTER_STORE` parsing, the mongo_guard exception chain (M9), and 16-thread races (M19). Read-only toward `src/` and `tests/`; nothing merged or pushed. No `.env` value was read or printed (the only secret-like string is the test canary `CANARY-...` from `tests/fake_mongo.py`).

## Result of my own re-runs (host: Windows 11, Python 3.11, worktree `.venv`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, <= 2 files per call)

| Command | Output |
|---|---|
| pytest test_state_backend_contract.py test_state_selection.py (`env -u ANTHROPIC_BASE_URL`) | 105 passed |
| pytest test_state_signatures.py test_state_wrappers.py | 52 passed |
| pytest test_mongo_guard.py test_mongo_guard_surface.py | 40 passed |
| pytest test_mongo_guard_chain.py test_mongo_guard_spec.py | 8 passed |
| `ruff check src tests scripts` | All checks passed! |
| `autotester.exe doctor` > `.work/chkb/doctor.txt` | exit 0, `doctor: clean` (only non-blocking D-087 advisories) |

## M19 concurrency
- The 16-thread tests (`-k "16_callers or stale or never_overwrites or missing_key"`, 12 tests = 6 x [file, memory]) run **25 times** in separate pytest processes: **25/25 `12 passed`**.
- My own in-process stress on `FileBackend`: 200 reps x (16-thread `create_exclusive` + 16-thread `put_if` on the same sha), barrier-started: **0 anomalies** (always exactly one winner, claim content non-empty after join).

## Mutants (full scratch copy of src/tests/scripts/pyproject, one mutant at a time, baseline green: 122 / 35 / 21 passed). Racy mutants ran 8x.

| # | Mutant | Result |
|---|---|---|
| S1-S8 | `safe_key`: backslash allowed; NUL allowed; empty key allowed; `..` allowed; `.` allowed; empty segment allowed; drive letter allowed; drive letter only checked in first segment | all 8 KILLED (2-13 tests each) |
| S9 | prefix trailing slash not stripped | KILLED (6) |
| F1, F2 | `FileBackend._path` / `keys` skip `safe_key` | KILLED (14, 12) |
| F3 | `backend_for` routes the raw key to `area_of` instead of `safe_key(key)` | **SURVIVED** - equivalent today: every backend method re-validates (`filestore.py:87,134`). Matters only if a backend ever stops validating. |
| F4 | `_route`: path outside the data root written under the data root | KILLED (1) |
| F5-F8 | unknown backend accepted; unknown area accepted; blank per-area backend falls back to file; backend name case-folded | all 4 KILLED |
| F9, F10 | `validate_store_env` wiring check removed; `ui/app.py:64` call removed | both KILLED |
| C1 | `create_exclusive` without `O_EXCL` | KILLED |
| C2 | `exists()`-then-open TOCTOU, no sleep (8 runs) | KILLED 8/8 |
| C3 | same with a 10 ms window | KILLED |
| C4 | `put_if` lock removed, no sleep (8 runs) | KILLED 8/8 |
| C5 | sleep added with the lock kept | SURVIVED - my error, equivalent mutant (lock still serialises). Re-done as C5b. |
| C5b | `put_if` lock removed + 10 ms window | KILLED (`test_put_if_has_one_winner_among_16_callers_holding_the_same_sha[file]`) |
| G1 | `_translate` raises inside `except` (`from None`, context kept) | KILLED (2) |
| G2, G3 | driver message copied into `StoreUnavailable` (`_translate`, constructor) | KILLED (4, 2) |
| G4 | constructor raises inside `except` | KILLED (2) |
| G5 | `_uri_path_database` raises inside `except` with `{exc}` | **SURVIVED** (21 passed) - see W4 |

The race tests are not vacuous: a lock or `O_EXCL` removal is caught deterministically, including with no artificial delay.

## Attacks that failed (good)
- Traversal on the real Windows FS: `../x`, `a/../b`, `/x`, `C:/x`, `c:x`, `a\b`, NUL are refused by `safe_key` before I/O (tests plus my probes). `x/.. /.. /secret.txt`, `x/y/.. /.. /.. /secret.txt`, `x/.../.../secret.txt` pass `safe_key` but do **not** escape: get returns `None`, put raises `FileNotFoundError`; the planted outside file `secret.txt` was untouched and no file appeared outside the data root (`rglob` check).
- Unicode lookalikes (`..` + U+2024, fullwidth `．．`) pass `safe_key` and become literal directory names inside the root; no traversal.
- `AUTOTESTER_STORE` parsing: `File`, `mongo,file`, blank area backend, unknown area all raise `StoreSelectionError`; `mongo` is "not wired" and raises at startup (`filestore.py:194-205`); no silent fallback found (F5-F10 killed).
- `_route` (`filestore.py:212`): a path under the root with `..` becomes a key with `..` and is refused; a path outside the root is a plain file keyed by its own name.
- Exception chain: invalid URIs (bad port, `http://` scheme, empty host, NUL in query, `%zz` userinfo) raise `StoreConfigError` with chain length 1 and no canary. Constructor, `ping`, `find`, `insert_one`, bucket upload failures: chain clean (tests plus mutants G1-G4).

## Findings

**W1 (Warning) `safe_key` is weaker than the repo's own `safe_name`; Windows aliases keys.** `core/safe_names.py:76-86`. M17 as written (`..`, absolute, drive letter) is met. But measured on this host with `FileBackend.put`: `a/foo.` and `a/foo ` write to the same file as `a/foo` (`keys("a/")` lists `a/foo`), so two distinct keys alias one document. Reserved device names are accepted (`a/prn`, `a/NUL.txt` written; `a/NUL` raised `FileExistsError`). `safe_name` (`safe_names.py:44-57`) refuses all of these (trailing dot/space, device names). A non-leading `:` only fails by accident (`a/host.json:hidden` -> `OSError`; `ab:x/y` -> `NotADirectoryError`), never as `UnsafeName`. No escape from the root, but on Cloud Run (Ubuntu) these are distinct keys while on a Windows dev host they alias, which breaks "same answer on Windows and Ubuntu" (module docstring, `safe_names.py:1-10`). Suggest `safe_key` also refuse a segment ending in `.`/space, a device name, and any `:` or `< > " | ? *`, and add those to `UNSAFE` in `tests/test_state_backend_contract.py`. Reserved for U3/U4 fix cycle or follow-up; not a U2 criterion failure.

**W2 (Warning, latent) `delete_prefix("")` deletes the whole data root.** `filestore.py:140` with `safe_key(prefix, prefix=True)` allowing `""`. Measured: root holding `.env`, `pyproject.toml`, `projects/a/p.json` -> `delete_prefix("")` returned 4 and left `[]`. Also string-prefix semantics: `delete_prefix("projects/a")` removed `projects/ab/q.json` too. `FileBackend` root is `repo_root()` in production, so `.env` is in reach. No caller exists today (grep of `src/` and `scripts/`), so nothing is broken yet. Recommend refusing an empty prefix and requiring a trailing `/` for `delete_prefix` before the first caller lands.

**W3 (Warning, M9/availability) A lazy driver cursor escapes `_translate`.** `store/mongo_guard.py:125`: `return list(_translate(_REGISTRY[self].find, ...))`. pymongo's `Collection.find` returns a lazy `Cursor`; the network call happens inside `list(...)`, outside `_translate`. Probe: a collection whose `find` returns an iterator that raises `AutoReconnect(f"... {URI}")` on `__next__` -> `col.find({})` raised the **raw** `pymongo.errors.AutoReconnect` with the canary in `str(e)` (not `StoreUnavailable`). The existing test `test_unavailable_errors_from_a_driver_failure_carry_no_chain` passes only because `tests/fake_mongo.py:61-63` raises eagerly in `find()`, unlike the real driver. Real pymongo messages quote host:port (not the password), so this is a contract (M9, "only `StoreUnavailable`") and error-handling defect rather than a proven password leak. Fix: `_translate(lambda: list(raw.find(...)))` (as `GuardedBucket.revisions` already does, `mongo_guard.py:~190`) plus a lazy-cursor case in the fake. This is U1 code touched by U2's M9 follow-up; I judge it against M9 (CRITICAL, dual) and flag it for the U4/U1 owner.

**W4 (Warning, test gap) mutant G5 survived.** `mongo_guard.py:213-215` (`_uri_path_database`): no test drives the invalid-URI branch under the chain walker. Current behaviour is clean (probed, 5 malformed URIs, chain length 1, no canary), so this is coverage, not a live leak. Add an invalid-URI case to `tests/test_mongo_guard_chain.py` using `assert_chain_clean`.

**W5 (Warning, minor) latent silent no-op areas and visible empty claim.** (a) `area_of` (`filestore.py:186-192`) never returns `approvals`, `auth`, `credentials`, `blobs` or `queue`, although `AREAS` (`filestore.py:27`) accepts them. Today `credentials=mongo` is rejected as "not wired"; once U4 wires `mongo`, `AUTOTESTER_STORE_AREAS=credentials=mongo` would be accepted yet route no key there, silently leaving credentials on disk. U4 must replace `area_of` with the real table and add a test per area. (b) `create_exclusive` (`filestore.py:108-120`) creates the file before writing, so a concurrent `get` can read an empty claim (stale-claim reader sees `""`). Winner uniqueness is unaffected (0 anomalies in 200 reps); reader handling is a caller concern for first-admin/marker claims.

## Disposition
All U2 criteria I attacked (M13, M14 spot, M15, M17, M19) hold. Mutation kill rate on U2 code: 27 of 29 meaningful mutants killed (F3 equivalent today, G5 test gap on U1 code; C5 excluded as my invalid mutant, redone as C5b). PASS with W1-W5 recorded for the maker; W1 and W3 are the ones I would not let slide past U4.

Evidence kept locally (not committed): `.work/chkb/` was deleted after this file was written.
