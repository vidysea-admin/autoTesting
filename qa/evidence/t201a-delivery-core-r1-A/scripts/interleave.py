"""Checker A: deterministic interleavings of two workers. Throwaway; tmp dir under argv[1]."""
import sys, tempfile, pathlib
from datetime import datetime, timedelta, UTC
import autotester; print("autotester at", autotester.__file__)
sys.path.insert(0, sys.argv[2])  # copy's tests dir for fakes
from delivery_fakes import recipient, summary, NOW
from autotester.delivery.inbox import deliver_once, DeliveryLog, STALE_AFTER, delivery_key
from autotester.delivery.message import render_message
from autotester.delivery.email import TransportError
from autotester.schema.delivery import DeliveryStatus, DeliveryChannel
msg = render_message(summary(), scrub=lambda s: s) if True else None
scrub = lambda s: s
class T:
    outcome = DeliveryStatus.SENT
    def __init__(s, hook=None, fail=None): s.sent=0; s.hook=hook; s.fail=fail
    def send(s, to, message, *, key):
        if s.hook: s.hook()
        s.sent += 1
        if s.fail: raise s.fail
def go(log, tr, now=NOW): return deliver_once(log, tr, recipient(), msg, run_id="run-0001", now=now, scrub=scrub)

def scenario(name, pre_send_close=False, fail=None):
    with tempfile.TemporaryDirectory(dir=sys.argv[1]) as d:
        d = pathlib.Path(d); w2 = T()
        res = {}
        def w2run(): res["w2"] = go(DeliveryLog(d), w2, NOW + STALE_AFTER)
        class L(DeliveryLog):
            def claim(self, key, attempt, now):
                ok = super().claim(key, attempt, now)
                if pre_send_close and ok: w2run()    # worker 2 closes AFTER claim, BEFORE worker 1 sends
                return ok
        w1 = T(hook=None if pre_send_close else w2run, fail=fail)
        r1 = go(L(d), w1)
        # replays for a day
        later = [go(DeliveryLog(d), T(), NOW + timedelta(hours=h)) for h in (1, 5, 30)]
        recs = DeliveryLog(d).records_for_key(delivery_key("run-0001", DeliveryChannel.EMAIL, "user-a"))
        total = w1.sent + w2.sent
        print(f"{name}: w1.sent={w1.sent} w2.sent={w2.sent} total_sends={total} records={len(recs)} "
              f"w1_returned_status={r1.status.value} err={'unknown' in (r1.error or '')} later_same={all(x==r1 for x in later)}")
        assert w2.sent == 0 and total <= 1 and len(recs) == 1 and r1 == res["w2"] == recs[0]
        assert "may or may not have been sent" in recs[0].error and "not resent" in recs[0].error
scenario("close-during-send (after send call begins)")
scenario("close-before-send (after claim, before send)", pre_send_close=True)
scenario("close-during-send then w1 send raises", fail=TransportError("550 nope"))
scenario("close-before-send then w1 send raises", pre_send_close=True, fail=TransportError("550 nope"))
# long ids: ValueError escape?
for r,u in [("R"*64,"U"*64),("run_"+"01HXYZ0123456789ABCDEFGHJK","U"*64),("run_"+"01HXYZ0123456789ABCDEFGHJK","usr_01HXYZ0123456789ABCDEFGHJK")]:
    with tempfile.TemporaryDirectory(dir=sys.argv[1]) as d:
        try:
            deliver_once(DeliveryLog(pathlib.Path(d)), T(), recipient(user_id=u), msg, run_id=r, now=NOW, scrub=scrub)
            print("ok", len(r), len(u), len(delivery_key(r, DeliveryChannel.EMAIL, u)))
        except Exception as e:
            print("ESCAPES", type(e).__name__, str(e), len(r), len(u))
