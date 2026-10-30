# Verdict - mongo-store-u12 (Checker A, containment and scoping)

**Verdict:** PASS (with warnings; none is a Block)
**Cycle checked:** 0
**Unit:** U12, session store (M38, M39, M40; leans on M8, M31). CRITICAL, dual check: this is checker A; the second checker's verdict is separate and not read.
**Code checked:** worktree `D:/autoTesting/.claude/worktrees/mongo-u12`, HEAD `93e6d4d2` (master `3c74e476` merged into `feat/mongo-store-u12`). Checker changed no `src/` or `tests/` file. Probes lived in the scratchpad.

## Commands run (all with `-o addopts=`, two files per call, `env -u ANTHROPIC_BASE_URL`)

| Command | Result |
|---|---|
| `pytest tests/test_session_store_u12.py tests/test_session_store_u12_redaction.py` | 24 passed |
| `pytest tests/test_secrets.py tests/test_multi_role_session.py` | 38 passed |
| `pytest tests/test_manual_login.py tests/test_credential_store_u11.py` | 26 passed (includes U11's pin: only `core/env.py` and `ui/env_editor.py` use `credential_collection(`) |
| `pytest tests/test_mongo_guard_scan.py tests/test_mongo_guard_surface.py` | 56 passed (M3 AST scan, M6 verb set still hold) |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor > .work/doctor-chkA.txt` | exit 0, `doctor: clean` (only non-blocking D-087 advisories); file and function caps hold |
| `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u12/mutations.json --repo .` | `24/24 mutations killed`, exit 0 (re-run by me, not read from the maker's file) |
| my adversarial probes (`scratchpad/probe/test_chka_probe.py`, fake Mongo, synthetic canaries) | results below |

Not run: full suite (low-memory rule); `tests/test_role_port_authz.py` (5 known environmental failures); live-Chromium `test_role_session_port*.py` (store-off path; the maker reports 18 passed).

## Containment checks, with evidence

1. **One writer.** `grep -rn "browser_sessions|SESSION_COLLECTION" src scripts` finds writes only at `browser/profiles.py:73` (`_put_session`, `replace_one` by `_id`), plus the `p`-filtered `delete_one` at `profiles.py:119, 141, 152` and `ui/env_editor.py:267` (`delete_many({"p": slug})`). The other hits are the collection list `store/mongo_guard.py:39`, the route table `store/mongo_routes.py:43` and the read-side refusal text `browser/db.py:42`. M31(b) holds for sessions.
2. **Never on disk.** `grep -rn storage_state src scripts`: the only call outside `profiles.py` is `browser/entry_reset.py:33` (pre-existing, in memory, result read and dropped). `capture_session` (`profiles.py:217`) calls `context.storage_state()` with no `path=`; the test double asserts `"path" not in kw` and the mutant "export written to a path" is killed. The probe `elsewhere()` dump shows no canary outside `browser_sessions`.
3. **Scope on save and restore.** `scope_state` (`profiles.py:83-90`) uses `_host_matches` (exact, `browser/secrets.py:104-112`). Probe with `allowed_domains=["app.pl.test"]`, zero mismatches against my expectation table:
   - Cookie domains kept: `app.pl.test`, `APP.PL.TEST`, `.app.pl.test`, `app.pl.test.` (one trailing dot), `..app.pl.test`, ` app.pl.test`.
   - Cookie domains dropped: `pl.test`, `.pl.test` (parent), `evil.pl.test`, `xapp.pl.test`, `app.pl.test.evil.example`, `app.pl.test:8443`, `xn--app-pl.test`, empty, NUL-injected, ideographic full stop (`app<U+3002>pl.test`), non-string and non-dict entries.
   - Origins kept: `https://app.pl.test`, upper case, `:8443`, `http://`, trailing slash, scheme-less `app.pl.test`.
   - Origins dropped: parent, sibling, lookalike suffix, `app.pl.test@evil.example`, `evil.example\@app.pl.test`, `evil.example#@app.pl.test`, `evil.example/@app.pl.test`, `file:`, `data:`, `[::1]`, `null`, empty.
   - Restore re-scopes: a tampered stored document whose `state` holds `evil.example` cookies and origins comes back with them removed (`load_session`, `profiles.py:143`).
4. **Never restored.** Probe results on `load_session`: a document with `_id` `pl|t1` but `p="other"` returns `None`, is left in place, and `save_session` raises `SessionRefused` without touching it. A `_project` document is not served to account `t2` and `t1` is not served to `t2` or `_project`. Expired (`expires_at` in the past) returns `None` and the document is deleted. `state` as a string, `None`, or missing `expires_at` returns `None` and is deleted. Ids with `|` in either part raise `SessionRefused`. `_project` cannot match `ROLE_ACCOUNT_ID_PATTERN` (mutant killed).
5. **Entry guard (RU5).** `restore_session` (`profiles.py:229`) returns `False` when `paths.slug` ends `-entry-test`. The only call sites are `multi_role_session.py:132` (role slug `<slug>-role-<id>`, never entry), `run_execution.py:178` (shared-profile session only, `lent is None`) and the capture sites `multi_role_session.py:203` and `manual_login.py:48`. The orchestrate path (`orchestrate_execute.py:112`, entry profile) does not call it. Holds.
6. **Redaction, probes.** After `capture_session`, `session.secrets.redactor().scrub` masks the cookie value raw, URL-encoded, JSON-escaped, upper-cased, a numeric-string value, and JSON string leaves (`leaf`, `deep` nested). `repo_redactor()` (`mongo_routes.py:189-198`) masks the same. The write gate refuses (`StoreSecretRefused`) a case body, a trace-key body and a body holding only a JSON leaf. The canary appears in no other collection.
   - Gap seen: base64 of the cookie value is not masked. The redactor does not do this for `.env` values either; informational.

## Findings

**W1 (Warning) - each session save opens a new Mongo client, undoing U11f's ruling.** `profiles.py:71-76` `_put_session` calls `reset_default_backend()` (`store/mongo_backend.py:295-296`, `_CACHE.clear()`), so the next `default_backend()` builds a new `GuardedStore`, a new `MongoClient` and re-runs index creation. U11f replaced exactly this with `default_backend().rearm()` (`mongo_backend.py:246-247`, `ui/env_editor.py:219-223`) and tests it (`tests/test_credential_store_u11f.py:181-199`, "one client"). Probe: three `capture_session` calls produced `CLIENTS for 3 captures: 3`. The old client is dropped, not closed. No fence breach: the new handle is still `GuardedStore` on `cfg.database` (M1/M5 unaffected). Fix: use `rearm()`; the existing "write gate not rebuilt" mutant would still apply.

**W2 (Warning) - a failed sign-in replaces a good stored state.** `capture_session` (`profiles.py:211-221`) runs after the click and settle (`multi_role_session.py:203`). Probe: an anonymous-cookie state overwrote the good one (`anon-with-cookie replaced good: True`); an empty state deleted the document. Fail-closed for confidentiality (a re-login, never a leak), but a bad sign-in drops a working session. The maker disclosed this (gap 4). Accepted for this cycle.

**W3 (Warning) - a malformed stored document raises instead of being dropped.** `load_session` with `state={"cookies": 5, "origins": 5}` and a valid `expires_at` raises `TypeError` from `scope_state` (`profiles.py:86`), and the document stays. Only the app writes these documents, and a raise during startup is fail-closed (`run_execution.py:177` turns it into an errored startup). The docstring's "unreadable document is deleted" is true for non-dict states only. A tampered far-future `expires_at` is also trusted (`profiles.py:140`; the 24 h cap applies at save only).

**W4 (Info) - leading-dot and whitespace tolerance.** `..app.pl.test` and ` app.pl.test` count as in scope (`lstrip(".")` at `profiles.py:87`, `strip()` in `_norm_host`). Both name only the allowed host; no leak.

## Judgement calls asked for

- **Exact vs suffix `_host_matches` for M38: exact is right.** M38 names `_host_matches`, which is exact since AT-651/D-087 (`secrets.py:104-112`). It is stricter than `Project.allows_domain` and fails closed (a dropped cookie costs a re-login; a kept lookalike would leak). `CLAUDE.md` (the "suffix match" wording under Credentials) is stale and should be corrected by its owner. Not a unit defect.
- **Mask floor (8 chars) and cap (200) narrowing M40: accepted.** The redactor has no length floor, so masking `1` or `en` would corrupt every trace and make the M8 gate refuse legitimate writes. Cost: a real token under 8 characters is not masked. Cap overflow takes the longest first. The contract amendment should record the floor.
- **24 h `MAX_AGE_S`: accepted.** Stricter than the contract; session cookies carry no expiry of their own, so it is their only bound.
- **Failed sign-in overwrite:** see W2; accepted as disclosed, not a Block.

## Criteria

| Crit | Verdict |
|---|---|
| M38 plain, scoped in and out, one collection | PASS |
| M39 restore semantics, entry guard, account isolation | PASS |
| M40 never leaves the door | PASS (floor and base64 noted) |
| M8 / M31 (one writer, no crypto, no other carrier) | PASS |
| Files at most 300 lines, functions at most 50 | PASS (`profiles.py` 239, `secrets.py` 300, doctor clean) |

W1 should be fixed before or with the dual-check close-out; it does not change PASS because containment, scoping and redaction hold.
