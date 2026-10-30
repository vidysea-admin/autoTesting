# Verdict - mongo-store-u2 (checker A, functional/contract)
Verdict: PASS
Cycle checked: 0
Head tested: 0b19a96e (feat/mongo-store-u2; code commit 42e1fae1, base 0f89becc). Unit U2, normal (not dual). Criteria judged: M13, M14, M15 (File + InMemory legs), M17, M19 (File + InMemory legs).
Class: all LOCAL. No Mongo connection, no `.env` value read. Worktree `.venv`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, at most 2 test files per call, `env -u ANTHROPIC_BASE_URL`.
I did not trust the manifest: every command below was re-run by me. `filestore.py` on master 3400132f is byte-identical to base 0f89becc (`git diff --stat` empty), so master's file is the "old" side of the differential.

## Result per criterion
| Crit | Result | Evidence |
|---|---|---|
| M13 backend is configuration | PASS | `store_selection` `filestore.py:171-183` (blank/unset = file, unknown backend or area raises `StoreSelectionError`), `_backend :194-197` (only `file` wired; `mongo` raises "not wired"), `validate_store_env :200-205`, called at `ui/app.py:64`. No `pymongo`/`gridfs`/`bson` text in `filestore.py` (grep empty); my own fresh interpreter after importing the new module: `pymongo gridfs bson in sys.modules = False False False`. `test_state_selection.py` passes (105-test pair). |
| M14 signatures unchanged | PASS | `inspect.signature` of all eight old public functions (`write_text write_bytes write_json read_json read_jsonl append_jsonl delete_jsonl_row upsert_jsonl`) plus `_atomic_write` (still imported by `stages/orchestrate_checkpoint.py:24`) vs master: all SAME. `test_state_signatures.py` 52-test pair green. No file under `src/autotester/store/` other than `filestore.py` and `mongo_guard.py` changed. Behaviour narrowings are in findings 1-4; none touches a signature. |
| M15 (File + InMemory) | PASS | `test_state_backend_contract.py` + `test_state_wrappers.py` green. Mongo leg is U4's. |
| M17 keys are safe | PASS | `safe_key` `core/safe_names.py:76-86`; contract suite refuses `..`, `/x`, `C:/x`, `a\b`, NUL, empty segments on every method before I/O. |
| M19 one winner | PASS | I looped the falsifier the manifest left to me: 200 repetitions x 16 threads, `create_exclusive` and `put_if` (same expected sha), File and InMemory: 0 violations each. |

Cap: `wc -l src/autotester/store/filestore.py` = 300 (cap 300 holds). `mongo_guard.py` = 300. ruff and doctor clean.

## Commands run and outputs
```
pytest tests/test_state_backend_contract.py tests/test_state_selection.py    -> 105 passed
pytest tests/test_state_signatures.py tests/test_state_wrappers.py           -> 52 passed
pytest tests/test_mongo_guard_chain.py tests/test_mongo_guard_spec.py        -> 8 passed
pytest tests/test_mongo_guard.py tests/test_mongo_guard_surface.py           -> 40 passed
pytest tests/test_store.py tests/test_store_crawl.py                         -> 28 passed
pytest tests/test_team_store.py tests/test_bug_store.py                      -> 79 passed
pytest tests/test_bug_store_concurrency.py tests/test_bug_store_hardening.py -> 31 passed
pytest tests/test_backup_restore.py tests/test_crawl_guidance_seam.py        -> 31 passed, 1 skipped
importer-heavy, added by me:
pytest tests/test_ui.py tests/test_ui_cases.py                               -> 21 passed
pytest tests/test_ui_case_management.py tests/test_ui_crawls.py              -> 27 passed
pytest tests/test_ui_intake.py tests/test_ui_auth_envkeys.py                 -> 47 passed
pytest tests/test_ui_crawl_approval.py tests/test_ui_crawl_login.py          -> 18 passed
pytest tests/test_ui_env_editor.py tests/test_ui_bench_inputs.py             -> 35 passed, 1 skipped
pytest tests/test_cli_orchestrate.py tests/test_cli_orchestrate_resume.py    -> 8 passed
ruff check src tests scripts                                                 -> All checks passed!
autotester doctor (> .work/doctor-chkA.txt)                                  -> exit 0, "doctor: clean" (3815 non-blocking D-087 advisories)
scripts/mutation_check.py qa/evidence/mongo-store-u2/mutations.json   --repo . -> 22/22 mutations killed
scripts/mutation_check.py qa/evidence/mongo-store-u2/mutations-b.json --repo . -> 10/10 mutations killed
scripts/mutation_check.py qa/evidence/mongo-store-u2/mutations-c.json --repo . ->  5/5 mutations killed
```
(`tests/test_orchestrate_checkpoint.py` and `tests/test_cli.py` do not exist; collected 0 items, substituted the two files above. Full suite not run, per the low-memory rule.)

## Old-vs-new byte differential (the check the maker did not have)
Scratch harness under `.work/chkA-bytediff/` (deleted afterwards): loaded master's `filestore.py` as a separate module next to the branch's, with `AUTOTESTER_STORE` unset, ran 40 identical steps against two fresh roots (write_text/bytes/json with unicode, CRLF and binary; append x3; upsert replace/append/by-property; delete hit/miss/missing-file; read missing/bad/malformed; hand-edited non-canonical rows; int-keyed model; file outside the root; relative path; `..` path) and compared return values, exception type/message, and every output file byte by byte.
Identical: all canonical-row writes and reads, atomic writes, append bytes, text newline translation, bytes writes, outside-root and relative-path writes, missing-file behaviour. 13 differences, all explained by findings 1-5 below.

## Findings (numbered; none blocks PASS)
1. **Flagged by maker, accepted.** `delete_jsonl_row` by a property is refused: `filestore.py:280-281` raises `ValueError("'derived' is not a stored field of Row")`; master returned True (`getattr` on the item). Both in-tree callers pass the default `id`: `store/project_store.py:123`, `:285`. A misspelt key also changes from `AttributeError` to `ValueError`. M14 covers signatures, which are unchanged. Acceptable; pinned by a test.
2. **Flagged by maker, accepted.** Malformed-row number counts non-blank rows (`_parse_rows :222` over `rows()`): a file `{ok}`, blank, `{ok}`, `{oops` reports `:3` on the branch, `:4` on master. Message shape otherwise identical. Cosmetic.
3. **NOT flagged. Byte equivalence holds only for canonical rows.** Master's `upsert_jsonl` and `delete_jsonl_row` re-serialised every surviving row through the model (adding defaults, dropping nulls, normalising spacing and key order, dropping blank lines). The branch keeps surviving rows verbatim (`upsert_row`/`delete_row`, `filestore.py:155-166`). Differential: a hand-edited file with `{"n": 1,  "id": "h1"}` then upsert of `h3` leaves the h1 row untouched on the branch, normalised on master; a delete gave `{"id":"h3"}` vs master's `{"id":"h3","n":0}`. Files written only by this code are canonical, so output is identical there. Reads are unaffected. Manifest judgement call 3 said bytes were not diffed; now they are, and this is the residual. Verbatim preservation is arguably better behaviour; record it, do not fix.
4. **NOT flagged. Key match is on the stringified stored JSON, not the typed value** (`row_matches :50-56`, `upsert_jsonl :292-299`, `delete_jsonl_row :284`). Effects against master: (a) `delete_jsonl_row(IntRow, "1")` on an int `id` now deletes (master: no-op, False), a broadening; (b) `upsert_jsonl` on a float or datetime key whose stored text differs from the dump form (`{"id":1}` vs `1.0`; `+00:00` vs `Z`) now appends a duplicate where master replaced (probe: both cases). Not reachable today: every in-tree key field (`id`, `slot_id`, `flow_id`) is `str` (`schema/case.py:26,106`, `issue.py:22`, `crawl.py:126`; call sites `project_store.py:113-157,280`, `run_store.py:40,62`, `crawl_store.py:75`, `request_store.py:43`) and rows are written by the same dumper. Latent only for a future non-str key. Suggest U4 document the string-key assumption or add a typed-key test.
5. **Intended (M17).** A path under the root containing `..` (`root/projects/p/../q/dd.txt`) now raises `UnsafeName`; master wrote it. No in-tree caller builds such a path.
6. **Manifest wording.** It says "the ten public functions" but lists eight; the eight are what exists on master and all eight are unchanged. New public names (`text_sha`, `row_matches`, `store_selection`, `area_of`, `backend_for`, `validate_store_env`, `StateBackend`, `FileBackend`, `StoreSelectionError`) are additions, not changes.
7. **Observation for U3/U4, no U2 criterion.** `_route :212-219` sends any path not under `repo_root()` (for example `ProjectPaths(slug, root=other)`) to a plain file regardless of `AUTOTESTER_STORE`. Fine for the file backend; the M16/U3 sweep must not assume every `ProjectPaths` path reaches the selected backend.
8. **Not a defect.** The `mongo_guard.py` changes (M9 chain fix) are behaviour-preserving; its four test files pass; the file stays at 300 lines. Not judged here (U1).

## Decision
All five assigned criteria pass on the File and InMemory legs, signatures are unchanged, the cap holds, ruff and doctor are clean, all 37 mutants are killed, and the old-vs-new differential shows identical bytes for canonical data. Findings 3 and 4 are residual behavioural narrowings the manifest did not list; neither is reachable with today's data and neither contradicts a criterion text. PASS.
