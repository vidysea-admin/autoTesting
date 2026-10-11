"""Blind-check A: report_url forms, message content, canary, scrub."""
from datetime import UTC, datetime
from autotester.core.redact import Redactor
from autotester.delivery.message import render_message
from autotester.schema.delivery import *
import inspect

NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)
def S(**o):
    b = dict(project_name="Demo", run_id="run-1", finished_at=NOW, counts=RunCounts(passed=1, failed=2, blocked=3, inconclusive=4),
             coverage_line="Coverage: 3 of 4 screens", label=ReportLabel.FAILED, report_url="https://t.test/runs/r1")
    b.update(o); return ReportSummary(**b)

urls = ["https://t.test/runs/r1", "/runs/r1", "http://t.test:8080/runs/r1", "https://t.test/runs/r1?token=abc", "https://t.test/runs/r1#frag",
        "https://user:pw@t.test/runs/r1", "https://user@t.test/runs/r1", "javascript:alert(1)", "JAVASCRIPT:alert(1)", "//evil.test/x", "///evil.test/x",
        "/\\evil.test", "\\\\evil.test\\x", "https://t.test\\@evil.test/x", "https://t.test/runs/r1\r\nBcc: z@y.test", "https://t.test/runs/r1 ", " https://t.test/x",
        "data:text/html,<script>", "ftp://t.test/x", "https://t.test", "https://t.test/", "https://t.test/%0d%0aBcc:z", "https://t.test/a b", "https://[::1]/x",
        "https://t.test/../../etc/passwd", "https://xn--e1afmkfd.test/x", "https://tеst.test/x", "/", "", "https://t.test:99999/x", "https://t.test/‮x"]
for u in urls:
    try:
        S(report_url=u); print("ACCEPT ", repr(u))
    except ValueError:
        print("refuse ", repr(u))

print("---- message text for a canary-laden summary")
CAN = "CANARY-SECRET-9f3a1c"
red = Redactor({"K": CAN}) if "Redactor" in globals() else None
try:
    sig = inspect.signature(Redactor.__init__); print("Redactor sig", sig)
except Exception as e: print(e)
