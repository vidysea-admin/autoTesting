# Verdict - t169-harness-login (coordinator A, dual check)

Date: 2026-10-21 · Cycle checked: 0 · Bound to D:/autoTesting/.worktrees/t169-harness-login · Head 4ff07564 (code a271a187) · Base 8956c9bc
Policy-Version: proportional-verification/2026-10-19.17 · Checkpoint: qa/checkpoints/t169-harness-login.md

## Check plan (step 0)
Diff touches a credential write path (settings page), a script that reads a password, and .env.example. Plan: criterion tests (C1-C3), candidate review (shard_suite --candidates plus extra reference-hit files), 1 falsification per criterion in copies, step 4c diff-scope read, security read of changed lines, Mode D live browser (UI changed), writer/loader round-trip probe. No persona walk (admin settings page; no new flow or user type).

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, invariants (core-invariants credential rules, as touched) hold
TIER: L (credential handling; dual trigger src/autotester/ui/routes_settings.py:89, read by me: the one set_env_value write path)

## Criteria
- C1 MET. Mode D, own server on :8317, temp AUTOTESTER_ROOT: /settings/providers shows 9 rows including AUTOTESTER_HARNESS_EMAIL (type=text) and AUTOTESTER_HARNESS_PASSWORD (type=password, no show/hide button). Saved both through the page: status becomes Set; after the password Save the page outerHTML holds neither the password nor a fragment of it, the field value is empty; an empty Save gives 400 (wipe guard). Write path unchanged (routes_settings.py:89 -> set_env_value). Tests: 12 passed. Falsification: `_WRITE_ONLY = frozenset()` in a copy -> both C1 tests red, green before.
- C2 MET. scripts/run_real_acceptance.py:55-64 reads both keys from os.environ (loaded by load_repo_env at :88); missing -> stderr `MISSING <KEY[, KEY]>: ... <origin>/settings/providers`, return 4 at :101-103 before the app import; no input/getpass/--email remain (diff read; git grep finds no other caller of --email). Password not printed (tests assert it in no output; server log: 0 hits). 23 passed. Falsification: check the email key only (`HARNESS_KEYS[:1]`) in a copy -> 2 of 4 red (password-missing, both-missing), green before. Cross-process probe: load_repo_env on the browser-written temp .env returns the exact password typed.
- C3 MET. .env.example:150-153 documents both keys, empty. test_hosting_deploy 15 passed. Falsification: delete the PASSWORD line in a copy -> test_env_example_documents_every_key_the_code_reads red, green before.

## Other steps
- 4c diff scope: files = .env.example, scripts/run_real_acceptance.py, core/env.py, ui/routes_settings.py, 2 test files, manifest; all listed in What changed. Removed: `getpass` import, `--email` flag, the `input()` and `getpass()` prompts, all required by C2; nothing else deleted.
- Test selection: shard_suite --candidates ran (qa/evidence/t169-harness-login-A/candidates.json; unit mode exits 2 integration-required, as in this repo generally). Extra reference-hit files ran: test_env_loading, test_ui_auth_own_origin, test_approval_signing, test_auth_deploy_files, test_ui_auth_policy_table, test_ui_auth_surface -> 125 passed. No sibling prompt path applies.
- Lint: ruff check src tests scripts clean; autotester doctor clean.
- Security read of changed lines: the password row is masked, never prefilled, no eye even for credentials.view; POST redirects 303 with no echo; the 400 page does not echo the value; closed key set still enforced at routes_settings.py:80-81; the policy row (auth/policy.py:81, settings.manage) is unchanged. No finding.
- Contract fold (US1): qa/contracts/ui-settings.md US1 says exactly six keys and is already stale (page has 7 provider keys plus these 2). Umesh's 2026-10-21 request is the authorizing amendment; not a FAIL. See P2.

FAILURES: none
CAPABILITY-COVERAGE: 3/3 rows reproduced
LIVE-BROWSER: qa/evidence/browser-t169-harness-login-2026-10-21-checker/ (console errors on :8317: 1, the expected 400 of the empty-password Save; a 400 on :8791 in the shared browser log is another session's page)
ISSUES-WRITTEN: none (dual coordinator: no side effects)
PROPOSED-ISSUE: {"id":"P1","sev":"medium","title":"password containing ${NAME} or a literal backslash-n is altered between the settings writer and load_repo_env","detail":"set_env_value renders a double-quoted value that parse_env reads back exactly, but core/env.py load_repo_env uses python-dotenv dotenv_values (interpolation and escape decoding). Probe D:/autoTesting/.work/tmp/chkA/probe_rt.py: 'a${HOME}b' loads as 'aC:\\Users\\Lenovob' and a literal backslash-n loads as a real newline; 11 of 13 test values round-trip. Effect: the script's sign-in is refused loudly for such a password. Not in a criterion; pre-existing loader; first key where exact fidelity matters.","fix":"load with interpolate=False and render single-quoted when a value has a dollar sign or backslash, or reject those characters on the harness password row"}
PROPOSED-ISSUE: {"id":"P2","sev":"low","title":"ui-settings US1 closed key set is stale (six keys) versus the page (nine)","fix":"amend US1 in the contract amendment log citing Umesh 2026-10-21"}
PROPOSED-ISSUE: {"id":"P3","sev":"low","title":"--dry-run never validates the harness login, so a missing key shows only on the real run","detail":"scripts/run_real_acceptance.py:98-103; disclosed by the maker; C2 states exit behaviour for the run, not the dry run."}
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: All three criteria are evidenced by my own test runs, one falsification each, and a live browser walk of the settings page from this worktree in which the password was saved, never echoed, and read back exactly by load_repo_env. The one defensible concern (P1) is a pre-existing writer/loader mismatch for unusual passwords that fails loudly, so it is a ledger candidate rather than a FAIL. A live sign-in against a real account was not run (needs the account and a crawl approval, as the manifest says).
Metrics: start=2026-10-21T07:26:56Z end=2026-10-21T07:40:00Z wall_min=13 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=780 mutants=0 defects_unit=0 defects_6c=0 slow: Mode D plus pytest groups 8 min
