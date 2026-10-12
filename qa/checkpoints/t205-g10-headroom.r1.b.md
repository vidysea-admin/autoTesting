# Checkpoint - t205-g10-headroom, coordinator B, cycle 1
Verdict: qa/verdicts/t205-g10-headroom.r1.b.md (PASS). Head fb93776bbf216c91c5854e0c5ce58dff8a22e052, product 57cec910bea153b8cfc53d14ad0491cc3da9c266, repair base 0b8325b61bf89e2ed66d62ef02ec47f94c211733. Attribution: checker coordinator B (claude-sonnet-subagent), evidence under qa/evidence/t205-g10-headroom-r1-B/.

Environment: Windows 11, Python 3.11.15, pytest 9.1.1, uv env in the checkout; `autotester.__file__` = D:\autoTesting\.worktrees\check-t205-r1-b\src\autotester\__init__.py; rootdir = the checkout. Dependency lock: uv.lock at fb93776b (unchanged by the repair).

| Check | Command and scope | Code hashes (tree fb93776b) | Result |
|---|---|---|---|
| Affected tests | `uv --directory <tree> run pytest -p no:xdist -o addopts=` over test_project_schema_team, test_team_enums_home, test_run_launcher, test_run_launcher_approval, test_safe_names_windows, test_team_store, test_schedule_model, test_policy_merge, test_routers_list, test_cli_subapp_hook (665 collected) | head tree | 665 passed (run twice; second with --directory) |
| Source users | test_ingest, _persist, _narration, test_orchestrate, test_reconcile_schema, test_cli_advice_resolves, test_ui_runs, test_ui_runs_live_case_approval | head tree | 98 passed, 1 failed (known AT-792 red) |
| Lint, design | `ruff check src tests scripts`; `autotester doctor` | head tree | clean |
| Data compat | compat.py (write at 0b8325b6 archive, read/re-write at head, provenance line read by base) | project.py, team_enums.py, filestore.py | bytes and ids identical; base cannot read provenance rows |
| Hostile names | hostile.py over 75 names via team_path/create_marker | safe_names.py | no escape, no device, legit names created |
| Falsifications | mutants.py, 12 rows, isolated git-archive copies minus qa/.goal | n/a | see verdict table |

Reuse note: TF3, TF4, TF5 were not re-run as separate criteria (their input files are untouched by the repair); they ran green inside the 665 set.
