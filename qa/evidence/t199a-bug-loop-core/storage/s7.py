from common import *
import time
from pathlib import Path
evs = multi_events(8, 130)   # 1040 events
root = Path(fresh("s7")); st = BugStore(root)
marks = {1, 50, 100, 200, 400}
t_total = time.perf_counter(); last = time.perf_counter(); times = []
for i, e in enumerate(evs[:400], 1):
    t = time.perf_counter(); st.apply(e); dt = time.perf_counter() - t; times.append(dt)
    if i in (50, 100, 200, 400):
        print(f"apply #{i}: this call {dt*1000:.1f} ms; mean of last 10 {sum(times[-10:])/10*1000:.1f} ms; cumulative {time.perf_counter()-t_total:.2f} s")
print("first call ms", times[0]*1000)
# fill to 1000 via apply_all (bulk), then time single apply and bugs()
st.apply_all(evs[400:1000])
files = len(list(st.dir.glob("*")))
t = time.perf_counter(); b = st.bugs(); print(f"bugs() on {files} files: {(time.perf_counter()-t)*1000:.0f} ms (warm cache)")
t = time.perf_counter(); st.apply(evs[1000]); print(f"single apply at {files} files: {(time.perf_counter()-t)*1000:.0f} ms")
t = time.perf_counter(); st.apply(evs[1000]); print(f"duplicate apply at {files+1} files: {(time.perf_counter()-t)*1000:.0f} ms")
# 1000 sequential applies cost extrapolation
n = 1000; per_file = (time.perf_counter()-t) # dummy
