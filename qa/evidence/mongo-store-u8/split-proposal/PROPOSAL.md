# mongo-store U8 split proposal (maker mongo-u8, fix cycle 0) -- STOP

## Why
D-122/D-123 approve exactly one new module for U8: `cli_store.py`. The doctor caps a file at 300
lines (`doctor.py` MAX_FILE_LINES, counted with `len(read_text().splitlines())`) and a function at
50. U8 is four jobs (state migrate, auth import, credential import, verify + report + commands).
The state half plus the auth half plus the credential half are already 351 lines
(`cli_store.draft.py` in this folder) with verify-approvals, the report renderer, the apply/dry-run
driver and the two typer commands still unwritten (estimated 450-500 lines total). Compaction
cannot remove 40 percent without dropping criteria (M43 auth verify, M45 credential filtering).
Raising the cap or exempting the file would weaken an enforcement rule, so this is a split, as in
D-126 for U6b/U7.

## Proposed modules (need an authorizing D-entry with Approved-by: Umesh)
| File | One job | Est. lines |
|---|---|---|
| `src/autotester/cli_store.py` (already approved) | the `store` typer sub-app: `migrate`/`verify` commands, report rendering, exit codes | ~150 |
| `src/autotester/store/migrate_state.py` | scan/classify/compare/copy of the file tree (M25 exclusions, approvals byte-identical, blobs before documents) | ~170 |
| `src/autotester/auth/migrate_auth.py` | SQLite read-only reader and the importer into the U6b store through `MongoAuthStore.transaction()` (ids, allocators, groups, sessions opt-in) | ~120 |
| `src/autotester/store/migrate_creds.py` | repo-root `.env` to the U11 door: declared-SecretRef filter before the door, deployment keys excluded, never prints a value | ~70 |

All four stay driver-free (pymongo only lazily, M13). Registration in `cli_subapps.py` is one line.

## Draft status
`cli_store.draft.py` (this folder, NOT under src so doctor stays green) holds the working design of
the state, auth and credential halves. It is untested. Once the D-entry lands the maker splits it
along the table above, writes tests (TDD on fake_mongo + tmp dirs), runs mutation_check and writes
`qa/manifests/mongo-store-u8.md`.

## Not done
Tests, registration, mutation evidence and the manifest are not produced; no Mongo contact, no .env
value read, nothing outside this worktree touched.
