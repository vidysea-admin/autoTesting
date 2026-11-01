# Verdict (checker B) - e2e-fixes-e7 (AT-1416 slug guard, AT-1420 stage token)

**Cycle checked:** 0
**Verdict:** PASS (3 warnings, none blocking; W1 recommended as a follow-up issue)
**Checker:** B (independent, adversarial focus). Code under test: branch `feat/e2e-e7` at `eaeab0af` (base `70a7a486`). Contract: `qa/contracts/e2e-fixes.md` E7.1-E7.5. Manifest: `qa/manifests/e2e-fixes-e7.md`.
I re-ran everything below myself, with `PYTHONPATH=<worktree>/src`, `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts=`, one call at a time. I did not read any other checker's verdict. No `.env` value was read or printed (all canaries are fake literals in temp roots).

## Commands and outputs

| Command | Result |
|---|---|
| `pytest tests/test_credential_guard_server_key.py tests/test_reachability_stage.py` | 46 passed |
| `pytest tests/test_target_probe.py tests/test_run_unreachable_target.py` | 37 passed |
| `pytest tests/test_ui_auth_envkeys.py tests/test_ui_auth_hardening.py` (unmodified) | 42 passed |
| `pytest tests/test_state_sweep_u3b.py tests/test_ui_auth_surface.py` (guard/AU21) | 30 passed |
| `pytest tests/test_reachability_warning.py tests/test_run_bounds_stop.py` (unmodified) | 14 passed |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor > .work/doctor-e7-chkB.txt` | rc=0, last line `doctor: clean` |
| `git diff 70a7a486 eaeab0af -- src` | only `credential_guard.py` (import + `refuse_reserved_slug` filter `:50` + one check `:68-69`) and `reachability.py` (`_failure_message`, `_UNREACHABLE_ERRNOS`, `import errno`). E7.3 hunks confirmed: `_refuse_unsafe_submission`, `refuse_server_key`, ns/other-project checks untouched. `qa/issues.jsonl` untouched (E7.5). |
| Maker's mutation spec: `uv run python scripts/mutation_check.py qa/evidence/e2e-fixes-e7/mutations.json` | **14/14 killed** (I re-ran all 14, 5m31s; src restored, `git status` clean afterwards) |
| My 4 own mutants (`.work/chkB-mut.json`) | 3/4 killed, 1 SURVIVED (see W2) |

### My own mutants
- B-A exemption widened to every `PATHLYNKS_*` variable (literal prefix): KILLED by `test_a_project_shaped_variable_still_blocks_the_slug`.
- B-B refusal in `refuse_foreign_key` dropped: KILLED (5 tests incl. `test_env_add_refuses_the_store_uri...[PATHLYNKS_MONGO_URI-403]`).
- B-C refusal compares the unstripped `key` (padding bypass): KILLED by the ` PATHLYNKS_MONGO_URI ` case.
- B-D exemption is "any held key containing MONGO": **SURVIVED** (pytest exit 0). See W2.

## Rulings on the five questions

**(1) Four test literals gained ` [stage=timeout]` (`tests/test_target_probe.py:33,104,188`, `tests/test_run_unreachable_target.py:45`).** Honest, nothing weakened. `git diff` shows each hunk is a one-line change keeping the exact-equality `==` (and `preflight_warnings == [message]`), appending only the suffix. The contract's "pass unmodified, substring" premise (E7.4) is wrong for these four pins because they assert equality on a message that E7.4 itself requires to reach `Run.preflight_warnings`; equality cannot survive an appended token. The substring-style tests (`test_reachability_warning.py`, `test_run_bounds_stop.py`) pass unmodified (14 passed). Recommend a one-line contract note so the amendment is on record (checker-owned).

**(2) Lower-case store URI through `/env/add` gives 400, not 403: acceptable, nothing writable.** `build_secret_ref` (`ui/routes_project_edit.py:58-66`) fails the UPPER_SNAKE_CASE `fullmatch` first. I drove 12 spellings through `/projects/pathlynks/env/add` and `/projects/pathlynks/secrets`, 12 through `/onboard`, and 3 through `/onboard/roles`, with the real URI set in the process env and a canary value:
- exact, leading space, trailing space, tab, newline: **403** (stripped, then `.upper()` match at `credential_guard.py:68`).
- `pathlynks_mongo_uri`, dotless-i `PATHLYNKS_MONGO_UR\u0131`, long-s `PATHLYNK\u017f_MONGO_URI`, full-width `\uff30ATHLYNKS_MONGO_URI`, trailing dot, zero-width space: **400** (regex), no declaration, no `.env` write, real URI never in any response body.
- `PATHLYNKS__MONGO_URI` (double underscore) is a distinct, claimable key and does not alias the store URI (`read_dotenv` and `os.environ` are literal-key), so not a shadow.
- `/onboard/roles` with the exact name: 400 carrying the E7 message (via `check_key_namespace` -> `refuse_foreign_key`); lower-case/unicode: 400 from the `RoleAccount` pattern.
- Slug `pathlynks-mongo` (namespace `PATHLYNKS_MONGO_`, no longer refused as a slug now the URI is filtered): `refuse_foreign_key` still answers 403 for the URI; `pathlynks` claiming `PATHLYNKS_MONGO_X` is refused as another project's namespace.
Every declaration path I traced (`routes_credentials.py` `_save_login`/`_save_custom`, `routes_project_edit.py` `declare_secret`, `/onboard`, `/onboard/roles`, `/projects/<slug>/accounts`) goes through `build_secret_ref` / `check_key_namespace` -> `refuse_foreign_key`. `mongo_uri()` precedence (`core/env.py:227-234`: process variable, then repo-root `.env`) is untouched; `test_mongo_uri_still_resolves_after_a_pathlynks_project_exists` passes.

**(3) Can a project key `PATHLYNKS_MONGO_URI` hijack `mongo_uri()` or expose/overwrite the real URI?** Not through any door that creates a declaration (above). One residual path exists for a declaration that already exists, see W1.

**(4) The message carries no credential or URL query.** `_failure_message` (`reachability.py:140-158`) interpolates only `host` (from `host_of(base_url)`: no scheme, userinfo, port, path or query) and fixed wording. Checked live with exception texts carrying `SECRET` and `10.1.2.3`: no leak for dns/tcp/tls/timeout/http/unknown/PermissionError. A base_url with userinfo gives `host_of == ""`, so the probe does not run at all (`probe_target`) and nothing is echoed. The token only changes the message string, never the pass/fail decision (`probe_target` untouched).

**(5) Known reds.** `tests/test_platform_links.py -k mp12` fails identically on a detached worktree of master `70a7a486` (2 failed: `test_mp12_fixture_links_redirect_sso_control_off_platform_chain_404_and_unreached`, `test_mp12_containment_first_hop_never_reaches_the_stray_host_later_hop_is_parked`; `net::ERR_FAILED` to `a.localhost`), so not introduced by E7. `tests/test_credential_store_u11.py::test_only_the_door_writes_secrets_and_no_crypto_exists` fails identically on master `70a7a486` (1 failed, 21 passed) and on the branch (1 failed, 21 passed): pre-existing.

## Criteria
- E7.1 PASS: `credential_guard.py:50` filters the one name; onboarding `pathlynks` with the URI set -> 303 (test + my own probe).
- E7.2 (a) PASS, (b) PASS (42+30 unchanged tests green), (c) PASS (403 at the gate, all declaring writers verified; the lower-case 400 ruling above), (d) PASS.
- E7.3 PASS (diff hunks confined; guard suites green unmodified).
- E7.4 PASS: 13 classes, host-only message, end-to-end through `launch_run` (`test_the_token_reaches_the_run_every_case_and_the_page_message`); mutants m8-m15 killed in my re-run.
- E7.5 PASS: `qa/issues.jsonl` untouched; AT-1420 stays open (infrastructure), diagnostic only.

## Findings

**W1 (follow-up issue, not blocking) - a PRE-EXISTING declaration of the store URI can still be overwritten and displayed.** `src/autotester/ui/routes_credentials.py:269-270` (`POST /projects/{slug}/env`) guards only with `refuse_server_key(key)`; it does not call the new check. With `projects/pathlynks/project.json` hand-injected to declare `PATHLYNKS_MONGO_URI` (a pre-E7 declaration was possible on a box where the URI was only in `.env`, since nothing refused it), I observed: `GET /projects/pathlynks/env` response contained the real URI text, and `POST /projects/pathlynks/env key=PATHLYNKS_MONGO_URI value=<canary>` returned 303 and overwrote the repo `.env` value (so `mongo_uri()` with the process variable unset would return the canary). Requires `credentials.edit`/`view` plus a legacy declaration; no door E7 leaves open produces one (verified), so E7 widens nothing and the three doors named by E7.2(c) are covered. Recommended: factor the E7.2(c) check into one helper (e.g. `refuse_store_uri(name)`), call it from `routes_credentials.py:270` and make `core/env.py::resolve_credentials` / the env table skip the store URI name, so a legacy declaration is neither written nor resolved. E7 may close without it.

**W2 (weak test, non-blocking).** Mutant B-D (exempt every held variable whose name contains `MONGO`) survives: no test holds a second `PATHLYNKS_MONGO_*` variable (e.g. `PATHLYNKS_MONGO_DB`) and expects the slug to stay refused. The contract's whole-prefix mutation hint is killed; this finer variant is a hardening gap only. One extra parametrized case in `tests/test_credential_guard_server_key.py` would kill it.

**W3 (informational).** (a) `refuse_reserved_slug`'s `k.upper() != MONGO_URI_ENV` uses Unicode `upper()`: an environment variable named `PATHLYNKS_MONGO_UR\u0131` (dotless i, operator-controlled) upper-cases to the store URI name and is also exempted from the slug scan (observed). Operator-set only; not reachable by a request. (b) The `timeout` token covers any `TimeoutError` (TCP connect, TLS handshake hang, slow first byte), so the live AT-1420 diagnosis separates dns / tcp-refused / tls / http but not "blackholed connect" from "handshake hang"; EACCES/EPERM-style egress denials fall to `unknown`. Honest limits of an exception-class diagnostic, consistent with E7.4/E7.5.

## Process note for the owner
Checker A and I share the worktree `D:/autoTesting/.claude/worktrees/e2e-e7`. My 14-mutant re-run edited `src/autotester/ui/credential_guard.py` and `src/autotester/stages/reachability.py` in place for about 5.5 minutes (restored by the harness; `git status` clean afterwards). An untracked `tests/test_zz_probe_chkA.py` (not mine, left untouched) was present. Any red a checker A run saw in that window may be mine; re-run those. My temp files: `.work/doctor-e7-chkB.txt`, `.work/mut-chkB.txt`, `.work/chkB-mut.json` (untracked/ignored); the temp probe test was deleted and the temp master worktree removed.
