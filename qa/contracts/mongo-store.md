# Contract — mongo-store: AutoTester's own state in one MongoDB database, with encrypted credentials and browser sessions (D-120, D-121, D-122)

**Covers:** the units U1-U12 of the mongo-store build (table below). Criteria `M1`-`M48`. **Owner:** /checker. **Status:** ACTIVE (2026-10-29).
Creation is human-approved: Umesh, D-120 (state moves to one Mongo database `autotester`), D-121 (name in a committed config file), D-122
(supersedes the D-002 storage clause; allowlist-of-one fence; credentials and Chromium sessions move into the store, encrypted).
**Criticality:** HIGH overall. Criteria marked **CRITICAL** are judged by a **dual check** (two independent fresh checkers, D-100); the
units that own them are marked dual in the unit table.
**Source:** the design read `.work/mongo-store-design.md` (analyst, 2026-10-29, sections 1-12), **amended by D-120, D-121 and D-122, which win
on any conflict** (see "Amendments applied").
**Serves:** `docs/intent.md` has no storage outcome. These criteria serve the outcomes whose delivery depends on state surviving a deploy or
staying private: O2/O12 (regression keeps running; evidence survives), O3 (evidence), O7 (credentials never leak; the Mongo URI is one), O10
(bug events), O13-O15 (auth, shares, groups). The boundary criteria also cite the standing hard boundary of D-120 (write only inside `autotester`).
**Depends on (cite, never restate):** `core-invariants.md` C5/C6/C7 (C5 and C6 are amended for the Mongo backend, see M48), `db-assert.md`
D1-D4, `browser-and-secrets.md` B5-B9, `manual-login.md` ML3, `ui-run.md` RU5, `auth.md` AU7/AU9/AU11/AU21, `failure-bundle.md` FB1-FB3,
`hosting.md`, `consent.md` (signed RunApproval, D-018).

## Amendments applied (where D-120/D-121/D-122 change the design read)

| Design read said | Ruling | Effect here |
|---|---|---|
| `product_databases` list in config; refuse a name in it; `connect_read_only` registry (design 4.0, 4.2 item 3, M4, M10) | D-122 item 3: **allowlist of one**, no list to maintain; every other database is foreign | M4 refuses three cases only (forbidden name, URI-path clash, unmarked non-empty database). No `product_databases` key exists; an extra key is refused by `extra="forbid"`. The runtime registry is dropped; M10 keeps only the read-side refusal of the store database. |
| Credentials, `.env` values and `profiles/` stay on disk (design 2.7, Q2) | D-122 item 4: project and role login values and Chromium `storage_state` sessions move into the store, **encrypted at rest** | New CRITICAL groups M31-M37 (credentials) and M38-M40 (sessions). Design M8 ("no secret value in a document") is narrowed: only a sealed envelope written through the secret door may carry a secret. |
| D-002 vs D-120 open (Q1); new-file list awaiting OK (Q9); config home (Q13) | Resolved by D-122: D-002 storage clause superseded; eight modules approved; `pyproject.toml` `[tool.autotester.store]` | No open decision in the guard group. Any module **not** in D-122's list (see M31 note) needs a new authorizing D-entry first. |
| Q3, Q5, Q6, Q8, Q11, Q12, scaling (design 12) | Defaults adopted by the checker seat on 2026-10-29 (no conflict with D-120..D-122) | M25 (CEO-bench list file-only; teaching-video chunks derived and not stored; `crawl_summaries/` still committed), M22 (KG split above 4 MB), M47 (hand-written fake, no `mongomock`; human-run live smoke on a `t_` collection, never CI), M28 (`--max-instances 1` until CAS lands). |
| Q4 (replica set?), Q7 (TTL), Q10 (dedicated role) | Not answered; not blocking | The backend works **without** multi-document transactions (CAS plus unique indexes, M20, M29). Blob cache cap defaults to 512 MB LRU (M25). No TTL on `audit_log`/`run_traces` in this build. A server-side `readWrite`-only Mongo role is a recommended follow-up, **not** a criterion; the code fence (M1-M12) is the only fence until then and must be tested as such. |

## Verification classes

`LOCAL` = the checker runs it on the dev host with the in-repo fake client; nothing connects to Mongo and no network is used. `SERVER-GATED`
= needs the real server; judged by a human at G1 and never by CI or by a checker connecting. Every criterion below is `LOCAL` unless it says
otherwise. A checker never connects to Mongo (standing rule); where a criterion needs "the server", the fake stands in and the row says so.

## Write fence (allowlist of one) — CRITICAL; every row here is dual-checked

The Mongo user can write to databases other than `autotester` (design F2). The code is therefore the only fence, so it is tested adversarially.

- **M1 — One source for the database name.** The name is `[tool.autotester.store].database` in `pyproject.toml` (value `autotester`, D-121,
  D-122 item 2), read **once** per process through `schema/store_config.py::StoreConfig` (`extra="forbid"`, `frozen=True`, required key, no
  default). It is not read from the environment, `.env`, the URI path, a CLI flag or any argument, and there is no environment override of the
  config path. The config path resolves from the **code** tree (`core/paths.py::code_root()`, new; `repo_root()` falls back to it when
  `AUTOTESTER_ROOT` has no `pyproject.toml`), because on Cloud Run the data root is `/data`. `store/mongo_guard.py` obtains its handle only as
  `client[cfg.database]`. **Falsifier:** set `AUTOTESTER_DB`, `AUTOTESTER_STORE_DATABASE`, `MONGODB_DB` and `AUTOTESTER_ROOT=<dir with no
  pyproject>` to other values; the spy client still sees exactly `{cfg.database}`. *LOCAL.* serves: O7, D-121 · CRITICAL · judges: U1
- **M2 — No API accepts a database name.** No public function, method or constructor in `store/mongo_guard.py`, `store/mongo_backend.py`,
  `store/blobs.py`, `cli_store.py` has a parameter named `db`, `database` or `db_name`; `GuardedStore(uri, "x")` and
  `GuardedStore(uri, db_name="x")` raise `TypeError`. **Falsifier:** `inspect.signature` over the whole public surface of those four modules
  finds a parameter with one of the three names, or the two constructor calls construct. `browser/db.py::connect_read_only` is exempt by
  design (it is the read side). *LOCAL.* serves: O7 · CRITICAL · judges: U1, U4, U5a, U8
- **M3 — One door, found by AST scan.** A scan of `src/` and `scripts/` finds `MongoClient(`, `get_database`, `get_default_database`,
  `list_database_names`, `drop_database`, `import pymongo` / `import gridfs`, or a subscript on a client-bound name in **exactly two files**:
  `browser/db.py` (read-only) and `store/mongo_guard.py`. Baseline on master `4de46d52`: one site, `browser/db.py:37-42`. **Falsifier:** add
  `MongoClient(...)` to any third file under `src/` or `scripts/`; the scan test goes red. *LOCAL.* serves: O7 · CRITICAL · judges: U1
- **M4 — Startup refuses the unsafe cases before any client access (D-122 item 3).** Construction of the store raises `StoreConfigError`
  (or pydantic `ValidationError` for model-level cases) with **zero** recorded client accesses when: (a) the configured name, case-folded, is
  `admin`, `local` or `config`; (b) it is not a plain identifier (`""`, `a.b`, `x y`, `$x`, `a/b`, 64 characters, non-ASCII) — pattern
  `^[A-Za-z][A-Za-z0-9_-]{0,37}$`; (c) it equals the database in the URI path (`pymongo.uri_parser.parse_uri(uri)["database"]`, parsing
  only, case-folded); (d) the `[tool.autotester.store]` table is missing, lacks `database`, or has any other key (including a leftover
  `product_databases`); (e) the database already exists, holds one or more collections, and has **no store identity marker** (M11) — that is
  somebody else's database. **Falsifier:** each of the above, fed to the spy client, either constructs, or touches the client before raising.
  The check in (e) uses only `list_collection_names()` on the **configured** database, never `list_database_names`. *LOCAL.* serves: O7,
  D-122 item 3 · CRITICAL · judges: U1
- **M5 — The URI's database is never used for writes.** With non-clashing URIs `mongodb://h/`, `mongodb://h/scratch`,
  `mongodb://h/?authSource=admin`, a spy whose `__getitem__` and `get_database` record every name sees **only** `cfg.database` across the
  entire workload: every collection verb, GridFS put/get/delete, the marker, migration `--apply`, ping. **Falsifier:** any other name in the
  recorded set. *LOCAL.* serves: O7 · CRITICAL · judges: U1, U4, U5a, U8
- **M6 — Closed verb set.** `GuardedCollection` exposes exactly `find`, `find_one`, `count_documents`, `insert_one`, `replace_one`,
  `update_one` (operators `$set`, `$setOnInsert`, `$inc` only; `generation` and other immutable fields are never in the allow-list),
  `delete_one`, `delete_many` (the filter must contain `p` or `k`), `create_index`. `GuardedStore` exposes `collection`, `bucket`, `ping`
  (plus the marker and `list_collection_names`-for-the-configured-db used by M4(e)/M11). No `aggregate`, `command`, `bulk_write`, `watch`,
  `drop*`, `rename`, `with_options`, `get_database`, `client`, `database`, and no attribute reachable through `__getattr__` or a `__dict__`
  walk returns a pymongo object. `collection(name)` accepts only names in the closed `COLLECTIONS` set (exception: M47 `t_` smoke).
  **Falsifier:** the public attribute set differs from the frozen list, or `$out`, `$merge`, `mapReduce` or a raw command is reachable.
  *LOCAL.* serves: O7 · CRITICAL · judges: U1, U4
- **M7 — Insert-only collections.** `approvals`, `approval_revocations`, `bug_events`, `delivery_records` expose no replace, update or delete
  verb (D-018/AT-110: an approval is never edited). **Falsifier:** calling any of those verbs on those collections does not raise.
  *LOCAL.* serves: O7, O10 · CRITICAL · judges: U1, U4
- **M8 — No secret value in a stored document, except a sealed envelope.** Every `put`/`append_row`/`upsert_row`/blob metadata write passes
  `Redactor.assert_clean`, built from every repo `.env` value **and every value held in the credential store** (M34), including the Mongo
  URI. A document or GridFS metadata containing one is refused with a named error and nothing is written. The **only** carrier of a secret is
  the sealed envelope of M31/M38, written through the secret door into `secrets` / `browser_sessions`, and it holds ciphertext, never the
  value. **Falsifier:** plant a known credential value in a case body, a trace row, an auth audit row and GridFS metadata; any write succeeds,
  or a dump of the whole fake database (all collections, all GridFS chunks) contains the plaintext. *LOCAL.* serves: O7 · CRITICAL · judges: U4, U5a, U11, U12
- **M9 — The URI is never logged or echoed.** Not in logs, exception text, `StoreUnavailable`, the UI 503 page, the dry-run report, or any
  `autotester store *` output (mirrors `db-assert.md` D2 and `tests/test_db.py:84`). **Falsifier:** a canary URI with a distinctive password
  appears in captured stdout, stderr, log records or response bodies across a failing ping, a failing write and a failing migrate.
  *LOCAL.* serves: O7 · CRITICAL · judges: U1, U8, U9
- **M10 — Read side refuses the store database.** `browser/db.py::connect_read_only` raises when `db_name` equals `cfg.database` (case-folded),
  so a test case cannot aim the read-only DB assertion at `auth_users`, `auth_sessions`, `secrets` or `browser_sessions` and turn them into
  `Evidence`. **Falsifier:** `connect_read_only(uri, "Autotester", "auth_users")` returns a handle. *LOCAL.* serves: O7, O3 · CRITICAL · judges: U1
- **M11 — Store identity marker.** On first write to an empty configured database the backend inserts `server_state` `_id="marker"` with
  `{database, created_at, schema_version}` (insert-only by `create_exclusive`). At startup a marker whose `database` differs from the configured
  name (a restored or renamed database) stops startup with a named error; a non-empty database without the marker is M4(e).
  `autotester store ping` prints the configured database name (not a secret). **Falsifier:** a fake database holding foreign collections and no
  marker starts; or a marker for another name starts; or the marker is rewritten on a second start. *LOCAL.* serves: O7 · CRITICAL · judges: U4, U9
- **M12 — The fence tests are not vacuous.** Using the repo's mutation harness (`tests/conftest.py` `mutation_repo`,
  `tests/test_mutation_sandbox.py`), the guard test module is run against each mutant of `store/mongo_guard.py` and `schema/store_config.py`:
  (a) name read from `os.environ`, (b) name read from the URI path, (c) forbidden-name check removed, (d) URI-clash check removed, (e) marker
  check removed, (f) `extra="forbid"` removed, (g) an `aggregate` verb added. Each mutant must turn at least one test **red**. **Falsifier:** a
  mutant leaves the guard tests green. *LOCAL.* serves: O7 · CRITICAL · judges: U1

## Seam and parity

- **M13 — Backend is configuration.** `AUTOTESTER_STORE` unset means `file`; with it unset `pymongo` and `gridfs` are not imported (cold-start
  test); the full existing suite passes with no Mongo and no network. An unknown value for `AUTOTESTER_STORE` or for an area in
  `AUTOTESTER_STORE_AREAS` stops startup (never a silent default). **Falsifier:** `import autotester` followed by a file-mode workload leaves
  `pymongo` in `sys.modules`; or a typo'd area boots. *LOCAL.* serves: O12 · judges: U2, U9
- **M14 — Signatures unchanged.** The public functions of `store/filestore.py` keep their signatures; the 30 direct importers of it (design
  A2) and the public methods of `ProjectStore`, `CrawlStoreMixin`, `RunStoreMixin` are unchanged. **Falsifier:** a signature diff of those
  public surfaces against `4de46d52`. Edit in place: no `filestore_v2`-style module. *LOCAL.* serves: O12 · judges: U2
- **M15 — One contract suite, three backends.** A single parametrised suite passes on `FileBackend`, `InMemoryBackend` and `MongoBackend` (over
  the fake): ordered rows; idempotent add; upsert keeps position; `delete_row` returns a bool; `keys(prefix)` ordering; model round-trip
  equality (`dump -> store -> load == original`) for every schema family in the route table. **Falsifier:** a route-table family with no
  round-trip case, or a backend that fails any case. *LOCAL.* serves: O12 · judges: U2, U4
- **M16 — No raw filesystem on state paths.** A doctor rule fails on `open(...,"w")`, `write_text`, `write_bytes`, `os.replace`, `shutil.*`,
  `unlink`, `glob`, `iterdir`, `.exists()`, `.stat()` applied to a path built by `ProjectPaths`, `team_path` or `repo_root()/".work"` outside
  `store/`, `browser/` scratch and an explicit allow-listed scratch set. The bypass sites of design 3.3 are moved first (U3a-U3c).
  **Falsifier:** reintroduce `Path.write_text` on a `ProjectPaths` path in `stages/`; `autotester doctor` stays green. *LOCAL.* serves: O12 · judges: U3a, U3b, U3c
- **M17 — Keys are safe.** A key containing `..`, an absolute path or a drive letter raises `UnsafeName` before any I/O on every backend.
  **Falsifier:** `put("../x")`, `put("C:/x")`, `put("/x")` reach a backend. *LOCAL.* serves: O7 · judges: U2, U4
- **M18 — Encoding.** Bodies are JSON-mode (datetimes as the same ISO strings the files hold). A body with a `.` or `$`-leading key is stored as
  `body_json` and round-trips. A body over 12 MB is refused with a named error, never truncated; over 4 MB logs a warning. Row order is
  `seq` (unique `(k,seq)`); append is `max(seq)+1` with retry on `DuplicateKeyError`; upsert preserves `seq`. **Falsifier:** a 13 MB body is
  accepted or truncated; a `{"a.b": 1}` body does not round-trip; two concurrent appends yield a duplicate `seq`. *LOCAL.* serves: O12 · judges: U4
- **M19 — Exclusive create has exactly one winner.** `create_exclusive` has one winner among 16 concurrent callers on every backend (schedule
  claims, delivery markers, frozen release scope, first-admin claim, marker). **Falsifier:** two winners in 200 repetitions. *LOCAL.*
  serves: O12, O13 · CRITICAL · judges: U2, U4, U7
- **M20 — Compare-and-set.** `put_if` with a stale `expect_sha` returns `False` and writes nothing (LangGraph checkpoint, run queue, heartbeat);
  the stale-instance refusal at `stages/orchestrate_checkpoint.py:173` still fires on the Mongo backend. **Falsifier:** a stale write lands, or
  the checkpoint identity check is skipped in mongo mode. *LOCAL.* serves: O12 · CRITICAL · judges: U7
- **M21 — Collections and indexes.** Every state family of design section 2 (including the lines added by this contract: `secrets`,
  `browser_sessions`, `server_state`) is in `COLLECTIONS` with its declared indexes, created idempotently at startup (running twice creates
  nothing new). **Falsifier:** a family in section 2 with no collection, or a second `create_index` pass that reports a change. *LOCAL.*
  serves: O12 · judges: U4
- **M22 — KG growth rule.** `PortalPersona` is stored whole in `project_docs/<slug>/portal_persona` while its body is at most 4 MB; above that
  `graph.nodes` and `graph.edges` are split into `kg_nodes` / `kg_edges` rows and re-assembled on read to an equal model. **Falsifier:** a
  5 MB persona does not round-trip equal, or a read mixes stale and fresh rows. *LOCAL.* serves: O1 · judges: U4

## Binary evidence

- **M23 — GridFS invariants.** `put` stores `sha256`, `kind`, `masked`, `content_type`; `kind=screenshot` with `masked=False` is refused (the FB3
  mirror); an equal-sha put is a no-op; a changed-sha put never leaves zero revisions (new revision first, then delete the old); `delete`
  removes all revisions of a key; the bucket is created only inside the configured database. **Falsifier:** an unmasked screenshot is
  stored; an interrupted changed-sha put leaves no readable revision. *LOCAL.* serves: O3, O7 · CRITICAL · judges: U5a
- **M24 — Evidence contract unchanged.** `Evidence.path` stays the run-relative string (`schema/run.py:20-26`); a `RawResult` is written only
  after its blobs are stored; every reader that needs a file gets one through `materialize` into `.work/blob-cache/`; no reader opens a state
  path directly. **Falsifier:** a `RawResult` whose referenced blob is missing in the fake; or `Evidence` schema fields change. *LOCAL.*
  serves: O3 · judges: U5b
- **M25 — What does not move.** Not stored in Mongo: the CEO-benchmark private answer list `.work/ceo-bench/` (file-only, private by design,
  `schema/ceo_inputs.py:57`); teaching-video **chunks** (derived, regenerable); generated xlsx/html exports (rebuilt per request); the
  `profiles/` Chromium user-data directory (scratch; sessions are M38-M40); `.env` and `.work/` scratch. `crawl_summaries/` keeps being
  committed to git as today (`core/paths.py:245-249`). The blob cache is capped at 512 MB LRU. **Falsifier:** the migrate dry-run lists
  any of these as a to-insert item; a cache run past the cap does not evict. *LOCAL.* serves: O7, O12 · judges: U5a, U5b, U8

## Failure behaviour and deployment

- **M26 — Fail closed.** With a mongo area and an unreachable backend (fake raising `AutoReconnect`): reads and writes raise `StoreUnavailable`
  after a bounded retry (3 tries); **no file under the data root is created or changed** (tree hash before equals after); auth requests are
  denied, never allowed; the UI renders a themed 503 ("State store unavailable, nothing was changed"); `/healthz` stays 200 and a readiness
  field reports the store; a run in progress ends `interrupted`. There is no file fallback. **Falsifier:** any file appears under the data root
  while the fake is down, or an auth request is allowed. *LOCAL.* serves: O4, O7, O12 · CRITICAL · judges: U9
- **M27 — Startup check.** Hosted startup pings every mongo area (`auth/config.py:43` `check_startup`, 5 s selection timeout) and refuses to
  start on failure, naming the area and the exception class, never the URI (M9). **Falsifier:** startup succeeds with the fake down. *LOCAL.*
  serves: O12 · judges: U9
- **M28 — Single instance until CAS is on.** `docker/DEPLOY.md` states `--max-instances 1` until U7 (Mongo claims and CAS) is switched on, drops
  the GCS-volume request (D-120 Result), and lists the env names (`AUTOTESTER_STORE`, `AUTOTESTER_STORE_AREAS`, `PATHLYNKS_MONGO_URI`,
  `AUTOTESTER_APPROVAL_KEY`). `docker/entrypoint.sh:38-59` stops claiming state is lost only when every area is mongo and the credential and
  session stores are on. **Falsifier:** DEPLOY.md lacks the note or still asks for a GCS volume. *LOCAL.* serves: O12 · judges: U10

## Auth

- **M29 — Invariants preserved (no transactions assumed).** Concurrent first signups produce exactly one admin (AU7; `create_exclusive` on an
  `auth_meta` doc); concurrent disabling of the last two admins leaves at least one enabled admin (AU9; two-thread test, optimistic CAS on
  `auth_meta/admin_guard`); `generation` cannot change; integer user ids are preserved by migration and never reused (allocator doc);
  sessions store only the sha256 of the token; disabling takes effect on the next request; default groups seed once (AU11). The existing auth
  tests are the oracle for `auth/store_sqlite.py` (behaviour-neutral extraction, U6a) and run unchanged against `auth/store_mongo.py` (U6b).
  **Falsifier:** the two-thread test leaves zero enabled admins in 200 repetitions, or any existing auth test is edited to pass. *LOCAL.*
  serves: O15 · CRITICAL · judges: U6a, U6b
- **M30 — Hashes stay inside.** `password_hash` never appears in a list API, log line, audit row, UI response or error text, and a Mongo dump
  contains argon2 strings only in `auth_users`. **Falsifier:** grep of captured logs and responses for the `$argon2` prefix. *LOCAL.*
  serves: O7, O15 · CRITICAL · judges: U6a, U6b, U6c

## Credential store (D-122 item 4) — CRITICAL; every row here is dual-checked

Scope: the project and role login values entered through the UI for declared `SecretRef` keys. **Not** in scope: the Mongo URI,
`AUTOTESTER_APPROVAL_KEY`, and provider API keys, which stay deployment environment (M36). **Module note:** D-122 approves eight new modules and
none is a credential or crypto module. The maker proposes an existing home first (`core/env.py` for resolve/write, `browser/secrets.py` for
`SecretStore`); a new module such as `store/secret_box.py` needs a new authorizing D-entry from Umesh before it exists. The line cap (300) still binds.

- **M31 — Sealed at rest.** A credential value is stored only as an authenticated-encryption envelope (`cryptography` AEAD, AES-256-GCM or
  ChaCha20-Poly1305) `{v, kid, nonce, ct}` in `secrets`, `_id` = the namespaced key, with `p` = project slug. The key is derived with
  **HKDF-SHA256** from `AUTOTESTER_APPROVAL_KEY` with `info = b"autotester-store-secrets-v1"` (the purpose label, D-122) and a fixed documented
  salt, 32 bytes; a fresh random 96-bit nonce per write; AAD binds `purpose|collection|_id|p` so a ciphertext moved to another document or
  project fails to open; `kid` is a truncated HMAC of a constant under the derived key (identifies the key without leaking it). The derived key
  lives only in process memory: never in the database, a log, a prompt, an exception, a trace or an artifact. **Falsifier:** (a) two writes of the
  same value yield equal ciphertext (nonce reuse); (b) flipping one byte of `ct`, `nonce`, `_id` or `p` still opens; (c) changing the HKDF label
  still opens; (d) the derived key or the master key appears in a dump of the fake database, in captured logs, or in `repr()` of the store.
  *LOCAL.* serves: O7 · CRITICAL · judges: U11
- **M32 — Fails closed on a missing or changed key.** With `AUTOTESTER_APPROVAL_KEY` unset or empty, every credential-store read and write raises
  `SecretKeyMissing` (a named error): no plaintext is written anywhere (not to the database, not to `.env`, not to a temp file), and no
  partial value is returned. With the key changed since the write (`kid` mismatch), a read raises `SecretKeyChanged` and says to re-enter the
  value; it never returns garbage or an empty string. The rest of the document store keeps working. **Falsifier:** unset the key, save a
  credential through the UI route; the save succeeds, or a file under the data root changed, or the failure is a bare `KeyError`. *LOCAL.*
  serves: O7 · CRITICAL · judges: U11
- **M33 — Substitution and scoping unchanged.** `{{SECRET:KEY}}` is substituted only at `page.fill()` time, scoped to the `SecretRef` domains
  inside `allowed_domains` (suffix match, `browser/secrets.py::_host_matches`); a project resolves only the keys it declares in `SecretRef[]`;
  `core.redact.assert_no_raw_secrets` is still the gate before any model call; screenshots still mask secret inputs before capture (B7); no
  schema model gains a field holding a value (C5). Resolution order in mongo mode: sealed store first, then process environment; a key present
  in both resolves to the store value. **Falsifier:** project B resolves a key declared only by project A; a value resolves for a host outside
  its domains; a prompt carrying a store-held value passes `assert_no_raw_secrets`; the existing `browser-and-secrets.md` B5-B9 tests are
  edited to pass. *LOCAL.* serves: O7 · CRITICAL · judges: U11
- **M34 — Redaction covers store-held values.** The `Redactor` used by logs, traces, prompts, evidence and reports is built from the union of
  `.env` values **and** the decrypted values of every credential in the store (loaded at run start, in memory only). Adding or changing a
  stored credential refreshes the redactor before the next scrub. **Falsifier:** write a credential through the store, put its value in a trace
  line, an exception message, a `Redactor.scrub` input and an assembled prompt; any output still contains the value. *LOCAL.*
  serves: O7 · CRITICAL · judges: U11
- **M35 — UI and API surface.** A saved value is returned only to a user holding `credentials.view` (default Admin/CEO, `auth.md` AU21; the
  C5 exception, tightened on hosted); every other viewer, every list API and every error sees "set" / "not set" and key names. In mongo mode
  the UI write goes to the sealed store and **not** to the repo `.env` (no second plaintext copy on the ephemeral disk); in file mode it
  writes `.env` exactly as today; the two never both receive the value. The route treats a newly submitted raw value as secret before any
  validator can echo it (the C5 guard rule). **Falsifier:** a viewer without `credentials.view` gets a value from any route; a mongo-mode save
  leaves the value in `.env`; a validation error echoes the submitted value. *LOCAL.* serves: O7 · CRITICAL · judges: U11
- **M36 — Deployment secrets are never stored.** The Mongo URI (`PATHLYNKS_MONGO_URI`), `AUTOTESTER_APPROVAL_KEY` and provider API keys are read
  from the process environment or `.env` only; the credential store refuses to accept them (named error) and `store migrate` never lists them.
  **Falsifier:** `put_secret("AUTOTESTER_APPROVAL_KEY", ...)` or a migrate dry-run naming one of the three classes succeeds. *LOCAL.*
  serves: O7 · CRITICAL · judges: U11, U8
- **M37 — Lifecycle.** Deleting a role account, a `SecretRef` or a project deletes its `secrets` and `browser_sessions` documents (a
  `delete_many` whose filter carries `p`, M6); a deleted credential cannot resolve afterwards; the `.env` snapshot-restore on failure in
  `ui/routes_role_accounts.py:196-211` has a store equivalent that restores the previous sealed envelope, not a plaintext copy. **Falsifier:**
  after deleting the account a read of its key still returns a value or the document remains. *LOCAL.* serves: O7, O17 · judges: U11

## Browser session store (D-122 item 4) — CRITICAL; every row here is dual-checked

Fact that shapes this unit: on `4de46d52` no code calls `storage_state` (`grep -rn storage_state src tests` is empty); a login survives today only
inside the persistent Chromium directory `profiles/<slug>/` (`browser/launch.py:188-191`, `manual-login.md` ML3). This unit **adds** an
export/restore of a Playwright `storage_state` (cookies plus origin `localStorage`) per role account; the `profiles/` directory stays local scratch.

- **M38 — Sealed `storage_state`, scoped on the way in and out.** A session is stored in `browser_sessions` (`_id` = `<slug>|<account_id>`, `p`,
  `saved_at`, `expires_at` = the earliest unexpired auth-cookie expiry, hosts list) as the same sealed envelope as M31 with its own purpose
  binding in the AAD. On **save and on restore** every cookie and every origin whose host does not satisfy `_host_matches` against the
  project's `allowed_domains` is dropped. **Falsifier:** a `storage_state` containing a cookie for `evil.example` is saved with that cookie,
  or restored into the context; or the stored document holds a cookie value in plaintext. *LOCAL.* serves: O7 · CRITICAL · judges: U12
- **M39 — Restore semantics.** Restore applies only to the account it was saved for (never account A's state into account B's context), only
  while unexpired, and not after an explicit logout/delete. An entry-screen case still never runs on a profile that was not removed (`ui-run.md`
  RU5): a restored session must not defeat `wipe_entry_profile` (`stages/orchestrate_execute.py:115`); an entry run starts without restored
  state. A human-run OTP/manual login (B8, ML3) is saved after the human finishes and is never replayed past its expiry. **Falsifier:** an expired
  or foreign-account state is restored; an RU5 entry run starts logged in; the existing ML3 and RU5 tests are edited to pass. *LOCAL.*
  serves: O7, O12 · CRITICAL · judges: U12
- **M40 — A session never leaves the door.** Cookie and `localStorage` values from a stored or restored session appear in no blob, evidence file,
  screenshot, trace, failure bundle, report, prompt, log or exception; they are registered with the `Redactor` (M34) when loaded.
  **Falsifier:** a restored cookie value in a trace line or exception text survives `Redactor.scrub`; a failure bundle built from a run on a
  restored session contains the value. *LOCAL.* serves: O7, O3 · CRITICAL · judges: U12

## Migration

Tool: `autotester store migrate [--area A] [--project SLUG] [--apply] [--include-sessions]` and `autotester store verify` (`cli_store.py`).

- **M41 — Dry run is the default and opens no connection.** Without `--apply` the tool opens no Mongo client (spy) and prints the section-8
  report of the design (per collection `to_insert / unchanged / conflicting-id`, bytes per kind, the ten largest documents against the 4 MB and
  12 MB thresholds, GridFS total, keys that failed `safe_name`); `--apply` without a resolvable URI refuses. **Falsifier:** a dry run
  constructs the guard or imports `pymongo`. *LOCAL.* serves: O7, O12 · CRITICAL · judges: U8
- **M42 — Idempotent and non-destructive.** A second `--apply` reports `written: 0`; blobs are written before the documents that reference
  them; no source file is modified, moved or deleted (tree hash before equals after). **Falsifier:** a second apply writes; a source file's
  hash changes. *LOCAL.* serves: O12 · CRITICAL · judges: U8
- **M43 — Signed rows verbatim.** Migrated `approvals` and `approval_revocations` bodies are byte-identical to the source rows (no re-sign, no id
  recompute); `store verify` loads each from the fake and `RunApproval.is_intact()` (`schema/approval.py:176`) is true for every row, and
  `is_signed_and_verified()` (`:202`) too when `AUTOTESTER_APPROVAL_KEY` is present. **Falsifier:** one flipped byte in a migrated row is not
  caught by `verify`. *LOCAL.* serves: O7 · CRITICAL · judges: U8
- **M44 — Verify.** `store verify` compares file against Mongo by canonical hash and blob sha256 and counts per collection, and exits non-zero on
  any mismatch. **Falsifier:** a deliberately altered fake document returns exit code 0. *LOCAL.* serves: O12 · judges: U8
- **M45 — Auth sessions excluded by default.** Unexpired `auth_sessions` are copied only with `--include-sessions`; users, hashes, `generation`,
  integer ids, seeded meta and allocator docs (`max(id)+1`) always. `browser_sessions` are **never** migrated: a Chromium profile directory is
  not convertible offline, so role logins are re-established by the human (stated in the dry-run report). **Falsifier:** a default run copies
  a session row; the allocator is seeded at or below an existing id. *LOCAL.* serves: O15 · judges: U8
- **M46 — Credential migration.** `store migrate` reads declared `SecretRef` values from the repo-root `.env`, seals them (M31) and writes them to
  `secrets`; it never prints, logs or reports a value (key names and counts only, M36 classes excluded); it never edits `.env`; without the
  master key it refuses (M32) rather than skipping silently. The first real `--apply` is G1, a human gate. **Falsifier:** report/stdout/stderr
  contains any `.env` value; `.env` hash changes; the run proceeds with the key unset. *LOCAL.* serves: O7 · CRITICAL · judges: U8, U11

## Tests, dependencies, docs

- **M47 — Test doubles and the live smoke.** The fake is a hand-written `FakeMongoClient` (plus minimal GridFS) covering exactly the verbs of M6;
  `mongomock` is not added (`grep -c mongomock pyproject.toml uv.lock` stays 0). The only new dependency is `cryptography`, declared as a direct
  dependency (it is already locked transitively, `uv.lock:871`; the undeclared-direct-import doctor check forbids relying on that), and the lock
  stays consistent (`uv lock --check`). A human-run live smoke is allowed only against a collection named `t_<...>` (`^t_[a-z0-9_]{1,30}$`) in the
  configured database, only when `AUTOTESTER_LIVE_MONGO_TEST=1`, and never when `CI` is set; it is the single exception to the closed
  `COLLECTIONS` set and does not touch the fence (collection-level only). **Falsifier:** `collection("t_x")` works with the flag unset or `CI`
  set; `collection("anything_else")` works under the flag; the suite imports `mongomock`. *LOCAL.* serves: O7 · judges: U1, U11
- **M48 — Docs follow the contract, and C5/C6 are amended.** After the CRITICAL units pass: `docs/ARCHITECTURE.md` Storage and Security prose and
  `CLAUDE.md` "Credentials (hard boundary)" change only under D-120/D-122; `core-invariants.md` **C5** (value lives only in the repo-root `.env`)
  and **C6** (files are the store; no database is the primary store) gain an amendment naming the Mongo backend, with the file backend still
  the local/test default and `Redactor`/`credentials.view` unchanged. The checker makes the `core-invariants.md` edit in a separate
  criticality-gated amendment commit; no maker edits it. **Falsifier:** prose still says "no new DB (D-036)" or "values live only in `.env`"
  for the Mongo backend after U10 PASS. *LOCAL.* serves: O7 · judges: U10

## Unit table (order, dependencies, dual check)

Unit ids follow `.goal/goal.json` at build time; U-numbers are this contract's. "Dual" = two independent fresh checkers (D-100). A new file
beyond the D-122 list is a STOP, not a decision for the maker.

| Unit | Scope (E = edit in place, N = new, all N files are on the D-122 list) | Criteria judged | Depends on | Dual |
|---|---|---|---|---|
| U0 | this contract (D-122 already settles Q1, Q9, Q13) | — | D-120..D-122 | gate (done) |
| U1 | N `schema/store_config.py`, `store/mongo_guard.py`, fake client + guard tests; E `pyproject.toml` (`[tool.autotester.store]`), `core/paths.py` (`code_root()`), `browser/db.py` (M10) | M1-M12, M47 | U0 | **dual** |
| U2 | E `store/filestore.py` (Protocol, `FileBackend`, key conversion, `AUTOTESTER_STORE` parse, file only wired) | M13-M15, M17, M19 (File/InMemory) | U0 | |
| U3a | E bypass sweep, stages and sources | M16 | U2 | |
| U3b | E bypass sweep, listings and stat (`core/env.py`, `credential_guard`, `schedule_wiring`, `project_view`) | M16 | U2 | |
| U3c | E bypass sweep, trace, checkpoint (`put_if`), audit, delivery inbox, schedule store; doctor rule | M16 | U2 | |
| U4 | N `store/mongo_backend.py`, `store/mongo_routes.py` | M2, M5-M8, M11, M15, M17-M19, M21, M22 | U1, U2 | **dual** |
| U5a | N `store/blobs.py` (`BlobStore`, GridFS, `materialize`) | M2, M5, M8, M23, M25 | U1, U2 | |
| U5b | E write-through at screenshot/video/crawl shot/frames, `sync_run_blobs`, read sites via `materialize` | M24, M25 | U3a-c, U5a | |
| U6a | N `auth/store.py`, `auth/store_sqlite.py` (SQL moved verbatim) | M29, M30 | U0 | **dual** (security backbone) |
| U6b | N `auth/store_mongo.py` (users, groups, sessions, grants; first-admin, last-admin) | M29, M30 | U1, U4, U6a | **dual** |
| U6c | E Mongo video shares/links/requests/comments, `schedule_owner`, `intake_gate_auth`, audit rows | M30 | U6b | |
| U7 | E coordination on Mongo: `create_exclusive`, `put_if`, purge as `delete_many`, run-queue `rev` | M19, M20 | U3c, U4 | **dual** |
| U9 | E area routing, startup ping, `StoreUnavailable` to 503, readiness field, `core/env.py::mongo_uri` | M9, M11, M13, M26, M27 | U4 | |
| **U11** | **Credential store**: sealed `secrets`, HKDF key, resolve order, redactor union, UI routes (`ui/routes_role_accounts.py`, env editor), lifecycle; existing module homes only unless a D-entry adds one | M8, M31-M37, M46, M47 | U1, U3b, U4, U9 | **dual (CRITICAL)** |
| **U12** | **Session store**: `storage_state` export/restore per role account, sealed `browser_sessions`, scoping, RU5-safe restore | M38-M40 | U11 | **dual (CRITICAL)** |
| U8 | N `cli_store.py` migrate and verify, auth importer, approvals verbatim, credential importer | M9, M25, M36, M41-M46 | U4, U5a, U6b, U7, U11 | **dual** |
| U10 | E `docker/DEPLOY.md`, `docker/entrypoint.sh`; `docs/ARCHITECTURE.md`, `CLAUDE.md` Credentials prose, `core-invariants.md` C5/C6 (checker amendment) | M28, M48 | U9, U11, U12 | |
| G1 | **HUMAN_GATE**: Umesh runs or approves the exact first `migrate --apply` and each area flip | SERVER-GATED | U8, U9, U10 | gate |

Waves: W0 = U0. W1 = U1, U2, U6a in parallel (disjoint files). W2 = U3a, U3b, U3c, U4, U5a, U6b in parallel. W3 = U5b, U6c, U7, U9. W4 = U11,
then U12. W5 = U8, U10. W6 = G1. G1 flip order (each reversible by flipping back until data diverges): settings/prefs/audit, projects, runs +
crawls + KG, approvals (verify intact), auth, credentials and browser sessions (after U11/U12 PASS), blobs, queue/claims (then lift
`--max-instances 1`).

Ordering risk that decides the table: U3 lands before U4 is switched on, otherwise a direct `write_text` keeps writing to the container disk
while the rest of the run is in Mongo (M16). U11 follows U3b because credential reads in `core/env.py` and `ui/credential_guard.py` are bypass sites.

## Not criteria (recorded so nobody adds them silently)

- A server-side Mongo role limited to `readWrite` on `autotester` (Q10): recommended follow-up, Umesh's call. Until then the code fence is the only fence.
- Rotation of `AUTOTESTER_APPROVAL_KEY`: a change makes sealed values unreadable and M32 says so; a re-seal tool is not part of this build.
- TTL on `audit_log` / `run_traces`; multi-instance Cloud Run (needs U7 on first).
- Dropping the `autotester` database is not exposed at runtime and needs a human gate (D-120).

## Amendment log

- 2026-10-29 · authored by /checker (Unit 0 of mongo-store) from `.work/mongo-store-design.md` as amended by D-120, D-121, D-122. Renumbered the
  design's M1-M33 into M1-M48; added M11 (marker, from design M33), M12 (mutants), M31-M40 (credential and session stores, D-122 item 4), M46,
  M47, M48; dropped the `product_databases` list and the `connect_read_only` registry (D-122 item 3).
