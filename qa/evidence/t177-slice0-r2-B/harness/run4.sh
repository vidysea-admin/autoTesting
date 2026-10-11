cd "$1/harness"; export PYTHONUNBUFFERED=1
echo "== affected tests"; t=$(date +%s); timeout 580 uv --directory "$1/head" run --no-sync python -c "import autotester;print(autotester.__file__)" 2>&1 | tail -1
timeout 580 uv --directory "$1/head" run --no-sync pytest tests/test_browser_cdp_probe_hostile.py tests/test_browser_session_cdp.py tests/test_browser_navigation_secrets.py tests/test_browser_session_cdp_live.py -p no:xdist -p no:cacheprovider -o addopts= 2>&1 | tail -8; echo "wall $(( $(date +%s) - t )) s"
echo "== base rounds 2"; R2B_SRC="$1/base/src" timeout 900 "$1/head/.venv/Scripts/python.exe" rounds.py base 20 > "$1/out/rounds-base-2.jsonl" 2>&1
echo "== head rounds 2"; R2B_SRC="$1/head/src" timeout 900 "$1/head/.venv/Scripts/python.exe" rounds.py head 20 > "$1/out/rounds-head-2.jsonl" 2>&1
echo "== ALLDONE4"
