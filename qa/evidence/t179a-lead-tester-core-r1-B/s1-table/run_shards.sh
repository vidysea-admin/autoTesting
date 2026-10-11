#!/bin/bash
# usage: run_shards.sh <copy-name head|base> <tag> <nshards>
B=C:/Users/Lenovo/AppData/Local/Temp/claude/chk-t179r1b-716fbf97
S=D:/autoTesting/qa/evidence/t179a-lead-tester-core-r1-B/s1-table
export PYTHONDONTWRITEBYTECODE=1
mkdir -p $S/out $B/tmp/s1-$2
for i in $(seq 0 $(($3-1))); do
  R1B_TMP=$B/tmp/s1-$2 timeout 1500 $B/$1/.venv/Scripts/python -I $S/s1_table.py $B/$1 $S/out/$2.shard$i.json $i $3 > $S/out/$2.shard$i.log 2>&1 &
done
wait
echo done-$2
