#!/bin/bash
# usage: run_pairs.sh outfile files...
out="$1"; shift
PY=D:/autoTesting/.claude/worktrees/mongo-u1/.venv/Scripts/python.exe
export PYTHONPATH="$(pwd)/src"
: > "$out"
while [ $# -gt 0 ]; do
  if [ $# -ge 2 ]; then a="$1"; b="$2"; shift 2; else a="$1"; b=""; shift; fi
  echo "=== $a $b" >> "$out"
  $PY -m pytest $a $b -o addopts= -p no:cacheprovider -q 2>&1 | tail -6 >> "$out"
done
echo DONE >> "$out"
