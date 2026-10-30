# Verdict - mongo-store-u11f (checker A, secret-door focus)

**Cycle checked:** 0
**Verdict:** PASS (with warnings; no Block)
**Checker:** A of a dual check (CRITICAL rows M31-M36). Fresh context; did not read any other checker's verdict on this unit.
**Branch / code checked:** `feat/mongo-store-u11f`, code SHA `d5f996d3` (manifest `770d8699`), base `890f79a4`. Worktree `D:/autoTesting/.claude/worktrees/mongo-u11f`.
**Method:** re-ran every claim myself; adversarial probes through `put_credentials` called directly (as U8 will), planted my own mutants in a scratch copy. Synthetic canaries only; no `.env` value read or printed (only key NAMES of the repo `.env` and `projects/*/project.json` were listed).

## Commands run and results

| Command (cwd = worktree, `PYTHONPATH=<worktree>/src`, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`) | Result |
|---|---|
| `pytest tests/test_credential_store_u11f.py tests/test_credential_store_u11.py` | 52 passed |
| `pytest tests/test_secrets.py tests/test_ui_env_editor.py` | 39 passed, 1 skipped |
| `pytest tests/test_credential_store_u11_routes.py tests/test_env_loading.py` | 19 passed |
| `ruff check src tests scripts` | All checks passed! |
| `autotester.exe doctor > .work/doctor-chkA.txt` | exit 0, `doctor: clean` (only non-blocking D-087 advisories) |
| `python scripts/mutation_check.py qa/evidence/mongo-store-u11f/mutations.json --repo .` | `15/15 mutations killed` (each "actually failed" equals "claims to kill") |
| my own 15 mutants (scratch copy, section "Own mutants") | baseline 52 passed; 15/15 KILLED |
| line counts | `ui/env_editor.py` 292, `core/env.py` 300, `store/mongo_backend.py` 300, `ui/routes_project_edit.py` 272, `store/run_store.py` 236, `tests/test_credential_store_u11f.py` 241: all <= 300. The longest new function is `put_credentials` (about 16 lines): all <= 50. |

Imports verified to resolve to the worktree (`autotester.__file__` under `.claude/worktrees/mongo-u11f/src`).

## Secret door, adversarial (probe `scratchpad/probe/test_probe_a.py`, `test_probe_b.py`; nothing committed)

Every attempt below was made with `put_credentials` directly on the fake server (credentials area on mongo). For every refused row I asserted: no `secrets` document added, data-root tree hash unchanged, error text carries neither the value nor the URI canary.

**Refused, nothing written (all good):**
- Server keys in any case/shape: `autotester_approval_key`, `Anthropic_Api_Key`, `pathlynks_mongo_uri` (shape check, `env_editor.py:85-87`); `AUTOTESTER_APPROVAL_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `OLLAMA_API_KEY`, `OLLAMA_BASE_URL`, `PATHLYNKS_MONGO_URI` (`env_editor.py:101-102`). A batch `{"PL_OK": ok, <bad key>: ...}` left `PL_OK` unwritten too (checked whole batch first, `:238-239`).
- Unicode look-alike keys: fullwidth `Ａ`, dotted `İ`, long-s `ſ`, trailing newline, leading space, empty key: all refused by the ASCII `[A-Z_][A-Z0-9_]*` fullmatch.
- Values: empty (`:97-98`), `\n`, `\r`, tab, NUL, bell, DEL, ESC, NEL U+0085 (category Cc, `:99-100`), the exact Mongo URI, and the URI padded with ASCII/Unicode whitespace (NBSP, U+3000, U+2028 are removed by `str.strip`, `:103`).
- Another project's key: `zz` writing `{"ZZ_OK", "PL_PASS"}` raises `CredentialRefused`; `ZZ_OK` not written, `PL_PASS` still `p="pl"` and unchanged; case-variant slug `PL`, empty slug, and a URI value under a foreign key all refused.
- Non-string key/value (`None`, `5`, `b"x"`): `TypeError` raised at `_check_pair` before any write; nothing written (no named error, see W6).

**Accepted (every success recorded as a finding, none is a Block):** see findings F1-F6 below.

**Store values reach both redaction sites (confirmed, not just by the maker's tests).** `core/env.py::stored_secret_values` / `redaction_values` -> `providers/litellm_provider.py:62` (`stored = list(redaction_values({}).values())`, appended at `:63`) and `sources/adapters.py:146` (`Redactor(redaction_values(...))` in `_sanitize_pdf_reading`). I planted four mutants on these two sites in a scratch copy (keys instead of values; store list dropped from the return; `stored_secret_values` returning `{}`; adapters Redactor built from the file only); each turned a named test red (`test_the_litellm_guard_withholds_a_value_held_only_in_the_store` or `test_a_pdf_reading_is_scrubbed_of_a_value_held_only_in_the_store`). A 2-character stored value is also scrubbed (`[REDACTED]:PL_A@store`). Nothing in `src/` exports a store value into `os.environ` (grep of `stored_secret_values|resolve_credentials|redaction_values` callers: read/redact only).

## File-mode change: `is_server_key` now case-insensitive (`core/env.py:55-59`)

Callers: `core/env.py::load_repo_env` (`:209`) and `ui/credential_guard.py::refuse_server_key` (`:33`), plus the door (`env_editor.py:101`).
- `projects/*/project.json` secret key names (11 projects, names only): all declared keys are `UPPER_SNAKE_CASE`; none is lowercase or mixed case, none matches a provider key or `AUTOTESTER_*` in any case. No existing declared SecretRef is broken.
- Repo-root `.env` key names (names only, no values): 21 names, 3 non-upper (an email-like string, `url`, an email address); none is a server key in any case. So `load_repo_env` exports the same set as before for this machine.
- Logic: before the change a lowercase server-named key was already exported unless it was also a declared or prefixed project key; the change can only move a key from "project, not exported" to "server, exported" when it is both, which needs a lowercase declared key; the door and the shape check make such a declaration impossible for new credentials (UPPER only), and none exists today. Tests: `test_env_loading.py` (19 with routes), `test_ui_env_editor.py` pass untouched. Judged safe.

## Findings

Numbered; severity W = warning (does not block PASS), I = informational.

**F1 (W) The Mongo-URI-as-value check is exact equality only** (`env_editor.py:103`: `value.strip() == uri`). Accepted with an innocent key (`PL_NOTES`), nothing refused: URI with upper-cased scheme and host (`MONGODB://...@DB.EXAMPLE/`), host case change only, trailing slash dropped, `?retryWrites=true` / `?authSource=admin` appended, URI embedded in text (`x <uri>`), `host:27017` added, URI with a zero-width space (U+200B) or BOM (U+FEFF) before/after, the bare password canary, and `user:<password>@host`. M36's own falsifier is key-based (`AUTOTESTER_APPROVAL_KEY`, migrate dry-run) and is closed, so this is hardening beyond the contract, but it is not a closed class. Impact is bounded: the store is behind the IP allowlist, a stored URI is added to the `Redactor` (`store/mongo_routes.py:195`), and the value is shown only to `credentials.view`. Suggest (follow-up, not required): compare after `urlsplit`/case-folding the host and refuse any value that contains the URI password or the full URI as a substring.

**F2 (W) Door accepts any UPPER_SNAKE key; namespace and declaration are only enforced by the route** (`put_credentials`, `env_editor.py:231-246`). Direct calls stored `PATH`, `HTTP_PROXY`, `NODE_OPTIONS`, `MONGODB_URI`, `AWS_SECRET_ACCESS_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `AZURE_API_KEY`, `GROQ_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `_`, `__PROTO__`. Harmless today because store values are never exported (see above) and `resolve_credentials` yields only keys the project declares (`core/env.py` `usable = ... k in declared`). Two consequences for U8 (migration calls the door directly, bypassing `ui/credential_guard.py::refuse_foreign_key`): (a) a squat is possible: `put_credentials("evil", {"PATHLYNKS_PASS": ...})` is accepted, after which project `pathlynks` is refused with "belongs to another project"; (b) provider-style names outside `PROVIDER_KEYS` (`core/env.py:34-38`: the repo's own list) are not "deployment secrets" for M36. Recommend U8 filter by project namespace/declared keys before calling the door.

**F3 (W) Whitespace-only and invisible-character values are accepted.** `" "`, `"   "`, NBSP, ZWSP, bidi override U+202E, line/paragraph separators U+2028/U+2029 (categories Zs/Zl/Zp/Cf are not `Cc`, `:99`) are stored as credentials. Also a lone surrogate (`"a\ud800b"`) and a 5 MB value pass; the lone surrogate would make real BSON encoding raise a non-named error (the fake does not). Nothing is written wrongly or leaked; this is input hygiene. A leading/trailing space in a real password must stay legal, so only the whitespace-only case is worth refusing.

**F4 (W, carried from U11, unchanged by this unit) Other-project protection is check-then-write, not atomic.** `env_editor.py:240-245`: `find_one` then `replace_one({"_id": key}, ..., upsert=True)` (`_put_doc :226-228`). I simulated the interleaving (project `zz`'s check saw nothing, `pl`'s write already landed): the document ended as `('PL_PASS', 'zz', <zz value>)`. The window is narrow and needs two concurrent writers, but M31(d) rests on the check alone. A fix needs no new verb: filter the write on `{"_id": key, "p": slug}` with `upsert=True` so a foreign owner raises `DuplicateKeyError` on `_id`.

**F5 (W, carried, unchanged) A multi-key batch is not atomic on a mid-batch outage.** Validation of the whole batch happens first (`:238-243`), but the writes are a loop (`:244-245`); forcing the second `replace_one` to raise left `PL_A` stored and `PL_B` absent, then `StoreUnavailable`-class error. Not a leak (fail closed, M32 holds: nothing written to `.env` or disk); the caller sees a partial save. The manifest does not claim this closed.

**F6 (I) Non-string inputs raise bare `TypeError`** at `_check_pair` (`:88`: `"\n" in value`) rather than `InvalidEnvValue`; refused before any write. A route that passes form strings never hits it.

**F7 (I) Undeclare double-fault wording.** `routes_project_edit.py:262-271`: if `restore_credentials(held)` itself raises after a failed `save_project`, the original exception is chained and the value stays dropped (safe side, the manifest's note 4). `snapshot_credentials` reads by `_id` only (`env_editor.py:279`), while `drop_credentials` deletes with `p` (`:270`); restore after a failed save would re-put a document that a concurrent writer owned. Race only; no defect found in the single-writer paths, which `test_a_store_outage_on_undeclare_is_a_503_and_nothing_changed`, `test_a_failed_project_save_on_undeclare_puts_the_stored_value_back` and `test_redeclaring_an_undeclared_key_does_not_revive_the_old_value` pin and my mutants `undeclare-no-drop` / `drop-delete-without-p` kill.

## Criteria judgment (this unit)

| Criterion | Judgment |
|---|---|
| M31 plain, one door (no `cryptography`, no `secret_box`, `_put_doc` only writer) | holds; the door now runs the shape check itself (`:239`), `validate_env_values` (`:122-123`) agrees (probe `VALIDATE` and `test_the_validation_only_gate_agrees_with_the_door`) |
| M32 no key dependency, fail closed | holds; undeclare with store down is a 503 with declaration and value intact (test) |
| M33 resolution/scoping | unchanged, `test_secrets.py` passes untouched |
| M34 redaction covers store values | holds at both formerly unpinned sites; mutants killed |
| M35 UI surface | file-mode `.env` writes byte-identical (`_check_pair` unchanged, `:85-89`; `test_ui_env_editor.py` passes) |
| M36 deployment secrets never stored | key-based falsifier closed in every letter case; value-based variants see F1 |
| M37 lifecycle | undeclare store-first with restore on failed save (`routes_project_edit.py:262-271`); mutants killed |
| One client, indexes once; `blob_store` | `rearm()` (`mongo_backend.py:246-247`) and `run_store.py:126-136` match the claims; mutants killed |

No `src/`/`tests/` file was edited by this checker. The probe files and the mutant sandbox live under the session scratchpad only.

## Residuals for the maker (none blocks the PASS)

1. F4: make the foreign-owner refusal atomic with the write (`{"_id": key, "p": slug}` upsert filter).
2. F2: U8 must filter keys by namespace/declaration before calling `put_credentials`.
3. F1/F3: optional hardening of the URI and whitespace-only checks; F5: batch atomicity if a caller needs all-or-nothing.
