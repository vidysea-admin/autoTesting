"""Substitution attacks on the real start()/close() path. usage: attacks.py [names...] -> JSON lines."""
from __future__ import annotations

import http.client
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import h
from autotester.browser import launch as L
from autotester.browser import session as S

READ = {"n": 0}
_real_read1 = http.client.HTTPResponse.read1


def _count_read1(self, n=-1):
    b = _real_read1(self, n)
    READ["n"] += len(b)
    return b


http.client.HTTPResponse.read1 = _count_read1


class Listener:
    def __init__(self, handler, ctx, backlog=16, stall=False):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(backlog)
        self.port = self.sock.getsockname()[1]
        self.ctx, self.handler = ctx, handler
        self.conns, self.first_at, self.drop_at, self.sent = 0, None, None, 0
        self.stop = False
        if not stall:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        self.sock.settimeout(0.2)
        while not self.stop:
            try:
                c, _ = self.sock.accept()
            except OSError:
                continue
            self.conns += 1
            if self.first_at is None:
                self.first_at = time.monotonic()
            threading.Thread(target=self._one, args=(c,), daemon=True).start()

    def _one(self, c):
        try:
            c.settimeout(8)
            buf = b""
            while b"\r\n\r\n" not in buf:
                d = c.recv(4096)
                if not d:
                    return
                buf += d
            self.handler(c, self)
        except OSError:
            pass
        finally:
            if self.drop_at is None:
                self.drop_at = time.monotonic()
            try:
                c.close()
            except OSError:
                pass

    def send(self, c, data):
        c.sendall(data)
        self.sent += len(data)

    def close(self):
        self.stop = True
        try:
            self.sock.close()
        except OSError:
            pass


def good_json(port, guid):
    return json.dumps({"Browser": "x", "webSocketDebuggerUrl": f"ws://127.0.0.1:{port}{guid}"}).encode()


def ok(body, extra=b""):
    return b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\n%s\r\n" % (len(body), extra) + body


# ---- handlers: (conn, listener) ; listener.ctx = {"guid":..., "real_port":..., "other": Listener|None}
def trickle_headers(c, l):
    l.send(c, b"HTTP/1.1 200 OK\r\nX: ")
    while not l.stop:
        l.send(c, b"a")
        time.sleep(0.1)


def trickle_body(c, l):
    body = good_json(l.port, l.ctx["guid"])
    l.send(c, b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(body))
    for i in range(len(body) - 1):  # never completes inside a few seconds
        l.send(c, body[i:i + 1])
        time.sleep(0.2)


def flood_lengthless(c, l):
    l.send(c, b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n")
    chunk = b"A" * 8192
    while not l.stop:
        l.send(c, chunk)


def flood_chunked(c, l):
    l.send(c, b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")
    chunk = b"A" * 8192
    while not l.stop:
        l.send(c, b"%x\r\n" % len(chunk) + chunk + b"\r\n")


def flood_declared(c, l):
    l.send(c, b"HTTP/1.1 200 OK\r\nContent-Length: 104857600\r\n\r\n")
    chunk = b"A" * 8192
    while not l.stop:
        l.send(c, chunk)


def nested(c, l):
    body = b"[" * 30000 + b"]" * 30000  # 60000 bytes < 64 KiB
    l.send(c, ok(body))


def nested_obj(c, l):
    body = b'{"a":' * 10000 + b"1" + b"}" * 10000  # 60001 bytes
    l.send(c, ok(body))


def redirect_real(c, l):
    l.send(c, b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:%d/json/version\r\nContent-Length: 0\r\n\r\n" % l.ctx["real_port"])


def redirect_counting(c, l):
    l.send(c, b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:%d/json/version\r\nContent-Length: 0\r\n\r\n" % l.ctx["other"].port)


def answer_right(c, l):
    l.send(c, ok(good_json(l.port, l.ctx["guid"])))


def delayed(delay):
    def hd(c, l):
        time.sleep(delay)
        answer_right(c, l)
    return hd


def right_then_hold(c, l):  # complete valid JSON, length-less, never closes
    body = good_json(l.port, l.ctx["guid"])
    l.send(c, b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n" + body)
    time.sleep(6)


def counting_right(c, l):
    answer_right(c, l)


VARIANTS = {
    "a1_trickle_headers": (trickle_headers, {}),
    "a2_trickle_body": (trickle_body, {}),
    "b1_flood_lengthless": (flood_lengthless, {}),
    "b2_flood_chunked": (flood_chunked, {}),
    "b3_flood_declared_length": (flood_declared, {}),
    "c1_nested_array": (nested, {}),
    "c2_nested_object": (nested_obj, {}),
    "d1_redirect_to_counting_correct_listener": (redirect_counting, {"other": True}),
    "d2_redirect_to_real_browser_port": (redirect_real, {}),
    "e_other_real_browser": (None, {"other_browser": True}),
    "f1_right_identity_after_1.9s": (delayed(1.9), {}),
    "f2_right_identity_after_2.1s": (delayed(2.1), {}),
    "g1_right_identity_lengthless_then_holds": (right_then_hold, {}),
    "g2_right_identity_immediately": (answer_right, {}),
    "h_backlog_full_connect_hangs": (None, {"stall": True}),
}


def run_variant(name, repeat=1):
    handler, opts = VARIANTS[name]
    tmp = Path(tempfile.mkdtemp(prefix="r2b-atk-"))
    s = h.mk(tmp)
    pf = s.paths.profile_dir / "DevToolsActivePort"
    st = {"t_file": None, "first": None, "last": None, "stop": False}
    real = {"port": None}

    def monitor():
        while not st["stop"]:
            try:
                if st["t_file"] is None and pf.exists():
                    lines = pf.read_text().splitlines()
                    if len(lines) >= 2:
                        real["port"] = int(lines[0])
                        st["t_file"] = time.monotonic()
                elif real["port"]:
                    if h.accepts("127.0.0.1", real["port"], 0.3):
                        st["first"] = st["first"] or time.monotonic()
                        st["last"] = time.monotonic()
            except Exception:
                pass
            time.sleep(0.05)

    mt = threading.Thread(target=monitor, daemon=True)
    mt.start()
    holder, stalled = {}, []
    real_url = S.verified_cdp_url

    def attacked(profile_dir):
        lines = (profile_dir / "DevToolsActivePort").read_text().splitlines()
        rp, guid = int(lines[0]), lines[1].strip()
        ctx = {"guid": guid, "real_port": rp, "other": None}
        holder["pids"] = h.tree_pids()
        holder["real_port"] = rp
        if opts.get("other"):
            ctx["other"] = Listener(answer_right, ctx)
            holder["other"] = ctx["other"]
        if opts.get("other_browser"):
            p = subprocess.Popen([sys.executable, "other.py"], stdout=subprocess.PIPE, text=True,
                                 env={**__import__("os").environ})
            holder["proc"] = p
            port = int(p.stdout.readline().split()[0])
            attacker_port = port
            lst = None
        elif opts.get("stall"):
            lst = Listener(None, ctx, backlog=0, stall=True)
            # fill the accept queue so a further connect hangs
            fillers = []
            for _ in range(6):
                f = socket.socket()
                f.setblocking(False)
                try:
                    f.connect_ex(("127.0.0.1", lst.port))
                except OSError:
                    pass
                fillers.append(f)
            stalled.extend(fillers)
            attacker_port = lst.port
        else:
            lst = Listener(handler, ctx)
            attacker_port = lst.port
        holder["lst"] = lst
        (profile_dir / "DevToolsActivePort").write_text(f"{attacker_port}\n{guid}\n")
        holder["t0"] = time.monotonic()
        READ["n"] = 0
        try:
            return real_url(profile_dir)
        finally:
            holder["t_verify_end"] = time.monotonic()

    S.verified_cdp_url = attacked
    out = {"variant": name}
    t_start = time.monotonic()
    result = None
    try:
        s.start()
        result = f"RETURNED cdp_url={s.cdp_url}"
        out["cdp_url_is_attacker"] = s.cdp_url == f"http://127.0.0.1:{holder['lst'].port}" if holder.get("lst") else None
    except BaseException as e:  # noqa: BLE001
        result = f"RAISED {type(e).__name__}: {str(e)[:100]}"
    t_end = time.monotonic()
    out["result"] = result
    out["start_total_s"] = round(t_end - t_start, 2)
    out["verify_hold_s"] = round(holder["t_verify_end"] - holder["t0"], 2)
    out["client_bytes_read"] = READ["n"]
    lst = holder.get("lst")
    if lst:
        out["listener_conns"] = lst.conns
        if lst.first_at and lst.drop_at:
            out["client_dropped_after_s"] = round(lst.drop_at - lst.first_at, 2)
        out["listener_sent"] = lst.sent
    if holder.get("other"):
        out["redirect_target_connections"] = holder["other"].conns
    if holder.get("proc"):
        holder["proc"].terminate()
    returned = result.startswith("RETURNED")
    if returned:
        out["browser_up_after_start_returned"] = h.accepts("127.0.0.1", holder["real_port"], 1)
        s.close()
    time.sleep(1.0)
    left = h.alive(list(holder["pids"]))
    for _ in range(40):
        if not left:
            break
        time.sleep(0.2)
        left = h.alive(left)
    st["stop"] = True
    t_closed = time.monotonic()
    out["real_browser_procs_left"] = left
    out["real_port_accepts_after"] = h.accepts("127.0.0.1", holder["real_port"], 1)
    out["portfile_after"] = pf.exists()
    out["timers_alive"] = h.timers()
    if st["t_file"] and st["first"] and st["last"]:
        out["exposure_window_s"] = round(st["last"] - st["t_file"], 2)
        out["launch_to_attack_start_s"] = round(holder["t0"] - st["t_file"], 2)
        out["exposure_after_attack_start_s"] = round(st["last"] - holder["t0"], 2)
    if lst:
        lst.close()
    if holder.get("other"):
        holder["other"].close()
    for f in stalled:
        f.close()
    S.verified_cdp_url = real_url
    shutil.rmtree(tmp, ignore_errors=True)
    return out


if __name__ == "__main__":
    names = sys.argv[1:] or list(VARIANTS)
    for n in names:
        print(json.dumps(run_variant(n)), flush=True)
