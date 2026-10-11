"""Blind-check A: delivery log / at-most-once attacks."""
import multiprocessing as mp, os, sys, tempfile, threading, time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from autotester.delivery.inbox import (DeliveryLog, deliver_once, delivery_key, retry_delay, next_retry_at,
                                       MAX_ATTEMPTS, STALE_AFTER)
from autotester.delivery.email import TransportError
from autotester.schema.delivery import *

NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)
MSG = RenderedMessage(subject="s", body="b")


class Count:
    outcome = DeliveryStatus.SENT
    def __init__(self, fail=False, delay=0.0, boom=None): self.n = 0; self.keys = []; self.fail = fail; self.delay = delay; self.boom = boom
    def send(self, to, message, *, key):
        self.n += 1; self.keys.append((to.user_id, key)); time.sleep(self.delay)
        if self.boom: raise self.boom
        if self.fail: raise TransportError("TransportError boom")


def rcp(u): return Recipient(user_id=u, address=f"{u.replace('.', '')}@x.test")
sc = lambda s: s

print("== 1. key collisions (distinct recipients, shared key / glob) ==")
td = Path(tempfile.mkdtemp(prefix="logA-")); log = DeliveryLog(td)
t = Count()
r1 = deliver_once(log, t, rcp("alice.smith"), MSG, run_id="run-1", now=NOW, scrub=sc)
r2 = deliver_once(log, t, rcp("alice"), MSG, run_id="run-1", now=NOW, scrub=sc)
print(f"alice.smith first, then alice: sends={t.n}  second returned recipient={r2.recipient_user_id!r} status={r2.status.value}")
print("  key(alice)=", delivery_key("run-1", DeliveryChannel.EMAIL, "alice"), "key(alice.smith)=", delivery_key("run-1", DeliveryChannel.EMAIL, "alice.smith"))
print("  files:", sorted(p.name for p in (td / "records").iterdir()))
bug_dot = (t.n == 1)
# __ collision: (run 'x__email__y', user 'z') vs (run 'x', user 'y__email__z')
k1 = delivery_key("x__email__y", DeliveryChannel.EMAIL, "z"); k2 = delivery_key("x", DeliveryChannel.EMAIL, "y__email__z")
print("  key collision across (run,user) pairs:", k1 == k2, k1)
td2 = Path(tempfile.mkdtemp(prefix="logA-")); log2 = DeliveryLog(td2); t2 = Count()
deliver_once(log2, t2, rcp("z"), MSG, run_id="x__email__y", now=NOW, scrub=sc)
r = deliver_once(log2, t2, rcp("y__email__z"), MSG, run_id="x", now=NOW, scrub=sc)
print(f"  second recipient mailed? sends={t2.n}  (1 means the second user was suppressed)")
# records_for_run leakage: run 'x' vs run 'x__email__y'
print("  records_for_run('x') shows other run's rows:", [(r.run_id, r.recipient_user_id) for r in log2.records_for_run("x")])
# '-' prefix for run ids: what do real run ids look like?
from autotester.core.ids import run_id as mint
print("  minted run id sample:", mint())

print("== 2. crash between send and record ==")
td = Path(tempfile.mkdtemp(prefix="logA-")); log = DeliveryLog(td); t = Count()
key = delivery_key("run-2", DeliveryChannel.EMAIL, "u1")
assert log.claim(key, 1, NOW)       # worker A claimed, "sent", crashed before append
for dt in [timedelta(0), timedelta(minutes=5), timedelta(minutes=9, seconds=59)]:
    r = deliver_once(log, t, rcp("u1"), MSG, run_id="run-2", now=NOW + dt, scrub=sc)
    print(f"  +{dt}: returned={r} sends={t.n}")
r = deliver_once(log, t, rcp("u1"), MSG, run_id="run-2", now=NOW + STALE_AFTER + timedelta(seconds=1), scrub=sc)
print("  after stale:", r.status.value, r.error, r.next_retry_at, "sends=", t.n)
for k in range(3):
    r = deliver_once(log, t, rcp("u1"), MSG, run_id="run-2", now=NOW + timedelta(days=k + 1), scrub=sc)
print("  days later still terminal, sends=", t.n, r.status.value)

print("== 3. concurrent threads, same delivery ==")
for trial in range(5):
    td = Path(tempfile.mkdtemp(prefix="logA-")); log = DeliveryLog(td); t = Count(delay=0.05)
    out = []
    def go(): out.append(deliver_once(log, t, rcp("u1"), MSG, run_id="run-3", now=NOW, scrub=sc))
    ths = [threading.Thread(target=go) for _ in range(12)]
    [x.start() for x in ths]; [x.join() for x in ths]
    print(f"  trial {trial}: sends={t.n} records={len(list((td/'records').iterdir()))} none-returns={sum(o is None for o in out)}")


def worker(args):
    root, = args
    t = Count(delay=0.05)
    deliver_once(DeliveryLog(Path(root)), t, rcp("u1"), MSG, run_id="run-4", now=NOW, scrub=sc)
    return t.n

if __name__ == "__main__":
    print("== 4. concurrent PROCESSES, same delivery ==")
    for trial in range(3):
        root = tempfile.mkdtemp(prefix="logA-")
        with mp.get_context("spawn").Pool(8) as pool:
            n = sum(pool.map(worker, [(root,)] * 8))
        print(f"  trial {trial}: total sends across 8 processes = {n}; records = {len(list((Path(root)/'records').iterdir()))}")
    print("== 5. retry schedule / bound ==")
    td = Path(tempfile.mkdtemp(prefix="logA-")); log = DeliveryLog(td); t = Count(fail=True); now = NOW
    for i in range(8):
        r = deliver_once(log, t, rcp("u1"), MSG, run_id="run-5", now=now, scrub=sc)
        print(f"  call {i}: sends={t.n} attempts={r.attempts} status={r.status.value} next={r.next_retry_at}")
        now = (r.next_retry_at or now + timedelta(hours=1))
    print("  MAX_ATTEMPTS", MAX_ATTEMPTS, [retry_delay(i) for i in range(1, 5)])
    print("== 6. unexpected exception text with secret + append-only ==")
    td = Path(tempfile.mkdtemp(prefix="logA-")); log = DeliveryLog(td)
    t = Count(boom=RuntimeError("password=HUNTER2 to a@x.test"))
    r = deliver_once(log, t, rcp("u1"), MSG, run_id="run-6", now=NOW, scrub=sc)
    print("  stored error:", r.error)
    t = Count(boom=TransportError("password=HUNTER2 reached TransportError"))
    r = deliver_once(log, t, rcp("u2"), MSG, run_id="run-6", now=NOW, scrub=lambda s: s.replace("HUNTER2", "[REDACTED]"))
    print("  stored error (TransportError, scrub applied):", r.error)
    r = deliver_once(log, Count(boom=TransportError("x" * 1000)), rcp("u3"), MSG, run_id="run-6", now=NOW, scrub=sc)
    print("  long error truncated to", len(r.error))
    try:
        log.append(delivery_key("run-6", DeliveryChannel.EMAIL, "u1"), r); print("  second append for same attempt: ALLOWED(!)")
    except FileExistsError: print("  second append refused (append-only)")
    txt = "\n".join(p.read_text() for p in td.rglob("*.json"))
    print("  address in any file:", "@x.test" in txt)
    # BaseException (KeyboardInterrupt) mid-send: marker stays, no record, next call?
    td = Path(tempfile.mkdtemp(prefix="logA-")); log = DeliveryLog(td)
    try:
        deliver_once(log, Count(boom=KeyboardInterrupt()), rcp("u1"), MSG, run_id="run-7", now=NOW, scrub=sc)
    except KeyboardInterrupt: print("  KeyboardInterrupt propagates; marker left:", [p.name for p in (td/'attempts').iterdir()])
    r = deliver_once(log, Count(), rcp("u1"), MSG, run_id="run-7", now=NOW + timedelta(minutes=1), scrub=sc)
    print("  next call within 10 min returns:", r)
