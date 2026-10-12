"""pytest plugin: record every socket connect / getaddrinfo target; non-loopback ones are logged to a file."""
import os, socket, ipaddress

LOG = os.environ["NETGUARD_LOG"]
_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex
_orig_gai = socket.getaddrinfo


def _note(kind, target):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{kind} {target!r} test={os.environ.get('PYTEST_CURRENT_TEST','')}\n")


def _is_loop(host):
    if host in ("localhost", "127.0.0.1", "::1", "", None):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if self.family == getattr(socket, "AF_UNIX", -1):
        return _orig_connect(self, address)
    _note("connect-loop" if _is_loop(host) else "CONNECT-NONLOOP", address)
    if not _is_loop(host):
        raise ConnectionRefusedError("netguard")
    return _orig_connect(self, address)


def connect_ex(self, address):
    host = address[0] if isinstance(address, tuple) else address
    _note("connect_ex-loop" if _is_loop(host) else "CONNECT_EX-NONLOOP", address)
    if not _is_loop(host):
        return 111
    return _orig_connect_ex(self, address)


def gai(host, *a, **k):
    if not _is_loop(host):
        _note("GETADDRINFO-NONLOOP", host)
    return _orig_gai(host, *a, **k)


socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
socket.getaddrinfo = gai
