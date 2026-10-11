import json, sys
E = sys.argv[1]
b = {(r["policy"], r["dest"]): r for r in json.load(open(f"{E}/s2-base.json"))}
h = {(r["policy"], r["dest"]): r for r in json.load(open(f"{E}/s2-head.json"))}
out = []
def P(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s)
for pol in ("read_only", "test_account", "allow_writes"):
    rows = [h[k] for k in h if k[0] == pol]
    ex = [r for r in rows if r["executed"]]; rf = [r for r in rows if not r["executed"]]
    P(f"== {pol}: {len(rows)} destinations; head executed {len(ex)}, refused {len(rf)}; escaped exceptions {sum(1 for r in rows if r['raised'])}; "
      f"refused rows with sessions>0 or calls>0 or files>0: {sum(1 for r in rf if r['sessions'] or r['run_case_calls'] or r['files'])}")
    cls = {}
    for r in rf: cls[r["refusal"]] = cls.get(r["refusal"], 0) + 1
    P("   refusal classes:", cls)
    if pol == "read_only":
        P("   READ_ONLY executed at head (plain in-domain read per independent classifier?):")
        for r in ex: P(f"     {r['dest']!r:60} plain_read={r['plain_read']} ({r['plain_why']}) goto@head={r['goto']}")
        bad = [r for r in ex if not r["plain_read"]]
        P("   READ_ONLY executed but NOT a plain read:", len(bad))
        for r in bad: P("     ", r["dest"], r["plain_why"], "goto:", r["goto"])
    else:
        P("   head-executed whose real goto (act time) would NOT refuse, yet classifier says not a plain in-domain read:")
        for r in ex:
            if r["goto"] is None and not r["plain_read"]: P(f"     {r['dest']!r:60} {r['plain_why']}")
        P("   base-executed -> head-refused (differences), with base goto result:")
        for k in h:
            if k[0] == pol and b[k]["executed"] and not h[k]["executed"]:
                P(f"     {k[1]!r:60} head={h[k]['refusal']} base-goto={b[k]['goto']}")
        P("   base-executed, head-refused, base goto would NOT refuse (narrowing):",
          [k[1] for k in h if k[0]==pol and b[k]["executed"] and not h[k]["executed"] and b[k]["goto"] is None])
        P("   head-executed but base-refused:", [k[1] for k in h if k[0]==pol and h[k]["executed"] and not b[k]["executed"]])
        P("   base refused anything (any class):", [ (k[1]) for k in b if k[0]==pol and not b[k]["executed"]][:5])
    # allowed under RO vs other policies sanity
open(f"{E}/s2-summary.txt", "w", encoding="utf-8").write("\n".join(out))
