#!/bin/bash
# usage: run_mut.sh <m> ; runs the 4 test files in copy <m> using the head venv python, PYTHONPATH on the copy
m=$1
R=657a14737238
T="C:/Users/Lenovo/AppData/Local/Temp"
C="$T/t201a_r2b_${R}_$m"
PY="$T/t201a_r2b_${R}_head/.venv/Scripts/python.exe"
E=/d/autoTesting/qa/evidence/t201a-delivery-core-r2-B
cd "$C" || exit 9
export PYTHONPATH="$C/src"
{
  "$PY" -c 'import autotester;print("autotester.__file__ =", autotester.__file__)'
  timeout 300 "$PY" -m pytest tests/test_cli_advice_resolves.py tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -q -rf --no-header 2>&1 | tail -n 30
} > "$E/falsify-$m.txt" 2>&1
