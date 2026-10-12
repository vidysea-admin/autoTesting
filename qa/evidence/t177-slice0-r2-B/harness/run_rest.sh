cd "$1/harness"; export R2B_SRC="$1/head/src" PYTHONUNBUFFERED=1; PY="$1/head/.venv/Scripts/python.exe"
echo "== c2" ; timeout 200 $PY attacks.py c2_nested_object 2>&1
echo "== threads"; timeout 400 $PY conc_threads.py 2>&1
echo "== procs"; D=$(mktemp -d -p "$1/out" syncXXXX); for i in 0 1 2 3 4; do (timeout 400 $PY conc_proc.py $i "$D" > "$1/out/proc$i.json" 2>&1 &); done; for k in $(seq 1 80); do n=$(ls $1/out/proc*.json 2>/dev/null | xargs cat 2>/dev/null | grep -c cross_ok); [ "$n" -ge 5 ] && break; sleep 3; done; cat $1/out/proc*.json
echo "== interrupts"; timeout 300 $PY interrupts.py 2>&1
echo "== raw wildcard"; timeout 200 $PY raw_wild.py 2>&1
echo "== ALLDONE"
