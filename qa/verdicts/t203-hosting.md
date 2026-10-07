# Verdict: t203-hosting (cycle 0, single checker)

Checked: 2026-10-07. Bound to `D:/autoTesting/.worktrees/t203-hosting`, branch `wave/t203-hosting`, code 61585fc2, manifest 47241bb8, parent c5f6a3cf (on 6f33ec8b). Judged as is; origin/master has moved (AT ids reach AT-781 there).
Policy-Version: proportional-verification/2026-10-06.6 (the .7 rules apply too). Cycle checked: 0.
Checkpoint: qa/checkpoints/t203-hosting.md. Authority: D-072. Contract: qa/contracts/hosting.md.

VERDICT: FAIL
SCOREBOARD: see the per-criterion table (HO1-HO38): 16 criteria MET or MET-static, 9 FAIL or PARTIAL-with-defect, the rest legitimately deferred or BLOCKED-CAPABILITY; criteria that carry a blocking defect are named under FAILURES.
TIER: L (concurrency/timing in `src/autotester/ui/run_queue.py`, config in `docker/compose.prod.yml`, `.env.example`, and a protected conftest edit `tests/conftest.py:59-68`). Single checker: no security/auth/tenancy or production-write trigger, so no dual check.

## Check plan (step 0)

| Signal | Check |
|---|---|
| Queue and settings logic changed | affected tests (213 in the manifest set re-run in the sub-checker copies), falsification per claim, own race harness |
| Concurrency/timing | single-flight, cap, 429, gate re-check, slot release, restart recovery judged on their own terms; baseline measured before repeats |
| conftest autouse fixture | protected change reviewed by a read-only sub-checker (3 experiments) |
| Deploy files (Dockerfile, compose.prod.yml, Caddyfile, DEPLOY.md, .env.example) | static review plus mutants; `docker compose config` (client only) |
| UI surface | the report page gained a queue panel (`ui/run_queue_view.py`, `routes_report.py`); the manifest does not claim a browser walk and Docker-less hosting cannot serve it; the panel is covered by TestClient tests only. Mode D browser check NOT run: see LIVE-BROWSER |
| Docker | daemon down: build, compose up, HTTPS, supervision, restart persistence are BLOCKED-CAPABILITY, never PASS |
| Full suite | one `uv run pytest` in the bound tree (policy trigger: conftest edit). Result below |

## Evidence

### Concurrency, on their own terms (my own harness, outside the tree, real code via PYTHONPATH)

| Claim | Evidence | Result |
|---|---|---|
| Server limit default 2 | `ServerSettings().max_concurrent_runs == 2`, `test_defaults_are_two_runs_and_two_gib` | MET |
| Never more than the cap; never two of one project | `probes/stress.py`: 12 submitter threads, 6 projects, 40 presses, real thread spawner, concurrency measured inside the runner itself: 40 runs, 0 cap violations, 0 same-project violations, 0 stuck. Mutant `>=` to `>` on the cap in a copy: 38 of 40 runs violated (p = 0.95), so 40 repeats is ample for the cap claim | MET |
| Two simultaneous requests cannot both claim the last slot | the stress harness cannot see a missing lock: the no-lock mutant (`self._lock = contextlib.nullcontext()`) violated 0 of 40 (p < 1/40, the GIL hides it) and survives all 20 queue tests. Deterministic harness `probes/race.py` (limit() sleeps 30 ms inside the claim window): shipped code 10 of 10 runs end with exactly 1 running at limit 1; no-lock mutant 10 of 10 end with 2 running | MET by construction (lock verified), but no shipped test guards the lock (AT-787, low) |
| Single flight per project | mutant drops `and e.project not in busy`: `test_never_more_than_the_limit_and_never_two_of_one_project_running` red on `len(running) == len(set(running))` | MET |
| FIFO start | mutant picks the newest queued entry: `probes/fifo.py` order `['a','c','b']`; killed only by `test_admin_raising_the_limit_applies...`, not by the test named for FIFO (incidental) | MET (low note) |
| 429 cap | `test_a_member_pressing_test_over_and_over_gets_a_429_with_the_reason`: codes `[303,303,303,303,429]`. The cap is 3 WAITING per project (`MAX_WAITING_PER_PROJECT`, `run_queue.py:25`), so the 429 is the 5th press on an idle project (1 running + 3 waiting), or the 4th when the project's first press is itself queued behind a full server | MET (the number is a chosen documented cap) |
| Gates re-checked when a queued run starts | `routes_runs.py _run_queued` calls `_prepare_run` again; a gone provider gives `refused` with the reason and 0 cases run (`test_credentials_deleted_while_waiting...`). Mutant memoising `_prepare_run` in a copy: the test goes red (`ran` has one run). `project.run` recheck NOT built (no permission model in src; T-204) | MET for credentials/provider/consent; permission part deferred |
| Slot always released | killed mutants: `finally` to `else` (red, entry stays `running`). Enumerated paths (finish, runner Exception, RunRefused) release. NOT released when the queue-file write fails in `submit()` (probe `edge.py` E4: entry stays `running` with no worker, blocks that project and one slot until restart). A `SystemExit`/`CancelledError` in a runner releases the slot but records `done` (E3) | FAIL on the word "always" (AT-785) |
| Restart recovery | mutant `INTERRUPTED` to `QUEUED`: `test_queue_survives_a_restart...` red; running becomes `interrupted` with a reason, never re-run, waiting entries resume; corrupt queue file does not stop the site | MET |
| Settings validation | mutants: `strict=True` removed (red, `DID NOT RAISE` on "2", 2.0, True), ceiling 65 (red on `[65]`) | MET |
| Saved beats env beats default, no restart | `test_saved_setting_wins_over_the_environment...` plus the manifest mutant | MET |
| Shared RAM bridge (HO20) | `test_a_second_run_plans_against_the_ram_the_first_one_already_holds`, planning-lock test; `_free_ram_mb() - reserved` also subtracts RAM already used by a running run, which is conservative, not unsafe | MET |

Baseline note for the race rule: only the lock claim is a race; its baseline under naive stress is p < 0.025 for the mutant, so I used the deterministic widened-window harness instead of more repeats.

### conftest `_inline_run_queue` (protected change)

Justified: with it removed, 23 existing UI tests fail (429 from queue state leaking across tests, or the run still unfinished). No existing test assertion was edited (`git diff 61585fc2^..61585fc2 -- tests/` touches only conftest and new files). It does weaken 3 tests: `RunQueue._work` swallows runner exceptions, so a crashing run returns 303 and still passes `test_a_run_that_stays_on_known_routes_asks_for_nothing`, `test_a_run_on_a_project_with_no_flowspec_asks_for_nothing` and the second POST in `test_ui_run_needs_no_human_approval_when_credentials_are_provisioned` (mutation: run body replaced by `raise RuntimeError` left them green; they would have errored before). The 17 happy-path, crash-recovery and refusal tests assert on saved runs or immediate 400/403 and keep their meaning. Re-raising runner exceptions inside the fixture's queue restores the old meaning (the sub-checker's variant with a bare `raise` left all 186 tests green). Filed AT-786.

### Deploy files (static; Docker down)

See the per-criterion table. Reproduced by me: `docker compose -f docker/compose.prod.yml config` exits 1 without `AUTOTESTER_DOMAIN` (the `:?` on the caddy service is not exempted by the profile), and with a `server.env` copied from `.env.example` it emits `ANTHROPIC_API_KEY: ""` and `AUTOTESTER_APPROVAL_KEY: ""`; `src/autotester/core/env.py:62` then skips those keys because they are already in `os.environ`. Mutant: deleting the `**/.env.*` line of `.dockerignore` leaves `test_dockerignore_keeps_secrets_and_project_state_out_of_the_image` green (`1 passed`).

## Per-criterion table (hosting.md)

| Row | Verdict | Evidence / ruling |
|---|---|---|
| HO1 | FAIL (LOCAL guard) | real `.dockerignore` excludes all six contract canaries (read), but the test asserts 1 of 6 and the `**/.env.*` mutant survives (AT-782). BUILD-HOST half BLOCKED-CAPABILITY |
| HO2 | FAIL (mechanism) | compose has no inline secret, the scan is clean, a planted `sk-ant-` key reddens the test; but the documented step empties `/data/.env` (AT-783). inspect/logs BLOCKED-CAPABILITY |
| HO3 | MET (static) | `AUTOTESTER_ROOT: /data`, healthz reads `package_root()`; test is weak (mutant survives, AT-787); `docker diff` BLOCKED-CAPABILITY |
| HO4 | BLOCKED-CAPABILITY, not built-claimed | needs Docker |
| HO5 | GAP, declared | no supervisor built (manifest says supervisord); BUILD-HOST; not claimed by this slice, T-203 stays open (AT-788) |
| HO6 | PARTIAL | hardening keys present and tested; non-root deviation recorded only as "wait on later units", no reason (AT-788) |
| HO7 | MET (static) | only `127.0.0.1:${BIND}:8000`, caddy 80/443 in the https profile, 6080 `expose` only, `x11vnc -localhost`, `/novnc/*` 503; mutants `6080:6080` and `0.0.0.0:8000` red. nmap SERVER-GATED |
| HO8 | SERVER-GATED | deferred, gates go-live |
| HO9 | MET (contract's own drift test) | all keys present; drift test killed on `MAX_UPLOAD_BYTES`; weaker per-key comments (AT-787) |
| HO10 | MET (LOCAL) / BLOCKED-CAPABILITY (linux run) | LF `*.sh`, no module-level fcntl/pwd, no drive letter in src; `qa/evidence/t203-linux-run.md` absent (needs Docker) |
| HO11 | FAIL (content defects) | guide has the steps but step 3 and step 8 do not work as written (AT-783, AT-784); backup is plain tar, not encrypted |
| HO12 | Legitimately deferred (T-204) | interim 503 for `/novnc/*` verified statically |
| HO13 | PARTIAL | HSTS and headers present, `*` origin refused (`tests/test_ui_origin_guard.py:112`); interim documented but compose fails without a domain (AT-784); no redirect/TLS config test, no startup mode log (AT-787) |
| HO14 | MET | tag 1.62.0 equals `uv.lock`; mutant 1.61.0 red |
| HO15 | PARTIAL, legitimately deferred page | schema, store, validation, precedence MET; admin page, audit line need `settings.manage` (T-204) |
| HO16 | MET | `test_pressing_test_returns_the_redirect_before_the_run_has_executed` (nothing ran inside the request), persistence tests |
| HO17 | MET | table above |
| HO18 | FAIL on "always" | AT-785 |
| HO19 | PARTIAL, permission part deferred | credentials/provider/consent re-checked; `project.run` needs T-204 |
| HO20 | MET | table above |
| HO21 | PARTIAL, scoping deferred | queue panel on the report page; `requested_by` and `trigger` recorded; per-user scoping needs T-204 |
| HO22-HO33 | Out of scope | Group 10 owns them (contract ownership table); a T-203 PASS never closes them |
| HO34, HO35 | SERVER-GATED | deferred |
| HO36 | Deferred, declared | `scripts/backup.sh` absent; drill is SERVER-GATED |
| HO37 | MET | `uv run ruff check src tests scripts`: All checks passed; `uv run autotester doctor`: clean |
| HO38 | MET for the set I ran; see suite | no existing assertion edited; 3 tests lose detection power (AT-786) |

Ruling on the maker's not-built rows: HO22-HO33 are out of scope by the contract's own ownership table. HO12, HO15 (page), HO19 (permission), HO21 (scoping) depend on `auth.md` permissions that do not exist in `src/` (T-204 pending), so they cannot be built in this unit: legitimate deferrals. HO8, HO34, HO35 and the HO36 drill are SERVER-GATED and gate go-live, not this unit's code. HO5 (supervision), HO36 (script), the non-root user and HO4 are NOT blocked by T-204; they are gaps of the T-203 task as a whole, not of this slice's claims, so they do not fail this slice but they keep T-203 open.

## FAILURES

- [HO1] sev: high · LOCAL guard asserts 1 of 6 contract canaries and a dropped `**/.env.*` rule survives (`tests/test_hosting_deploy.py:104-115`; my mutant run: `1 passed`) · add the five canaries · issue: AT-782
- [HO2/HO11] sev: high · the guide's step 3 makes `/data/.env` provider and approval keys unloadable (`docker/DEPLOY.md:47-48`, `.env.example:27-28,38`, `core/env.py:62`; `docker compose config` shows `ANTHROPIC_API_KEY: ""`) · separate server-only env example or treat empty inherited values as unset · issue: AT-783
- [HO11/HO13] sev: medium · the no-domain interim fails at compose interpolation (`compose.prod.yml:52`, rc=1 reproduced) and the guide cites an unpublished 6080 tunnel and a Host allow-list that is not in code (`DEPLOY.md:60-62,96,130`) · issue: AT-784
- [HO18] sev: medium · the slot is not released when the queue-file write fails in `submit()`; a runner SystemExit is recorded done (`ui/run_queue.py submit/_work`, probe `edge.py` E3/E4) · issue: AT-785
- [HO38/protected change] sev: medium · the conftest fixture lets a crashing run pass 3 existing tests · issue: AT-786

Non-blocking rows filed: AT-787 (low, weak guards), AT-788 (medium, open T-203 rows), AT-789 (low, `ui-run.md` RU1 still says synchronous; my contract amendment write was denied by the auto-mode classifier, so it is not done).

## Full suite

One `uv run pytest` in the bound tree, run 2 (`-v`, output in the checker scratchpad `suite2.log`). Run 1 ended abnormally at 18% in `tests/test_crawl_inventory_live.py` (log ends `EXIT 1`; known pre-existing, treated as BLOCKED-PROCESS cause, not a unit FAIL); run 2 got past that file (first test there FAILED, pre-existing live-crawl file) and continued. Final result: see the checkpoint; if the checkpoint has no final line the suite was still running when the shell tools were denied (below).

## Process note (honest)

From the `ui-run.md` edit onward the auto-mode classifier denied every Bash and PowerShell call in this session ("Modify Shared Resources"), including `date`. Because of that: no commit of this verdict, checkpoint or the ledger rows, no merge, no push, no goal CLI call. Read/Write/Edit still worked, so the verdict, checkpoint and `qa/issues.jsonl` rows were written to the worktree uncommitted. The PIDs of my background suite are 9500, 29828 and 38252 (bash parent 31476); I could not stop them.

CAPABILITY-COVERAGE: 20 rows reproduced by me or my sub-checkers (queue: 7, settings: 2, recheck 1, deploy: 10 incl. 4 survivors recorded); UNVERIFIED-by-checker: none claimed; Docker rows not-applicable (BLOCKED-CAPABILITY)
LIVE-BROWSER: not run. The queue panel is a UI surface; no browser was available to drive against a hosted instance (Docker down) and no local server was started before the shell was denied. Unit FAILs on other grounds, so the browser check is mandatory at the repair cycle.
ISSUES-WRITTEN: AT-782, AT-783, AT-784, AT-785, AT-786, AT-787, AT-788, AT-789 (ids follow origin/master's AT-781; `qa/issues.jsonl` is `merge=union`)
EXECUTOR: claude (maker build subagent) (checker: claude-sonnet-subagent, with 2 read-only sonnet sub-checkers for the conftest review and the deploy files)
EXPLANATION: The run queue itself is sound under real threads (cap, single flight, lock, 429, recovery, gate re-check all falsified green-to-red), but the slot-release claim breaks on a failed queue write, the deploy guide's documented steps break the secret flow and the no-domain interim, the HO1 guard is far weaker than the contract text, and the conftest fixture lets a crashing run pass three old tests. Docker rows are BLOCKED-CAPABILITY. Fix the five FAILURES; the deferred rows stay on the T-203 backlog.
full-suite trigger: tests/conftest.py edit (run here once).
Metrics: start=2026-10-07T18:31:25+05:30 end=2026-10-07T19:05:00+05:30 wall_min=34 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=170 mutations=24 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
