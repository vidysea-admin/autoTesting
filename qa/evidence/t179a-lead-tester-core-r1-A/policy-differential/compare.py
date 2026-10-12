"""Compare base.csv and head.csv row by row. Key columns: ok, refusal, sessions, run_case_calls.
Writes diff.txt (all differing rows) and prints a summary."""
import csv
import sys
from collections import Counter

E = sys.argv[1]
def load(n):
    return {(r["project"], r["policy"], r["row"]): r for r in csv.DictReader(open(f"{E}/{n}.csv", encoding="utf-8"))}
b, h = load("base"), load("head")
assert b.keys() == h.keys(), "row sets differ"
K = ["ok", "refusal", "sessions", "run_case_calls"]
def key(r): return "ok={} ref={} sess={} runs={}".format(r['ok'], r['refusal'] or '-', r['sessions'], r['run_case_calls'])
diffs = []
for k in b:
    if key(b[k]) != key(h[k]):
        diffs.append(k)
cnt = Counter((k[0], k[1]) for k in diffs)
tot = Counter((k[0], k[1]) for k in b)
lines = [f"rows total={len(b)} differing={len(diffs)}"]
for k, n in sorted(cnt.items()):
    lines.append(f"  {k[0]}/{k[1]}: {n} of {tot[k]}")
for k in diffs:
    lines.append(f"{k[0]} | {k[1]} | {k[2]}\n    BASE: {key(b[k])}\n    HEAD: {key(h[k])}\n    act_time: {h[k]['act_time']}  host_of: {h[k]['host_of']}")
open(f"{E}/diff.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines[:12]))
# consistency: act_time columns are computed from the same code in both runs
assert all(b[k]["act_time"] == h[k]["act_time"] for k in b), "act_time differs between copies"

# classification for non-READ_ONLY policies
cls = Counter()
for k in diffs:
    if k[1] == "read_only":
        continue
    bk, hk = b[k], h[k]
    a = h[k]["act_time"]
    if bk["ok"] == "True" and hk["ok"] == "False":
        cls["newly refused; act-time=" + (a.split()[0] if a else "n/a(non-navigate)")] += 1
    else:
        cls["other change"] += 1
print(dict(cls))
