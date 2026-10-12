import json, statistics as st, sys
S = sys.argv[1]
runs = [json.load(open(f"{S}/run{i}.json")) for i in (1, 2, 3)]
names = [r["case"] for r in runs[0]]
def mm(v): return f"{min(v):.2f}/{st.median(v):.2f}/{max(v):.2f}"
lines = ["| case | direct wall min/med/max s | return | client bytes read (max) | listener sent (max) | accepts | public wall min/med/max s | public result | leftover thr/sock/netstat |",
         "|---|---|---|---|---|---|---|---|---|"]
maxd = maxp = 0; anomalies = []
for i, n in enumerate(names):
    rs = [r[i] for r in runs if i < len(r) and r[i]["case"] == n]
    d = [r["direct_wall"] for r in rs]; p = [r["public_wall"] for r in rs]
    maxd = max(maxd, max(d)); maxp = max(maxp, max(p))
    rets = {str(r["direct_ret"]) + (("!" + r["direct_exc"]) if r["direct_exc"] else "") for r in rs}
    left = any(r["threads_after_100ms"] or r["public_threads_after_100ms"] or r["threads_after_stop"]
               or r["client_sock_still_open"] or r["public_sock_open"] for r in rs) or bool(rs[0]["netstat_rows_after_stop"])
    acc = {(r["listener_accepts"], r["public_listener_accepts"], r["connect_calls"], r["public_connects"]) for r in rs}
    pub = {r["public"] for r in rs}
    lines.append(f"| {n} | {mm(d)} | {'/'.join(sorted(rets))} | {max(r['client_bytes'] for r in rs)} | {max(r['listener_sent'] for r in rs)} | {sorted(acc)} | {mm(p)} | {'/'.join(sorted(pub))} | {'LEAK' if left else 'none'} |")
    if rs[0].get("note"): anomalies.append((n, rs[0]["note"]))
    for r in rs:
        if r["aux_accepts"] and any(r["aux_accepts"]): anomalies.append((n, f"aux accepts {r['aux_accepts']}"))
        if r["connect_addrs"] and len(r["connect_addrs"]) > 1: anomalies.append((n, f"connect addrs {r['connect_addrs']}"))
open(f"{S}/results.md", "w").write("\n".join(lines) + f"\n\nMAX direct wall {maxd:.3f}s; MAX public wall {maxp:.3f}s\n\nnotes: {anomalies}\n")
print("\n".join(lines)); print(maxd, maxp); print(anomalies)
