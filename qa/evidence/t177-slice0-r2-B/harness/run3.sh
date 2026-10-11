cd "$1/harness"; export R2B_SRC="$1/head/src" PYTHONUNBUFFERED=1 R2B_B="$1"; PY="$1/head/.venv/Scripts/python.exe"
echo "== threads"; timeout 400 $PY conc_threads.py 2>&1
echo "== misc2"; timeout 100 $PY misc2.py 2>&1
for p in 1a 1b 2 3; do echo "== fals $p"; timeout 600 $PY falsify.py $p 2>&1; done
echo "== ruff"; timeout 200 uv --directory "$1/head" run --no-sync ruff check src tests scripts 2>&1 | tail -5
echo "== doctor"; timeout 300 uv --directory "$1/head" run --no-sync autotester doctor 2>&1 | tail -15
echo "== ALLDONE3"
