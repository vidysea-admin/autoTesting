"""Step 2: old (7dd225d4) vs new (701a50e6) records_for_run pattern equality + same lists on a real store."""
import importlib.util, sys, tempfile, itertools, random
from pathlib import Path
from datetime import datetime
head, base = Path(sys.argv[1]), Path(sys.argv[2])
import autotester
norm=lambda s: s.lower().replace(chr(92),'/'); assert norm(str(head)) in norm(autotester.__file__), autotester.__file__
print("autotester.__file__ =", autotester.__file__)
def load(name, p):
    s = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(s)
    sys.modules[name] = m; s.loader.exec_module(m); return m
new = load("inbox_new", head/"src/autotester/delivery/inbox.py")
old = load("inbox_old", base/"src/autotester/delivery/inbox.py")
assert "inbox_old" in old.__name__ and old.__file__ != new.__file__
print("old file:", old.__file__); print("new file:", new.__file__)
ids = ["run1","Run1","RUN-1","a.b","a-b","a_b","A_B","x","x__email__y","x__inbox__y","email__x","run1.2","run1",
       "r","R","a"*64,"A"*64,"_"*0 or "a_a","a1_B-c.D","x_","Z9",("ab_"*21)+"a", "0", "9a", "a.1", "a.1.2", "inbox", "email"]
ids = [i for i in ids if i]
bad = 0; n = 0
for rid in ids:
    try: new.safe_id(rid)
    except ValueError: continue
    pats = []
    for m in (old, new):
        log = m.DeliveryLog(Path("/nonexistent"))
        cap = []
        log._load = lambda name, cap=cap: cap.append(name) or []
        log.records_for_run(rid)
        pats.append((cap[0].pattern, cap[0].flags))
    n += 1
    if pats[0] != pats[1]: bad += 1; print("DIFF", rid, pats)
print(f"pattern ids compared={n} different={bad}")
print("sample:", pats[0][0][:140])
assert bad == 0 and n >= 20
# module-level constants equal
assert old._CHANNELS == new._CHANNELS and old._PART == new._PART
print("_CHANNELS/_PART equal:", new._CHANNELS, new._PART)
# real store
from autotester.schema.delivery import DeliveryRecord, DeliveryChannel, DeliveryStatus
runs = ["run1","Run1","RUN1","run1.2","run1-2","a_b","A_B","x","x__email__y","x__inbox__y","y","email__x","r.1"]
users = ["alice","Alice","alice.smith","alice.01","bob","y__email__z","z","u_1","U_1","x__email__y"]
rnd = random.Random(7)
tmp = Path(tempfile.mkdtemp(prefix="t201a-store-", dir=sys.argv[3]))
logs = {}
count = 0
for tag, m in (("old", old), ("new", new)):
    root = tmp/tag; log = m.DeliveryLog(root); logs[tag]=log
    recs = []
    for r, u, ch in itertools.product(runs, users, list(DeliveryChannel)):
        try: key = m.delivery_key(r, ch, u)
        except ValueError: continue
        for att in range(1, random.Random(f"{r}{u}{ch}").randint(1,3)+1):
            rec = DeliveryRecord(created_at=datetime(2026,1,1,tzinfo=__import__("datetime").timezone.utc), run_id=r, channel=ch, recipient_user_id=u, status=DeliveryStatus.FAILED if att<3 else (DeliveryStatus.SENT if ch is DeliveryChannel.EMAIL else DeliveryStatus.OUTBOXED), error="e", attempts=att, next_retry_at=datetime(2026,1,1) if att<3 else None)
            log.append(key, rec); count += 1
    # stray files
    (root/"records"/"stray.txt").write_text("x"); 
    (root/"records"/"email__run1__alice.01.02.json.bak").write_text("x")
print("records per store:", count//2)
same_run = same_key = 0
for r in runs + ["nope","run","RUN1x","x__email"]:
    a, b = old and logs["old"].records_for_run(r), logs["new"].records_for_run(r)
    assert [x.model_dump_json() for x in a] == [x.model_dump_json() for x in b], r
    same_run += 1
for r, u, ch in itertools.product(runs, users, list(DeliveryChannel)):
    try: key = new.delivery_key(r, ch, u)
    except ValueError: continue
    a, b = logs["old"].records_for_key(key), logs["new"].records_for_key(key)
    assert [x.model_dump_json() for x in a] == [x.model_dump_json() for x in b], key
    same_key += 1
tot = sum(len(logs["new"].records_for_run(r)) for r in runs)
print(f"records_for_run identical for {same_run} run ids, records_for_key identical for {same_key} keys; total records via run lookup={tot}")
assert tot == count//2
print("ALL EQUAL")
