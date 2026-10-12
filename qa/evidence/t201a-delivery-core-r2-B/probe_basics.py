from __future__ import annotations
import sys, tempfile, threading, time
from datetime import UTC, datetime
from pathlib import Path
import autotester
from autotester.delivery.inbox import DeliveryLog, deliver_once
from autotester.schema.delivery import DeliveryStatus, Recipient, RenderedMessage

print("autotester.__file__ =", autotester.__file__)
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
MSG = RenderedMessage(subject="s", body="b")
RCP = Recipient(user_id="alice", address="a@example.test")


class T:
    outcome = DeliveryStatus.SENT
    def __init__(self, delay=0.0): self.calls, self.delay, self.lock = 0, delay, threading.Lock()
    def send(self, to, message, *, key):
        with self.lock: self.calls += 1
        time.sleep(self.delay)

def go(log, tr, **kw):
    return deliver_once(log, tr, RCP, MSG, run_id="Run-1", now=NOW, scrub=lambda s: s, **kw)

with tempfile.TemporaryDirectory(dir=sys.argv[1]) as d:
    log, tr = DeliveryLog(Path(d)), T()
    r1 = go(log, tr)
    print("first:", r1.status.value, r1.attempts, "sends", tr.calls)
    r2 = go(log, tr)
    print("second:", r2.status.value, r2.attempts, "sends", tr.calls, "files", len(list((Path(d)/"records").iterdir())))
    assert tr.calls == 1 and r1.status is DeliveryStatus.SENT and r2.status is DeliveryStatus.SENT

for trial in range(20):
    with tempfile.TemporaryDirectory(dir=sys.argv[1]) as d:
        log, tr = DeliveryLog(Path(d)), T(delay=0.05)
        res, bar = [], threading.Barrier(2)
        def w():
            bar.wait(); res.append(go(log, tr))
        ts = [threading.Thread(target=w) for _ in range(2)]
        [t.start() for t in ts]; [t.join() for t in ts]
        files = sorted(p.name for p in (Path(d)/"records").iterdir())
        assert tr.calls == 1, (trial, tr.calls)
        assert len(files) == 1, files
print("race: 20 trials of 2 threads, each sent exactly once, exactly one record file")
