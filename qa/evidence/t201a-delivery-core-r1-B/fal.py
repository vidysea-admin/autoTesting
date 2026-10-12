"""Mini independent probe: one line per repaired item. Run with PYTHONPATH=<copy>/src."""
import os, sys, tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
import autotester
assert os.environ["H_EXPECT"] in autotester.__file__, autotester.__file__
from autotester.delivery.inbox import DeliveryLog, STALE_AFTER, deliver_once
from autotester.schema.delivery import DeliveryStatus, Recipient, RenderedMessage, ReportSummary, RunCounts, ReportLabel
NOW = datetime(2026, 10, 12, 9, tzinfo=UTC)
M = RenderedMessage(subject="s", body="b")
class T:
    outcome = DeliveryStatus.SENT
    def __init__(self): self.sent = []
    def send(self, to, message, *, key): self.sent.append(to.user_id)
def go(log, t, run, user, now=NOW, tr=None):
    return deliver_once(log, tr or t, Recipient(user_id=user, address=f"{user}@example.com"), M, run_id=run, now=now, scrub=lambda s: s)
def fresh(): return DeliveryLog(Path(tempfile.mkdtemp(prefix="fal-", dir=os.environ["H_TMP"])))
res = {}
# F1 key: separator spelled in ids, and case
log, t = fresh(), T()
go(log, t, "x__email__y", "z"); go(log, t, "x", "y__email__z")
go(log, t, "Alice9", "u"); go(log, t, "alice9", "u")
res["F1-key"] = len(t.sent) == 4
# F1 matching: dotted prefix, run listing
log, t = fresh(), T()
go(log, t, "run-1", "alice.smith"); go(log, t, "run-1", "alice")
a = log.records_for_run("x")
go(log, t, "x", "q"); go(log, t, "x__email__y", "q")
res["F1-matching"] = (len(t.sent) == 4 and [r.run_id for r in log.records_for_run("x")] == ["x"])
# F2: second worker with skewed clock closes the live attempt mid-send
log, outer = fresh(), T()
class Racing:
    outcome = DeliveryStatus.SENT
    def send(self, to, message, *, key): go(DeliveryLog(log.records_dir.parent), T(), "run-r", "ru", now=NOW + STALE_AFTER)
try:
    r = go(log, outer, "run-r", "ru", tr=Racing()); res["F2"] = r is not None and r.status is DeliveryStatus.FAILED
except FileExistsError as e:
    res["F2"] = False
# F3: report_url
def mkurl(u):
    ReportSummary(project_name="p", run_id="r1", finished_at=NOW, counts=RunCounts(passed=1, failed=0, blocked=0, inconclusive=0), coverage_line="c", label=ReportLabel.GREEN, report_url=u)
def refused(u):
    try: mkurl(u); return False
    except Exception: return True
res["F3-slashes"] = all(refused(u) for u in ("//host", "///host", "https://x//host"))
res["F3-ports"] = all(refused(f"https://x.test:{p}/r") for p in (0, 65536, 99999)) and not refused("https://x.test:65535/r") and not refused("/a//b")
print(res)
