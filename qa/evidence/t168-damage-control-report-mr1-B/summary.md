# t168 mr1 B evidence (head 2425506a, worktree .worktrees/t168-damage-control-report)
autotester.__file__ = D:\autoTesting\.worktrees\t168-damage-control-report\src\autotester\__init__.py
c1.txt..c4.txt  per-criterion verify commands (1, 1, 3, 8 passed)
files.txt       unified_report(+secrets), cli_surface, cli_release, ui_report, cli_advice_resolves: 118 passed
ruff.txt        All checks passed ; doctor.txt  doctor: clean
routes.txt      openapi has GET /projects/{slug}/damage-report; request returns project-specific 404 (route resolves); foreign Host -> 403
falsify-*.txt   copy outside worktree (PYTHONPATH=copy/src, import path in falsify-import.txt, copy deleted): dc4 7 passed green -> 2 failed after removing scrub_obj at stages/unified_report.py:265
