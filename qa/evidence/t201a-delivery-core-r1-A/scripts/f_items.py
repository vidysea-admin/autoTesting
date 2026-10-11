import sys, tempfile, pathlib
sys.path.insert(0, sys.argv[2])
import autotester; print("autotester at", autotester.__file__)
from delivery_fakes import recipient, summary, NOW
from autotester.delivery.inbox import deliver_once, DeliveryLog, delivery_key
from autotester.delivery.message import render_message
from autotester.schema.delivery import DeliveryChannel as C, DeliveryStatus, Recipient, ReportSummary
class T:
    outcome = DeliveryStatus.SENT
    def __init__(s): s.sent=[]
    def send(s, to, m, *, key): s.sent.append((to.user_id, key))
msg = render_message(summary())
with tempfile.TemporaryDirectory(dir=sys.argv[1]) as d:
    log = DeliveryLog(pathlib.Path(d)); t = T()
    for run, user in [("run-1","alice.smith"),("run-1","alice"),("x__email__y","z"),("x","y__email__z")]:
        deliver_once(log, t, Recipient(user_id=user, address="a@example.test"), msg, run_id=run, now=NOW, scrub=lambda s:s)
    print("F1 sends:", len(t.sent), "(expect 4)  distinct keys:", len({k for _,k in t.sent}))
    print("F1 records_for_run('x'):", [(r.run_id, r.recipient_user_id) for r in log.records_for_run("x")], "(expect only y__email__z)")
    print("F1 records_for_run('x__email__y'):", [(r.run_id, r.recipient_user_id) for r in log.records_for_run("x__email__y")])
for u in ["//evil.test/x","///e/x","https://x.test//e","https://x.test:0/r","https://x.test:65536/r","https://x.test:99999/r","https://x.test:1/r","https://x.test:65535/r","/","/a//b","https://x.test:/r","https://x.test:00080/r","/\evil", "http://x.test:6553/r?x"]:
    try: summary(report_url=u); r="ACCEPT"
    except Exception: r="refuse"
    print("F3", u, r)
for a in ["a@example.test\r","a@example.test\n","\ra@example.test","a\nb@example.test","a@example.test "]:
    try: Recipient(user_id="u", address=a); r="ACCEPT"
    except Exception: r="refuse"
    print("C12", ascii(a), r)
