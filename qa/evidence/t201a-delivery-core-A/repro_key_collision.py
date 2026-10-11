"""Repro (checker A): deliver_once key is not injective for ids the unit's own schema accepts.
Run: uv --directory <copy of 9b6d44c1> run python repro_key_collision.py"""
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from autotester.delivery.inbox import DeliveryLog, deliver_once, delivery_key
from autotester.schema.delivery import DeliveryChannel, DeliveryStatus, Recipient, RenderedMessage

class Ok:
    outcome = DeliveryStatus.SENT
    def __init__(self): self.sent = []
    def send(self, to, message, *, key): self.sent.append(to.user_id)

NOW = datetime(2026, 10, 11, 12, tzinfo=UTC); M = RenderedMessage(subject="s", body="b")
rcp = lambda u: Recipient(user_id=u, address="x@x.test")
# 1. dot-prefix ids: "alice.smith" is mailed first, then "alice" (same run)
t = Ok(); log = DeliveryLog(Path(tempfile.mkdtemp()))
deliver_once(log, t, rcp("alice.smith"), M, run_id="run_A", now=NOW, scrub=str)
r = deliver_once(log, t, rcp("alice"), M, run_id="run_A", now=NOW, scrub=str)
print("1) mailed:", t.sent, "| record returned for 'alice' belongs to:", r.recipient_user_id, "| alice has own record:", bool(log.latest(delivery_key("run_A", DeliveryChannel.EMAIL, "alice")) and log.latest(delivery_key("run_A", DeliveryChannel.EMAIL, "alice")).recipient_user_id == "alice"))
# 2. '__' ids collide on the key itself
print("2) same key for two (run,user) pairs:", delivery_key("x__email__y", DeliveryChannel.EMAIL, "z") == delivery_key("x", DeliveryChannel.EMAIL, "y__email__z"))
# 3. records_for_run leaks another run's rows
t = Ok(); log = DeliveryLog(Path(tempfile.mkdtemp()))
deliver_once(log, t, rcp("z"), M, run_id="x__email__y", now=NOW, scrub=str)
print("3) records_for_run('x') ->", [(q.run_id, q.recipient_user_id) for q in log.records_for_run("x")])
