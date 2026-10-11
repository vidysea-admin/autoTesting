import json, sys
a = {r["id"]: r for r in json.load(open(sys.argv[1]))}; b = {r["id"]: r for r in json.load(open(sys.argv[2]))}
ndiff = 0
print("rows", len(a), len(b), "ids equal:", set(a) == set(b))
for k in sorted(a):
    x, y = a[k], b[k]; msgs = []
    for i, (sx, sy) in enumerate(zip(x["steps"], y["steps"])):
        for f in ("exit", "stdout", "stderr"):
            if sx[f] != sy[f]: msgs.append(f"step{i}.{f}")
    if x["spy"] != y["spy"]: msgs.append("spy")
    if x["listing"] != y["listing"]: msgs.append("listing")
    if len(x["steps"]) != len(y["steps"]): msgs.append("nsteps")
    if msgs: ndiff += 1; print("DIFF", k, msgs)
print("rows with any difference:", ndiff)
