# Persona walk: land-t203-hosting (checker sub-walk, 2026-10-11)

Worktree D:/autoTesting/.worktrees/land-t203-hosting, HEAD 05b8b7ba (code fddbf469). Headless Chromium (playwright sync, one browser), loopback 127.0.0.1:8123 only, no model calls.
Server: `.venv/Scripts/python.exe -I <scratchpad>/launcher.py` (uvicorn on `autotester.ui.app:app`, AUTOTESTER_ROOT=<worktree>/.work/checker-walk, 3 scratch projects alpha/beta/gamma, 2 cases each, no auth: T-204 login is not on this branch's UI path, pages are anonymous).
Phase 1 = product code unmodified (real gates). Phase 2 = harness only: `routes_runs._prepare_run` stubbed to a no-op and the queue runner replaced by a blocking fake (released by flag files), so Press-Run reaches the queue without an AI key/credentials. Product files untouched. The queue file was pre-seeded with a running (-> interrupted at boot), a refused (long reason, trigger schedule) and a done (trigger api) entry.

## Tester
- Phase 1, real press on alpha: lands on bare `400 Bad Request: no AI provider is configured (set an API key in .env) -- cannot grade a run` (03). Immediate, nothing queued, no run id minted. Tester would not know what `.env` is.
- Phase 2, press via keyboard (Tab focus, Enter): 303 to `/projects/alpha/report` (not a "run page"), panel shows RUNNING, "Server: 1 of 2 run slots busy" (05). beta: 2 of 2 busy (06).
- Server cap: gamma press -> `QUEUED (#1)`, "2 of 2 run slots busy, 1 waiting" (07). Same-project: alpha presses 2-4 -> QUEUED #2,#3,#4 while alpha runs (single flight holds) (08).
- Depth cap: 5th alpha press -> `429 Too Many Requests: 3 runs of 'alpha' are already waiting; wait for one to start` (09). Clear, but a bare error page.
- Transition: released alpha run 1; gamma page auto-reloaded (meta refresh) and flipped QUEUED -> RUNNING in 5.2 s with no manual reload (11); FIFO respected (gamma ahead of alpha #2). After all releases every row is DONE with a run link (13).

## Developer
- Report page queue panel: Status pill + Time + (run link only for DONE) + reason. Long reason (4x sentence) wraps readably on desktop (10). INTERRUPTED shows the restart reason; REFUSED shows the gate sentence (04).
- Finding: panel does NOT show `requested_by` or `trigger` (both stored: seed rows carry tester.one@example.test/button, scheduler/schedule, ci-bot/api; UI rows show nothing). A developer cannot see who pressed or whether a run was scheduled. Also a QUEUED/RUNNING/REFUSED/INTERRUPTED row has no run id, so the "running" row cannot be matched to anything.
- Finding: Time column is `HH:MM:SS UTC` with no date; for old rows it is ambiguous.
- Finding: "Server: N of M run slots busy, K waiting" counts all projects, visible on any project's report (aggregate only; no other project's id/user leaks).
- Finding: a project with no finished run shows the queue panel followed by "no runs yet -- run a case against this project to see a report here", while a run is RUNNING (07, 10). Contradictory for a tester.
- Finding: INTERRUPTED reason says "press Test again" but the project page button is labelled "Run tests".
- Finding: mobile 390 px: queue table overflows its card (table right 414 vs card right 362) with a long reason / run id (14). The page-level horizontal overflow (422 vs 390) pre-exists on `/` and `/projects/alpha` (nav), not caused by this change.

## Accessibility and console
- Run button is keyboard operable (focus + Enter worked; default focus ring `auto 1px`); no unlabelled buttons/links; queue table has 2 `th` header cells (no scope attr, no caption).
- Console errors: phase 1 only the expected 400 resource error (1); phase 2 only the expected 429 resource error (1); 0 JS page errors; 0 on report/project pages.
