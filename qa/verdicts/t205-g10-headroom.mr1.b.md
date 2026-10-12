# Verdict — t205-g10-headroom, merge-reconcile 1, coordinator B (blind dual)
Date: 2026-10-11 (host `date -u`) · Cycle checked: 1 (manifest `Fix cycle: 1`) · Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting · Branch `wave/t205-g10-headroom` head `ecaaf7e4` (product `39b42ca5`, merge `b841c232` = parents `fb93776b` + `1c52bf71`) · Repair base `fb93776b` (verified ancestor of head) · compared against master `1c52bf71`
Checkpoint: qa/checkpoints/t205-g10-headroom.mr1.b.md · Evidence: qa/evidence/t205-g10-headroom-mr1-B/ (scripts, JSON outputs, falsification logs)

## Check plan (step 0)
Emphasis assigned: behavioural equivalence through the real app, head vs master. Two private copies on C: (`git archive` of each commit, own `.venv` each; `autotester.__file__` confirmed inside each copy, in every probe's first output line). Same scripts on both, spies at the shared low seam (`BrowserSession`, `run_execution.run_and_grade_case_resilient`, `for_role` in `routes_runs`), a scratch `AUTOTESTER_ROOT` per row, a dummy signing key; no real browser, site or model; no `.env` read. Plan: (1) run-trigger route, 34 rows; (2) approval-gate doors, 99 head rows vs 46 master rows; (3) `Source.origin` shapes, real intake routes + stored samples + hostile shapes; (4) CLI help; (5) schedule enum identity; ruff + doctor; one falsification per re-homed behaviour (priority pass-through, judge refusal, approval gate). Diff audit and the suite are the other coordinator's. SERIAL: none needed (copies are distinct; probes ran one at a time, falsifications in parallel across 5 separate copies).

## Result
VERDICT: PASS
SCOREBOARD: 8/8 criteria (TF1-TF8) evidenced on the emphasis assigned (TF1, TF2, TF3 by route-table equality through the app, TF5, TF6, TF8); 0 invariants failed. TF4/TF7 not in my emphasis, covered by the other coordinator.
TIER: L (security trigger, `src/autotester/stages/run_launcher.py:179` `require_live_case_approval` called from `prepare_run`; dual-trigger line present in the manifest and confirmed by me at that line)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 falsification rows reproduced (green in copy, red after) -- table below
LIVE-BROWSER: not-applicable (no screen, route, template or command changed: route table and `--help` held equal; no real browser by instruction)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

### 1. Run trigger, head == master on every row (34/34)
`routes-head.json` vs `routes-master.json`: status, body, `Location`, executor-spy case titles, judge-factory calls `(slug, role)`, browser-session count, normalised `run.json` bytes and the written file tree are identical.
| Row | head = master |
|---|---|
| no priority / p0 / p1 / p2 / p3 / p0+p1 / p1+p1 | 303; cases `all` / `p0,pin` / `p1,pin` / `p2,pin` / `pin` / `p0,p1,pin` / `p1,pin` |
| `p9`, `P1`, empty, `p1&p9` | 422, same pydantic body (loc `query.priority.N`) |
| p2-only project + `priority=p0` (zero selection), no cases (with/without priority) | 400 "project 'demo' has no cases to run", nothing written |
| no approval (with/without priority) | 403, same text and `--max-actions` hint (4 vs 2 follows the selection) |
| provider unavailable (reason / none) | 400 "no AI provider is configured (<why>) -- cannot grade a run" |
| `ProviderError` from the factory | 400 with the exception's own text; unexpected `RuntimeError` -> 500 |
| placeholder with no value | 400 "PROBE_PW has no value yet ..." |
| slug `NOPE`, `a b`, `9lives`, `demo%0A` / `nope`, `demo-` / `../etc` | 400 invalid slug / 404 no project / 404 |
| executor raising in a case | 303, run saved with all cases (resilient path) |
| judge selection | `for_role(project, "judge")`, once at press and once at start, both sides |
| queued path: press `priority=p1`, then a new p1 and p2 arrive, then the worker starts | stored `priorities=[p1]`; run covers `p1, pin, late-p1`, not `late-p2` (`_run_queued` re-applies the entry's priorities) |
| queued: approval removed / provider gone / cases removed before start | entry `refused`, same reason strings, 0 sessions, no run dir |

Intended differences (named): none observed on the route. Run model differences exist only for a queue entry that carries `requested_by` (below, section 2).

### 2. Approval gate (TF2) -- no path found without the gate
Doors tried on head (`stages/run_launcher.py`): `launch_run`, `prepare_run`, `RunSeams`/`DEFAULT_SEAMS`, the route, `_run_queued` (queue worker), each with `priorities` in `None`, `[]`, `['p1']`, `['p0']`, `['p9']`, `'p1'` (str), `('p1',)`, and a zero-selection project; triggers manual/schedule/ci with `requested_by`/`slot_key`; approval absent, approval present, approval `max_actions=1`.
- NO-APPROVAL: every row ends in `LaunchRefused` 403 (or 400 no cases) with 0 browser sessions, 0 executor calls and an unchanged data root. `priorities=[]` selects pinned cases only and is still gated; `['p9']`/`'p1'` raise `ValueError` before anything runs; a selection of zero cases is a 400 before the approval is consulted.
- Approved: `priorities` only narrows (`['p1']` -> `p1,pin`; `[]` -> `pin`); a tiny approval refuses both `None` and `['p1']`.
- `launch_run` has no `skip_approval`/`approval`/`force`/`gate`/`no_gate` keyword (TypeError each); `RunSeams` fields are `judge_factory, planner, free_ram_mb, ledger` (none carries an approval).
- Master equivalents (`_prepare_run`/`_execute_and_record`/`_run_queued`): same refusals and same executed sets row by row. Only the exception class differs (`HTTPException` 403 -> `LaunchRefused` 403), and the route and queue translate it back to identical responses (section 1).
- Lower door, same on both sides: `run_launcher.run_cases_traced` (master: `routes_runs._execute_with_trace`) executes with whatever `RunApproval` object it is handed (an unsigned fabricated one ran 4 cases on both). Nothing in `src/` calls it except `launch_run` (grep), and `test_exactly_one_non_test_call_site_executes_the_cases` pins that. Not a regression (P2 below).
- Observation, not a defect: head's `_run_queued` builds `_seams()` (which calls `get_queue()`) before the gates; with no queue object present this creates `.work/run_queue.json` on a refusal where master did not. The only caller is the queue itself, so the queue exists; unreachable through the real door.
- Intended difference (TF2): for a queue entry carrying `requested_by`, head writes `"requested_by"` into `run.json` (master omits it); the route never sets it today. `entry.trigger` is not forwarded (a `trigger="schedule"` entry is stamped `manual` on both sides) -- P1.

### 3. `Source.origin` table (head; master in the last column)
| Input | Head | Master |
|---|---|---|
| master intake output via real routes: upload, zip (2 members), Drive link | stored lines normalised-equal to master's; origins `UploadOrigin`, `ZipOrigin`x2, `DriveOrigin` | same |
| those 4 master-written lines: load, re-save | bytes identical to the stored line (4/4); id unchanged; load-save-load equal | same |
| field absent / `null` | accepted, `None` | same |
| bare `"upload"` / `"zip"` / `"drive"` / `"recording"` (fb93776b form) | accepted as `SourceOriginKind`, re-saves as the bare string, id unchanged | refused (dict_type) |
| `{"kind":"zip"}`, `{"kind":"drive"}` (detail missing) | refused | refused |
| `{"kind":"recording"}`, `{"kind":"email"}`, `{"kind":"DRIVE",...}`, `{"file_id":"x"}` (no kind), `{"kind":["zip"]}` | refused (union tag invalid/missing) | refused |
| drive/upload dict with an extra or foreign key | refused (extra_forbidden) | refused |
| bare `""`, `"email"`, `"UPLOAD"`, `5`, `["zip"]` | refused | refused |
| `UploadOrigin(kind="zip")` in code | refused | refused |
Via the store file a refused line raises `ValueError` on both. `Source` built in code with `origin="drive"` is the enum arm on head, refused on master; with a detail model or dict it is the model arm and `Source.id` is identical on both (`src_65f348bb730c`). The two-shape cost is as the maker described; no existing shape changed bytes.

### 4. CLI
`autotester --help`, `ingest`, `issues`, `release-report`, `expand`, `ledger`, `flowspec`, `report` `--help` run as subprocesses: byte-identical head vs master (8/8). Root help carries master's `expand` ("Review/prune proposals, then generate only persisted human-approved cases.") and `release-report` rows. A click-tree walk of all 43 commands/groups is identical on both. `tests/golden/cli_commands.json` == the live listing built the way the test builds it (True).

### 5. Schedule enums
`ScheduleMode, ScheduleZone, SlotOutcome, SchedulerHealth, CredentialState` each have one defining class in the package (walk of every module), `autotester.schema.schedule.X is autotester.schema.team_enums.X` for all five, and the same object is reachable through `stages.schedule_gate`/`stages.scheduler`. Members equal master's. Every module named in the plan imports in a fresh interpreter. The only public-name difference of `schema.schedule` is that it no longer exposes `StrEnum` (no importer uses it).

### Lint and doctor
`ruff check src tests scripts` on head copy: All checks passed. `autotester doctor` on head copy: `doctor: clean` (git-less copy; the generated-doc checks that need git are the other coordinator's).

### Falsification (green before in the copy, red after, one per re-homed behaviour; copies discarded)
| Row | Edit (single hunk) | Named check | Before | After |
|---|---|---|---|---|
| F1a priority, queued re-check | `_run_queued` drops `priorities=entry.priorities` (`ui/routes_runs.py`) | `test_ui_runs.py::test_trigger_runs_exact_selected_priority_plus_pinned_once` | 2 pass | 2 fail |
| F1b priority, prepare | `prepare_run` calls `store.list_cases()` (`stages/run_launcher.py`) | same | 2 pass | 2 fail |
| F2a judge refusal, unavailable | delete the `why_unavailable` branch of `judge_or_refuse` | `test_ui_runs.py::test_run_refuses_when_no_ai_provider_is_configured` | pass | fail |
| F2b default judge | `default_judge` returns `None` | `test_run_launcher.py::test_the_default_judge_is_the_provider_factorys_and_an_unusable_one_is_a_400` | pass | fail (AttributeError raised through the real `why_unavailable` path, not an import error) |
| F3 approval gate | replace the `require_live_case_approval(...)` call in `prepare_run` with a fabricated approval | `test_run_launcher_approval.py` + `test_ui_runs_live_case_approval.py` | 25 pass | 15 fail, 10 pass (every refusal row red; the 10 greens are the rows that never needed the gate) |
Logs: `qa/evidence/t205-g10-headroom-mr1-B/falsify/`.

## Proposed issues
PROPOSED-ISSUE: {"severity":"low","feature":"team-foundation","title":"_run_queued does not forward entry.trigger/slot_key to launch_run: a scheduler-origin queue entry is stamped trigger=manual (same as master); G5 must forward them","evidence":"src/autotester/ui/routes_runs.py:72-77; probe rb.py: QueueEntry(trigger='schedule', requested_by='alice') -> run.json trigger=manual, requested_by=alice"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-foundation","title":"run_cases_traced is a public gate-free door: it executes with any RunApproval object passed in (identical to master's _execute_with_trace); only the single-call-site test keeps callers on launch_run","evidence":"src/autotester/stages/run_launcher.py:196-203; probe drive_doors.py LOWER DOOR row, both sides"}

EXPLANATION: Head is behaviourally equal to master through the real app on all 34 route rows, the queued re-check, every refusal body and the written files; the approval gate has no unguarded door for any `priorities` value, and the three re-homed behaviours go red when broken. The `Source.origin` union keeps every master-written shape byte-stable and adds only the bare-enum arm; hostile shapes are refused as on master. Owner still rules on the two-shape field (maker's flag), which is not a defect.
Metrics: start=2026-10-11T20:02Z end=2026-10-11T20:47Z wall_min=45 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2700 mutants=0 defects_unit=0 defects_6c=0
