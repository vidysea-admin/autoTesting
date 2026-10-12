"""Checker B (repair cycle 1) harness: real loopback SMTP sink + deliver_once under concurrency.

Usage: python h.py <matrix|concurrent|stale|failures|longids|url|dupe> <data-root> <out-json>
Only example.com / .invalid addresses; only 127.0.0.1; no .env read.
"""
from __future__ import annotations

import itertools
import json
import multiprocessing as mp
import os
import random
import shutil
import socketserver
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import autotester

NOW = datetime(2026, 10, 12, 9, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------- sink
class Sink:
    def __init__(self, latency: float = 0.0):
        self.lock = threading.Lock()
        self.msgs: dict[str, list[float]] = {}
        self.behav: dict[str, str] = {}
        self.latency = latency
        self.conns = 0
        sink = self

        class H(socketserver.StreamRequestHandler):
            def handle(self):  # noqa: C901
                with sink.lock:
                    sink.conns += 1
                r, w = self.rfile, self.wfile

                def send(t):
                    w.write((t + "\r\n").encode())
                    w.flush()

                send("220 sink ESMTP")
                rcpt = None
                while True:
                    line = r.readline()
                    if not line:
                        return
                    cmd = line.decode(errors="replace").strip()
                    up = cmd.upper()
                    if up.startswith(("EHLO", "HELO")):
                        send("250 sink")
                    elif up.startswith("MAIL FROM"):
                        send("250 ok")
                    elif up.startswith("RCPT TO"):
                        rcpt = cmd.split("<", 1)[1].split(">", 1)[0]
                        b = sink.behav.get(rcpt, "ok")
                        if b == "refuse_rcpt":
                            send("550 mailbox unavailable")
                            continue
                        send("250 ok")
                    elif up == "DATA":
                        b = sink.behav.get(rcpt, "ok")
                        send("354 go")
                        n = 0
                        while True:
                            dl = r.readline()
                            if not dl:
                                return
                            n += 1
                            if b == "drop_mid_data" and n >= 3:
                                self.request.close()
                                return
                            if dl in (b".\r\n", b".\n"):
                                break
                        with sink.lock:
                            sink.msgs.setdefault(rcpt, []).append(time.time())
                        if b == "drop_after_data":
                            self.request.close()
                            return
                        if b == "timeout":
                            time.sleep(30)
                            return
                        if b.startswith("stalldrop"):
                            time.sleep(float(b.split(":")[1]))
                            self.request.close()
                            return
                        if b.startswith("stall"):
                            time.sleep(float(b.split(":")[1]))
                        if sink.latency:
                            time.sleep(random.random() * sink.latency)
                        send("250 queued")
                    elif up == "QUIT":
                        send("221 bye")
                        return
                    else:
                        send("250 ok")

        class S(socketserver.ThreadingTCPServer):
            daemon_threads = True
            allow_reuse_address = True
            request_queue_size = 256

        self.srv = S(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def count(self, addr: str) -> int:
        with self.lock:
            return len(self.msgs.get(addr, []))

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


# ---------------------------------------------------------------- helpers
def addr_for(run: str, user: str) -> str:
    # unique address per (run, user): hex of the pair keeps it distinct and legal
    import hashlib
    return "p" + hashlib.sha1(f"{run}|{user}".encode()).hexdigest()[:24] + "@example.com"


def mk(port: int, timeout: float = 5.0, slow: bool = False):
    from autotester.delivery.email import SmtpAdapter
    from autotester.schema.delivery import SmtpConfig

    cfg = SmtpConfig(host="127.0.0.1", port=port, sender_address="autotester@example.com", tls="none")
    import smtplib
    def fac(host, port, ssl_, tmo):  # explicit local_hostname: skips a slow getfqdn() on this host
        return smtplib.SMTP(host, port, timeout=tmo, local_hostname="localhost")
    return SmtpAdapter(cfg, lambda: None, timeout=timeout, client_factory=None if slow else fac)


def msg():
    from autotester.schema.delivery import RenderedMessage

    return RenderedMessage(subject="report", body="body text")


def call(log, transport, run, user, now=NOW, address=None, **kw):
    from autotester.delivery.inbox import deliver_once
    from autotester.schema.delivery import Recipient

    to = Recipient(user_id=user, address=address or addr_for(run, user))
    return deliver_once(log, transport, to, msg(), run_id=run, now=now, scrub=lambda s: s, **kw)


def fresh(root: str, name: str) -> Path:
    p = Path(root) / name
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)
    return p


# ---------------------------------------------------------------- 1 matrix
def cmd_matrix(root, out):
    from autotester.delivery.inbox import DeliveryLog, delivery_key
    from autotester.schema.delivery import DeliveryChannel

    runs = ["x", "x.1", "x.1.1", "X", "x__email__y", "x_", "x_0", "x-1", "Run", "RUN", "run", "r_1",
            "R_1", "a" * 64, "a" * 63 + "b", "a" * 63 + "A", "x.01", "x1", "x_x", "x__x"]
    users = ["alice", "alice.smith", "alice.1", "alice.01", "Alice", "ALICE", "alice-smith",
             "alice_smith", "alice__smith", "a_b", "a_0b", "a__b", "a_", "z", "y__email__z", "y",
             "email", "x", "1", "10", "01", "a.b", "a-b", "A.B", "b" * 64, "b" * 63 + "c"]
    pairs = list(itertools.product(runs, users))
    keys = {p: delivery_key(p[0], DeliveryChannel.EMAIL, p[1]) for p in pairs}
    res = {"pairs": len(pairs), "distinct_keys": len(set(keys.values())),
           "distinct_keys_casefold": len({k.lower() for k in keys.values()})}
    sink = Sink()
    log = DeliveryLog(fresh(root, "matrix"))
    tr = mk(sink.port)
    rng = random.Random(7)
    orders = [list(pairs), list(reversed(pairs)), rng.sample(pairs, len(pairs)), rng.sample(pairs, len(pairs))]
    exc = []
    for o in orders:
        for run, user in o:
            try:
                call(log, tr, run, user)
            except Exception as e:  # noqa: BLE001
                exc.append(f"{run}/{user}: {type(e).__name__}: {e}")
    bad_counts = {f"{r}/{u}": sink.count(addr_for(r, u)) for r, u in pairs if sink.count(addr_for(r, u)) != 1}
    bad_key = []
    for r, u in pairs:
        recs = log.records_for_key(keys[(r, u)])
        if not (len(recs) == 1 and recs[0].run_id == r and recs[0].recipient_user_id == u
                and recs[0].attempts == 1 and recs[0].status.value == "sent"):
            bad_key.append(f"{r}/{u}: {[(x.run_id, x.recipient_user_id) for x in recs]}")
    bad_run = []
    for r in runs:
        recs = log.records_for_run(r)
        if not (len(recs) == len(users) and all(x.run_id == r for x in recs)
                and {x.recipient_user_id for x in recs} == set(users)):
            bad_run.append(f"{r}: n={len(recs)} runs={sorted({x.run_id for x in recs})}")
    files = sorted(p.name for p in (Path(root) / "matrix" / "records").iterdir())
    res.update(exceptions=exc, wrong_message_counts=bad_counts, records_for_key_wrong=bad_key,
               records_for_run_wrong=bad_run, record_files=len(files),
               attempt_files=len(list((Path(root) / "matrix" / "attempts").iterdir())),
               total_messages=sum(len(v) for v in sink.msgs.values()),
               stray=[f for f in files if not f.endswith(".01.json")][:5], passes=len(orders))
    sink.close()
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({k: (v if not isinstance(v, (list, dict)) or len(v) < 6 else f"{len(v)} items")
                      for k, v in res.items()}, indent=1))


# ---------------------------------------------------------------- 2 concurrency
def _worker(args):
    (idx, nproc, nthr, rounds, port, rootdir, skew_frac, barrier, q, seed) = args
    from autotester.delivery.inbox import DeliveryLog
    from concurrent.futures import ThreadPoolExecutor

    log = DeliveryLog(Path(rootdir))
    tr = mk(port, timeout=20.0)
    rng = random.Random(seed + idx)
    errs, returns = [], []

    def one(rnd_, pairs_, skewed):
        order = rng.sample(pairs_, len(pairs_))
        for run, user in order:
            try:
                now = NOW + (timedelta(minutes=11) if skewed else timedelta(0))
                r = call(log, tr, run, user, now=now)
                returns.append((run, user, None if r is None else r.status.value))
            except Exception as e:  # noqa: BLE001
                errs.append(f"{run}/{user}: {type(e).__name__}: {e}")

    for rnd in range(rounds):
        pairs_ = [(f"rn{rnd}{s}", u) for s in ("", ".1") for u in ("u", "u.1", "U")]
        try:
            barrier.wait(timeout=60)
        except Exception as e:  # noqa: BLE001
            errs.append(f"barrier: {e}")
        with ThreadPoolExecutor(nthr) as ex:
            futs = [ex.submit(one, rnd, pairs_, rng.random() < skew_frac) for _ in range(nthr)]
            for f in futs:
                f.result()
    q.put((idx, errs, returns))


def cmd_concurrent(root, out, skew_frac=0.0, name="concurrent", rounds=200, nproc=6, nthr=4):
    from autotester.delivery.inbox import DeliveryLog, delivery_key
    from autotester.schema.delivery import DeliveryChannel

    sink = Sink(latency=0.02 if skew_frac else 0.0)
    rootdir = fresh(root, name)
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(nproc)
    q = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=((i, nproc, nthr, rounds, sink.port, str(rootdir), skew_frac,
                                                 barrier, q, 99),)) for i in range(nproc)]
    t0 = time.time()
    for p in procs:
        p.start()
    results = []
    for _ in procs:
        results.append(q.get(timeout=900))
    for p in procs:
        p.join(60)
    log = DeliveryLog(rootdir)
    wrong, torn, statuses = {}, [], {}
    nkeys = 0
    for rnd in range(rounds):
        for s in ("", ".1"):
            for u in ("u", "u.1", "U"):
                run = f"rn{rnd}{s}"
                nkeys += 1
                c = sink.count(addr_for(run, u))
                if c != 1:
                    wrong[f"{run}/{u}"] = c
                recs = log.records_for_key(delivery_key(run, DeliveryChannel.EMAIL, u))
                if len(recs) != 1:
                    torn.append(f"{run}/{u}: {len(recs)} records")
                else:
                    statuses[recs[0].status.value + "|" + (recs[0].error or "")[:30]] = \
                        statuses.get(recs[0].status.value + "|" + (recs[0].error or "")[:30], 0) + 1
    recdir = rootdir / "records"
    files = [p.name for p in recdir.iterdir()]
    tmps = [f for f in files if f.endswith(".tmp")] + [p.name for p in (rootdir / "attempts").iterdir() if p.name.endswith(".tmp")]
    unparsable = []
    for p in recdir.iterdir():
        try:
            json.loads(p.read_text("utf-8"))
        except Exception as e:  # noqa: BLE001
            unparsable.append(p.name)
    allerrs = [e for (_, errs, _) in results for e in errs]
    nret = sum(len(r) for (_, _, r) in results)
    res = dict(name=name, rounds=rounds, procs=nproc, threads_per_proc=nthr, skew_frac=skew_frac, keys=nkeys,
               seconds=round(time.time() - t0, 1), deliver_once_calls=nret, exceptions=allerrs[:10],
               n_exceptions=len(allerrs), keys_with_wrong_message_count=wrong, keys_without_exactly_one_record=torn,
               record_files=len(files), tmp_leftovers=tmps[:5], unparsable=unparsable, final_status=statuses,
               total_messages=sum(len(v) for v in sink.msgs.values()),
               none_returns=sum(1 for (_, _, r) in results for x in r if x[2] is None))
    sink.close()
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res, indent=1))


# ---------------------------------------------------------------- 3 stale-close with real timing
def _proc_call(port, rootdir, run, user, now_off_min, delay, q, tag, timeout=30.0):
    from autotester.delivery.inbox import DeliveryLog

    time.sleep(delay)
    t = time.time()
    try:
        r = call(DeliveryLog(Path(rootdir)), mk(port, timeout), run, user,
                 now=NOW + timedelta(minutes=now_off_min))
        q.put((tag, "ret", None if r is None else json.loads(r.model_dump_json()), round(time.time() - t, 2)))
    except Exception as e:  # noqa: BLE001
        q.put((tag, "EXC", f"{type(e).__name__}: {e}", round(time.time() - t, 2)))


def cmd_stale(root, out):
    from autotester.delivery.inbox import DeliveryLog, delivery_key
    from autotester.schema.delivery import DeliveryChannel

    ctx = mp.get_context("spawn")
    res = {}
    scenarios = {
        "S1 A stalls 3s then OK; B skewed +11min closes during stall": ("stall:3", 0, 11, False),
        "S2 A (skewed) stalls then OK; B normal": ("stall:3", 11, 0, False),
        "S3 A stalls 3s then connection dropped (no 250); B skewed closes": ("stalldrop:3", 0, 11, False),
    }
    for name, (beh, a_off, b_off, _) in scenarios.items():
        sink = Sink()
        run, user = "stale1", "su"
        address = addr_for(run, user)
        sink.behav[address] = beh if beh.startswith("stall") else "stall:3"
        rootdir = fresh(root, "stale")
        q = ctx.Queue()
        a = ctx.Process(target=_proc_call, args=(sink.port, str(rootdir), run, user, a_off, 0, q, "A"))
        b = ctx.Process(target=_proc_call, args=(sink.port, str(rootdir), run, user, b_off, 1.0, q, "B"))
        a.start(); b.start()
        got = {}
        for _ in range(2):
            tag, kind, val, secs = q.get(timeout=120)
            got[tag] = (kind, val if kind == "EXC" else (val and (val["status"], val["attempts"], (val["error"] or "")[:40])), secs)
        a.join(30); b.join(30)
        log = DeliveryLog(rootdir)
        key = delivery_key(run, DeliveryChannel.EMAIL, user)
        recs = [(r.status.value, r.attempts, (r.error or "")[:60]) for r in log.records_for_key(key)]
        before = sink.count(address)
        # follow ups much later: nothing may be resent
        from autotester.delivery.inbox import DeliveryLog as DL
        for off in (60, 24 * 60, 7 * 24 * 60):
            call(DL(rootdir), mk(sink.port), run, user, now=NOW + timedelta(minutes=off))
        after = sink.count(address)
        res[name] = dict(workers=got, final_records=recs, messages_at_sink=before, messages_after_followups=after)
        sink.close()
    # S4: attempt 2 (after a real refusal) stalls; B skewed closes it
    sink = Sink(); run, user = "stale2", "su"; address = addr_for(run, user)
    rootdir = fresh(root, "stale")
    sink.behav[address] = "refuse_rcpt"
    from autotester.delivery.inbox import DeliveryLog as DL
    r1 = call(DL(rootdir), mk(sink.port), run, user, now=NOW)
    sink.behav[address] = "stall:3"
    q = ctx.Queue()
    a = ctx.Process(target=_proc_call, args=(sink.port, str(rootdir), run, user, 2, 0, q, "A"))
    b = ctx.Process(target=_proc_call, args=(sink.port, str(rootdir), run, user, 15, 1.0, q, "B"))
    a.start(); b.start()
    got = {}
    for _ in range(2):
        tag, kind, val, secs = q.get(timeout=120)
        got[tag] = (kind, val if kind == "EXC" else (val and (val["status"], val["attempts"], (val["error"] or "")[:40])), secs)
    a.join(30); b.join(30)
    key = delivery_key(run, DeliveryChannel.EMAIL, user)
    recs = [(r.status.value, r.attempts, (r.error or "")[:60], str(r.next_retry_at)) for r in DL(rootdir).records_for_key(key)]
    for off in (60, 24 * 60):
        call(DL(rootdir), mk(sink.port), run, user, now=NOW + timedelta(minutes=off))
    res["S4 attempt 2 after a refusal; A stalls; B skewed closes attempt 2"] = dict(
        first_attempt=(r1.status.value, r1.attempts), workers=got, final_records=recs,
        messages_at_sink=sink.count(address))
    sink.close()
    json.dump(res, open(out, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


# ---------------------------------------------------------------- 4 failure paths
def cmd_failures(root, out):
    from autotester.delivery.inbox import DeliveryLog
    import socket

    res = {}
    sink = Sink()
    for beh in ("refuse_rcpt", "drop_mid_data", "timeout", "drop_after_data", "ok"):
        run, user = f"f{beh}".replace("_", "x"), "fu"
        address = addr_for(run, user)
        sink.behav[address] = beh
        log = DeliveryLog(fresh(root, f"fail-{beh}"))
        t = time.time()
        try:
            r = call(log, mk(sink.port, timeout=1.0), run, user)
            rr = (r.status.value, r.attempts, r.error, str(r.next_retry_at))
        except Exception as e:  # noqa: BLE001
            rr = f"EXC {type(e).__name__}: {e}"
        blob = " ".join(p.read_text("utf-8") for d in ("records", "attempts") for p in (Path(root) / f"fail-{beh}" / d).iterdir())
        res[beh] = dict(result=rr, secs=round(time.time() - t, 2), address_in_files=address in blob,
                        messages=sink.count(address))
    # connection refused: closed port
    s = socket.socket(); s.bind(("127.0.0.1", 0)); dead = s.getsockname()[1]; s.close()
    log = DeliveryLog(fresh(root, "fail-refused"))
    r = call(log, mk(dead, timeout=1.0), "frefused", "fu")
    res["connection_refused"] = (r.status.value, r.error)
    # non-transport exception inside transport
    class Boom:
        outcome = __import__("autotester.schema.delivery", fromlist=["x"]).DeliveryStatus.SENT
        def send(self, to, message, *, key): raise RuntimeError("secret-token-123 leaked?")
    log = DeliveryLog(fresh(root, "fail-boom"))
    r = call(log, Boom(), "fboom", "fu")
    res["runtime_error_in_transport"] = (r.status.value, r.error)
    # retry schedule when the sink delivered but dropped the reply: duplicates (P7)
    sink.behav[addr_for("fdupe", "fu")] = "drop_after_data"
    log = DeliveryLog(fresh(root, "fail-dupe"))
    t = NOW; seq = []
    for i in range(8):
        r = call(log, mk(sink.port, timeout=1.0), "fdupe", "fu", now=t)
        seq.append((i, r.status.value, r.attempts, str(r.next_retry_at)[11:16]))
        t = t + timedelta(minutes=31)
    res["delivered_but_reply_dropped"] = dict(calls=seq, copies_at_sink=sink.count(addr_for("fdupe", "fu")))
    sink.close()
    json.dump(res, open(out, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


# ---------------------------------------------------------------- 4b over-long ids
def cmd_longids(root, out):
    from autotester.delivery.inbox import DeliveryLog, delivery_key
    from autotester.schema.delivery import DeliveryChannel, safe_id

    res = {}
    sink = Sink()

    def mixed(n_upper):  # 64 chars, n_upper capitals
        return "a" * (64 - n_upper) + "A" * n_upper

    for ku, kv in ((63, 0), (63, 1), (50, 13), (0, 64), (64, 64), (32, 32), (10, 10)):
        run, user = mixed(ku), mixed(kv)
        safe_id(run); safe_id(user)  # both valid ids
        keylen = None
        try:
            keylen = len(delivery_key(run, DeliveryChannel.EMAIL, user))
        except ValueError as e:
            keylen = f"ValueError({e})"
        log = DeliveryLog(fresh(root, f"long-{ku}-{kv}"))
        try:
            r = call(log, mk(sink.port), run, user)
            out_ = (r.status.value if r else None)
        except Exception as e:  # noqa: BLE001
            out_ = f"PROPAGATED {type(e).__name__}: {e}"
        rec_files = len(list((Path(root) / f"long-{ku}-{kv}" / "records").iterdir())) if (Path(root) / f"long-{ku}-{kv}" / "records").exists() else 0
        res[f"upper_run={ku},upper_user={kv}"] = dict(keylen=keylen, deliver_once=out_, messages=sink.count(addr_for(run, user)),
                                                         record_files=rec_files)
    # realistic ids: uuid hex run id, typical user ids
    import uuid
    for run, user in ((uuid.uuid4().hex, "umesh"), ("run-2026-10-12T09-00-00Z", "Umesh_Sugara"), ("R" * 20 + "_" * 20, "U" * 20)):
        k = delivery_key(run, DeliveryChannel.EMAIL, user)
        res[f"realistic {run[:12]}../{user}"] = dict(keylen=len(k))
    sink.close()
    json.dump(res, open(out, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


# ---------------------------------------------------------------- 5 report_url table
def cmd_url(root, out):
    from autotester.schema.delivery import ReportSummary, RunCounts, ReportLabel

    def mkurl(u):
        return ReportSummary(project_name="p", run_id="r1", finished_at=NOW,
                             counts=RunCounts(passed=1, failed=0, blocked=0, inconclusive=0),
                             coverage_line="c", label=ReportLabel.GREEN, report_url=u)

    refuse = ["//host", "//host/a", "///host", "///host/a", "https://x//host", "http://x//a", "https://x.test:0/r",
              "https://x.test:65536/r", "https://x.test:99999/r", "https://x.test:100000/r", "https://x.test:000000/r",
              "\\\\host\\a", "/\\host", "\\/host", "/\thost", "/a\tb", "/a b", "https://u@x.test/r", "https://u:p@x.test/r",
              "https://x.test:80@evil.test/r", "/%2F%2Fhost", "/%2fhost", "/a%2F%2Fb", "https:/x.test/r", "https:///x.test/r",
              "https://x.test", "https://x.test:/r", "https://[::1]/r", "javascript:alert(1)", "data:text/html,x",
              "/r?x=1", "/r#f", "https://x.test/r?x", "/r\n", "/r\r\nBcc: a@b.c", " /r", "/r ", "ftp://x.test/r",
              "HTTPS://x.test/r ", "/‮", "https://x.test:+80/r", "https://x.test:8_0/r", "//", "https://exa mple.com/r",
              "https://x.test:١٢٣/r", "/r\x00", "x/y", "", "\\", "/..//x"]
    accept = ["/", "/a//b", "https://x.test:1/r", "https://x.test:65535/r", "https://x.test/r", "http://localhost:8080/runs/r1",
              "/runs/r1/report", "https://x.test:00080/r", "/a/./b", "/a/../b", "/~u", "/.hidden"]
    res = {"refused_but_accepted": [], "accepted_but_refused": []}
    for u in refuse:
        try:
            mkurl(u)
            res["refused_but_accepted"].append(u)
        except Exception:  # noqa: BLE001
            pass
    for u in accept:
        try:
            mkurl(u)
        except Exception as e:  # noqa: BLE001
            res["accepted_but_refused"].append((u, str(e)[:60]))
    res["n_refuse"], res["n_accept"] = len(refuse), len(accept)
    json.dump(res, open(out, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    mp.freeze_support()
    cmd, root, out = sys.argv[1:4]
    assert os.environ.get("H_EXPECT", "r1b-copy") in autotester.__file__, autotester.__file__
    print("autotester.__file__ =", autotester.__file__)
    if cmd == "concurrent":
        cmd_concurrent(root, out)
    elif cmd == "concurrent_skew":
        cmd_concurrent(root, out, skew_frac=0.5, name="concurrent_skew")
    else:
        globals()["cmd_" + cmd](root, out)
