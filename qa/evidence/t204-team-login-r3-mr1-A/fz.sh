#!/bin/bash
# usage: fz.sh <label> <dir> <tests...>
label=$1; dir=$2; shift 2
PY=D:/autoTesting/.worktrees/t204-team-login/.venv/Scripts/python.exe
cd "$dir" && PYTHONPATH="$dir/src" $PY -c "import autotester;print('SRC',autotester.__file__)" > ../fz_$label.log 2>&1
PYTHONPATH="$dir/src" $PY -m pytest -o addopts= -p no:xdist -p no:cacheprovider "$@" >> ../fz_$label.log 2>&1
echo "EXIT $?" >> ../fz_$label.log
