# at888-target-closed

Status: ready-for-check
Fix cycle: 2
Issue: AT-888
Branch: wave/at888-target-closed

Change: serial path now treats a closed page/context/browser mid-case as that case's INCONCLUSIVE
(cause "browser closed"), relaunches the session on the same profile (login continues from saved
profile; repo has no login-case pattern), continues; relaunches bounded (3/run, also in
VideoMixin._restart_session), then a named stop reason. Files: stages/browser_recovery.py (new),
ui/run_execution.py, browser/video.py (relaunch + cap), tests/test_ui_runs_target_closed.py, docs/MAP.md.
Verified: scoped pytest (15 pass), ruff clean, doctor clean after `autotester map`.
Not done: serial-loop wiring is not driven end to end by a test (fake loop mirrors it).
Cycle 2: test now drives the real _run_cases_serially (fake session/store); _loop copy removed; cap test added.
