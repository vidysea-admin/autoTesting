from common import *
import threading, time
from pathlib import Path
from collections import Counter
evs = multi_events(5, 130)[:640]
total = Counter()
for rnd in range(5):
    root = fresh("s3"); stop = threading.Event(); errs = Counter(); reads = [0]
    def writer(i):
        BugStore(Path(root)).apply_all(evs[i*80:(i+1)*80])
        BugStore(Path(root)).apply_all(evs[:80])   # rewrite dups concurrently
    def reader():
        st = BugStore(Path(root))
        while not stop.is_set():
            try:
                st.bugs(); st.events(); reads[0] += 1
            except FileNotFoundError as ex:
                errs["FileNotFoundError(dir missing)"] += 1
            except BaseException as ex:
                errs[type(ex).__name__ + ":" + str(ex)[:60].replace(root,'R')] += 1
    ws = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
    rs = [threading.Thread(target=reader) for _ in range(3)]
    for t in rs + ws: t.start()
    for t in ws: t.join()
    stop.set()
    for t in rs: t.join()
    print(rnd, "reads", reads[0], "errors", dict(errs))
    total.update(errs)
print("TOTAL", dict(total))
