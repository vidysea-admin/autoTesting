"""Shared helpers for the r2-A hostile probe battery: raw-socket listener + client instrumentation."""
from __future__ import annotations

import gc
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

COPY = "C:/Users/Lenovo/AppData/Local/Temp/chk-t177r2a-1798127267"
sys.path.insert(0, COPY + "/src")
from autotester.browser import launch  # noqa: E402

assert launch.__file__.replace("\\", "/").startswith(COPY), launch.__file__

PATH = "/devtools/browser/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
CAP = launch.PROBE_MAX_BYTES

# ---- client-side instrumentation ------------------------------------------------------------
CLIENT_BYTES = [0]
CONNECTS: list = []
SOCKS: list = []  # every client socket create_connection returned
_orig_readinto = socket.SocketIO.readinto
_orig_connect = socket.socket.connect
_orig_cc = socket.create_connection


def _readinto(self, b):  # counts every byte any makefile'd socket (the probe's reply) consumed
    n = _orig_readinto(self, b)
    if n:
        CLIENT_BYTES[0] += n
    return n


def _connect(self, addr):
    CONNECTS.append(addr)
    return _orig_connect(self, addr)


def _cc(*a, **k):
    s = _orig_cc(*a, **k)
    SOCKS.append(s)
    return s


socket.SocketIO.readinto = _readinto
socket.socket.connect = _connect
socket.create_connection = _cc


def reset_client():
    CLIENT_BYTES[0] = 0
    CONNECTS.clear()
    SOCKS.clear()


def good_json(port: int, path: str = PATH) -> bytes:
    return json.dumps({"webSocketDebuggerUrl": f"ws://127.0.0.1:{port}{path}"}).encode()


def http_head(cl: int | None = None, extra: str = "", status: str = "200 OK", chunked=False,
              close=False) -> bytes:
    h = f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\n"
    if cl is not None:
        h += f"Content-Length: {cl}\r\n"
    if chunked:
        h += "Transfer-Encoding: chunked\r\n"
    if close:
        h += "Connection: close\r\n"
    return (h + extra + "\r\n").encode()


# ---- hostile listener -----------------------------------------------------------------------
class Ctx:
    def __init__(self, lst, conn):
        self.lst, self.conn, self.port = lst, conn, lst.port
        self.stop = lst.stop_ev

    def request(self) -> bytes:
        buf = b""
        self.conn.settimeout(2)
        try:
            while b"\r\n\r\n" not in buf:
                d = self.conn.recv(4096)
                if not d:
                    break
                buf += d
        except OSError:
            pass
        self.lst.req_bytes += len(buf)
        return buf

    def send(self, data: bytes) -> bool:
        """Send all of data (counting bytes the kernel accepted); False once the peer is gone."""
        self.conn.settimeout(0.5)
        view = memoryview(data)
        while len(view) and not self.stop.is_set():
            try:
                n = self.conn.send(view[:65536])
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                return False
            self.lst.sent += n
            view = view[n:]
        return not self.stop.is_set()

    def wait(self, s: float) -> bool:
        return not self.stop.wait(s)

    def peer_gone(self) -> bool:
        try:
            self.conn.settimeout(0.05)
            return self.conn.recv(1) == b""
        except (TimeoutError, socket.timeout):
            return False
        except OSError:
            return True


class Listener:
    def __init__(self, behavior, backlog: int = 64):
        self.behavior, self.sent, self.accepts, self.req_bytes = behavior, 0, 0, 0
        self.stop_ev = threading.Event()
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(backlog)
        self.port = self.srv.getsockname()[1]
        self.conns: list = []
        self.threads: list = []
        t = threading.Thread(target=self._accept, name="L-accept", daemon=True)
        t.start()
        self.threads.append(t)

    def _accept(self):
        self.srv.settimeout(0.2)
        while not self.stop_ev.is_set():
            try:
                c, _ = self.srv.accept()
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                return
            self.accepts += 1
            self.conns.append(c)
            t = threading.Thread(target=self._serve, args=(c,), name="L-conn", daemon=True)
            t.start()
            self.threads.append(t)

    def _serve(self, c):
        try:
            self.behavior(Ctx(self, c))
        except Exception:
            pass
        finally:
            try:
                c.close()
            except OSError:
                pass

    def snap(self):
        return (self.accepts, self.sent, self.req_bytes)

    def stop(self):
        self.stop_ev.set()
        for c in self.conns:
            try:
                c.close()
            except OSError:
                pass
        try:
            self.srv.close()
        except OSError:
            pass
        for t in self.threads:
            t.join(2)


# ---- leak checks ----------------------------------------------------------------------------
def foreign_threads(baseline: set) -> list:
    return [t.name for t in threading.enumerate()
            if t not in baseline and not t.name.startswith("L-") and t.is_alive()]


def netstat_pid_conns(pid: int) -> list:
    """TCP rows owned by pid (netstat -ano), excluding LISTENING; used only when nothing of ours should be open."""
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                             timeout=20).stdout
    except Exception as e:  # pragma: no cover
        return [f"netstat-failed:{e}"]
    rows = []
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0] == "TCP" and p[-1] == str(pid) and p[3] != "LISTENING":
            rows.append(ln.strip())
    return rows
