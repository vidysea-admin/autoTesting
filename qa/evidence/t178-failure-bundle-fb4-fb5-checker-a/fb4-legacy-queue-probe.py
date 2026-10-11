import json, pathlib, tempfile, sys
sys.path.insert(0, str(pathlib.Path(sys.argv[1])/"tests"))
from test_store import make_case
from autotester.schema.case import Case
from autotester.schema.run_queue import RunQueueFile, QueueEntry
from autotester.store.project_store import ProjectStore, PinnedCaseError
import autotester; print(autotester.__file__)
root = pathlib.Path(tempfile.mkdtemp())
st = ProjectStore("demo", root)
c = make_case("demo")
d = json.loads(c.model_dump_json()); d.pop("priority"); 
print("legacy no-priority ->", Case.model_validate(d).priority)
d2 = dict(d, pinned=True, pinned_issue_id="ISS-1", priority="p3"); print("legacy pinned p3 stored ->", Case.model_validate(d2).priority)
try: Case.model_validate(dict(d, priority="p9"))
except Exception as e: print("p9 rejected:", type(e).__name__)
try: Case.model_validate(dict(d, priority="p0", bogus=1))
except Exception as e: print("extra rejected:", type(e).__name__)
st.add_case(Case.model_validate(d2)); 
try: st.delete_case(Case.model_validate(d2).id); print("DELETED (bad)")
except PinnedCaseError as e: print("pinned delete refused")
old = {"entries":[{"id":"run-1","project":"demo","status":"queued","trigger":"button","enqueued_at":"2026-01-01T00:00:00Z"}]}
q = RunQueueFile.model_validate(old); print("old queue row loads, priorities =", q.entries[0].priorities)
try: QueueEntry(id="r", project="demo", priorities=["p0","zz"])
except Exception as e: print("bad queue priority rejected:", type(e).__name__)
