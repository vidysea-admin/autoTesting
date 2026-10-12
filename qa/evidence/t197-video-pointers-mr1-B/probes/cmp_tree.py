import json
t={n:json.load(open(f"tree-{n}.json")) for n in("unit","master","head")}
for n in t: print(n, t[n]["file"], len(t[n]["commands"]))
m,h,u=(t[x]["commands"] for x in("master","head","unit"))
print("master-only in head?", sorted(set(m)-set(h)))
print("head-only vs master:", sorted(set(h)-set(m)))
print("unit-only vs head:", sorted(set(u)-set(h)), "head-only vs unit:", sorted(set(h)-set(u)))
diff=[k for k in m if k in h and m[k]!=h[k]]
print("help differs master->head:", diff)
for k in diff:
    import difflib
    print("--",k); print("\n".join(difflib.unified_diff(m[k]["help"].splitlines(),h[k]["help"].splitlines(),lineterm="",n=0)))
# unit vs head, for common commands that exist in both
du=[k for k in u if k in h and u[k]!=h[k]]
print("help differs unit->head:", du)
print("review help identical unit/head:", u["ingest review"]==h["ingest review"])
print("groups:", sorted(k for k,v in h.items() if v["group"]))
print("ingest cmds head:", sorted(k for k in h if k.startswith("ingest ")))
print("ingest cmds master:", sorted(k for k in m if k.startswith("ingest ")))
