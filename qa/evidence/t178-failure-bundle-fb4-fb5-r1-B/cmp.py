import json,re,sys,collections
def norm(s):
    s=re.sub(r"proposal_spec_[0-9a-f]+","<FP>",s); s=re.sub(r"proposal_[0-9a-f]+","<ID>",s)
    s=re.sub(r"(case|flow)_[0-9a-f]{6,}","<CID>",s)
    s=re.sub(r"[A-Za-z]:[^ \"']*?t178r1b-\w+","<ROOT>",s)
    return s
def summ(res):
    o={}
    for k,v in res.items():
        d={}
        for kk,vv in v.items():
            if kk=="files":
                fs={}
                for fn,txt in vv.items():
                    if fn.endswith(".jsonl"):
                        rows=[json.loads(l) for l in txt.splitlines() if l.strip().startswith("{") and l.strip().endswith("}")]
                        c=collections.Counter(r.get("status") for r in rows)
                        fs[norm(fn)]=(len(txt.splitlines()),dict(c), sorted(set(r.get("reviewed_by") or "-" for r in rows)))
                    else: fs[norm(fn)]="len%d"%len(txt)
                d[kk]=fs
            else:
                d[kk]=json.loads(norm(json.dumps(vv)))
        o[k]=d
    return o
a=summ(json.load(open(sys.argv[1]))); b=summ(json.load(open(sys.argv[2])))
nd=0
for k in sorted(a):
    if a[k]==b[k]: print("SAME",k, "calls",a[k]["calls"])
    else:
        nd+=1; print("DIFF",k)
        for kk in a[k]:
            if a[k][kk]!=b[k].get(kk): print("  ",kk,"\n    base:",str(a[k][kk])[:600],"\n    head:",str(b[k].get(kk))[:600])
print("scenarios",len(a),"diffs",nd)
