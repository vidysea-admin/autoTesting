# Verdict - mongo-store-u1

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** 34988b42 (branch `feat/mongo-store-u1`, base `1c072711`). Checker A (contract); the dual-check partner (D-100) judges independently.
**Contract:** `qa/contracts/mongo-store.md` U1 = M1-M12, M47. D-123 removed encryption, so the `cryptography` part of M47 no longer applies; judged: hand-written fake, no `mongomock`, lock consistent.

## Independent checks (run by the checker in the worktree, `PYTHONPATH=<worktree>/src`, shared venv, 2 test files per pytest call)
- `pytest tests/test_store_config.py tests/test_mongo_guard.py`: 56 passed (re-run after the maker's last edit, as asked).
- `pytest tests/test_mongo_guard_surface.py tests/test_mongo_guard_scan.py`: 28 passed. `pytest tests/test_mongo_guard_spec.py tests/test_db.py`: 6 passed, 1 skipped (pre-existing skip).
- Mutation harness (`scripts/mutation_check.py`): the recorded spec runs 4 test files per pytest, over the 2-file limit, so the checker split the same 19 mutants by the file of the test that claims the kill (scratch specs, not committed): spec A (store_config + mongo_guard) 11/11 KILLED, spec B (surface + scan) 8/8 KILLED. 19/19; the seven mutants M12 requires (a env, b URI path, c forbidden name, d URI clash, e marker, f `extra="forbid"`, g `aggregate`) are all present and killed. Worktree clean after the run.
- `ruff check src tests scripts`: All checks passed. `uv lock --check`: Resolved 335 packages. `autotester doctor`: clean. `grep -c mongomock pyproject.toml uv.lock`: 0 / 0.
- File caps: `mongo_guard.py` 300 lines (cap 300), `store_config.py` 76, `core/paths.py` 299.

## Criteria
M1 PASS (one source `schema/store_config.py:29-76`, `pyproject.toml [tool.autotester.store]`, handle only `mongo_guard.py:233`; config path from `code_root()` `core/paths.py:21`) but see F2. M2 PASS on the literal text (no `db`/`database`/`db_name` parameter), see F2. M3 PASS (AST scan, two files). **M4 FAIL on clause (c), see F1**; (a), (b), (d), (e) PASS. M5 PASS (spy sees only `autotester` across 4 URIs). M6 PASS (closed verbs `mongo_guard.py:112-174`, `$where/$function/$accumulator` refused, `server_state` marker unreachable `:252-259`). M7 PASS (`InsertOnlyCollection` has no replace/update/delete). M9 PASS for U1's scope (class name only, `from None`, `:60-71`, `:234-235`). M10 PASS (`browser/db.py:44-45`, before any client). M11 PASS in the guard (`:240-272`). M12 PASS (19/19). M47 PASS (see above).

## Rulings on the maker's deviations
1. **`repo_root()` fallback to `code_root()` not implemented: a contract DEFECT, not a miss.** M1 text: "`repo_root()` falls back to it when `AUTOTESTER_ROOT` has no `pyproject.toml`". Taken literally this redirects every test that sets `AUTOTESTER_ROOT=<tmp dir>` (147 test files reference it) to the real checkout, and on Cloud Run (`/data`, no `pyproject.toml`) it silently moves all state back into the image, which is the opposite of the clause's own "because on Cloud Run the data root is `/data`". The clause's purpose (config read from the code tree, falsifier: `AUTOTESTER_ROOT=<dir with no pyproject>` leaves the name unchanged) is met by a separate `code_root()` (`paths.py:21`, test `test_the_data_root_moves_repo_root_but_never_code_root`). Not held against U1. Contract amendment to make in a separate criticality-gated commit: replace the parenthetical with "`code_root()` is separate from `repo_root()`; `repo_root()` returns it only when `AUTOTESTER_ROOT` is unset". `Dockerfile:39,46` copies `pyproject.toml` into `/app`, so `code_root()` resolves there (U9/U10 should re-confirm in the image).
2. **Stricter `delete_many` (`:100-109`), `server_state` `_id` rule (`:252-259`), `$where/$function/$accumulator` refusal (`:41,77`): ACCEPTED.** The contract text "the filter must contain `p` or `k`" is satisfied by `{"p": {"$exists": true}}`, which matches everything, so the tightening serves M6's intent and only adds refusals. U4/U7 must supply `p` or `k` as a non-empty string or `$in` of strings.
3. **M8, 503 page, `store ping`, 3-try retry deferred: CORRECT per the contract.** M8's own `judges:` line is "U4, U5a, U11, U12" and its falsifier needs `put/append_row`, trace rows and the `Redactor` union (M34, U11); M26/M27 are "judges: U9"; the `store ping` CLI is U8/U9. The unit table's loose "M1-M12" for U1 over-reaches M8 (and M11 is tagged U4/U9, though U1 implements the marker, which it did). Suggest the table row say "M1-M7, M9-M12 (M8 by U4/U5a/U11/U12)".

## Findings
**F1 (BLOCKING, M4(c), CRITICAL). A percent-encoded URI path bypasses the clash refusal.** `mongo_guard.py:203-208` takes the path from `urlsplit` without decoding. M4(c) names the oracle: `pymongo.uri_parser.parse_uri(uri)["database"]`, which decodes. Checker probe on the fake: `mongodb://h/autotester` and `mongodb://h/AUTOTESTER` raise `StoreConfigError`, but `mongodb://h/%61utotester` and `mongodb://h/%41utotester?x=1` CONSTRUCT, and `parse_uri("mongodb://h/%61utotester")["database"]` is `autotester`. This is exactly the criterion's falsifier ("either constructs"). Writes are still pinned to `cfg.database` by M5, so no data risk, but the refusal is the stated control. Fix: `unquote_plus(parts.path.lstrip("/"))` (the maker was right to avoid `parse_uri` itself, which does DNS for `mongodb+srv`), plus a parametrised case `%61utotester` / `%41utotester` in `test_a_uri_path_naming_the_store_database_is_refused_before_any_client` and a mutant that drops the decode.

**F2 (BLOCKING, M1/M2 intent). The fence constructor takes a config path.** `GuardedStore.__init__(uri, *, config_path, client_factory, bucket_factory)` at `mongo_guard.py:226-228`. M1: the name "is not read from the environment, `.env`, the URI path, a CLI flag or any argument", and "no API accepts a database name". Probe: `GuardedStore("mongodb://h/", config_path=<toml naming "pathlynks_prod">, client_factory=...)` constructs and writes to `pathlynks_prod` (fake server lists only that database). Literal M2 (parameter names) passes, but one TOML file re-points the only fence at any non-system name, which is what M1/M2 exist to prevent. No `src/` caller uses any of the three today (grep), so the exposure is latent, but the guard is the fence for every later unit. Acceptable remedies: (a) move the three seams out of the public signature (a module-private test hook), or (b) keep them and add an AST test that no `src/` or `scripts/` call site passes `config_path=`, `client_factory=` or `bucket_factory=`, with a mutant. U1's own tests need `config_path` for non-default configs, so (b) is the smaller change.

**F3 (note, not blocking). Docs.** `qa/evidence/mongo-store-u1/mutation-run.txt` was produced with 4 files per pytest; fine, but re-record after F1/F2 adds a mutant. The manifest's M2 row says other store modules (`mongo_backend`, `blobs`, `cli_store`) are re-checked by U4/U5a/U8: agreed, carried forward.

## Next
Maker takes fix cycle 1 for F1 and F2 only; re-submit with `Fix cycle: 1`. Everything else is verified and need not be re-litigated. No code was edited by the checker.

---

# Cycle checked: 1

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 1
**Reviewed SHA:** 45445e95 (branch `feat/mongo-store-u1`; cycle-1 diff `b3eba175..45445e95`, 12 files). Checker A (contract); the dual-check partner (D-100) judges independently. Scope: close F1 and F2 from cycle 0 and confirm no other U1 criterion regressed. Nothing else was re-litigated.

## Independent checks (checker, worktree, `PYTHONPATH=<worktree>/src`, 2 test files per pytest call, one at a time)
- `pytest tests/test_store_config.py tests/test_mongo_guard.py`: 72 passed. `tests/test_mongo_guard_surface.py tests/test_mongo_guard_scan.py`: 38 passed. `tests/test_mongo_guard_spec.py tests/test_db.py`: 7 passed, 1 skipped (the same pre-existing skip as cycle 0). Cycle 0 was 56 / 28 / 6+1 skipped, so the cycle added tests and lost none.
- `scripts/mutation_check.py` on the committed specs, re-run by the checker: `mutations.json` (2 files) 14/14 KILLED, `mutations-b.json` (2 files) 9/9 KILLED, 23/23 in total, up from 19. The four new mutants (s, s2, t, u) are all killed, and each spec is within the two-file limit, so the cycle 0 split is no longer needed. The worktree was clean afterwards.
- `ruff check src tests scripts`: All checks passed. `uv lock --check`: Resolved 335 packages. `autotester doctor`: 3 violations, all `decision-citation-dangling` for D-123 (`qa/manifests/mongo-store-u1.md:98,100`, `qa/verdicts/mongo-store-u1.md:7`). This is expected, because D-123 exists on master only.
- File caps: `mongo_guard.py` 299 lines (cap 300), `store_config.py` 76, `core/paths.py` 299.

## F1 (percent-encoded URI path clash): CLOSED
Fix: `mongo_guard.py:209` is now `unquote_plus(parts.path.lstrip("/"))`, and the import is at `:17`.
My own probe (scratch script, FakeMongoServer, no socket, compared with `pymongo.uri_parser.parse_uri(uri)["database"]`):
- `mongodb://h/%61utotester` is refused (parse_uri database is `autotester`).
- `mongodb://h/%41utotester?x=1` is refused (parse_uri itself raises ConfigurationError on the unknown option, the fence refuses).
- `mongodb://h/auto%74ester` is refused, as is `mongodb://u:p@h/%61UTOTESTER?authSource=x`.
- `mongodb://h/autotester` and `mongodb://h/AUTOTESTER` are still refused.
- `mongodb://h/%2561utotester` constructs. parse_uri gives `%61utotester`, so one decode is correct and there is no double decode.
- `mongodb://h/a+utotester` constructs. It decodes to `a utotester`, not a clash. The malformed forms parse_uri rejects outright are the driver's to refuse, not the fence's.
Tests: parametrised `%61utotester` / `%41utotester?x=1` cases in `test_a_uri_path_naming_the_store_database_is_refused_before_any_client`, plus `test_the_path_is_decoded_exactly_as_the_driver_decodes_it` and `test_a_plus_in_the_path_decodes_to_a_space_like_the_driver_and_is_no_clash` (`tests/test_mongo_guard.py`). Mutant s (no decode) and s2 (decode without plus handling) are both KILLED.

## F2 (injectable constructor): CLOSED (remedy a, with the AST scan from remedy b as the backstop)
- `GuardedStore.__init__(self, uri: str) -> None` (`mongo_guard.py:227`). Probe: `inspect.signature` shows only `uri`. `GuardedStore("mongodb://h/", config_path=None)`, `client_factory=None` and `bucket_factory=None` each raise TypeError, and a second positional argument raises TypeError.
- The three seams moved to the module-private `_SEAM` dict (`:43-44`, read at `:228,232,235`). Tests reach it only through `tests/fake_mongo.py::seams` / `open_store`, which restore it on exit.
- `git grep` of `src` and `scripts` for `_SEAM`, `config_path=`, `client_factory=` and `bucket_factory=`: the only hits outside `mongo_guard.py` are unrelated (`delivery/email.py` has its own `client_factory`, `stages/acceptance_baseline.py:83` is a local variable, and `RunSeams` / `DEFAULT_SEAMS` are in `run_launcher.py`). No call site injects anything into the fence.
- AST backstop `tests/test_mongo_guard_scan.py::test_no_src_or_scripts_call_injects_a_config_path_or_factory_into_the_fence` flags a `GuardedStore(...)` call with an injected keyword, `**kw`, a second positional argument or a starred argument, and any touch of `_SEAM` outside `mongo_guard.py`. `test_the_injection_scan_flags_each_way_in` covers 8 forms and `test_the_injection_scan_leaves_a_plain_construction_alone` the negative case. Mutants t (signature takes a config path again) and u (a `src/autotester/browser/db.py` caller injecting `config_path=`) are both KILLED.
- Residual, not blocking: the scan matches Name and Attribute nodes, so a deliberate string-keyed reach such as `getattr(module, "_SEAM")` would not be flagged. That is a hand-written bypass of a leading-underscore name, the same class as monkeypatching, and no `src` or `scripts` code does it today. U4 and later units that construct the store should keep passing only `uri`.

## No-regression review of the cycle-1 diff
`mongo_guard.py` changed by 17 lines: the `Path` import removed, the `unquote_plus` import, `_SEAM`, the one decode line, and the constructor. No verb, filter, marker or identity logic was touched, so M3 to M7, M9 to M11 are unchanged; the cycle 0 verified criteria still hold (the whole cycle 0 mutant set re-killed, 19 of 19 carried inside 23 of 23, and the 72 / 38 / 7 test counts above). The test edits are mechanical (`GuardedStore(..., client_factory=...)` becomes `open_store(...)`). The spec test now also asserts at most 2 test files per spec and covers both spec files. M1, M2 and M5 hold: probes show the constructor takes no database name or config path, and the spy test is green. The deferrals and the contract defect ruled in cycle 0 (the `repo_root()` fallback, the stricter `delete_many` rule and the M8 / 503 / `store ping` deferrals) are unchanged and not re-opened.

## Result
U1 (M1-M7, M9-M12, M47) PASS at 45445e95. The manifest may flip to `checked-PASS`. Carry-forwards: amend the contract's `repo_root()` parenthetical in a separate criticality-gated commit (cycle 0 ruling 1); U9 / U10 re-confirm `code_root()` in the image; the unit table row should read "M1-M7, M9-M12 (M8 by U4/U5a/U11/U12)". No code was edited by the checker. The push on PASS (D-007) is not done from this worktree: it is a feature branch and the merge is the human's.
