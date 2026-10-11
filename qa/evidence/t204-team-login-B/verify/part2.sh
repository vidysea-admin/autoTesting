#!/bin/bash
S=C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/t204b-verify
V=D:/autoTesting/qa/evidence/t204-team-login-B/verify
PY=D:/autoTesting/.worktrees/t204-team-login/.venv/Scripts/python.exe
$PY $V/falsify.py AU16a AU14a AU21a AU3a AU27a AU1 AU2 AU5a AU6 AU7 AU9a AU8 AU4 AU12 AU13 AU10 AU11a AU15 AU17 AU18a AU19 AU20 AU22 AU23 AU25 AU27b AU21b AU9b AU16b AU3b AU5b AU18b AU14b AU3c AU21c AU11b AU5c > $S/p2.log 2>&1
echo done > $S/p2.done
