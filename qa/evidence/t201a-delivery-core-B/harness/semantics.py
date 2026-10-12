"""may_email / NotificationPref / deliver_once / retry schedule / outbox / config, checker B."""
import email, email.policy, itertools, json, os, shutil, subprocess, sys, threading, time
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from miniserver import Server  # noqa: E402

import autotester  # noqa: E402
from autotester.delivery import email as dmail  # noqa: E402
from autotester.delivery import inbox as dinbox  # noqa: E402
from autotester.delivery.inbox import (  # noqa: E402
    MAX_ATTEMPTS, RETRY_DELAYS, STALE_AFTER, DeliveryLog, deliver_once, next_retry_at, retry_delay)
from autotester.delivery.message import render_message  # noqa: E402
from autotester.schema.delivery import (  # noqa: E402
    DeliveryChannel, NotificationPref, Recipient, ReportLabel, ReportSummary, RunCounts, SmtpConfig)

CERTS = HERE / "certs"
W = HERE / "proj3"
shutil.rmtree(W, ignore_errors=True)
W.mkdir()
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
SUM = ReportSummary(project_name="Demo Shop", run_id="run-0001", finished_at=NOW,
                    counts=RunCounts(passed=7, failed=2, blocked=1, inconclusive=3),
                    coverage_line="Coverage: 12 of 15 screens (80%)", label=ReportLabel.FAILED,
                    report_url="https://tester.example.test/runs/run-0001")
MSG = render_message(SUM)
ident = lambda t: t  # noqa: E731


def adapter(srv, timeout=15.0):
    cfg = SmtpConfig(host="127.0.0.1", port=srv.port, user=None, sender_address="noreply@example.com", tls="none")
    return dmail.SmtpAdapter(cfg, lambda: "x", timeout=timeout)


print("autotester from:", autotester.__file__)
print("\n=== 3. may_email x NotificationPref (default off; ticked AND still allowed to view) ===")
prefs = {"no pref stored (None)": None, "default NotificationPref(user)": NotificationPref(user_id="u1"),
         "ticked=False": NotificationPref(user_id="u1", email_run_reports=False),
         "ticked=True": NotificationPref(user_id="u1", email_run_reports=True)}
print("| pref | can_view_report | may_email |\n|---|---|---|")
for (pn, p), cv in itertools.product(prefs.items(), (True, False)):
    print(f"| {pn} | {cv} | {dmail.may_email(p, can_view_report=cv)} |")
print("default value of email_run_reports:", NotificationPref(user_id="u1").email_run_reports)
for label, kw in [("extra field 'to'", dict(user_id="u1", to="a@b.test")), ("extra 'cc'", dict(user_id="u1", cc="x")),
                  ("string 'yes'", dict(user_id="u1", email_run_reports="yes")), ("string 'on'", dict(user_id="u1", email_run_reports="on")),
                  ("int 1", dict(user_id="u1", email_run_reports=1)), ("string 'false'", dict(user_id="u1", email_run_reports="false")),
                  ("int 2", dict(user_id="u1", email_run_reports=2)), ("None", dict(user_id="u1", email_run_reports=None)),
                  ("user_id '../x'", dict(user_id="../x")), ("user_id 'a b'", dict(user_id="a b")), ("missing user_id", dict())]:
    try:
        v = NotificationPref(**kw)
        print(f"NotificationPref({label}) -> accepted, email_run_reports={v.email_run_reports}")
    except Exception as e:  # noqa: BLE001
        print(f"NotificationPref({label}) -> rejected {type(e).__name__}")
# the pref of ANOTHER user passed for this recipient: does may_email notice?
other = NotificationPref(user_id="someone-else", email_run_reports=True)
print("may_email(pref of a different user, can_view=True) ->", dmail.may_email(other, can_view_report=True),
      "(signature has no recipient parameter)")
import inspect
print("may_email signature:", inspect.signature(dmail.may_email))
print("deliver_once signature:", inspect.signature(dinbox.deliver_once))

print("\n=== 4. deliver_once idempotency, counted on the loopback server ===")
to = Recipient(user_id="u-7f3", address="alice.rcpt@example.com")
# 4a sequential twice
srv = Server(certdir=str(CERTS)); log = DeliveryLog(W / "seq")
r1 = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW, scrub=ident)
r2 = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(seconds=5), scrub=ident)
r3 = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(days=2), scrub=ident)
print("4a sequential x3 (same run/channel/recipient):", r1.status.value, r2.status.value, r3.status.value,
      "| server messages:", len(srv.messages), "| record files:", sorted(p.name for p in (W/'seq'/'records').iterdir()))
srv.close()
# 4b two threads (8) at once; slow server so the race window is wide
class Slow(Server):
    pass
srv = Server(certdir=str(CERTS)); log = DeliveryLog(W / "race")
results, errs = [], []
bar = threading.Barrier(8)
def worker():
    try:
        bar.wait()
        results.append(deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW, scrub=ident))
    except BaseException as e:  # noqa: BLE001
        errs.append(f"{type(e).__name__}: {e}")
ts = [threading.Thread(target=worker) for _ in range(8)]
[t.start() for t in ts]; [t.join() for t in ts]
print("4b 8 threads at once:", "server messages:", len(srv.messages), "| returns:",
      sorted(str(r.status.value) if r else "None" for r in results), "| exceptions:", errs,
      "| records:", [(r.attempts, r.status.value) for r in log.records_for_key("run-0001__email__u-7f3")])
srv.close()
# 4b2 four OS processes at once
srv = Server(certdir=str(CERTS))
worker_src = f'''
import sys
sys.path.insert(0, {str(HERE)!r})
from datetime import UTC, datetime
from autotester.delivery import email as dmail
from autotester.delivery.inbox import DeliveryLog, deliver_once
from autotester.delivery.message import render_message
from autotester.schema.delivery import *
S = ReportSummary(project_name="Demo Shop", run_id="run-0001", finished_at=datetime(2026,10,11,12,0,tzinfo=UTC),
    counts=RunCounts(passed=7, failed=2, blocked=1, inconclusive=3), coverage_line="c", label=ReportLabel.FAILED,
    report_url="https://t.example.test/r")
cfg = SmtpConfig(host="127.0.0.1", port={srv.port}, user=None, sender_address="noreply@example.com", tls="none")
r = deliver_once(DeliveryLog(__import__("pathlib").Path({str(W / "procs")!r})), dmail.SmtpAdapter(cfg, lambda: "x"),
    Recipient(user_id="u-7f3", address="alice.rcpt@example.com"), render_message(S), run_id="run-0001",
    now=datetime(2026,10,11,12,0,tzinfo=UTC), scrub=lambda t: t)
print(r.status.value if r else "None")
'''
(W / "w.py").write_text(worker_src)
ps = [subprocess.Popen([sys.executable, str(W / "w.py")], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
outs = [p.communicate(timeout=60) for p in ps]
print("4b2 4 OS processes at once: server messages:", len(srv.messages), "| stdout:", [o[0].strip() for o in outs],
      "| stderr:", [o[1].strip()[:80] for o in outs if o[1].strip()])
srv.close()

# 4c crash simulation
class SendThenDie:
    """Send for real, then die (BaseException) before deliver_once can write the record."""
    outcome = dmail.DeliveryStatus.SENT
    def __init__(self, inner): self.inner = inner
    def send(self, to, message, *, key):
        self.inner.send(to, message, key=key)
        raise KeyboardInterrupt("simulated kill between sent and recorded")
srv = Server(certdir=str(CERTS)); log = DeliveryLog(W / "crash")
try:
    deliver_once(log, SendThenDie(adapter(srv)), to, MSG, run_id="run-0001", now=NOW, scrub=ident)
except KeyboardInterrupt:
    pass
key = "run-0001__email__u-7f3"
print("4c after crash: records:", len(log.records_for_key(key)), "markers:", sorted(p.name for p in (W/'crash'/'attempts').iterdir()),
      "server messages:", len(srv.messages))
rA = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(minutes=2), scrub=ident)
rB = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(minutes=9, seconds=59), scrub=ident)
rC = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(minutes=10, seconds=1), scrub=ident)
rD = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(hours=3), scrub=ident)
print("   replay +2m ->", rA, "| +9m59 ->", rB, "|\n   +10m01 ->", rC and (rC.status.value, rC.attempts, rC.error, rC.next_retry_at),
      "|\n   +3h ->", rD and (rD.status.value, rD.attempts, rD.next_retry_at), "| server messages total:", len(srv.messages))
srv.close()
# 4d crash BEFORE the send (claim written, process died): mail is lost, never resent
srv = Server(certdir=str(CERTS)); log = DeliveryLog(W / "crash0")
log.claim(key, 1, NOW)
x1 = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(minutes=1), scrub=ident)
x2 = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(minutes=11), scrub=ident)
x3 = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(days=1), scrub=ident)
print("4d claim-then-die (nothing sent): +1m ->", x1, "| +11m ->", x2 and (x2.status.value, x2.error), "| +1d ->", x3 and x3.status.value,
      "| server messages:", len(srv.messages), "(a never-sent mail is lost: documented at-most-once)")
srv.close()
# 4e skewed clock: second worker's now is 11 minutes ahead while the first is still mid-send
class SlowServer(Server):
    pass
srv = Server(certdir=str(CERTS)); log = DeliveryLog(W / "skew")
slow_started = threading.Event(); release = threading.Event()
class Gate:
    outcome = dmail.DeliveryStatus.SENT
    def __init__(self, inner): self.inner = inner
    def send(self, to, message, *, key):
        slow_started.set(); release.wait(10); self.inner.send(to, message, key=key)
res = {}
def first():
    try: res["first"] = deliver_once(log, Gate(adapter(srv)), to, MSG, run_id="run-0001", now=NOW, scrub=ident)
    except BaseException as e: res["first"] = f"RAISED {type(e).__name__}: {e}"  # noqa: BLE001
t1 = threading.Thread(target=first); t1.start(); slow_started.wait(5)
res["second"] = deliver_once(log, adapter(srv), to, MSG, run_id="run-0001", now=NOW + timedelta(minutes=11), scrub=ident)
release.set(); t1.join(15)
print("4e clock-skewed second worker closes a live attempt:", "second ->", res["second"] and (res["second"].status.value, res["second"].error),
      "| first ->", res["first"] if isinstance(res["first"], str) else (res["first"] and res["first"].status.value),
      "| server messages:", len(srv.messages), "| records:", [(r.attempts, r.status.value) for r in log.records_for_key(key)])
srv.close()

print("\n=== 4f key collision between user ids that share a dotted prefix ===")
srv = Server(certdir=str(CERTS)); log = DeliveryLog(W / "collide")
bob_smith = Recipient(user_id="alice.smith", address="smith@example.com")
alice = Recipient(user_id="alice", address="alice@example.com")
ra = deliver_once(log, adapter(srv), bob_smith, MSG, run_id="run-0001", now=NOW, scrub=ident)
rb = deliver_once(log, adapter(srv), alice, MSG, run_id="run-0001", now=NOW, scrub=ident)
rcpts = [e[1] for e in srv.events if e[0] == "rcpt"]
print("alice.smith first ->", ra.status.value, "attempts", ra.attempts, "| then alice ->", rb.status.value,
      "attempts", rb.attempts, "recipient_user_id in returned record:", rb.recipient_user_id,
      "| rcpts the server saw:", rcpts, "| messages:", len(srv.messages))
print("files:", sorted(p.name for p in (W/'collide'/'records').iterdir()))
print("records_for_key(alice) ->", [(r.recipient_user_id, r.status.value) for r in log.records_for_key("run-0001__email__alice")])
srv.close()
# reverse and failed-state variants
srv = Server(certdir=str(CERTS), auth="none", rcpt="reject"); log = DeliveryLog(W / "collide2")
ra = deliver_once(log, adapter(srv), Recipient(user_id="alice.smith", address="smith@example.com"), MSG, run_id="run-0001", now=NOW, scrub=ident)
rb = deliver_once(log, adapter(srv), Recipient(user_id="alice", address="alice@example.com"), MSG, run_id="run-0001", now=NOW, scrub=ident)
print("both rejected: alice.smith attempts", ra.attempts, "| alice attempts", rb.attempts, "(alice's first try should be attempt 1)",
      "| rcpt tries seen:", len([e for e in srv.events if e[0] == 'rcpt']))
srv.close()

print("\n=== 5. retry schedule ===")
print("RETRY_DELAYS:", [str(d) for d in RETRY_DELAYS], "MAX_ATTEMPTS:", MAX_ATTEMPTS, "STALE_AFTER:", STALE_AFTER)
for n in range(1, 7):
    print(f"retry_delay({n}) = {retry_delay(n)}   next_retry_at(NOW,{n}) = {next_retry_at(NOW, n)}")
try:
    retry_delay(0)
except Exception as e:  # noqa: BLE001
    print("retry_delay(0) raises", type(e).__name__)
src = Path(autotester.__file__).parent / "delivery" / "inbox.py"
import re
text = src.read_text("utf-8")
print("inbox.py mentions sleep/time.time/datetime.now/utcnow:", re.findall(r"sleep|time\.time|datetime\.now|utcnow|monotonic", text))
# bound under an always-failing transport, with an enormous max_attempts
class Boom:
    outcome = dmail.DeliveryStatus.SENT
    n = 0
    def send(self, to, message, *, key): Boom.n += 1; raise dmail.TransportError("nope")
log = DeliveryLog(W / "bound"); t = NOW; recs = []
for i in range(50):
    r = deliver_once(log, Boom(), to, MSG, run_id="run-0001", now=t, scrub=ident, max_attempts=1000)
    if r is None: break
    recs.append((r.attempts, r.status.value, str(r.next_retry_at - t) if r.next_retry_at else None))
    if r.next_retry_at is None: break
    t = r.next_retry_at
print("always-failing transport, max_attempts=1000:", recs, "| send calls:", Boom.n)
n0 = Boom.n
for off in (0, 60, 3600, 86400 * 30):
    deliver_once(log, Boom(), to, MSG, run_id="run-0001", now=t + timedelta(seconds=off), scrub=ident, max_attempts=1000)
print("   further calls after the bound sent:", Boom.n - n0)
# not due yet
log = DeliveryLog(W / "notdue"); Boom.n = 0
deliver_once(log, Boom(), to, MSG, run_id="run-0001", now=NOW, scrub=ident)
deliver_once(log, Boom(), to, MSG, run_id="run-0001", now=NOW + timedelta(seconds=59), scrub=ident)
deliver_once(log, Boom(), to, MSG, run_id="run-0001", now=NOW + timedelta(seconds=60), scrub=ident)
print("not-due test: send calls at t0, +59s, +60s ->", Boom.n, "(expected 2)")

print("\n=== 6. outbox + selection + config ===")
env_full = {"AUTOTESTER_SMTP_HOST": "127.0.0.1", "AUTOTESTER_SMTP_PORT": "2525", "AUTOTESTER_SMTP_FROM": "noreply@example.com",
            "AUTOTESTER_SMTP_USER": "uu", "AUTOTESTER_SMTP_PASSWORD": "PW-OUTBOX-CANARY", "AUTOTESTER_SMTP_TLS": "0"}
for label, env in [("empty env", {}), ("password only", {"AUTOTESTER_SMTP_PASSWORD": "PW-OUTBOX-CANARY"}),
                   ("no FROM", {k: v for k, v in env_full.items() if k != "AUTOTESTER_SMTP_FROM"}),
                   ("port abc", dict(env_full, AUTOTESTER_SMTP_PORT="abc")), ("port 0", dict(env_full, AUTOTESTER_SMTP_PORT="0")),
                   ("port 99999", dict(env_full, AUTOTESTER_SMTP_PORT="99999")), ("host with space", dict(env_full, AUTOTESTER_SMTP_HOST="a b")),
                   ("bad sender", dict(env_full, AUTOTESTER_SMTP_FROM="not an address")),
                   ("sender name CRLF", dict(env_full, AUTOTESTER_SMTP_FROM_NAME="x\r\nBcc: z@y.test")),
                   ("sender name 100", dict(env_full, AUTOTESTER_SMTP_FROM_NAME="n" * 100)),
                   ("full", env_full)]:
    try:
        tr = dmail.select_transport(env, W / "ob")
        print(f"select_transport({label}) -> {type(tr).__name__}; is_configured={dmail.is_configured(env)}")
    except Exception as e:  # noqa: BLE001
        print(f"select_transport({label}) RAISED {type(e).__name__}")
ob = dmail.OutboxAdapter(W / "ob2")
deliver_once(DeliveryLog(W / "oblog"), ob, to, MSG, run_id="run-0001", now=NOW, scrub=ident)
deliver_once(DeliveryLog(W / "oblog"), ob, to, MSG, run_id="run-0001", now=NOW, scrub=ident)
files = sorted(p.name for p in (W / "ob2").iterdir())
print("outbox files after 2 deliveries:", files)
em = email.message_from_bytes((W / "ob2" / files[0]).read_bytes(), policy=email.policy.default)
print("outbox message To:", em["To"], "| From:", em["From"], "| multipart:", em.is_multipart(), "| Cc/Bcc:", em["Cc"], em["Bcc"])
print("outbox key traversal:", end=" ")
for k in ("../x", "a/b", "a\\b", "x..y", "", ".hidden", "k" * 201):
    try:
        ob.send(to, MSG, key=k); print(f"{k!r}: WROTE", end="; ")
    except dmail.TransportError as e:
        print(f"{k!r}: refused", end="; ")
print()
# default factory refuses non-loopback under pytest marker, and opens no socket
import socket
opened = []
orig = socket.create_connection
socket.create_connection = lambda *a, **k: (opened.append(a), orig(*a, **k))[1]
os.environ[dmail.TEST_MARKER] = "x"
cfg = SmtpConfig(host="smtp.example.com", port=587, user="u", sender_address="noreply@example.com", tls="starttls")
r = deliver_once(DeliveryLog(W / "marker"), dmail.SmtpAdapter(cfg, lambda: "x"), to, MSG, run_id="run-0001", now=NOW, scrub=ident)
print("under TEST_MARKER, host smtp.example.com ->", r.status.value, r.error, "| sockets opened:", opened)
for host in ("localhost.example.com", "127.0.0.2", "0.0.0.0", "[::1]"):
    try:
        cfg = SmtpConfig(host=host, port=587, user="u", sender_address="noreply@example.com", tls="starttls")
    except Exception as e:  # noqa: BLE001
        print(f"   host {host!r}: config rejected"); continue
    r = deliver_once(DeliveryLog(W / f"marker-{host}"), dmail.SmtpAdapter(cfg, lambda: "x"), to, MSG, run_id="run-0001", now=NOW, scrub=ident)
    print(f"   host {host!r} under marker ->", r.error)
del os.environ[dmail.TEST_MARKER]
socket.create_connection = orig
