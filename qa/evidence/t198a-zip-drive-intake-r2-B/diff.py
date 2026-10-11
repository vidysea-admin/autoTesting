import sys, tempfile, collections, traceback
from pathlib import Path
import test_hostile as T
from zip_fixtures import make_store
from autotester.sources.zip_intake import expand_zip
import autotester.sources.zip_intake as z
print("module", z.__file__)
cnt = collections.Counter(); raised = collections.defaultdict(list); outcomes = collections.Counter()
for cid, data in T.CASES:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); st = make_store(d); a = d / "h.zip"; a.write_bytes(data)
        try:
            r = expand_zip(st, a, max_file_bytes=4*1024*1024)
            outcomes[(cid.split("-")[0], r.status.value)] += 1
            cnt["ok"] += 1
        except BaseException as e:
            cnt[type(e).__name__] += 1; raised[type(e).__name__].append(cid)
print(dict(cnt))
for k, v in raised.items(): print(k, len(v), v[:6])
reg = collections.Counter()
for (k, s), n in sorted(outcomes.items()): print(k, s, n)
