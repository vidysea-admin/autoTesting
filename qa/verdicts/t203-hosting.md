# Verdict: t203-hosting (cycle 1, repair checker, single checker)

Checked: 2026-10-07. Bound to `D:/autoTesting/.worktrees/t203-hosting`, branch `wave/t203-hosting`, code 9a644597 (fix on 6be74d89; base 7782df41 = current origin/master, so there is no merge diff). Policy-Version: proportional-verification/2026-10-06.6 (the .7 rules apply too). Cycle checked: 1. Resume: 0 of 2 (first dispatch of cycle 1), completed by Resume: 1 of 2 below.
Checkpoint: qa/checkpoints/t203-hosting.md. Authority: D-072. Contract: qa/contracts/hosting.md. The cycle-0 verdict is at qa/verdicts/t203-hosting.r0-1.md.

VERDICT: PASS (see the Resume 1 addendum at the end; the sections above are the first dispatch, written while the suite was running)
SCOREBOARD: the 5 failed criteria (HO1, HO2/HO11, HO11/HO13, HO18, HO38) are all MET on my own evidence; the one mandatory check not yet complete is the single full suite (running, 36% when this was written). All other rows keep their cycle-0 ruling (MET / legitimately deferred / BLOCKED-CAPABILITY).
TIER: L (concurrency in `src/autotester/ui/run_queue.py`, config in `docker/compose.prod.yml` and `.env.example`, env loading in `src/autotester/core/env.py`, protected edit `tests/conftest.py`). Single checker: no security/auth/tenancy or production-write trigger.

## Check plan (step 0)

| Signal | Check |
|---|---|
| Fix diff 6be74d89..9a644597 (12 files, +332/-26) | each failed criterion re-run end to end plus a named falsification in its own copy; affected tests; importers of `core/env.py` |
| Concurrency/timing (`_persist`, `_work`) | my own probes: failed write then restart, SystemExit, CancelledError, KeyboardInterrupt through a real thread spawner |
| Deploy files | real `docker compose config` (client only), guide claims read against code |
| Protected conftest edit | 3 named tests re-run with an injected crash, with and without the fix |
| UI surface (queue panel) | Mode D browser check by a Playwright sub-checker, loopback only, scratch data root, no run started |
| Docker | BLOCKED-CAPABILITY (daemon down): build, up, HTTPS, supervision, restart persistence, `docker diff/history` |
| Full suite | one `uv run pytest`, suite lock |

## Per-criterion results (the five failed rows)

| Row | Result | Evidence (own runs) |
|---|---|---|
| HO1 (AT-782) | MET (LOCAL) | the test now asserts the six contract canaries (`.env`, `.env.local`, `projects/x/runs/r1/secret.txt`, `profiles/x/Cookies`, `.work/auth/users.json`, `.work/audit.jsonl`: read in `_HO1_CANARIES`) plus six more, and `.env.example` is not ignored. Falsified: dropping each of 7 `.dockerignore` rules (`**/.env`, `**/.env.*`, `**/projects/`, `**/profiles/`, `.work/`, `qa/evidence/`, `.git/`), one copy each, green before, `1 failed` after, 7 of 7. The cycle-0 survivor `**/.env.*` is now killed. BUILD-HOST half BLOCKED-CAPABILITY |
| HO2 (AT-783) | MET (LOCAL) | `core/env.py` treats an empty inherited value as unset. Mutant back to `key in os.environ`: `1 passed` -> `1 failed`. Fresh-interpreter probe: `ANTHROPIC_API_KEY=` and `AUTOTESTER_APPROVAL_KEY=` empty plus a `<data>/.env` with real values loads both; an explicit non-empty `GEMINI_API_KEY` still wins. Importers (36 test files, `-m "not harness"`): 266 passed, 1 skipped. inspect/logs BLOCKED-CAPABILITY |
| HO11/HO13 (AT-784) | MET (LOCAL, doc) | real `docker compose -f docker/compose.prod.yml config` with `.env.example` as server.env: no domain rc=0, `--profile https` without a domain rc=0 (`AUTOTESTER_DOMAIN: localhost`), 8000 published on 127.0.0.1 only, 6080 only `expose`. Mutant with `:?` restored: rc=1 `required variable AUTOTESTER_DOMAIN is missing` (the cycle-0 failure) and the guard test red. Guide claims read against code: `ui/helpers.py:195 _origin_allowed` does read `AUTOTESTER_ALLOWED_ORIGINS`; `ALLOWED_HOSTS` is nowhere in `src` (nor on origin/master 7782df41), so "ships with AT-758 ... not in this release" is true; 6080 is not published and the tunnel claim is gone; the UFW-bypass note is correct for Docker. Guide mutants (re-add `http://localhost:6080`; "ships with" -> "is enforced by") each `1 passed` -> `1 failed` |
| HO18 (AT-785) | MET | (a) full disk: `_persist` logs and never raises, all three call sites use it (`run_queue.py:99,114,189`), the entry marked running is always launched, the slot goes to the next waiter. Mutant bare `_save()`: red. (b) `BaseException`: `_work` records `interrupted` with the class name, re-raises, and `finally` still frees the slot. Real thread spawner probe with SystemExit, CancelledError and KeyboardInterrupt: each entry `interrupted`, reason = class name, next waiter `done`, the abort propagates. Mutants (abort recorded DONE; abort swallowed; `finally` to `else`): each red on `test_a_run_cut_off_by_exit_or_cancellation_is_not_recorded_as_done`. Restart after a failed write, my probe: see "New hole check" |
| HO38 / conftest (AT-786) | MET | `_inline_run_queue` re-raises runner crashes and keeps `RunRefused` quiet. With a crash injected in `_run_queued`: the 3 named tests (`test_a_run_that_stays_on_known_routes_asks_for_nothing`, `test_a_run_on_a_project_with_no_flowspec_asks_for_nothing`, `test_ui_run_needs_no_human_approval_when_credentials_are_provisioned`) go `3 passed` -> `3 failed` with the shipped fixture, and stay `3 passed` with the re-raise disabled (the cycle-0 weakness, reproduced). The new fixture test is red with the re-raise disabled. No existing assertion edited (the diff since cycle 0 touches tests only by adding and by the conftest fixture). Protected change justified as in cycle 0 |

Affected tests, bound tree, the manifest set plus `test_run_queue_resilience.py` and `test_env_loading.py`: 228 passed, 1 skipped (a live-Chromium RAM gate, AT-576), twice. `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: clean. Diff scope (4c): the 12 files in the fix diff are all in the manifest, nothing removed beyond the one conftest line it replaced and the matcher lines the HO1 fix rewrote; `qa/contracts` untouched.

## New hole check on the AT-785 fix (task item 2)

- `BaseException` handling re-raises correctly: confirmed above, including KeyboardInterrupt, and the `finally` still runs `_finish` so the slot is freed and the next waiter starts.
- `_persist` swallows write errors. What a restart does after a failed write (probe `probe785.py`, writes fail after alpha running and beta queued were saved): in memory both end `done`; after a restart alpha (really finished) is shown `interrupted` and beta (really already ran) is launched again, a second run. The window is a failing data disk AND a restart before any later write succeeds: once one write succeeds the file is rewritten whole (probe B: recover launches 0). The maker disclosed the trade-off, HO18's "slot always released" is met, and the contract's "not re-executed" applies to entries left `running`, not to a stale `queued` row. Filed as AT-790, low, not a FAIL.
- Boot-time recovery is real: my own uvicorn on a scratch root with a seeded `running` row rewrote it to `interrupted` at startup with no request sent (lifespan `get_queue()` in `ui/app.py:70`). The browser sub-checker's note that recovery happens "lazily on the first report visit" is wrong; it did not look at the file between startup and the first visit.

## Mode D browser check (queue panel)

Sub-checker a8f22cf47f5b1683d, Playwright MCP, own tab, `127.0.0.1:8767` only, scratch data root with 3 fixture projects (no cases, so no real run could start) and a seeded queue; no Test button pressed; both servers it started were killed by PID and the ports confirmed free. Evidence: `qa/evidence/browser-t203-hosting-2026-10-07-checker/` (7 screenshots, report.json, queue-after-recovery.json).

- `/`: 200, 0 console errors. `/projects/alpha/report`: 200, 0 console errors at 1280 and 390 px, stable on reload; panel "Run queue", summary "Server: 0 of 2 run slots busy, 0 waiting", newest-finished first, each row a status pill plus time plus reason; the recovered `running` row shows `interrupted` with the restart reason and was not re-run; reasons shown for refused, interrupted, failed (class name only); a script-tag reason was escaped (`window.__xss` unset, 0 script elements). `/projects/beta/report`: only beta's rows (project filter works). `/projects/quiet/report`: no entries, no blank card.
- Not seen on the live server: `queued` and `running` rows, because a seeded queued row is started and refused at once on a case-less project. Those two states and the `meta refresh` were seen only in an in-process render of the same `queue_panel` function (screenshot 07). Disclosed gap, not a substitute for a live run; running a real case was out of bounds.
- Defect AT-791 (low): a reason with a long unbreakable token overflows the card and makes the page scroll sideways (scrollWidth 1391 > 1280; 1121 at 390 px); the cause is the plain `<span class='meta'>` in `run_queue_view.py:29`. Observations, not defects of this unit: the top nav spills 32 px at 390 px on every page; refused, interrupted and failed pills share one amber colour (told apart by label); queue position is server-wide.
- The sub-checker's 404 on a seeded `done` row's run link is a fixture artifact (no envelope), expected.

## Full suite (mandatory, NOT complete)

One `uv run pytest --deselect tests/test_crawl_inventory_live.py` (that file deselected by name: pre-existing hang, as instructed), no `-q`, no `-x`, in the bound tree. Suite lock `D:/autoTesting/.work/suite.lock` acquired 2026-10-07T19:29:29+05:30 (it was held by the t190-ux checker until 19:28, so no lock wait of mine). Log: `C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/a2bbaa41-59b6-48f1-8ec7-8aa0d97b8a5a/scratchpad/suite_c1.log` (the wrapper appends `EXIT <rc> <time>` and removes the lock when the suite ends). It was at 36% with no failure marker at 19:47 (stalls of several minutes inside the 29-36% band on a host running about a dozen other pytest runs, free RAM about 4 GB); at that rate it cannot end inside this checker's 45-minute wall deadline, so the full suite is the single remaining mandatory item. The two cycle-0 attempts died, so no earlier suite result counts.

Remaining:

1. The result of that ONE running suite: read the final summary line and the `EXIT` line of the log above; do NOT start a second suite. If the log ends with a pytest summary and no failure outside the deselected file, and the 5 rows above stand (nothing in the tree has changed), the unit is PASS-ready. If the processes are gone and the log has no summary, that is BLOCKED-PROCESS with the time and free RAM.
2. On PASS: flip the manifest to `checked-PASS (slice)`, flip AT-782..AT-786 `open -> fixed`, merge onto the latest origin/master keeping both sides of ledger/goal/dashboard and renumbering ids after the maximum (my rows AT-790..792 and the open AT-787..789 follow origin's AT-781; other worktrees also hold AT-782..796, so renumber at merge), re-run the affected tests, push origin master (D-007). Do NOT mark T-203 done (T-204 dependency, AT-788).

## FAILURES

None (no criterion failed on my evidence).

## Ledger and contract notes

- Filed: AT-790 (low, stale queue file after a failed write), AT-791 (low, long reason overflows the queue panel), AT-792 (low, `WARN over-scope test: test_the_canary_check_itself_notices_a_dropped_rule`, redundant with the per-canary test). Open and unchanged: AT-787 remainder, AT-788 (open T-203 rows), AT-789.
- AT-789 stands: `qa/contracts/ui-run.md` RU1 still describes a synchronous run; HO16 (D-072) supersedes it. I did not edit qa/contracts, as instructed. Suggested wording: RU1 = "a real run through one execution path, no second implementation; it is queued and the request returns at once (hosting.md HO16)", with an amendment-log line citing D-072/HO16.
- No contract line needs rewording for the five rows here. HO1's own text lists six canaries and the test now matches it.

CAPABILITY-COVERAGE: 18 falsifications reproduced by me in isolated copies (HO1 x7, HO2 x1, HO11/HO13 x3 including the real compose mutant, HO18 x4, HO38 x3); UNVERIFIED-by-checker: none; Docker rows not-applicable (BLOCKED-CAPABILITY).
LIVE-BROWSER: qa/evidence/browser-t203-hosting-2026-10-07-checker/ (sub-checker drove its own Playwright browser; queued/running seen only in an in-process render, disclosed above)
ISSUES-WRITTEN: AT-790, AT-791, AT-792
EXECUTOR: claude (maker build subagent) (checker: claude-sonnet-subagent, with 1 sonnet sub-checker for the browser check)
EXPLANATION: All five cycle-0 failures are fixed and each was re-run end to end with falsification in its own copy; the AT-785 fix opens no blocking hole (a restart inside a disk-failure window can misreport and re-run an entry: AT-790, low). The only mandatory evidence left is the one full suite, which is running but cannot finish inside the 45-minute wall, so this is CONTINUE-NEEDED, not a FAIL; PASS needs that suite's clean summary and nothing else.
full-suite trigger: tests/conftest.py edit (protected change, run once here, in progress).
Metrics: start=2026-10-07T19:10:32+05:30 end=2026-10-07T19:50:00+05:30 wall_min=40 agent_min=55 blocked_min=0 suite_runs=1 repeat_runs=0 mutations=18 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6

## Addendum: cycle 1, Resume: 1 of 2 (2026-10-07, suite result)

The one full suite finished: `uv run pytest --deselect tests/test_crawl_inventory_live.py` (no -q, no -x, bound tree, tree unchanged since 27556170, code 9a644597), lock held 19:29:29 to 20:04:36, `EXIT 1`:

`1 failed, 2707 passed, 5 skipped, 2 deselected, 14 xfailed, 15 warnings in 2093.70s (0:34:53)`

The single failure is `tests/test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus`: `AssertionError: 500 KB scan took 3.24s, expected under 3s` (test line 194), a wall-clock bound, on a host running about a dozen other pytest runs (free RAM 1.8 GB at the time). Not caused by this unit:
- the unit changes no redact code (`git diff 7782df41 --stat` over `src` shows no redact file);
- re-run alone it passes: 18 passed in 6.2 s on the bound tree, and 18 passed twice (6.8 s, 8.1 s) on a `git archive` of base 7782df41 in a scratch copy.
So the suite is clean for this unit. Filed as AT-793 (low, unscaled timing bound, same family as AT-757/AT-772). `tests/test_crawl_inventory_live.py` stays deselected by name (pre-existing hang), as the brief said. No `harness` re-selection was needed.

All mandatory evidence is now in: five failed rows MET with falsification, affected tests green, browser check done (disclosed gap on queued/running states), full suite run once with no failure caused by this unit. Docker rows remain BLOCKED-CAPABILITY and the T-203 rows in AT-788 stay open, so this is a slice PASS: manifest flipped to `checked-PASS (slice)`, AT-782..AT-786 flipped `open -> fixed`. T-203 is NOT marked done (T-204 dependency, AT-788).

Merge note (coordinator's order d063, then at758-759, then T-204, then T-203): I did not merge and did not push master. Everything is committed only on `wave/t203-hosting`. Ledger ids on this branch (AT-787..789 from cycle 0, AT-790..793 from cycle 1) collide with master's AT-787..798 and must be renumbered after master's highest id at merge; `qa/issues.jsonl` is `merge=union`, so check that no id appears twice before the push.

VERDICT: PASS
SCOREBOARD: HO1, HO2, HO11, HO13, HO18, HO38 (the failed rows) met; every other row keeps its cycle-0 ruling (met, legitimately deferred, or BLOCKED-CAPABILITY). Slice PASS only.
ISSUES-WRITTEN: AT-793 (this addendum); AT-790, AT-791, AT-792 (first dispatch)
Metrics: start=2026-10-07T19:10:32+05:30 end=2026-10-07T20:10:00+05:30 wall_min=45 agent_min=70 blocked_min=15 suite_runs=1 repeat_runs=2 mutations=18 cycle=1 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-06.6
