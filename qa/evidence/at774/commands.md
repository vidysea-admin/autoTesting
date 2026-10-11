# at774 checker A evidence (2026-10-12, copy C:/Users/Lenovo/AppData/Local/Temp/at774-chk-598700, own venv; autotester.__file__ inside copy)
- git facts: HEAD 91f28550, parent c5d97e0e (head adds only qa/manifests/at774.md), merge-base with master = 822dca2b, master now d867024f; run_launcher.py unchanged on master since base.
- C774 command: pytest tests/test_run_launcher_retired.py -o addopts= -> 3 passed (0.99 s).
- Falsify (throwaway copy fals/, scripts/ copied for conftest): green 3 passed; filter replaced by "if True" -> test_prepare_run_skips_retired_cases FAILED (2 extra case ids), pinned test FAILED (extra id), all-retired test FAILED "DID NOT RAISE LaunchRefused"; restored -> 3 passed.
- Affected: test_run_launcher_retired, test_run_launcher, test_run_launcher_approval, test_ui_runs, test_doctor, test_credential_run_approval, test_ui_runs_live_case_approval, test_ui_runs_queue, test_pinned_regression, test_cli_surface (-m "not harness") -> 175 passed.
- ruff check src tests scripts -> All checks passed. autotester doctor -> clean. run_launcher.py = 300 lines.
- Trial merge of 91f28550 into master d867024f in throwaway clone: clean (no conflicts), run_launcher.py 300 lines after merge.
- Entry-path enumeration: grep of src/autotester for list_cases/get_case/run_case/run_cases/run_cases_traced/prepare_run/launch_run. launch_run importers: ui/routes_runs.py only (queue worker _run_queued + trigger_run's prepare_run). run_case importers: agent_loop, explore, run_case_pipeline, script_replay (see verdict table).
