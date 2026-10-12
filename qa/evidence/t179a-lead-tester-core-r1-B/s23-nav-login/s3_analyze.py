import json, sys
E = sys.argv[1]
b = {(r["row"], r["mode"]): r for r in json.load(open(f"{E}/s3-base.json"))}
h = {(r["row"], r["mode"]): r for r in json.load(open(f"{E}/s3-head.json"))}
out = []
def P(s): out.append(s); print(s)
P(f"rows {len(h)}; escaped exceptions head {sum(1 for r in h.values() if r['raised'])}; refused rows with sessions/calls/files>0: {sum(1 for r in h.values() if not r['executed'] and (r['sessions'] or r['run_case_calls'] or r['n_files_written']))}")
for mode in ("login", "other", "unset"):
    ex = [k for k in h if k[1] == mode and h[k]["executed"]]
    P(f"mode={mode}: head executed {len(ex)} / {sum(1 for k in h if k[1]==mode)}; base executed {sum(1 for k in b if k[1]==mode and b[k]['executed'])}")
P("\nHEAD EXECUTED rows, mode login:")
for k in h:
    if k[1] == "login" and h[k]["executed"]: P(f"  EXEC  {k[0]:55} {h[k]['steps'][:110]}")
P("\nHEAD EXECUTED rows, mode other/unset (must be only reads):")
for k in h:
    if k[1] != "login" and h[k]["executed"]: P(f"  EXEC  [{k[1]}] {k[0]:50} {h[k]['steps'][:110]}")
P("\nHEAD REFUSED rows, mode login:")
for k in h:
    if k[1] == "login" and not h[k]["executed"]: P(f"  REFUSED {h[k]['refusal']:13} {k[0]}")
P("\nbase executed in mode other/unset (the cycle-0 hole):  %d" % sum(1 for k in b if k[1]!="login" and b[k]["executed"]))
open(f"{E}/s3-summary.txt", "w", encoding="utf-8").write("\n".join(out))
