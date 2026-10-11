from common import *
import autotester.store.bug_store as bsm
from autotester.schema.tracked_bug import *
from datetime import datetime, UTC
ev = BugEvent(bug_key="k"*200, kind=EventKind.ASSIGN, ref="r"*200, at=datetime(2026,10,1,9,5,tzinfo=UTC), actor="user:x", assignee="a")
n = bsm.file_name(ev); print(n, len(n), "event_id", ev.event_id, len(ev.event_id))
ev2 = BugEvent(bug_key="a", kind=EventKind.ASSIGN, ref="\u00e9\u4e2d"*100, at=datetime(9999,12,31,23,59,59,999999,tzinfo=UTC), actor="user:x", assignee="a")
print(bsm.file_name(ev2), len(bsm.file_name(ev2)))
import re
print("charset ok:", re.fullmatch(r"bev_[0-9a-f]{12}@\d{8}T\d{12}Z\.json", n) is not None, "has ':'?", ':' in n)
print("case-fold collisions possible? ids lowercase hex:", n == n.lower() or True, "name==name.lower() except T/Z:", re.sub(r"[TZ]","",n)==re.sub(r"[TZ]","",n).lower())
