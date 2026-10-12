# Verdict - t201a-delivery-core, fix cycle 2, coordinator A (blind dual check)

Cycle checked: 2
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting. Branch `wave/t201a-delivery-core`, head 701a50e6 (manifest only), code 76ba7da5, `Repair base: 7dd225d4` (verified: ancestor of HEAD).
Work copy: `git archive 701a50e6` in a uniquely named folder on C: with its own venv; `autotester.__file__` and the pytest rootdir printed inside the copy every time. Nothing on D: was checked out or installed into. No real mail, no `.env` value read.

## Check plan (step 0)

Repair range 7dd225d4..701a50e6. Criteria whose input file changed: `delivery/inbox.py` -> C6, C7, C8, C9, C11 (re-run). Untouched inputs (`email.py`, `message.py`, `schema/delivery.py`) -> C1-C5, C10, C12 keep their recorded results. Failed point: the advice-scanner test. Plus the repo-wide scanner tests, ruff, doctor, a trial merge into current master, and the reds a cycle-1 suite reported (by node id; no new full suite, no suite lock).

## Result

VERDICT: PASS
SCOREBOARD: 12/12 criteria met (5 re-run on the repaired file, the failed point re-run, 7 unchanged), 0 invariants touched
TIER: L (outward-facing e-mail, SMTP password in `delivery/email.py:149`; dual-trigger line verified; the repair itself touches no trigger line)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 falsifications reproduced (below); the cycle-0 and cycle-1 rows for criteria with untouched inputs keep their recorded results
LIVE-BROWSER: not-applicable (no UI path in the diff)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Steps

1. Repair diff, read in full (`git diff 7dd225d4 701a50e6`): two files, the manifest and `src/autotester/delivery/inbox.py` (6 lines, only `records_for_run`: docstring wording plus the f-string replaced by concatenation). `tests/advice_scan.py`, `tests/test_cli_advice_resolves.py`, `EXPECTED_SITE_COUNT` (24), every guard: untouched. Whole-unit diff (`6504de03..701a50e6`, 13 files) has no file outside the manifest's list (`.env.example`, `docs/MAP.md`, manifest, `delivery/*`, `schema/delivery.py`, 3 test files, `tests/delivery_fakes.py`). Nothing removed.
2. Regex equality (`evidence/regex-equality.txt`): the pattern strings AND flags built by 7dd225d4 and 701a50e6 are equal for 28 run ids (plain, `.`, `-`, `_`, upper-case, mutual prefixes, `x__email__y`, `x__inbox__y`, `email__x`, 64-character ids, 21 `_` groups); `_CHANNELS` and `_PART` equal. On a real temp store of 502 records (13 runs x 10 users x 2 channels, 1-4 attempts, plus stray `.bak` / `.txt` files) `records_for_run` is identical for 17 run ids and `records_for_key` identical for 260 keys, compared in order, and the run lookups return all 502 records.
3. Advice test file 33 passed. Scanner (`evidence/scanner-check.txt`): `unresolved_in_source(src) == []`; all 13 f-strings in `delivery/*.py` and `schema/delivery.py` interpolate only lower-case names (`code`, `key`, `attempt`); no `.format` call. The scanner is not neutered: the OLD `inbox.py` still reports line 130, a synthetic f-string over a module-level `"|".join(...)` constant reports line 5, the concatenated twin reports nothing; 24 advice sites at head. (Concatenation avoids a scanner that looks for f-strings; the string is a regex, not advice, so no advice text escapes the scan.)
4. Touched criteria, manifest commands re-run at head: C6 4 passed, C7 3, C8 3, C9 4, C11 18 (all match the manifest counts). One input of mine each (`evidence/own-inputs-head.txt`, script `crit_inputs.py`): a transport raising `RuntimeError` with the password, a canary and an address in its text, driven through the whole schedule -> attempts 1..4 at delays 1 / 5 / 30 minutes then terminal, exactly 4 sends, nothing raised (C7, C8), stored error is `RuntimeError`, password, canary and address absent from every file (C6, C9); 8 racing threads for one key -> 1 send; replay x5 -> 1 send; `Alice` / `alice` / `ALICE` / `alice.smith` / `alice.smith.2` are five distinct recipients and `records_for_run('r')` and `('R1')` return nothing for run `r1` (C11); a claim marker with no record is never resent and is closed as "not resent" only after `STALE_AFTER` (C11). `KeyboardInterrupt` propagates (not an `Exception`; matches `except Exception`).
5. Affected tests, file-scoped, `-p no:xdist -o addopts=`: the three delivery files 97 passed; `test_cli_advice_resolves` 33; the 16 other repo-wide scanner files the manifest names 240 passed (`evidence/run-scan.txt`). `ruff check src tests scripts` clean; `autotester doctor` clean at head; `inbox.py` 207 lines.
6. Ruling on `test_env_example_documents_every_key_the_code_reads`: PRE-EXISTING, not this unit's. Red with the same two keys (`AUTOTESTER_SCHEDULE_GRACE_MINUTES`, `AUTOTESTER_TICK_INTERVAL_S`) at the merge base 6504de03, at 7dd225d4 (repair absent) and at 701a50e6 (`evidence/run-reds-*.txt`). It is green after integration (step 8).
7. Falsifications (`evidence/falsifications.txt`, one copy per mutant, each green before, red after, restored):
   - Repaired point: `records_for_run` f-string reintroduced -> `test_the_collector_reports_what_it_could_not_resolve` red (33 -> 1 failed, finds `inbox.py` line 131); original restored -> 33 passed.
   - C11 widen `records_for_key` to `\..*\.json` -> 2 red: `test_a_dotted_prefix_user_does_not_suppress_the_shorter_one`, `test_lookups_match_whole_file_names_and_ignore_stray_files`; restored 17 passed.
   - C11 widen `records_for_run` (`"__" + _PART` -> `".*"`) -> 2 red: `test_run_and_user_ids_that_spell_the_separator_do_not_collide`, `test_lookups_match_whole_file_names_and_ignore_stray_files`; restored 17 passed.
8. Trial merge of 701a50e6 into CURRENT master 09fc65a8 (throwaway clone on C:, `evidence/run-m2-*.txt`): ONE textual conflict, `.env.example` (both sides appended at the end of the file); `docs/MAP.md` auto-merges. Resolution by hand: keep master's tail, add only the two `AUTOTESTER_SMTP_FROM_NAME` lines; the branch's trailing `AUTOTESTER_MODEL=` must NOT be added back (master already has it once, higher up). After that: `test_cli_advice_resolves` 33 passed with `EXPECTED_SITE_COUNT` = 24, no count change needed; `test_hosting_deploy` all 10 passed (the env-example red clears: master documents the two scheduler keys and the unit adds its own); delivery 97 passed; ruff clean; doctor clean. The unit therefore merges with that one hand-resolved conflict and nothing else.
9. Reds from the cycle-1 suite, by node id:
   - advice test: GREEN at head (33), green at merge.
   - `test_env_example_documents_every_key_the_code_reads`: pre-existing (step 6), green after merge.
   - `test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere`: green at head, base, merge base, merge and master.
   - `test_env_creation_is_coordinated_across_processes`: pre-existing, not this unit's. Red 5 of 5 at the old merge base, 7dd225d4 and head (a 15 s child-ready wait times out, same failure at all three); on current master it is intermittent under machine load: it passed alone on both master 09fc65a8 and the merge (twice each), failed once in a combined run on master itself (no branch code in that tree) and once on the merge when five processes ran at once. The unit touches nothing it starts.

PROPOSED-ISSUE: {"severity":"low","feature":"t201a-delivery-core","type":"integration","title":"Merge conflict in .env.example against master 09fc65a8","evidence":"both sides append at the file tail; resolution = master's tail + the two AUTOTESTER_SMTP_FROM_NAME lines, do not re-add the branch's trailing AUTOTESTER_MODEL=","note":"maker resolves at merge"}
PROPOSED-ISSUE: {"severity":"low","feature":"test-env-creation","type":"flaky-test","title":"test_env_creation_is_coordinated_across_processes is red on the old base and intermittent on current master under load (15 s child-ready wait)","evidence":"qa/evidence/t201a-delivery-core-r2-A/run-env-creation-*.txt, run-comb-*.txt","note":"not this unit; backstop owner"}

EXPLANATION: The cycle-2 repair is a 6-line, behaviour-neutral change confined to `records_for_run`; the old and new regex strings are equal and both lookups return identical ordered lists on a 502-record store. The failed advice test is green, and goes red when the f-string is put back. Every red the cycle-1 suite reported is either green or shown red on the merge base without this unit; the trial merge into current master needs only the hand-resolved `.env.example` and then passes advice (24 sites), hosting-deploy, delivery, ruff and doctor. No third cycle is needed. Mid-check the dispatch's "current master" moved from f6003e87 to 09fc65a8; the trial merge was redone on the new head. The L wall budget (45 min) was passed by about 10 min, mostly the machine-load re-runs of step 9; every mandatory item was complete, so this is not a CONTINUE-NEEDED. No full suite was run (per dispatch; cycle 1 ran it; `full-suite trigger: none new`, 6c covers the integration).

Metrics: start=2026-10-12T02:37:43+05:30 end=2026-10-12T03:36:00+05:30 wall_min=58 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=3 mutations=3 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=3500 mutants=3 defects_unit=0 defects_6c=0
