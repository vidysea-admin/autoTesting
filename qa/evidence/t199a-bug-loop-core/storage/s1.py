from common import *
import threading, json, os
from pathlib import Path
print("autotester file:", autotester.__file__)
evs = multi_events(5, 130)[:640]
print("distinct events", len({e.event_id for e in evs}))
bad_total = 0
for rnd in range(10):
    root = fresh("s1")
    errors = []
    def work(i, chunk):
        try:
            st = BugStore(Path(root))
            st.apply_all(chunk)
        except BaseException as ex:
            errors.append(repr(ex))
    chunks = [evs[i*40:(i+1)*40] for i in range(16)]
    ts = [threading.Thread(target=work, args=(i, c)) for i, c in enumerate(chunks)]
    for d in range(4):  # duplicates: other threads apply every event
        for i in range(16):
            pass
    dup = [threading.Thread(target=work, args=(100+d, evs[d*160:(d+1)*160])) for d in range(4)]
    allt = ts + dup
    for t in allt: t.start()
    for t in allt: t.join()
    files = list((Path(root)/EVENTS_DIR).glob("*"))
    names = sorted(f.name for f in files)
    nonbev = [n for n in names if not n.startswith("bev_")]
    st = BugStore(Path(root))
    try:
        got = {k: v.model_dump_json() for k, v in st.bugs().items()}
    except BaseException as ex:
        got = repr(ex)
    exp = {k: v.model_dump_json() for k, v in fold(evs).items()}
    ok = (not errors) and len(files) == len(evs) and not nonbev and got == exp
    bad_total += (not ok)
    print(rnd, "ok" if ok else "FAIL", "files", len(files), "errors", errors[:2], "nonbev", nonbev[:3], "match", got == exp)
print("bad rounds", bad_total)
