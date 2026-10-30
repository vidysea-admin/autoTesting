# Verdict - mongo-store-u11

**Verdict:** PASS (checker A of a dual check; 0 Block, 4 Warnings)
**Cycle checked:** 0
**Checker:** chk-mongo-u11-a (fresh, independent; read no other checker's verdict on this unit)
**Code SHA checked:** `a2d77b9e` on `feat/mongo-store-u11` (base `4df612ca`)
**Criteria judged:** M8 (store half), M31, M32, M33, M34, M35, M36, M37, M47 (no-crypto half); the U11 row. Focus: secret containment. All values below are synthetic canaries; no `.env` value was read or printed.

## Findings

1. **M31 one door holds.** `credential_collection` is the single place `secrets` is named (`src/autotester/core/env.py:244`). The only write of a credential document is `_put_doc` -> `replace_one` (`src/autotester/ui/env_editor.py:210`); `env_editor.py` has no `insert_one`/`update_one`. `grep -rn '"secrets"\|credential_collection\|default_store' src` shows only `core/env.py`, `ui/env_editor.py` (read side + door), the closed `COLLECTIONS` name (`store/mongo_guard.py:39`) and the owner map (`store/mongo_routes.py:43`); no state-key route maps to `secrets`. Doc shape is `{_id,p,value,updated_at}`, plain (D-123).
2. **M47 / M31(c) no crypto, no key.** `grep -rniE "fernet|aesgcm|pbkdf2|hkdf|secret_box|(import|from) cryptography" src` -> only the unrelated `auth/passwords.py` scrypt line; `cryptography` absent from `pyproject.toml`; `git diff 4df612ca HEAD --stat -- pyproject.toml uv.lock` is empty; `AUTOTESTER_APPROVAL_KEY` is not referenced in `core/env.py` or `ui/env_editor.py` (M32). Unset/empty/rotated key tests pass.
3. **M8/M34 gate rebuilt after a door write, no restart (my probe).** Build the cached gate (`put`), `put_credentials("pl", {"PL_PASS": V})`, then through a fresh `default_backend()`: `put` (body), `put` (key name), `create_exclusive`, `put_if`, `append_text`, `append_row`, `replace_rows` all raise `StoreSecretRefused`; whole fake DB holds V exactly once. `MongoBlobStore.put` raises `BlobRefused` for V in a body typed `text/plain`, `application/ndjson`, `application/json`, empty type, and in the content type and the key. `litellm_provider._env_secret_values()` is `[]` before and contains V after the write. `_sanitize_pdf_reading` with a `DocumentReading` carrying V returns text and reading without V. Error pages (`/projects/pl/<V>` -> 404) do not echo V (`error_pages._repo_redactor` goes through `SecretStore.load`, so it covers every stored value as shadow).
4. **Cross-project isolation (slug/prefix tricks).** Project `pathlynks` stores `PATHLYNKS_PASS`. `resolve_credentials({}, "pathlynksx", {"PATHLYNKS_PASS"})` -> `usable == {}` and V sits in `shadow` (masked, not resolvable); `put_credentials("pathlynksx" | "PATHLYNKS", {"PATHLYNKS_PASS": ...})` -> `CredentialRefused`; `SecretStore.load` for `pathlynksx` still refuses a prompt carrying V; the owner resolves V. Resolution filters on exact `d.get("p") == slug` (`core/env.py:269`).
5. **M36 / batch atomicity.** Mixed batches (`AUTOTESTER_APPROVAL_KEY`, `PATHLYNKS_MONGO_URI`, `GEMINI_API_KEY`, another project's key, an empty value, each after a valid key) raise `CredentialRefused` and `rig.secrets()` still holds only the pre-existing doc: validation loop (`env_editor.py:220-227`) completes before the write loop (`:228`). Error text and `repr` for four failure kinds contain neither the submitted nor the stored value.
6. **Failure and surface.** Store down on an HTML request ends in the themed 503 (outer `_StoreDownGate` catches the `StoreDown` raised inside the 404 handler); JSON request keeps its 404. Neither body carries V. Route twins (503 on save, no file written) pass.
7. **M33 order.** `resolve_credentials` layers file, then declared process-env keys, then this project's own stored docs; every value a higher layer hides, and every other project's doc, goes to `shadow` (`core/env.py:259-278`). Matches "store first, then process environment". The file-mode asymmetry (env not a layer) is documented and pinned by `test_with_the_store_off_everything_is_the_env_path`. B5-B9 tests unedited and pass.
8. **Layering and one-concept: acceptable, not ideal.** The contract's Module note names `core/env.py` for resolve/write; the write door is in `ui/env_editor.py` because `core/env.py` is at 298/300. `ui/env_editor.py` was already "the one legitimate WRITE path to `.env`", so the door is the same concept in the same module, and no `*_v2` module was added. Cost: `stages/role_onboarding.py` (a stage) imports a UI module (`:30`, pre-existing import line, now carrying `save_credentials`), and `core/env.py` lazily imports `store/mongo_routes` (core -> store). Accepted; flag for U8, which must call `put_credentials` and not name `secrets`.
9. **M37.** Every delete carries `p` (`env_editor.py:253,254,256`); `undeclare_secret` drops the value (`routes_project_edit.py:263`); `_commit` snapshots before and restores in a `finally` (`routes_role_accounts.py:216,224-228`). Maker's note 3 verified: no project-delete or role-account-remove route exists (`accounts_submit` merges by id only), so the "role account" and "project" clauses are met by the primitive `drop_credentials(slug, None)`, not a route. Accepted.
10. **Size rules.** Doctor clean; touched files 278/298/299/290/300/295 lines.

## Warnings (none falsifies a criterion; all should be closed before the credentials area flips at G1)

- **W1. Two M34 redaction sites are not pinned by any test.** My mutation spec (`extra_mut.json`) against the unit's own two test files: `litellm_provider._env_secret_values` ignoring the store -> **SURVIVED**; `sources/adapters._sanitize_pdf_reading` ignoring the store -> **SURVIVED** (0/2 killed). Behaviour is correct today (finding 3), but the maker's "26/26" does not cover them and they were written without red-first tests. Add one test each (the litellm guard on a stored value; a PDF reading carrying one).
- **W2. `put_credentials` does not validate shape.** Direct calls store key `"lower case"`, value `"a\nb"`, and key `"autotester_approval_key"` (lower case slips `is_server_key`, `core/env.py:55`). Only `save_credentials` runs `_check_pair`. Not reachable from a UI route today, but U8 will call `put_credentials` directly: run `_check_pair` inside it. Also `save_credentials("pl", ..., {"PL_URL": <Mongo URI value>})` stores the URI under an innocent key name (M36 is names only; consider refusing a value equal to the configured URI).
- **W3. Check-then-write race and multi-instance staleness.** `put_credentials` does `find_one` (`:225`) then `replace_one({"_id": key}, ..., upsert=True)` (`:210`) with no `p` in the filter, so two writers for one key can overwrite across projects; and the cached secret gate refreshes only on this process's own write (maker note 4). Both are harmless at `--max-instances 1`; filter the replace on `{"_id": key, "p": slug}` and state the single-instance limit in DEPLOY.md.
- **W4. Container diagnostics do not know store values.** `scripts/container_diagnose_lib.sh:98,198` masks bundles from `core/redact_cli.py --values-from-env` (`.env` only). With the credentials area on mongo, a stored value in a container log is not masked there (M34 "logs"). Out of the unit's file list; needs an owner.
- **Observation outside U11 (base bug, not introduced here).** `store/run_store.py:132,134` reads `mongo_backend.URI_ENV`, which does not exist at `4df612ca` either (`git grep URI_ENV 4df612ca -- src/autotester/store` shows only `MONGO_URI_ENV`): `blob_store()` raises `AttributeError` when `blobs=mongo`. Found by my blob probe; belongs to U5b/U9 before the blobs flip.

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u11`)

```
uv run pytest tests/test_credential_store_u11.py tests/test_credential_store_u11_routes.py -o addopts=  -> 32 passed
uv run pytest tests/test_ui_env_editor.py tests/test_secrets.py -o addopts=                            -> 39 passed, 1 skipped
uv run pytest tests/test_role_onboarding.py tests/test_ui_credential_exemption.py -o addopts=          -> 20 passed
uv run ruff check src tests scripts                                                                    -> All checks passed!
uv run autotester doctor  (redirected to a file)                                                       -> doctor: clean (advisories only), exit 0
uv run python scripts/mutation_check.py qa/evidence/mongo-store-u11/mutations.json                     -> 26/26 mutations killed
uv run python scripts/mutation_check.py <scratch>/extra_mut.json (2 extra mutants)                     -> 0/2 killed (W1)
my probe file (scratchpad, not committed; 9 tests via -p conftest): writers, blobs, litellm/pdf, slug tricks, batch, errors, 404 under outage -> all assertions held; prints recorded W2
```
Not run: full suite, `tests/test_role_port_authz.py` (5 known environmental failures), auth envkeys tests (U11 does not touch `auth/`).

## Closing

No Block: the secret containment claims hold under planted canaries. Dual check: a second checker must still judge; W1 should be closed (or accepted by the closing checker) before the unit is marked `checked-PASS`.
