#!/bin/bash
# usage: probe.sh <rowdir> <pytest args...>
C="$1"; shift
unset VIRTUAL_ENV
export PYTHONPATH="$C/src;$C/tests"
H=C:/Users/Lenovo/AppData/Local/Temp/chkA_t179r1_355800/head
cd "$C"
$H/.venv/Scripts/python -c "import autotester,sys;print('autotester.__file__',autotester.__file__)"
$H/.venv/Scripts/python -m pytest --rootdir "$C" -c "$C/pyproject.toml" "$@" -o addopts= -p no:cacheprovider -rf 2>&1 | tail -${TAILN:-40}
