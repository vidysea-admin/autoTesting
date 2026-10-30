# Verdict - d110-allow-all (Checker A, contract)

**Verdict:** PASS
**Status:** PASS (Checker A of the dual check; Checker B's verdict is separate and both must PASS)
**Cycle checked:** 0
**Reviewed SHA:** 51dbbf80 (code; base 19a9dd79); manifest read at 6e6e7810 (adds the Round cap line only)

## Scope
D-110 criteria C1-C4 of `qa/manifests/d110-allow-all.md`, judged against D-110 and `qa/contracts/auth.md` AU18-AU20.
`git diff 19a9dd79..51dbbf80 --stat`: exactly five files, `src/autotester/auth/config.py`, `src/autotester/ui/helpers.py`,
`tests/test_ui_auth_host_and_consent.py`, `tests/test_ui_auth_own_origin.py`, `tests/test_ui_origin_guard.py`. All are within D-110
Changes-authorized (the two source files and their tests). No `qa/contracts/`, `docs/DECISIONS.md`, ARCHITECTURE.md or enforcement path touched.

## Criteria
- C1 PASS. `helpers.py:206-212` `_origin_allowed` short-circuits on `_allow_all("AUTOTESTER_ALLOWED_ORIGINS")`; `helpers.py:224-230` `_host_allowed`
  returns True when `*` is in either list. Tests `test_star_in_allowed_origins_opens_both_the_origin_and_the_host_guard` and
  `test_au18_a_wildcard_in_the_allowed_origins_is_an_opt_in_allow_all` (login POST 303) pass.
- C2 PASS. `ALLOWED_HOSTS=*` opens only the Host guard; a cross-site POST is still 403
  (`test_star_in_allowed_hosts_opens_only_the_host_guard_not_the_origin_guard`). Reproduced directly (Finding 1).
- C3 PASS. `config.py:61-78` `_check_hosted`: `*` satisfies the allow-list and returns before `_check_public_origin` / the own-origin pin, on any
  bind. Tests: parametrize rows `("*","",True)`, `("","*",True)`, `(" , * "," ,",True)`, PUBLIC rows `wild-star-origins-no-public`,
  `wild-star-hosts-no-public`, and `test_au20_a_star_allow_all_lets_any_bind_start` (bind 0.0.0.0, ::, *, "").
- C4 PASS. With no `*` nothing changes: `_listed` (`helpers.py:195-198`) still drops `*`; `_allow_all` only matches the exact token `*` after the same
  comma/space tokenising; `(",","",False)` still fails startup; the literal-list assertions are untouched. The AT-761 repeated Host/Origin refusal
  (`_OriginGuard`, `names.count`) runs before the allow-lists and is unaffected by `*`. The only test edits are inversions of the three old
  "no wildcard" assertions plus additions, each citing D-110.

## Independent checks (run in this worktree, `-o addopts=`, no `-q`)
- `pytest tests/test_ui_origin_guard.py tests/test_ui_auth_own_origin.py` -> `205 passed, 2 warnings in 18.84s`
- `pytest tests/test_ui_auth_host_and_consent.py` -> `13 passed, 1 warning in 3.44s` (205 + 13 = the maker's 218)
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean` (the maker's 4 root-clutter violations were main-checkout clutter, absent here; only advisory decision-citation warnings)

## Baseline of the 7 full-suite failures
Detached worktree of 19a9dd79 (`.work/d110-base`, removed afterwards, `git worktree prune` run); same commands on base and branch:

| Test | Base 19a9dd79 | Branch | Verdict |
|---|---|---|---|
| test_container_ci_workflow.py::test_exit_trap_removes_container_without_unbound_error | PASS | PASS | not reproduced on either side in isolation: full-suite-only flake, not D-110 |
| test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild | PASS | PASS | same |
| test_infra_trio.py::test_verify_gates_keeps_exit_code[0] | FAIL | FAIL | pre-existing; cause `WSL ... execvpe(/bin/bash) failed` (environment) |
| test_infra_trio.py::test_verify_gates_keeps_exit_code[3] | FAIL | FAIL | pre-existing; same WSL cause |
| test_role_port_mail.py::test_w2_a_mail_that_arrived_is_observed_through_the_read_only_reader | FAIL | FAIL | pre-existing |
| test_ui_auth_envkeys.py::test_au21_no_onboarded_key_becomes_an_environment_variable[anthropic-ANTHROPIC_BASE_URL] | FAIL | FAIL | pre-existing |
| test_ui_auth_envkeys.py::test_au21_env_add_and_undeclare_leave_nothing_exported[anthropic-ANTHROPIC_BASE_URL] | FAIL | FAIL | pre-existing |

Result lines, base and branch identical: `27 passed` (container+flake), `3 failed, 6 passed` (infra_trio+role_port_mail), `2 failed, 21 passed` (envkeys).
Five failures are identical and pre-existing on base; two did not fail in isolation on either side. None touches a D-110 file. Full suite not rerun (memory budget).

## Findings
1. WARNING (not a breach of D-110 `What`; needs a human/maker follow-up). `ALLOWED_HOSTS=*` alone gives a hosted server where no browser POST works.
   Reproduced with `AUTOTESTER_ALLOWED_HOSTS=*` and no `ALLOWED_ORIGINS`:
   `origin_refusal({'origin':'http://34.47.136.12:8000','host':'34.47.136.12:8000','sec-fetch-site':'same-origin'})` returns
   `cross-site request refused: origin 'http://34.47.136.12:8000' is not allowed (D-066)` while `_host_allowed('34.47.136.12:8000')` is True;
   with `ALLOWED_ORIGINS=*` the same call returns `None`. A browser sends `Origin` on a same-origin POST, so login, logout and every admin route would 403.
   Startup passes in this configuration (`config.py:65-69`), so startup and the guard disagree, which `config.py:62-64` says AU20 exists to prevent.
   D-110 `Result` tells DevOps to set `AUTOTESTER_ALLOWED_HOSTS=*`; that instruction yields an unusable login. The contract now states `ALLOWED_ORIGINS=*` is the working setting.
   Follow-ups (human gate, not mine to edit): a DECISIONS entry correcting D-110 `Result`, and a maker unit making `HOSTS=*` also open the Origin guard, or failing/warning at startup when only `HOSTS=*` is set. Tell DevOps to use `ORIGINS=*` meanwhile.
2. LOW. `config.py:73-75`: the early return on `*` skips `_check_public_origin(required=False)`, so a set-but-malformed `AUTOTESTER_PUBLIC_ORIGIN` is not validated under `*`. D-110 `What` says the check "no longer requires" it, and `PUBLIC_ORIGIN` is read only in `config.py`. Accepted and recorded in AU20.
3. NOTE. `qa/contracts/hosting.md:121` (HO13, DEFERRED TO UBUNTU) still says `AUTOTESTER_ALLOWED_ORIGINS=https://<host>` set and `*` refused. D-110 authorises auth.md AU18-AU20 only, so I did not edit hosting.md; once a domain exists that criterion would conflict with D-110. HUMAN_GATE: keep `*` refused after TLS/domain, or retire the criterion.
4. NOTE. Manifest `Round cap` line (6e6e7810) judged as part of the manifest: SECURITY CLASS, D-014 never caps it; consistent with the auth/guard scope.
5. NOTE. `.env.example:62-67` comments do not mention the `*` option (documentation drift, low; not a D-110 authorised file).

## Contract amendment
`qa/contracts/auth.md` AU18, AU19, AU20 amended (criticality HIGH, dual check; dated 2026-10-30; cite D-110): AU18 gains the opt-in `*` rule, `HOSTS=*` as Host-only, an explicit statement that `HOSTS=*` alone is not a working hosted deploy and `ORIGINS=*` is, plus re-derive and mutation hints; AU19 replaces "no wildcard" with the D-110 exception; AU20 records that `*` counts as set and skips the own-origin and PUBLIC_ORIGIN checks and that startup does not distinguish the two lists.

## Limits
Full suite not rerun. The two "flake-only" failures are inferred from isolated passes, not reproduced under full-suite load. No sabotage mutation run. Checker B's independent verdict is required for the dual check.
