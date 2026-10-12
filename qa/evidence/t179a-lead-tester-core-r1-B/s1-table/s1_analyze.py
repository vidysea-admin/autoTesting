"""Merge shards and answer (a)-(d). Run with any python: s1_analyze.py  (reads ./out/*.json, writes ./analysis.txt,
nav_targets.json for the S1(b) goto probe)."""
from __future__ import annotations

import ast
import collections
import glob
import json
import re
import sys
from urllib.parse import unquote, urlsplit

S = "D:/autoTesting/qa/evidence/t179a-lead-tester-core-r1-B/s1-table"
out_lines: list[str] = []


def P(*a):
    line = " ".join(str(x) for x in a)
    out_lines.append(line)
    print(line)


def load(tag):
    rows, meta = {}, {"rejected": collections.Counter(), "wall": 0, "specs": 0}
    for f in sorted(glob.glob(f"{S}/out/{tag}.shard*.json")):
        d = json.load(open(f))
        meta["wall"] = max(meta["wall"], d["wall_s"])
        meta["specs"] = d["specs_total"]
        for k, v in d["rejected"].items():
            meta["rejected"][k] += v
        for r in d["rows"]:
            assert r["key"] not in rows, r["key"]
            rows[r["key"]] = r
    return rows, meta


base, mb = load("base1")
head, mh = load("head1")
head2, _ = load("head2")
P(f"rows base={len(base)} head={len(head)} head2={len(head2)} specs={mh['specs']} "
  f"step/case-rejected: base={dict(mb['rejected'])} head={dict(mh['rejected'])}")
P(f"wall_s (slowest shard): base={mb['wall']} head={mh['wall']}  (shards in parallel)")
assert set(base) == set(head), "row key mismatch"

# ---- totals per policy/action -----------------------------------------------
P("\n## TOTALS rows executed/refused  (policy, action | base exec/ref | head exec/ref)")
tot = collections.defaultdict(lambda: [0, 0, 0, 0])
for k, h in head.items():
    b = base[k]
    t = tot[(h["policy"], h["action"])]
    t[0 if b["executed"] else 1] += 1
    t[2 if h["executed"] else 3] += 1
for key in sorted(tot):
    b1, b2, h1, h2 = tot[key]
    P(f"{key[0]:13} {key[1]:10} | base {b1:5}/{b2:5} | head {h1:5}/{h2:5}")
for pol in ("read_only", "test_account", "allow_writes"):
    s = [sum(v[i] for k, v in tot.items() if k[0] == pol) for i in range(4)]
    P(f"TOTAL {pol:13} | base {s[0]:5}/{s[1]:5} | head {s[2]:5}/{s[3]:5}")
P("grand total rows:", len(head), "(incl. composed:", sum(1 for r in head.values() if r["pos"] == "composed"), ")")

# ---- escapes / refusal class sanity -------------------------------------------
P("\n## anomalies: escaped exceptions")
for tag, rows in (("base", base), ("head", head), ("head2", head2)):
    bad = [r["key"] for r in rows.values() if r["raised"]]
    P(tag, "escaped:", len(bad), bad[:5])
P("head refusal class distribution (policy, refusal):",
  dict(collections.Counter((r["policy"], r["refusal"]) for r in head.values())))
P("base refusal class distribution:", dict(collections.Counter((r["policy"], r["refusal"]) for r in base.values())))
odd = [r for r in head.values() if not r["executed"] and r["refusal"] not in ("write_policy", "destination")]
P("head refused with a class other than write_policy/destination:", len(odd), [(r["key"], r["refusal"]) for r in odd[:10]])
odd2 = [r for r in head.values() if r["executed"] and r["refusal"]]
P("head executed but refusal set:", len(odd2))
odd3 = [r for r in head.values() if r["policy"] != "read_only" and r["refusal"] == "write_policy"]
P("head write_policy refusals at TEST_ACCOUNT/ALLOW_WRITES:", len(odd3),
  collections.Counter((r["policy"], r["action"]) for r in odd3))
odd4 = [r for r in head.values() if r["refusal"] == "destination" and r["action"] != "navigate" and r["pos"] != "composed"
        and not any(s for s in [])]
P("head destination refusals on rows whose TESTED action is not navigate (fillers may navigate):", len(odd4))
P("rows where 'destination' refusal class but READ_ONLY-only reason:", sum(
    1 for r in head.values() if r["refusal"] == "destination" and "http(s) URL inside" not in r["summary"]))
P("rows where write_policy refusal summary contains 'destination is not':", sum(
    1 for r in head.values() if r["refusal"] == "write_policy" and "destination is not" in r["summary"]))

# ---- (a) READ_ONLY oracle -------------------------------------------------------
P("\n## (a) READ_ONLY at HEAD")
ro = [r for r in head.values() if r["policy"] == "read_only"]
ro_exec = [r for r in ro if r["executed"]]
viol = [r for r in ro_exec if r["oracle_mut_outside"]]
P(f"READ_ONLY rows={len(ro)} executed={len(ro_exec)}; EXECUTED with mutating step outside login carve-out (oracle) = {len(viol)}")
for r in viol:
    P("  VIOLATION", r["key"], r["summary"])
# STRICT oracle pass (whole FILL value must be >=1 declared placeholder and NOTHING else, no whitespace pad)
PHR = re.compile(r"\{\{SECRET:([A-Z0-9_]+)\}\}")
def strict_cred(v):
    return bool(v) and bool(PHR.findall(v)) and PHR.sub("", v) == "" and all(k in ("APP_PASS", "APP_USER") for k in PHR.findall(v))
strict = []
for r in ro_exec:
    if r["pos"] == "composed":
        st = [(a, ast.literal_eval(t) if t != "None" else None, ast.literal_eval(v) if v != "None" else None) for a, t, v in r["steps"]]
        if any(a == "fill" and not strict_cred(v) for a, t, v in st):
            strict.append(r["key"])
    elif r["action"] == "fill":
        v = ast.literal_eval(r["value"]) if r["value"] != "None" else None
        if not strict_cred(v):
            strict.append(r["key"])
P(f"STRICT oracle (whole FILL value = declared placeholders only, >=1, no whitespace): executed READ_ONLY rows with a non-credential FILL = {len(strict)}")
for k in strict:
    P("  STRICT-VIOLATION", k)
ro_base_exec = [r for r in base.values() if r["policy"] == "read_only" and r["executed"]]
P(f"(for contrast) BASE READ_ONLY executed={len(ro_base_exec)}, of which oracle-violating="
  f"{sum(1 for r in ro_base_exec if r['oracle_mut_outside'])}")
# dedupe list
P("\nREAD_ONLY executed at HEAD, deduped by (tested action, target, value, login) with counts [positions]:")
grp = collections.defaultdict(list)
for r in ro_exec:
    if r["pos"] == "composed":
        continue
    grp[(r["action"], r["target"], r["value"], r["login"])].append(r["pos"])
cat = collections.Counter()
for key, poss in sorted(grp.items()):
    a, t, v, lg = key
    if a in ("wait", "assert", "back", "hover", "scroll"):
        why = "read/wait (no state change)"
    elif a == "navigate":
        why = "nav (in-domain absolute http(s), no query unless login)" + (" [LOGIN]" if lg else "")
    elif lg:
        why = "login carve-out: " + a
    else:
        why = "??? MUTATING NOT LOGIN"
    cat[(a, why)] += len(poss)
P("  category counts (rows):")
for (a, why), n in sorted(cat.items()):
    P(f"   {a:10} {n:5}  {why}")
P(f"  distinct deduped keys: {len(grp)}")
only_non_read = {k: v for k, v in grp.items() if k[0] not in ("wait", "assert", "back", "hover", "scroll")}
P("  deduped NAVIGATE + login-mutating (non-read tested actions) keys:")
for key, poss in sorted(only_non_read.items()):
    P(f"   {key[0]:9} T={key[1][:48]:50} V={key[2][:30]:32} login={key[3]!s:5} n={len(poss)}")
P("  deduped read/wait keys (tested action; count of keys; rows):",
  {a: (sum(1 for k in grp if k[0] == a), sum(len(v) for k, v in grp.items() if k[0] == a))
   for a in ("wait", "assert", "back", "hover", "scroll")})
P("\nREAD_ONLY executed COMPOSED rows at HEAD:")
for r in ro_exec:
    if r["pos"] == "composed":
        P("  ", "LOGIN" if r["login"] else "plain", r["target"], "oracle_mut_outside=", r["oracle_mut_outside"], r["steps"])

# independent NAVIGATE oracle for executed READ_ONLY navigations
DENY = re.compile(r"delete|remove|logout|log[-_ ]?out|sign[-_ ]?out|pay|send|destroy|cancel|purchase|confirm|submit|"
                  r"unsubscribe|checkout|buy|order|save|register", re.I)
nav_anom = []
for r in ro_exec:
    if r["action"] != "navigate" or r["pos"] == "composed":
        continue
    # reconstruct target from label
    t = ast.literal_eval(r["target"]) if r["target"].startswith(("'", '"')) else r["target"]
    u = urlsplit(t.strip()) if isinstance(t, str) else None
    issues = []
    if u is None or u.scheme not in ("http", "https"):
        issues.append("not absolute http(s)")
    if u is not None and u.query and not r["login"]:
        issues.append("query on non-login")
    if "{{" in str(t):
        issues.append("placeholder")
    if u is not None and DENY.search(unquote(u.path + " " + u.fragment)):
        issues.append("destructive-ish word in path/fragment")
    if u is not None and u.hostname not in ("app.test", "sub.app.test"):
        issues.append(f"host {u.hostname}")
    if issues:
        nav_anom.append((r["key"], issues))
P(f"\nexecuted READ_ONLY NAVIGATE rows failing my independent nav oracle: {len(nav_anom)} rows")
seen = set()
for k, i in nav_anom:
    kk = (k.split("|")[2], k.split("|")[5], tuple(i))
    if kk not in seen:
        seen.add(kk)
        P("  ", k, i)

# ---- (b) TEST_ACCOUNT / ALLOW_WRITES diffs -----------------------------------------
P("\n## (b) base-executed -> head-refused at TEST_ACCOUNT / ALLOW_WRITES")
diffs = [(base[k], head[k]) for k in head if head[k]["policy"] != "read_only" and base[k]["executed"] and not head[k]["executed"]]
P("count rows:", len(diffs))
byclass = collections.Counter((h["policy"], h["action"], h["refusal"]) for b, h in diffs)
P("by (policy, tested action, head refusal class):", dict(byclass))
non_dest = [(b, h) for b, h in diffs if h["refusal"] != "destination"]
P("NON-destination differences (NARROWING FINDINGS):", len(non_dest))
for b, h in non_dest[:40]:
    P("   NARROW", h["key"], h["refusal"], h["summary"])
reverse = [k for k in head if head[k]["policy"] != "read_only" and not base[k]["executed"] and head[k]["executed"]]
P("head-executes-but-base-refused (widening) at non-RO:", len(reverse), reverse[:10])
nav_targets = sorted({ast.literal_eval(h["target"]) if h["target"].startswith(("'", '"')) else h["target"]
                      for b, h in diffs if h["action"] == "navigate"} )
P("distinct NAVIGATE target labels differing:", len(nav_targets))
for t in nav_targets:
    P("   ", t)
# also fillers: differences where tested action != navigate but case refused on destination (filler nav)
fill_nav = [(b, h) for b, h in diffs if h["action"] != "navigate"]
P("differing rows whose tested step is not NAVIGATE:", len(fill_nav), [h["key"] for b, h in fill_nav[:5]])
# raw target strings for goto probe (need exact strings: re-derive from NAV list in s1_table)
json.dump(nav_targets, open(f"{S}/nav_targets.json", "w"))
P("per-policy diff counts equal?", {p: sum(1 for b, h in diffs if h["policy"] == p) for p in ("test_account", "allow_writes")})

# ---- (c) refused multi-step --------------------------------------------------------
P("\n## (c) refused multi-step rows")
for tag, rows in (("head", head), ("base", base)):
    ms = [r for r in rows.values() if r["nsteps"] > 1 and not r["executed"]]
    bad = [r for r in ms if r["sessions"] or r["run_case_calls"] or r["n_files"] or r["tree_changed"]]
    by = collections.Counter(r["nsteps"] for r in ms)
    P(f"{tag}: refused multi-step rows={len(ms)} (by nsteps {dict(by)}) violating(0 sessions/0 run_case/0 files/tree unchanged)={len(bad)}")
    for r in bad[:10]:
        P("   VIOL", r["key"], r["sessions"], r["run_case_calls"], r["n_files"], r["tree_changed"])
    ex = [r for r in rows.values() if r["executed"]]
    P(f"{tag}: executed rows with sessions!=1 or run_case_calls!=1: {sum(1 for r in ex if r['sessions'] != 1 or r['run_case_calls'] != 1)}")
    P(f"{tag}: refused rows total={sum(1 for r in rows.values() if not r['executed'])}, any refused with sessions/calls/files: "
      f"{sum(1 for r in rows.values() if not r['executed'] and (r['sessions'] or r['run_case_calls'] or r['n_files'] or r['tree_changed']))}")

# ---- (d) item 7 cost ----------------------------------------------------------------
P("\n## (d) BENIGN READ_ONLY rows executed at base, refused at head")
cost = [(base[k], head[k]) for k in head if head[k]["policy"] == "read_only" and head[k]["benign"]
        and base[k]["executed"] and not head[k]["executed"]]
P("benign rows (all positions, login+plain):", len(cost))
P("by tested action (rows):", dict(collections.Counter(h["action"] for b, h in cost)))
single = [h for b, h in cost if h["pos"] == "single" and not h["login"]]
P("same, single-step non-login only:", len(single), dict(collections.Counter(h["action"] for h in single)))
dd = collections.defaultdict(int)
for b, h in cost:
    if h["pos"] == "single" and not h["login"]:
        dd[(h["action"], h["target"], h["value"])] += 1
P("single-step non-login distinct (action,target,value):", len(dd))
for k in sorted(dd):
    P("   ", k)
benign_total = sum(1 for r in head.values() if r["policy"] == "read_only" and r["benign"] and base[r["key"]]["executed"])
P("benign READ_ONLY rows executed at base (denominator):", benign_total)
rest = [h for k, h in head.items() if h["policy"] == "read_only" and h["benign"] and not base[k]["executed"]]
P("benign READ_ONLY rows refused at base already:", len(rest), dict(collections.Counter(h["action"] for h in rest)))

# ---- determinism ---------------------------------------------------------------------
P("\n## determinism head vs head2")
if head2:
    f = ("executed", "refusal", "sessions", "run_case_calls", "n_files", "summary", "raised", "tree_changed", "ok")
    nd = [k for k in head if k not in head2 or any(head[k][x] != head2[k][x] for x in f)]
    P("rows differing between two identical head runs:", len(nd), nd[:5])
else:
    P("head2 missing")

# ---- other base vs head differences at READ_ONLY (full) --------------------------------
P("\n## READ_ONLY base vs head transitions")
P(dict(collections.Counter((base[k]["executed"], head[k]["executed"]) for k in head if head[k]["policy"] == "read_only")))
open(f"{S}/analysis.txt", "w", encoding="utf-8").write("\n".join(out_lines))
