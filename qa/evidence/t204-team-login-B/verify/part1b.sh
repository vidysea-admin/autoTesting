#!/bin/bash
# Part 1b + Part 2: strictly one pytest process at a time.
W=D:/autoTesting/.worktrees/t204-team-login
S=C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/t204b-verify
V=D:/autoTesting/qa/evidence/t204-team-login-B/verify
cd $W
export PYTHONDONTWRITEBYTECODE=1
PY=$W/.venv/Scripts/python.exe
$PY -m pytest -p no:xdist -p no:cacheprovider -rA --junitxml=$S/p1_misc.xml tests/test_permission_coverage.py tests/test_credential_run_approval.py tests/test_env_loading.py > $S/p1_misc.log 2>&1
echo done > $S/p1_misc.done
$PY $V/falsify.py AU16a AU14a AU21a AU3a AU27a AU1 AU2 AU5a AU6 AU7 AU9a AU8 AU4 AU12 AU13 AU10 AU11a AU15 AU17 AU18a AU19 AU20 AU22 AU23 > $S/p2a.log 2>&1
echo done > $S/p2a.done
$PY -m pytest -p no:xdist -p no:cacheprovider -rA --junitxml=$S/p1_au25.xml tests/test_ui.py tests/test_ui_healthz.py tests/test_ui_error_pages.py tests/test_ui_env_editor.py tests/test_ui_project_intake.py > $S/p1_au25.log 2>&1
echo done > $S/p1_au25.done
$PY $V/falsify.py AU25 AU27b AU21b AU9b AU16b AU3b AU5b AU18b AU14b AU3c AU21c AU11b AU5c > $S/p2b.log 2>&1
echo done > $S/p2b.done
