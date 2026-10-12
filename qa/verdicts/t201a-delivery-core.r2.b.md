# Verdict - t201a-delivery-core - cycle 2 - coordinator B (repair, blind dual check)

Cycle checked: 2
Bound to: D:/autoTesting. Branch wave/t201a-delivery-core, head 701a50e6 (manifest only), code SHA 76ba7da5, Repair base 7dd225d4 (verified: ancestor of HEAD; repair range = 2 files).
Policy-Version: proportional-verification/2026-10-10.9. Dual check: required (dual-trigger security src/autotester/delivery/email.py:149, the line exists and holds `client.login`).
Coordinator B writes PROPOSED-ISSUE lines only: no ledger write, no manifest flip, no merge, no push. No earlier verdict, checkpoint or evidence of this unit was opened; no `.a.md` / `-A` file was opened.

## Plan (step 0)
Tier L (SMTP password module; outward-facing mail). The repair is one regex expression plus a docstring in `src/autotester/delivery/inbox.py`. Checks: (1) behaviour equality base vs head over a stressed store, (2) cross-read, (3) `deliver_once` regression, (4) repair diff in full + whole-unit scope scan, (5) head tests/lint/doctor, (6) falsifications. SERIAL: none needed; copies are separate and independent runs went in parallel. No UI surface changed, so no browser check. No full suite (policy .7: no suite at a repair cycle; the affected-test files below were run). No spawn used; I ran the steps myself.

## Result by step
1. Equality (probe `qa/evidence/t201a-delivery-core-r2-B/probe_equality.py`, run in two `git archive` copies on C: with their own venvs; `autotester.__file__` printed inside each copy, see `probe-build.txt`, `probe-dump.txt`): 88 deliveries (27 run ids x 17 user ids x 2 channels, chosen: prefix/suffix run ids, `.`, `-`, `_`, upper case, `x__email__y` vs `x` + `y__email__z`, `email`/`inbox` as ids, same user over many runs, 19 keys that fail to 4 attempts or once-then-ok, unexpected exception, 5 stale-claim "outcome unknown" records). Fake transport only, no network.
   | Item | Rows | Mismatch |
   |---|---|---|
   | record file names on disk | 149 | 0 (identical sets) |
   | attempt-claim file names | 149 | 0 |
   | file contents (created_at removed, it is wall clock) | 298 | 0 |
   | `deliver_once` return sequence per delivery (88 x 12 calls) | 88 | 0 |
   | `records_for_run`: 27 runs with records + 20 with none | 47 lookups, 149 rows | 0; all 20 no-record runs return `[]` on both |
   | `records_for_key`: 925 delivery keys + 9 odd keys, order included | 934 lookups, 149 rows | 0 |
   | `latest(key)` | 918 | 0 |
   All four dump files have the same sha256 (`probe-hashes.txt`).
2. Cross-read: head code over the store written by base code, and base code over the store written by head code: both byte-identical to base/base (4 of 4 identical). The repair does not change what is on disk.
3. `deliver_once` on head (`probe_basics.py`, fake transport): first send recorded once (1 send, 1 file); second call same key sends 0 more; 20 trials of two threads racing the same key (barrier) each sent exactly once with exactly one record file.
4. Repair diff 7dd225d4..701a50e6 read in full: `inbox.py` (the f-string over `_CHANNELS` replaced by the same pattern built with `+`; docstring now says "file-name order", which matches `sorted(self.records_dir.iterdir())`; no def/class/test removed, nothing else) and the manifest (cycle bookkeeping; the removed lines are the cycle 1 pre-check lines and fix-cycle fields). Whole-unit diff `6504de03..701a50e6`: 13 files, all in the manifest's "What changed" list; `tests/advice_scan.py`, `tests/test_cli_advice_resolves.py`, conftest, qa/contracts, qa/hooks, .claude, .githooks, pyproject.toml and uv.lock: untouched (0 lines).
5. On head (copy, own venv): `tests/test_cli_advice_resolves.py` + three delivery files: 130 passed (33 + 97), including the cycle 1 red `test_the_collector_reports_what_it_could_not_resolve`. `ruff check src tests scripts`: All checks passed. `autotester doctor`: clean. I read `tests/test_cli_advice_resolves.py` in full. Side note: `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads` is red on head naming only `AUTOTESTER_SCHEDULE_GRACE_MINUTES` and `AUTOTESTER_TICK_INTERVAL_S` (read by `stages/scheduler.py`, which this unit does not touch; present at the merge-base 6504de03 where `.env.example` lacks them): pre-existing, not this unit's.
6. Falsifications (4 copies of head, PYTHONPATH on each copy, `__file__` printed inside each, pristine copy m0 green first: 130 passed). Files `falsify-m*.txt`.
   | Mutant | Edit | Result |
   |---|---|---|
   | m1 (the repaired point) | `records_for_run` pattern back to `rf"(?:{_CHANNELS})__{...}"` | RED: exactly `test_the_collector_reports_what_it_could_not_resolve` (1 failed, 129 passed; `delivery/inbox.py:131` reported) |
   | m3 | drop the `"__"` after the run id | RED: 5 tests in `test_delivery_failure.py` (always-fails bound, successful-send-once, separator-spelling, whole-file-name, clock-skewed worker) |
   | m4 | run part followed by `.*` instead of `__` + user part | RED: `test_run_and_user_ids_that_spell_the_separator_do_not_collide`, `test_lookups_match_whole_file_names_and_ignore_stray_files` |
   | m2 | drop `re.escape` around the encoded run id | NOT CAUGHT: 130 passed. My equality probe on the m2 code does see it: `records_for_run('run.1')` returns 10 rows instead of 6 (`.` matches `-`), and `'run-1.'`, `'run.'`, `'x.'` return rows although they have none (`probe-dump-m2.txt`). |
   Restore: the copies were separate throwaways; the bound tree and head copy were never edited.

## Findings
No blocking finding. The repair is behaviour-equal to 7dd225d4 on every row above, and the one failed point is fixed and guarded.

PROPOSED-ISSUE: {"severity":"medium","feature":"t201a-delivery-core","title":"records_for_run exact-match property for run ids containing '.' is unguarded: dropping re.escape stays green","evidence":"throwaway copy of 701a50e6, inbox.py records_for_run with re.escape(...) removed: 130 passed (tests/test_cli_advice_resolves.py + 3 delivery files); equality probe on the same copy: records_for_run('run.1') returns 10 rows vs 6, records_for_run('run.') returns 1 row vs 0, 'run-1.' 7 vs 0, 'x.' returns rows vs 0 (qa/evidence/t201a-delivery-core-r2-B/probe-dump-m2.txt)","fix":"add a test with run ids 'run.1' next to 'run-1' (and 'run.' vs 'run-') asserting records_for_run returns only its own run; product code is correct today (src/autotester/delivery/inbox.py:131-134)","found_by":"checker-unit"}

PROPOSED-ISSUE: {"severity":"low","feature":"t201a-delivery-core","title":"test_hosting_deploy env-key drift test red on this branch for two scheduler keys (pre-existing at merge-base 6504de03)","evidence":"pytest tests/test_hosting_deploy.py in a head copy: 1 failed, 9 passed, undocumented env keys ['AUTOTESTER_SCHEDULE_GRACE_MINUTES','AUTOTESTER_TICK_INTERVAL_S']; both read at src/autotester/stages/scheduler.py, absent from .env.example at 6504de03; the unit's .env.example diff adds only AUTOTESTER_SMTP_FROM_NAME","fix":"owned by the scheduler unit or the integration merge; not this unit","found_by":"checker-unit"}

## Verdict
VERDICT: PASS
SCOREBOARD: 1/1 repaired criterion met (cycle 1 failed point: advice-scanner test green, behaviour equal); no passed criterion's input file touched by the repair (only `delivery/inbox.py` `records_for_run`), so the other criteria keep their recorded results.
TIER: L (outward-facing mail; SMTP password in `src/autotester/delivery/email.py:149`; repair itself is S-sized in `inbox.py`)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 repaired-criterion falsification reproduced (m1 green before in a pristine copy, red after on the named test)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/delivery/inbox.py, qa/manifests; no UI surface)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (builder: claude-sonnet-subagent; checker is a fresh subagent on the Anthropic session, no ANTHROPIC_BASE_URL override)
EXPLANATION: The repair swaps an f-string for string concatenation of the identical regex; 88 deliveries over stressed ids give byte-identical files and identical answers for 47 run lookups, 934 key lookups and 918 `latest` calls between base and head, in both cross-read directions, and `deliver_once` still sends once and survives a two-thread race. The advice test goes red when the f-string is reintroduced and green again on the repaired code. The exact-match anchoring is guarded for the `__` and the trailing part but not for `re.escape` (m2 stays green): a test gap, not a product defect, filed as a PROPOSED-ISSUE. No evidenced new failure beyond cycle 1's single failed point.
Metrics: start=2026-10-12T02:37:42+05:30 end=2026-10-12T02:58:00+05:30 wall_min=20 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=20 mutations=4 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1218 mutants=3 defects_unit=0 defects_6c=0
