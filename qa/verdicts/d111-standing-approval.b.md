# Verdict - d111-standing-approval (checker B, adversarial, fix cycle 1)
Verdict: PASS
Cycle checked: 1
Head tested: f3a5b12a (branch feat/d111-standing-approval, worktree .claude/worktrees/d111-standing). Security trigger: consent gate (D-018 / D-111). B half of the dual check; the manifest is not flipped by this verdict.

Cycle 1 touches only `core/consent.py` (3 lines, `git diff d20eb037 HEAD -- src`), `tests/test_consent.py`, `tests/test_cli_advice_resolves.py` and the manifest. `schema/approval.py`, `cli_crawl.py`, `ui/routes_crawl_approval.py` and `auth/policy.py` are byte-identical to the cycle-0 PASS head, so the cycle-0 B findings (S1-S10, N1-N4) carry over unchanged and are not re-opened.

## The two cycle-1 fixes
1. Pasteable grant command. `core/consent.py:153-156` `_grant_command` is a pure command again (no `(or --standing, ...)`). `core/consent.py:258-262` appends the standing alternative as its OWN line, `To keep it valid until revoked, replace --expires <YYYY-MM-DD> with --standing.`, only `if kind in STANDING_KINDS` (= `{CRAWL}`, `schema/approval.py:56`). Hint placement is after the command, so `ui/routes_crawl.py:46` (`detail.split("Grant one with:", 1)[0]`) and `re.search(r"autotester approve.*")` in `tests/test_crawl_real_cli.py:134` still isolate the command line.
2. Advice-site guard. `tests/test_cli_advice_resolves.py` registers `("cli_crawl.py", "revoke")` and `EXPECTED_SITE_COUNT` 31 -> 32 with a history comment. Registering (not rewording) is correct: the `approve --standing` help (`cli_crawl.py:238-239`) tells an operator to run `autotester revoke`, which is what the guard freezes; it now also falls under the "every named command resolves" test.

## Re-run, mine (worktree, one pytest at a time, `-o addopts=`)
- `tests/test_crawl_real_cli.py tests/test_cli_advice_resolves.py tests/test_consent.py`: 84 passed, 1 failed. The failure is `test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve`, `unresolved_in_source` reports `ui/routes_crawl_approval.py:203` (the `validate_grant_bounds(...)` call). It is baseline AT-1024: `qa/verdicts/integration-6c-int1017-r7.md:22` records the same test red on the base with the same site (`routes_crawl_approval.py:184`; the line moved to 203 only because the file grew in this unit). Not a regression of this unit.
- `tests/test_standing_approval.py tests/test_standing_approval_grant.py tests/test_approve_cli.py tests/test_explore_consent.py tests/test_ui_crawl_approval.py tests/test_cli_release.py`: 62 passed (same count as the manifest).
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 29 violations, ALL `decision-citation-dangling` (D-110/D-111 have no entry on this branch: `qa/contracts/consent.md`, the manifest, the 6c and d111 verdicts). No size / function-length / duplicate / name / root rule. `core/consent.py` = 296 lines.

## Mode B probe (`.work/probe_b_c1.py`, run as a temporary copy under `tests/` for the repo conftest key, then deleted; 117 passed)
- Cross product of kind (read, crawl, adversarial, live_case, video_review) x bounds (defaults; 150 actions + 900 s; 10/25/30.5 s; probes only; production with caps; 0.001 s; 2000 actions + 86400 s) x target (plain; with space, `?`, `&`; with `#frag`): for each refusal, exactly one line holds `autotester approve`, it has no `(` and no `--standing`, `shlex.split` yields no token ending `,`; after substituting the three placeholders the pasted command exits 0, writes exactly one row, and `require_approval` with the original bounds accepts it. The row's `max_actions`/`max_probes`/`production`/`target`/`run_kind` equal the refused run, `expires_at` set, `standing` False: nothing wider than refused is granted.
- Hint exclusivity: `--standing` appears in the refusal for crawl only, on one line that is not the command line; absent for read, adversarial, live_case, video_review. A refusal on a production-declared project (`require_project_approval`) still keeps the command line clean (the D-088 note is appended after the hint).
- Applying the hint literally (`--expires <D>` replaced by `--standing`) to every kind's command: crawl exits 0, writes a signed standing row with the refused caps (40 actions, 90 s), accepted at 2099-01-01, and REFUSED for a run of 41 actions (no wider than asked); every other kind exits 1 and writes nothing. So the hint cannot be followed into a standing adversarial / live_case / read / video_review grant.
- Cannot make the standing hint appear for adversarial: not by kind, bounds, `production=True`, or project production flag.

## Findings (none blocking; both pre-existing and unchanged by this diff)
- F1 (info): a run whose recorded `actions` exceeds the 2000 grant cap prints a command that exits 1 with `max actions 5000 exceeds the limit of 2000` (probe `test_over_cap...`). Fail closed, clear message, same on the base (`_grant_command` bounds logic is untouched).
- F2 (info): `--wall-clock` below 0.001 is rejected by typer (`min=0.001`, `cli_crawl.py:239-240` area), exit 2. No real run has such a bound; same on the base.
- N1-N4 from the cycle-0 B verdict stand as written (same-day re-grant after revoke shares an id; UI treats any non-empty `standing` as true; `auth/policy.py` outside D-111's Changes-authorized list, for Umesh to ratify; CN4 text was subsequently amended in `qa/contracts/consent.md`).

## Verdict
PASS, cycle 1. Both 6c regressions are fixed at the cause with tests that fail on the old code (the new `tests/test_consent.py` test asserts no `(`/`--standing` in the command line and exclusivity for adversarial), the printed grant command is pasteable and grants exactly the refused run for all five kinds, and the standing alternative is crawl-only. The cycle-0 gate semantics are untouched. Remaining before close-out: A's cycle-1 verdict, then the 6c integration re-run after merge (as the manifest says); the baseline AT-1024 red is not this unit's.
