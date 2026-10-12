"""Step 4 own inputs for C6 C7 C8 C9 C11 (files touched: delivery/inbox.py). Loopback/no network: fake transports only."""
import sys, tempfile, threading, json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import autotester; print(autotester.__file__)
from autotester.core.redact import Redactor
from autotester.delivery.inbox import (DeliveryLog, deliver_once, delivery_key, MAX_ATTEMPTS, retry_delay, STALE_AFTER)
from autotester.delivery.email import TransportError
from autotester.schema.delivery import Recipient, RenderedMessage, DeliveryChannel, DeliveryStatus
tmp = Path(tempfile.mkdtemp(prefix="c4-", dir=sys.argv[1]))
PW, CAN = "hunter2-S3CRET-pw", "CANARY-page-text-zzz"
scrub = Redactor({"PW": PW, "CANARY": CAN}).scrub
msg = RenderedMessage(subject="s", body="b")
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
class Ok:
    outcome = DeliveryStatus.SENT
    def __init__(s): s.calls = []; s.lock = threading.Lock()
    def send(s, to, message, *, key):
        import time; time.sleep(0.05)
        with s.lock: s.calls.append((to.user_id, key))
class Boom:
    outcome = DeliveryStatus.SENT
    def __init__(s, exc): s.exc = exc; s.n = 0
    def send(s, to, message, *, key): s.n += 1; raise s.exc
def rcp(u): return Recipient(user_id=u, address=f"{u.lower()}@example.test")
# --- C8 / C9 / C6 / C7: unexpected exception carrying secrets, driven through the whole retry schedule
log = DeliveryLog(tmp/"c8")
tr = Boom(RuntimeError(f"smtp said {PW} {CAN} to alice@example.test"))
now = T0; seen = []
for i in range(MAX_ATTEMPTS + 3):
    rec = deliver_once(log, tr, rcp("alice"), msg, run_id="Run1", now=now, scrub=scrub)   # must never raise
    seen.append((rec.attempts, rec.status.value, rec.next_retry_at))
    if rec.next_retry_at: now = rec.next_retry_at
    else: now = now + timedelta(hours=1)
print("attempt trail:", [(a, s, (n - T0).total_seconds() / 60 if n else None) for a, s, n in seen])
assert tr.n == MAX_ATTEMPTS, tr.n                                        # C7 bounded
delays = [retry_delay(i) for i in range(1, MAX_ATTEMPTS + 1)]
assert [d.total_seconds() / 60 if d else None for d in delays] == [1, 5, 30, None]
recs = log.records_for_run("Run1"); assert len(recs) == MAX_ATTEMPTS and recs[-1].next_retry_at is None
blob = "".join(p.read_text("utf-8") for p in (tmp/"c8").rglob("*") if p.is_file())
for secret in (PW, CAN, "alice@example.test"): assert secret not in blob, secret   # C9 / C6 (no address stored)
assert all(r.status is DeliveryStatus.FAILED for r in recs)
print("C7/C8/C9/C6 ok; stored error:", recs[0].error)
# C8: BaseException subclasses outside Exception (KeyboardInterrupt) are not swallowed (documented: except Exception)
try:
    deliver_once(DeliveryLog(tmp/"ki"), Boom(KeyboardInterrupt()), rcp("bob"), msg, run_id="r", now=T0, scrub=scrub); print("KI swallowed")
except KeyboardInterrupt: print("KeyboardInterrupt propagates (not an Exception; expected)")
# --- C11: replay + racing workers + prefix-ids
log2 = DeliveryLog(tmp/"c11"); ok = Ok()
for _ in range(5): deliver_once(log2, ok, rcp("alice"), msg, run_id="r1", now=T0, scrub=scrub)
assert len(ok.calls) == 1
ok2 = Ok(); res = []
def w(): res.append(deliver_once(log2, ok2, rcp("alice.smith"), msg, run_id="r1", now=T0, scrub=scrub))
th = [threading.Thread(target=w) for _ in range(8)]; [t.start() for t in th]; [t.join() for t in th]
assert len(ok2.calls) == 1, ok2.calls
print("8 racing workers -> sends:", len(ok2.calls), "returns:", sorted(str(r.status.value) if r else "None" for r in res))
ok3 = Ok()
for u in ["Alice", "alice", "alice.smith", "alice.smith.2", "ALICE"]:
    deliver_once(log2, ok3, rcp(u), msg, run_id="r1", now=T0, scrub=scrub)
assert sorted(c[0] for c in ok3.calls) == ["ALICE", "Alice", "alice.smith.2"], ok3.calls
assert len(log2.records_for_run("r1")) == 5 and log2.records_for_run("r") == [] and log2.records_for_run("R1") == []
print("prefix/case ids ok; records_for_run(r1)=5")
# crash between sent and recorded: claim without record is never resent, closed (not resent) after STALE_AFTER
log3 = DeliveryLog(tmp/"crash"); ok4 = Ok(); key = delivery_key("r9", DeliveryChannel.EMAIL, "carol")
assert log3.claim(key, 1, T0)
assert deliver_once(log3, ok4, rcp("carol"), msg, run_id="r9", now=T0 + timedelta(minutes=1), scrub=scrub) is None
late = deliver_once(log3, ok4, rcp("carol"), msg, run_id="r9", now=T0 + STALE_AFTER + timedelta(seconds=1), scrub=scrub)
assert ok4.calls == [] and late.status is DeliveryStatus.FAILED and "not resent" in late.error and late.next_retry_at is None
again = deliver_once(log3, ok4, rcp("carol"), msg, run_id="r9", now=T0 + timedelta(days=2), scrub=scrub)
assert ok4.calls == [] and again.attempts == late.attempts
print("crash rule ok:", late.error[:60])
print("CRIT INPUTS OK")
