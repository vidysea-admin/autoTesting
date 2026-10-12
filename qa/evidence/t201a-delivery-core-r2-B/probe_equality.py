"""Behaviour-equality probe for DeliveryLog (t201a r2 B). Usage:
  probe_equality.py build <store_dir> <out_json>    build a store via deliver_once with a fake transport
  probe_equality.py dump  <store_dir> <out_json>    read a store with THIS copy's code
First line printed: autotester.__file__ (proves which copy ran). No network, no real email."""
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import autotester
from autotester.delivery.email import TransportError
from autotester.delivery.inbox import (
    MAX_ATTEMPTS, STALE_AFTER, DeliveryLog, deliver_once, delivery_key,
)
from autotester.schema.delivery import (
    DeliveryChannel, DeliveryStatus, Recipient, RenderedMessage,
)

print("autotester.__file__ =", autotester.__file__)

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
RUNS = ["run", "run-1", "run-10", "run-1.0", "run.1", "Run", "RUN", "run_1", "run-1_a", "x",
        "x__email__y", "y", "email", "inbox", "a_b", "a__b", "R1", "r1", "1", "10", "0",
        "x-", "x.", "A", "a", "inbox__inbox", "email__x"]
USERS = ["alice", "alice.smith", "Alice", "ALICE", "bob", "bob_1", "bob-1", "Bob_1",
         "z", "y__email__z", "u", "u1", "U1", "email", "x", "y", "inbox_x"]
NO_RECORD_RUNS = ["ru", "run-", "run-1.", "Run-1", "run-100", "run-1.00", "run.", "x__email",
                  "x__email__", "x__email__y_", "email__", "e", "inbox__", "Y", "X", "a_",
                  "a__", "a___b", "9", "zzz"]
MSG = RenderedMessage(subject="s", body="b")


class Fake:
    def __init__(self, script: list[str]) -> None:
        self.outcome = DeliveryStatus.SENT
        self.script, self.calls = list(script), 0

    def send(self, to, message, *, key):
        self.calls += 1
        step = self.script.pop(0) if self.script else "ok"
        if step == "terr":
            raise TransportError("fake transport refused: code 451")
        if step == "exc":
            raise RuntimeError("boom")


def plan() -> list[tuple[str, str, DeliveryChannel, list[str], bool]]:
    out = []
    i = 0
    for ri, run in enumerate(RUNS):
        for k in range(3):
            user = USERS[(ri * 3 + k) % len(USERS)]
            ch = DeliveryChannel.EMAIL if (ri + k) % 2 == 0 else DeliveryChannel.INBOX
            stale = False
            if i % 7 == 0:
                script = ["terr"] * 10
            elif i % 5 == 0:
                script = ["terr", "ok"]
            elif i % 11 == 0:
                script = ["exc", "ok"]
            elif i % 13 == 0:
                script, stale = ["ok"], True
            else:
                script = ["ok"]
            out.append((run, user, ch, script, stale))
            i += 1
    # separator-spelling pairs and same-user-many-runs
    for ch in DeliveryChannel:
        out.append(("x__email__y", "z", ch, ["ok"], False))
        out.append(("x", "y__email__z", ch, ["ok"], False))
        out.append(("x", "y", ch, ["terr"] * 10, False))
        out.append(("x__email__y", "y", ch, ["ok"], False))
    return out


def build(store: Path, out_json: Path) -> None:
    log = DeliveryLog(store)
    rows = []
    seen_keys = set()
    for run, user, ch, script, stale in plan():
        key = delivery_key(run, ch, user)
        if key in seen_keys:
            continue                      # keep one delivery per key
        seen_keys.add(key)
        tr = Fake(script)
        rcp = Recipient(user_id=user, address="person@example.test")
        if stale:
            assert log.claim(key, 1, NOW - STALE_AFTER * 3)   # crashed worker: marker, no record
        results = []
        for step in range(MAX_ATTEMPTS + 2):
            now = NOW + timedelta(minutes=45 * step)
            rec = deliver_once(log, tr, rcp, MSG, run_id=run, now=now, scrub=lambda s: s, channel=ch)
            results.append(None if rec is None else [rec.status.value, rec.attempts, rec.error])
            rec2 = deliver_once(log, tr, rcp, MSG, run_id=run, now=now, scrub=lambda s: s, channel=ch)
            results.append(None if rec2 is None else [rec2.status.value, rec2.attempts])
        rows.append({"key": key, "run": run, "user": user, "channel": ch.value, "stale": stale,
                     "sends": tr.calls, "results": results})
    out_json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print("deliveries:", len(rows))


def norm(rec) -> dict:
    d = json.loads(rec.model_dump_json())
    d.pop("created_at", None)
    return d


def dump(store: Path, out_json: Path) -> None:
    log = DeliveryLog(store)
    names = sorted(p.name for p in (store / "records").iterdir()) if (store / "records").is_dir() else []
    anames = sorted(p.name for p in (store / "attempts").iterdir()) if (store / "attempts").is_dir() else []
    contents = {}
    for sub in ("records", "attempts"):
        d = store / sub
        if d.is_dir():
            for p in sorted(d.iterdir()):
                j = json.loads(p.read_text("utf-8"))
                j.pop("created_at", None)
                contents[f"{sub}/{p.name}"] = j
    by_run = {r: [norm(x) for x in log.records_for_run(r)] for r in RUNS + NO_RECORD_RUNS}
    keys = sorted({delivery_key(r, c, u) for r in RUNS for u in USERS for c in DeliveryChannel})
    garbage = ["email", "email__run", "email__run__alice", "email__run__alice.0", "a.b", ".*",
               "email__run__alice.01.json", "inbox__x__y.*", "email__x__y"]
    by_key = {k: [norm(x) for x in log.records_for_key(k)] for k in keys + garbage}
    latest = {k: (lambda r: None if r is None else norm(r))(log.latest(k)) for k in keys}
    out = {"record_files": names, "attempt_files": anames, "contents": contents,
           "by_run": by_run, "by_key": by_key, "latest": latest}
    out_json.write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print("record files:", len(names), "attempt files:", len(anames),
          "run lookups:", len(by_run), "key lookups:", len(by_key),
          "nonempty run rows:", sum(len(v) for v in by_run.values()),
          "nonempty key rows:", sum(len(v) for v in by_key.values()))


if __name__ == "__main__":
    mode, store, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    {"build": build, "dump": dump}[mode](store, out)
