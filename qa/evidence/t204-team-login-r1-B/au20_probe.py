"""AU20 blind probe (r1-B sub-checker). In-process: sets sys.argv + os.environ, calls check_startup()."""
from __future__ import annotations

import contextlib
import io
import ipaddress
import os
import socket
import sys

import autotester
from autotester.auth import config

print("autotester from:", autotester.__file__)
KEYS = ["AUTOTESTER_HOSTED", "AUTOTESTER_ALLOWED_HOSTS", "AUTOTESTER_ALLOWED_ORIGINS",
        "AUTOTESTER_AUTH_DISABLED", "UVICORN_HOST", "UVICORN_PORT", "PORT",
        "AUTOTESTER_FIRST_ADMIN_EMAIL"]


def run(argv, env):
    saved_argv, saved_env = sys.argv, dict(os.environ)
    for k in KEYS:
        os.environ.pop(k, None)
    os.environ.update(env)
    os.environ["AUTOTESTER_FIRST_ADMIN_EMAIL"] = "dummy@example.invalid"
    sys.argv = ["uvicorn", "autotester.ui.app:app", *argv]
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            config.check_startup()
        return "ok", ""
    except Exception as e:  # noqa: BLE001
        return "RAISE", f"{type(e).__name__}: {e}"
    finally:
        sys.argv = saved_argv
        os.environ.clear()
        os.environ.update(saved_env)


# ---- independent expectation (my reading of AU20) -------------------------------------------
def canon(v: str):
    """('wild'|'loop'|'host', normalized name) as the OS would interpret the bind string."""
    v = v.strip().lower()
    if v == "localhost":
        return "loop", v
    if v in ("", "*"):
        return "wild", v
    try:
        ip = ipaddress.ip_address(v)
    except ValueError:
        try:  # inet_aton short/hex forms: 0, 127.1, 0x7f.1
            ip = ipaddress.ip_address(socket.inet_ntoa(socket.inet_aton(v)))
        except OSError:
            return "host", v.rstrip(".")
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    if ip.is_unspecified:
        return "wild", str(ip)
    if ip.is_loopback:
        return "loop", str(ip)
    return "host", (f"[{ip}]" if ip.version == 6 else str(ip))


def expect(bind, port, hosts, origins):
    if not (hosts.strip() or origins.strip()):
        return "RAISE"
    kind, name = canon(bind)
    if kind in ("wild", "loop"):
        return "ok"
    listed = {x.rstrip("/").lower() for x in (hosts + " " + origins).replace(",", " ").split()
              if x != "*"}
    nets = {x.split("://", 1)[1] if "://" in x else x for x in listed}
    nets = {n.rstrip(".") for n in nets}
    return "ok" if (name in nets or f"{name}:{port}" in nets) else "RAISE"


BINDS = ["10.0.0.5", "127.0.0.1", "localhost", "::1", "2001:db8::5", "0.0.0.0", "::",
         "", "*", "app.example.com", "App.Example.COM", "app.example.com.", "::ffff:10.0.0.5",
         "0", "127.1", "0x7f.1", "::ffff:127.0.0.1", "::0", "::ffff:0.0.0.0", "127.0.0.2"]
PORT_FORMS = {"noport": [], "--port 8443": ["--port", "8443"], "--port=8443": ["--port=8443"]}


def cfgs(bind, port):
    kind, name = canon(bind)
    n = name if kind == "host" else (bind.strip().lower() or "srv.example.com")
    return {
        "H=n": (n, ""), f"H=n:{port}": (f"{n}:{port}", ""),
        f"O=http://n:{port}": ("", f"http://{n}:{port}"),
        "O=https://n": ("", f"https://{n}"), "H=other": ("other.example.com", ""),
        "H=n:9999": (f"{n}:9999", ""), "H=n:8000": (f"{n}:8000", ""), "empty": ("", ""),
    }


rows, disagree, fneg, fpos, formdiff = [], [], [], [], []
for b in BINDS:
    for pname, pargs in PORT_FORMS.items():
        port = "8443" if pargs else "8000"
        res_by_form = {}
        for form in ("sp", "eq"):
            hargs = ["--host", b] if form == "sp" else [f"--host={b}"]
            outs = []
            for cname, (h, o) in cfgs(b, port).items():
                env = {"AUTOTESTER_HOSTED": "1"}
                if h:
                    env["AUTOTESTER_ALLOWED_HOSTS"] = h
                if o:
                    env["AUTOTESTER_ALLOWED_ORIGINS"] = o
                out, msg = run(hargs + pargs, env)
                exp = expect(b, port, h, o)
                outs.append((cname, out, exp, msg, h, o))
                if out != exp:
                    disagree.append((form, b, pname, cname, out, exp, h, o, msg))
                    if out == "ok" and exp == "RAISE":
                        fneg.append((form, b, pname, cname))
                    if out == "RAISE" and exp == "ok":
                        fpos.append((form, b, pname, cname, msg))
            res_by_form[form] = outs
        if [o[1] for o in res_by_form["sp"]] != [o[1] for o in res_by_form["eq"]]:
            formdiff.append((b, pname))
        rows.append((b, pname,
                     "".join("." if o[1] == "ok" else "R" for o in res_by_form["sp"]),
                     "".join("." if o[1] == "ok" else "R" for o in res_by_form["eq"]),
                     "".join("." if o[2] == "ok" else "R" for o in res_by_form["sp"])))

print("\n== MATRIX (HOSTED=1). Config order of the 8 columns:", list(cfgs("x", "8000").keys()))
print("   '.'=startup ok, 'R'=raises. actual(--host V) | actual(--host=V) | expected")
print(f"{'bind':<20}{'port form':<14}{'actual sp':<10}{'actual eq':<10}{'expected':<10}agree")
for b, p, a1, a2, e in rows:
    print(f"{b!r:<20}{p:<14}{a1:<10}{a2:<10}{e:<10}{'yes' if a1 == e and a2 == e else 'NO'}")
print("\nspace-vs-equals form differences:", formdiff or "none")
print("\n== DISAGREEMENTS (space form only)")
for form, b, p, c, out, exp, h, o, msg in disagree:
    if form != "sp":
        continue
    print(f"  bind={b!r} {p} cfg={c} H={h!r} O={o!r}: actual={out} expected={exp} {msg[:110]}")
print("\n== FALSE NEGATIVES (ok but expected RAISE):",
      sorted({(b, p, c) for f, b, p, c in fneg if f == 'sp'}) or "none")
print("== FALSE POSITIVES (RAISE but expected ok): count",
      len({(b, p, c) for f, b, p, c, m in fpos if f == 'sp'}),
      "binds:", sorted({b for f, b, p, c, m in fpos if f == 'sp'}))

# ---- environment / argv shape scenarios -------------------------------------------------------
print("\n== SCENARIOS")


def show(label, argv, env):
    env = {"AUTOTESTER_HOSTED": "1", **env}
    out, msg = run(argv, env)
    print(f"  {label:<66} -> {out} {msg[:120]}")


H, O = "AUTOTESTER_ALLOWED_HOSTS", "AUTOTESTER_ALLOWED_ORIGINS"
show("UVICORN_HOST=10.0.0.5, H=10.0.0.5", [], {"UVICORN_HOST": "10.0.0.5", H: "10.0.0.5"})
show("UVICORN_HOST=10.0.0.5, H=other", [], {"UVICORN_HOST": "10.0.0.5", H: "other.example.com"})
show("UVICORN_HOST=10.0.0.5 + argv --host 127.0.0.1, H=other", ["--host", "127.0.0.1"],
     {"UVICORN_HOST": "10.0.0.5", H: "other.example.com"})
show("no --host, H=other (uvicorn default 127.0.0.1)", [], {H: "other.example.com"})
show("--uds /tmp/s.sock, H=other", ["--uds", "/tmp/s.sock"], {H: "other.example.com"})
show("--uds /tmp/s.sock --host 10.0.0.5, H=other", ["--uds", "/tmp/s.sock", "--host", "10.0.0.5"],
     {H: "other.example.com"})
show("--host 10.0.0.5 --host 127.0.0.1 (uvicorn: last wins), H=other",
     ["--host", "10.0.0.5", "--host", "127.0.0.1"], {H: "other.example.com"})
show("--host 127.0.0.1 --host 10.0.0.5 (uvicorn: last wins), H=other",
     ["--host", "127.0.0.1", "--host", "10.0.0.5"], {H: "other.example.com"})
show("--host (no value, last arg), H=other", ["--host"], {H: "other.example.com"})
SH = ["--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
print("  -- shipped entrypoint argv: uvicorn autotester.ui.app:app --host 0.0.0.0 --port 8000 "
      "--no-access-log")
for label, env in [
    ("compose.prod+Caddy: H=app.example.com O=https://app.example.com",
     {H: "app.example.com", O: "https://app.example.com"}),
    ("only H=app.example.com", {H: "app.example.com"}),
    ("only O=https://app.example.com", {O: "https://app.example.com"}),
    ("DEPLOY interim: H=203.0.113.9 O=http://203.0.113.9:8000",
     {H: "203.0.113.9", O: "http://203.0.113.9:8000"}),
    ("neither set", {}),
    ("H=other.example.com (names nothing the container serves)", {H: "other.example.com"}),
    ("H='*' only (ignored by _listed)", {H: "*"}),
    ("O='*' only (ignored by guard)", {O: "*"}),
    ("H=',' only", {H: ","}),
    ("H='  ,  ' only", {H: "  ,  "}),
    ("O='/' only", {O: "/"}),
    ("H=localhost only (loopback is always allowed anyway)", {H: "localhost"}),
]:
    show(label, SH, env)
show("wildcard '::' + H='*'", ["--host", "::"], {H: "*"})
show("concrete 10.0.0.5 + H='*' (ignored)", ["--host", "10.0.0.5"], {H: "*"})
show("concrete 10.0.0.5 + H=',10.0.0.5'", ["--host", "10.0.0.5"], {H: ",10.0.0.5"})
show("concrete 10.0.0.5 + O=http://10.0.0.5:8000/", ["--host", "10.0.0.5"],
     {O: "http://10.0.0.5:8000/"})
show("concrete 10.0.0.5 + O=http://10.0.0.5:8000/path", ["--host", "10.0.0.5"],
     {O: "http://10.0.0.5:8000/path"})
show("concrete 10.0.0.5 + O=http://user@10.0.0.5", ["--host", "10.0.0.5"],
     {O: "http://user@10.0.0.5"})

print("\n== PORT SEMANTICS (concrete 10.0.0.5)")
B = ["--host", "10.0.0.5"]
show("no --port, H=10.0.0.5:8000", B, {H: "10.0.0.5:8000"})
show("no --port, H=10.0.0.5:9000", B, {H: "10.0.0.5:9000"})
show("no --port, UVICORN_PORT=9000, H=10.0.0.5:9000 (uvicorn binds 9000)", B,
     {"UVICORN_PORT": "9000", H: "10.0.0.5:9000"})
show("no --port, PORT=9000, H=10.0.0.5:9000", B, {"PORT": "9000", H: "10.0.0.5:9000"})
show("--port 8443, H=10.0.0.5:8443", B + ["--port", "8443"], {H: "10.0.0.5:8443"})
show("--port 8443, H=10.0.0.5:8000", B + ["--port", "8443"], {H: "10.0.0.5:8000"})
show("--port 8443, H=10.0.0.5 (bare)", B + ["--port", "8443"], {H: "10.0.0.5"})
show("--port 8443, O=http://10.0.0.5:8443", B + ["--port", "8443"], {O: "http://10.0.0.5:8443"})
show("--port 8443, O=http://10.0.0.5:8000", B + ["--port", "8443"], {O: "http://10.0.0.5:8000"})
show("--port 8443, O=https://10.0.0.5 (no port)", B + ["--port", "8443"], {O: "https://10.0.0.5"})
show("--port 1111 --port 8443 (uvicorn: last wins), H=10.0.0.5:8443",
     B + ["--port", "1111", "--port", "8443"], {H: "10.0.0.5:8443"})
show("--port 8443 --port 1111 (uvicorn: last wins), H=10.0.0.5:8443",
     B + ["--port", "8443", "--port", "1111"], {H: "10.0.0.5:8443"})
show("--port abc, H=10.0.0.5:abc", B + ["--port", "abc"], {H: "10.0.0.5:abc"})
show("IPv6 2001:db8::5 --port 8443 H=[2001:db8::5]:8443",
     ["--host", "2001:db8::5", "--port", "8443"], {H: "[2001:db8::5]:8443"})
show("IPv6 2001:db8::5 H=2001:db8::5 (unbracketed; Host header is bracketed)",
     ["--host", "2001:db8::5"], {H: "2001:db8::5"})
show("IPv6 bind 2001:DB8:0::5 H=[2001:db8::5] (non-canonical bind text)",
     ["--host", "2001:DB8:0::5"], {H: "[2001:db8::5]"})
show("IPv6 bind 2001:DB8:0::5 H=[2001:db8:0::5]", ["--host", "2001:DB8:0::5"],
     {H: "[2001:db8:0::5]"})
show("bind 010.0.0.5 H=10.0.0.5", ["--host", "010.0.0.5"], {H: "10.0.0.5"})
out, msg = run(B, {})
print("  (HOSTED unset) concrete bind, no ALLOWED_*  ->", out, msg[:100])
show("bind '[::1]' (bracketed; uvicorn cannot bind this text), H=other", ["--host", "[::1]"], {H: "other.example.com"})

print("\n== RUNTIME CROSS-CHECK: does the Host header a client really sends pass _host_allowed?")
from autotester.ui.helpers import _host_allowed  # noqa: E402


def host_ok(host, env):
    saved = dict(os.environ)
    for k in KEYS:
        os.environ.pop(k, None)
    os.environ.update(env)
    try:
        return _host_allowed(host)
    finally:
        os.environ.clear()
        os.environ.update(saved)


for label, host, env in [
    ("bind 10.0.0.5 --port 8443, H=10.0.0.5 (startup ok): client Host '10.0.0.5:8443'", "10.0.0.5:8443", {H: "10.0.0.5"}),
    ("same, O=https://10.0.0.5 (startup ok): client Host '10.0.0.5:8443'", "10.0.0.5:8443", {O: "https://10.0.0.5"}),
    ("shipped container, H=other.example.com (startup ok): client Host 'app.example.com'", "app.example.com", {H: "other.example.com"}),
    ("shipped container, H='*' (startup ok): client Host 'app.example.com'", "app.example.com", {H: "*"}),
    ("shipped container, H='*' : client Host 'localhost:8000'", "localhost:8000", {H: "*"}),
    ("shipped container, H=',' : client Host 'app.example.com'", "app.example.com", {H: ","}),
    ("proxy case H=app.example.com : client Host 'app.example.com'", "app.example.com", {H: "app.example.com"}),
]:
    print(f"  {label:<95} -> allowed={host_ok(host, env)}")

print("\n== EXTRA false-negative / false-positive probes")
show("UVICORN_PORT=9000 (real bind 9000), H=10.0.0.5:8000 -> own origin :9000 unlisted", B + [], {"UVICORN_PORT": "9000", H: "10.0.0.5:8000"})
show("concrete 10.0.0.5 behind a LAN proxy, public name only: H=app.example.com O=https://app.example.com", B, {H: "app.example.com", O: "https://app.example.com"})
show("same + also H=10.0.0.5:8000 (workaround)", B, {H: "app.example.com,10.0.0.5:8000"})
show("--port=8443 first, then --port 9 (last wins in uvicorn), H=10.0.0.5:9", B + ["--port=8443", "--port", "9"], {H: "10.0.0.5:9"})
