# Verdict - mongo-store-u1 (checker B, adversarial, independent)
Verdict: PASS
Cycle checked: 2
Head tested: b99deb4e (feat/mongo-store-u1). Unit: U1, CRITICAL, dual check (D-100). Checker B did not read checker A's verdict.
Class: all LOCAL. Fake client only; nothing connected to Mongo; no `.env` value read. Python 3.11.15, `PYTHONPATH=<worktree>/src`, shared venv, at most 2 test files per pytest call.

Cycle 1 FAIL findings F1-F9 are closed (table below). I attacked the new code for URI parity, exception chains, object reach, operator injection and `replace_one` `_id`. No contract falsifier is met. I found eight weaker items (W1-W8): one code hardening gap (W1), one untested branch of a CRITICAL criterion (W2), the rest low or accepted residuals. None blocks PASS; W1 and W2 are worth a cheap follow-up.

## Cycle 1 findings, re-run
Evidence: `qa/evidence/mongo-store-u1/checker-b/probe1..5.py` re-run unchanged; new probes in `qa/evidence/mongo-store-u1/checker-b2/`.

| # | Cycle 1 finding | Now | How shown |
|---|---|---|---|
| F1 | M4(c) `db.collection` and `#` in userinfo bypass | CLOSED | `probe2.py`: all five URIs `refused:StoreConfigError`. `_uri_path_database` (`mongo_guard.py:209-218`) calls the driver's own `parse_uri(validate=False)`. `probe7.py` fuzz: 400,000 random URIs built from 35 tricky tokens, 152,321 accepted by the driver's own `_validate_uri` (`pymongo/uri_parser_shared.py:510`), 0 where the driver reads `autotester` (case-folded) and the guard does not, 0 where the guard refuses a driver-valid URI |
| F2 | M9 `urlsplit` NFKC error echoes password | CLOSED | `probe5.py`: fullwidth colon and at-sign construct (pymongo accepts them, no error exists); `[h` gives `StoreConfigError` with fixed text, no `__context__` or `__cause__`, canary absent from str, repr and traceback (`probe6.py` section 5 repeats it) |
| F3 | M6 `_raw()` hands out the driver collection | CLOSED | `probe1.py` section B: `AttributeError: no attribute '_raw'`. `probe8.py` walks store, both collection kinds and bucket through `dir()`, every zero-argument method, `__closure__`, `__defaults__`, `__kwdefaults__`, class bodies: no driver or fake object found. The only reach is `__weakref__` (W6) |
| F4 | `find` projection unchecked | CLOSED | `probe3.py` and `probe8.py`: `$function` in a projection, nested in `$cond`, and `$where` as a key: refused (`mongo_guard.py:125`) |
| F5 | replacement `_id`, `$set` shape | CLOSED with a caveat (W5) | `mongo_guard.py:93-101, 152-161`; `probe3.py`: `{"$set": "abc"}` refused, replacement `_id` marker upsert refused |
| F6 | AST scan evasions | CLOSED | `probe4.py`: concat or variable `import_module`, `getattr(importlib, ...)`, `exec`, `motor`, `mongoengine`, `mongosh` via subprocess: all FLAGGED |
| F7 | `tool = "x"` raised `AttributeError` | CLOSED | `probe3.py`: `tool-is-str refused StoreConfigError` (`schema/store_config.py:60-63`) |
| F8 | lowercase `ci` env var | cannot be shown on Windows | env names are case-insensitive here; `mongo_guard.py:284` reads correct. Mutant 8 (case-sensitive check) SURVIVES, as the manifest already says |
| F9 | `StoreConfig` accepts any identifier | DEFERRED to the G1 human gate | maker's recorded ruling; the fence for a wrong committed name is the marker plus M4(e) |

## Attacks on the new code that held
- **URI vs driver (M4(c), M5).** `probe7.py` hand corpus (35 shapes, all read against the driver): unix socket `mongodb://%2Ftmp%2Fm.sock/autotester`, `%2Ftmp%2Fm.sock,h`, IPv6 `[::1]:27017`, three hosts, empty path, `/` only, `?authSource=autotester` with no path, `autotester%2e`, `/%2Fautotester`, `autotester/x`, `h//autotester`, userinfo with `@@` or two colons, `mongodb+srv` with `replicaSet` and `authSource`. Every driver-valid shape that names `autotester` is refused; shapes that name something else construct. The URI never selects the write database (`mongo_guard.py:233`, M5).
- **Exception text (M9).** `str`, `repr` and `traceback.format_exception` contain no canary on connect failure, ping, insert and GridFS upload (`probe6.py` sections 1 and 5). The parse failure has no `__context__`, no `__cause__` and `__suppress_context__` is false (`probe6.py` section 5 chain `[('StoreConfigError', fixed text, False)]`).
- **Copy, pickle, repr (M6, M9).** `copy.copy` and `deepcopy` of store and collection, and a pickle round trip: the copy exists but every verb raises `KeyError` (it is not in the registry), so copying cannot mint a usable handle. `repr` and `vars()` of store, collections and bucket carry neither the canary nor the host. `store.__dict__` is `{_cfg, _marked}`, collection `{_name, _store}`, bucket `{_store}`.
- **Operators (M6).** `$where`, `$function`, `$accumulator` in a filter, in a projection, nested in `$or`, `$and` and tuples, in `count_documents` and `find_one`: refused (`probe3.py`, `probe8.py`). Update pipelines raise `TypeError` before the driver. `generation.x`, `_id`, `$unset`, `$rename`: refused.
- **`replace_one` `_id`.** other `_id`, `_id` with no filter `_id`, NaN, and any form against the marker: refused. The marker is untouched after the whole run (`probe8.py`: server_state holds the marker plus one unrelated `_id: "x"` row).
- **Verb and collection closure, `delete_many` scope, smoke names, marker, bucket name:** every `probe3.py` row refused or allowed as before.
- **Mutation.** Official specs, run by me with `scripts/mutation_check.py`: `mutations.json` 11/11, `mutations-b.json` 14/14, `mutations-c.json` 6/6 = 31/31 killed, each naming and failing a real test (`checker-b2/official-mutations-run.txt`). My own 24 mutants on the new code (`checker-b2/extra_mutants2.py`, `extra_mutants2.out`): control green; 17 killed with a named failing test; 7 survived (mutant 8 = F8, mutants 10 and 11 = W2, 14 = W3, 18 = W4, 15 and 16 = W8).
- **Suites (my runs):** `test_store_config.py` + `test_mongo_guard.py` 52 passed; `test_mongo_guard_surface.py` + `test_mongo_guard_scan.py` 56 passed; `test_mongo_guard_spec.py` + `test_db.py` 8 passed, 1 skipped; `test_mongo_guard_uri.py` 71 passed. `ruff check src tests scripts`: All checks passed. Doctor not re-run (dangling D-123 citations are expected on this branch).

**Self-correction.** My cycle 1 "31/31 extra mutants killed" is withdrawn: that harness copied only `src`, `tests` and `qa/contracts`, so `tests/conftest.py` could not import `scripts/regression_proof.py` and every run exited 4 on a collection error, which my script counted as a kill. `checker-b2/extra_mutants2.py` copies `scripts/`, runs a no-op control (green), and prints the failing test name for each kill. The official harness (`scripts/mutation_check.py`) was never affected.

## Warnings (non-blocking; none meets a contract falsifier)

**W1 (M9) - `from None` suppresses the display only; the driver exception stays reachable.** `mongo_guard.py:234-235` (constructor) and `:69,71,73` (`_translate`). `probe6.py` section 1: with a client factory that raises `RuntimeError("cannot connect <uri>")`, the `StoreUnavailable` has `__suppress_context__ = True` but `__context__` is the original exception whose text carries the canary; the same holds for a failing `ping` (`context canary: True`). `traceback.format_exception`, `logging.exception` and Sentry-style walkers honour the suppress flag (`format canary: False`), so the M9 falsifier (stdout, stderr, log records, response bodies) is not met. Code that walks `e.__context__` by hand, or serialises it with `repr`, does get it. The maker already did the stronger thing for the parse error (`:209-218`, raise outside the `except`); doing the same here would close it. Real-driver note: `InvalidURI` messages echo host and database parts, not the password (checked against `uri_parser_shared.py:510-600`).

**W2 (M9, test gap on a CRITICAL criterion) - the constructor error branch has no test.** Mutants 10 (`from None` removed) and 11 (`({type(exc).__name__})` replaced by `({exc})` at `mongo_guard.py:235`) both SURVIVE. `tests/test_mongo_guard.py:214-221` (`test_a_failing_connect_never_echoes_the_uri`) takes the down-server path: the client is created, then `find_one` in `_verify_identity` fails and is translated by `_translate`, so line 234-235 never runs. A test whose client factory itself raises with the canary in its message would kill both. The code is correct today; nothing defends it. Contract M12 lists seven required mutants and this is not among them, so not a PASS blocker.

**W3 - `NoFile` to `StoreNotFound` translation is untested** (mutant 14 survives; `_translate` `:70-71`). Without it, `download` of a missing blob would raise `StoreUnavailable`, which U5a callers would read as "server down". Belongs to U5a if not here.

**W4 - `find` may silently drop `projection` and `sort`** (mutant 18 survives; `mongo_guard.py:126-127`). No test passes either argument and checks it reaches the driver. Not a security gap.

**W5 - hardening, nothing leaks.** (a) `replace_one` compares `_id` with Python `!=` (`:156`), so `True == 1 == 1.0` passes the guard (`probe8.py`); a real server rejects the change, and the marker is unaffected because `server_state` filters need a string `_id` and `"marker"` is blocked by name. (b) `_check_update` (`:93-101`) does not run `_check_query` on `$set` values; `{"$set": {"x": {"$function": 1}}}` passes the guard, but a non-pipeline update value is data, not an executed expression. (c) `sort` is not checked (a list of pairs has no operator syntax).

**W6 (M6 residual, same class as `__globals__`) - a third path to `_REGISTRY` that touches no module global.** `store.__weakref__.__callback__.__defaults__[0]()` is `_REGISTRY` (the `WeakKeyDictionary`'s `remove` callback holds a weak reference to its owner as a default argument); `_REGISTRY[store]` then yields the raw database. `probe8.py` finds it by walking `dir()`. Python cannot hide this; it needs in-process code execution, which already has `sys.modules`. Manifest point 5 lists gc and a global read; add `__weakref__`. Related and equal in class: any exception that is not a `PyMongoError` escapes `_translate` untranslated (real examples: `bson.errors.InvalidDocument` is not a `PyMongoError`, shown in `probe7.py` line 1; `find(limit="abc")` raises `TypeError`), and its traceback frame `_translate` has the local `call`, a bound method of the raw collection (`probe6.py` section 2: `tb_frame.f_locals["call"].__self__` is the raw collection, whose `.database.client` is a client handle). Reaching it needs a `try/except` and frame introspection by the caller.

**W7 - frame locals hold the URI.** Any exception through `GuardedStore.__init__` or `_uri_path_database` has `uri` in its traceback frame locals (`probe6.py` section 5). Inherent to taking the URI as an argument; a locals-capturing reporter (Sentry with local variables on) would log it. Also `repr(store)` raises `AttributeError` if the constructor failed before `self._cfg` is set (`:237` vs `:299-300`), which a locals reporter must survive.

**W8 - the srv rewrite refuses two valid Atlas-style options (fail closed).** `mongo_guard.py:215` rewrites `mongodb+srv://` to `mongodb://`; the driver then raises for `srvServiceName` and `srvMaxHosts` ("only allowed with 'mongodb+srv://' URIs", `uri_parser_shared.py` after the `is_srv` branch). `probe7.py`: `mongodb+srv://c.example.net/autotester?srvServiceName=x` and `?srvMaxHosts=2` give `ERR:StoreConfigError` while the driver accepts them. A wrong refusal, not a bypass. Also mutants 15 (`rpartition`) and 16 (`startswith` instead of equality) survive: no test pins "a URI containing `://` later in the string" or "a database whose name merely starts with `autotester`" as accepted.

## Commands
```
export PYTHONPATH=/d/autoTesting/.claude/worktrees/mongo-u1/src
for p in probe2 probe5 probe1 probe3 probe4; do /d/autoTesting/.venv/Scripts/python qa/evidence/mongo-store-u1/checker-b/$p.py; done
/d/autoTesting/.venv/Scripts/python qa/evidence/mongo-store-u1/checker-b2/probe6.py   # chains, frames, copy/pickle/repr
/d/autoTesting/.venv/Scripts/python qa/evidence/mongo-store-u1/checker-b2/probe7.py   # URI parity, 400k fuzz
/d/autoTesting/.venv/Scripts/python qa/evidence/mongo-store-u1/checker-b2/probe8.py   # attribute walk, operators, replace_one _id
python -m pytest <two files> -o addopts= -q -p no:cacheprovider                        # four calls, see Suites
python scripts/mutation_check.py qa/evidence/mongo-store-u1/mutations{,-b,-c}.json --repo .   # 11/11, 14/14, 6/6
/d/autoTesting/.venv/Scripts/python qa/evidence/mongo-store-u1/checker-b2/extra_mutants2.py    # 24 mutants + control
```

## Recommended follow-up (does not hold the PASS)
1. W1: raise `StoreUnavailable` outside the `except` in the constructor and `_translate` (the pattern already used at `:218`), and add a constructor-factory-raises test (kills W2 mutants 10 and 11).
2. W6: add `__weakref__` and untranslated-exception frames to manifest point 5 / the contract residual list.
3. W8: strip `srvServiceName` and `srvMaxHosts` before the swap, or accept the false refusal knowingly.

Metrics: checker=B cycle=2 suite_runs=4 official_mutants=31/31 extra_mutants=24+control (17 killed, 7 survived) fuzz=400000 defects_unit=0 blocking, 8 warnings mode=adversarial
