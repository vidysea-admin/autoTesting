#!/bin/bash
COPY=C:/Users/Lenovo/AppData/Local/Temp/chk-t177r2a-1798127267
PY=$COPY/.venv/Scripts/python.exe
cd /c/Users/Lenovo
for f in tests/test_browser_cdp_probe_hostile.py tests/test_browser_session_cdp.py tests/test_browser_settle.py tests/test_browser.py tests/test_browser_navigation_secrets.py tests/test_browser_session_cdp_live.py; do
  s=$(date +%s)
  echo "=== $f" 
  PYTHONPATH=$COPY/src timeout 540 $PY -m pytest $COPY/$f --rootdir $COPY -p no:xdist -p no:cacheprovider -o addopts= -q -rs 2>&1 | tail -15
  echo "wall_s=$(($(date +%s)-s))"
done
