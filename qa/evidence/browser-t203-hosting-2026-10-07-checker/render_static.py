import sys
from datetime import datetime, UTC
from autotester.schema.run_queue import QueueEntry, QueueStatus as Q
from autotester.ui.run_queue import RunQueue
from autotester.ui import run_queue_view, theme
q = RunQueue(spawn=lambda j: None, runner=lambda e: None, limit=lambda: 2)
def E(i,p,s,m,**k):
    return QueueEntry(id=i, project=p, status=s, enqueued_at=datetime(2026,10,7,9,m,tzinfo=UTC), **k)
q._entries = [
 E("run-RUN1","alpha",Q.RUNNING,1,started_at=datetime(2026,10,7,9,1,5,tzinfo=UTC)),
 E("run-RUN2","beta",Q.RUNNING,2,started_at=datetime(2026,10,7,9,2,5,tzinfo=UTC)),
 E("run-Q1","alpha",Q.QUEUED,3), E("run-Q2","beta",Q.QUEUED,4), E("run-Q3","alpha",Q.QUEUED,5),
 E("run-D1","alpha",Q.DONE,0,started_at=datetime(2026,10,7,8,1,tzinfo=UTC),finished_at=datetime(2026,10,7,8,5,tzinfo=UTC)),
]
body = "<h1>Report</h1>" + run_queue_view.queue_panel("alpha", q)
open(sys.argv[1], "w", encoding="utf-8").write(theme.page("Report", body, active_slug="alpha"))
