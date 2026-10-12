"""AU20 differential harness (read-only sub-checker, r2-A): startup decision vs request-time guard.

Run: uv run --project D:/autoTesting/.worktrees/t204-team-login python <this file>
Writes cases.csv / cases.json / summary.json next to this file. Nothing under the worktree is edited.
"""
from __future__ import annotations

import contextlib
import csv
import io
import ipaddress
import json
import re
import shutil
import socket
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import pytest

WT = Path("D:/autoTesting/.worktrees/t204-team-login")
sys.path.insert(0, str(WT / "tests"))
OUT = Path(__file__).parent

import autotester  # noqa: E402
from auth_harness import ADMIN, PASSWORD, account, gate_on  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from autotester.auth import config  # noqa: E402
from autotester.auth.config import AuthConfigError, check_startup  # noqa: E402
from autotester.auth.ratelimit import login_limiter, signup_limiter  # noqa: E402
from autotester.ui.app import app  # noqa: E402

print("autotester.__file__ =", autotester.__file__)
assert Path(autotester.__file__).resolve().is_relative_to((WT / "src").resolve())

mp = pytest.MonkeyPatch()
TMP = Path(tempfile.mkdtemp(prefix="au20-"))
gate_on(TMP, mp)
account(ADMIN)

ENV_KEYS = ["AUTOTESTER_ALLOWED_HOSTS", "AUTOTESTER_ALLOWED_ORIGINS", "AUTOTESTER_PUBLIC_ORIGIN",
            "UVICORN_HOST", "UVICORN_PORT"]
_SERVED_CACHE: dict = {}


def served(hosts: str, origins: str, scheme: str, host_header: str) -> dict:
    """Ask the real app from a browser at scheme://host_header (env already set)."""
    key = (hosts, origins, scheme, host_header)
    if key in _SERVED_CACHE:
        return _SERVED_CACHE[key]
    try:
        c = TestClient(app, base_url=f"{scheme}://testserver", follow_redirects=False,
                       headers={"host": host_header})
        g = c.get("/auth/login").status_code
        login_limiter.reset()
        signup_limiter.reset()
        p = c.post("/auth/login", data={"email": ADMIN, "password": PASSWORD},
                   headers={"origin": f"{scheme}://{host_header}"}).status_code if g == 200 else None
        r = {"get": g, "post": p, "ok": g == 200 and p == 303}
    except Exception as exc:  # header the client itself rejects
        r = {"get": f"ERR:{type(exc).__name__}", "post": None, "ok": False}
    _SERVED_CACHE[key] = r
    return r


# ---- independent reference model of uvicorn's bind (click 8.5 semantics) ----------------------
def ref_bind(argv: list[str], uh: str | None, up: str | None):
    args = argv[:]
    host = port = None
    i = 0
    err = None
    while i < len(args):
        a = args[i]
        for opt in ("--host", "--port"):
            if a == opt:
                if i + 1 >= len(args):
                    err = f"{opt} requires an argument (click error)"
                else:
                    if opt == "--host":
                        host = args[i + 1]
                    else:
                        port = args[i + 1]
                    i += 1
            elif a.startswith(opt + "="):
                if opt == "--host":
                    host = a.split("=", 1)[1]
                else:
                    port = a.split("=", 1)[1]
        i += 1
    if err:
        return None, None, err
    if host is None:
        host = uh if uh else "127.0.0.1"  # click: an EMPTY env var counts as unset
    if port is None:
        port = up if up else "8000"
    try:
        p = int(port)
    except ValueError:
        return host, None, f"--port {port!r} not an integer (click error)"
    if not 0 <= p <= 65535:
        return host, None, f"port {p} out of range"
    if p == 0:
        return host, None, "port 0 = ephemeral, no stable origin"
    return host, p, None


_BIND_CACHE: dict = {}


def probe_bind(host: str):
    """What does uvicorn's own bind (family by ':' in host) do with this spelling on THIS OS?"""
    if host in _BIND_CACHE:
        return _BIND_CACHE[host]
    fam = socket.AF_INET6 if host and ":" in host else socket.AF_INET
    s = socket.socket(fam)
    try:
        s.bind((host, 0))
        bound = s.getsockname()[0]
        r = {"bindable": True, "bound": bound,
             "wild": ipaddress.ip_address(bound.split("%")[0]).is_unspecified}
    except socket.gaierror as exc:
        r = {"bindable": False, "bound": f"gaierror: {exc}", "wild": None}
    except OSError as exc:  # EADDRNOTAVAIL etc: the spelling resolved to a concrete, non-local address
        r = {"bindable": exc.errno in (10049, 99, 49, 10048) or "assign" in str(exc).lower(),
             "bound": f"concrete-non-local ({exc.errno})", "wild": False}
    finally:
        s.close()
    try:
        r["ip_unspecified"] = ipaddress.ip_address(host).is_unspecified
    except ValueError:
        r["ip_unspecified"] = None
    _BIND_CACHE[host] = r
    return r


def parsed_lists(hosts: str, origins: str) -> bool:
    for v in (hosts, origins):
        for t in v.replace(",", " ").split():
            if t != "*":
                return True
    return False


STRICT = re.compile(r"(?i)(https?)://(\[[0-9a-f:.]+\]|[^/?#@:\[\]\s,]+)(?::(\d{1,5}))?/?")


def strict_valid(raw: str) -> bool:
    t = raw.strip()
    m = STRICT.fullmatch(t)
    if not m:
        return False
    return m.group(3) is None or 1 <= int(m.group(3)) <= 65535


def intended(raw: str):
    """(scheme, Host header) a browser at the operator's intended origin sends; lenient parse."""
    toks = raw.strip().rstrip("/").lower().split()
    if not toks:
        return None
    try:
        p = urlparse(toks[0])
        host, port = p.hostname, p.port
    except ValueError:
        return None
    if p.scheme not in {"http", "https"} or not host:
        return None
    try:
        host.encode("ascii")
    except UnicodeEncodeError:
        host = host.encode("idna").decode()  # a browser sends punycode
    name = f"[{host}]" if ":" in host else host
    default = 80 if p.scheme == "http" else 443
    return p.scheme, (name if port in (None, default) else f"{name}:{port}")


def brk(host: str) -> str:
    h = host.strip().lower()
    return h if h.startswith("[") or ":" not in h else f"[{h}]"


def own_forms(host: str, port: int):
    name = brk(host)
    return [(s, name if port == d else f"{name}:{port}") for s, d in (("http", 80), ("https", 443))]


# ------------------------------------ one case -------------------------------------------------
def run_case(c: dict) -> dict:
    argv, uh, up = c["argv"], c.get("uh"), c.get("up")
    hosts, origins, public = c["hosts"], c["origins"], c.get("public")
    for k in ENV_KEYS:
        mp.delenv(k, raising=False)
    mp.setenv("AUTOTESTER_HOSTED", "1")
    mp.setenv("AUTOTESTER_FIRST_ADMIN_EMAIL", "boss@at.example")
    mp.setenv("AUTOTESTER_ALLOWED_HOSTS", hosts)
    mp.setenv("AUTOTESTER_ALLOWED_ORIGINS", origins)
    if public is not None:
        mp.setenv("AUTOTESTER_PUBLIC_ORIGIN", public)
    if uh is not None:
        mp.setenv("UVICORN_HOST", uh)
    if up is not None:
        mp.setenv("UVICORN_PORT", up)
    mp.setattr(sys, "argv", ["uvicorn", "autotester.ui.app:app", *argv])
    row = {k: c.get(k) for k in ("id", "dim")}
    row.update(argv=json.dumps(argv), uvicorn_host=uh, uvicorn_port=up, hosts=hosts,
               origins=origins, public=public)
    # startup
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        try:
            check_startup()
            startup, msg = "OK", ""
        except AuthConfigError as exc:
            startup, msg = "RAISE", str(exc)
        except Exception as exc:  # noqa: BLE001
            startup, msg = "CRASH", f"{type(exc).__name__}: {exc}"
    row.update(startup=startup, msg_head=msg[:110])
    try:
        row.update(code_host=config.bind_host(), code_port=config.bind_port())
    except Exception as exc:  # noqa: BLE001
        row.update(code_host="", code_port=f"RAISES {type(exc).__name__}")
    rhost, rport, rerr = ref_bind(argv, uh, up)
    row.update(ref_host=rhost, ref_port=rport, ref_err=rerr)
    if rerr:
        row.update(verdict="UNBINDABLE-uvicorn-refuses", bound="", wild="", served="{}")
        return row
    pb = probe_bind(rhost)
    row.update(bound=pb["bound"], wild=pb["wild"], ip_unspecified=pb["ip_unspecified"])
    if not pb["bindable"]:
        row.update(verdict="UNBINDABLE-os-refuses", served="{}")
        return row
    wild = pb["wild"]
    pub_eff = public if (public is not None and public.strip()) else None
    pub_b = intended(pub_eff) if pub_eff else None
    browsers: dict[str, tuple[str, str]] = {}
    if not wild:
        for s, h in own_forms(rhost, rport):
            browsers[f"own-{s}"] = (s, h)
    if pub_b:
        browsers["public"] = pub_b
    sv = {k: served(hosts, origins, *v) for k, v in browsers.items()}
    row["served"] = json.dumps({k: {"host": browsers[k][1], "scheme": browsers[k][0], **v}
                                for k, v in sv.items()})
    own_ok = wild or any(sv[k]["ok"] for k in sv if k.startswith("own-"))
    pub_ok = (pub_eff is None) or (pub_b is not None and sv["public"]["ok"])
    would = parsed_lists(hosts, origins) and own_ok and pub_ok and not (wild and pub_eff is None)
    pub_invalid = pub_eff is not None and not strict_valid(pub_eff)
    by_design = (not parsed_lists(hosts, origins) or (wild and pub_eff is None) or pub_invalid)
    row.update(would_serve=would, by_design_raise=by_design)
    if startup == "CRASH":
        v = "CRASH-not-AuthConfigError"
    elif startup == "OK":
        if not by_design:
            v = "ok-started-served" if would else "DISAGREE-started-but-403"
        elif not parsed_lists(hosts, origins) or (wild and pub_eff is None):
            v = "DISAGREE-spec-violation-started"
        else:  # accepted a public origin that the strict grammar rejects
            v = ("ODDITY-accepted-malformed-harmless" if (own_ok and pub_b and sv["public"]["ok"])
                 else "DISAGREE-started-but-403(malformed-public)")
    else:
        if by_design:
            v = "ok-refused-by-design"
        else:
            v = "DISAGREE-refused-but-would-serve" if would else "ok-refused"
    row["verdict"] = v
    # bind parser differential (does the code read the same bind uvicorn will use?)
    row["bind_parse_mismatch"] = (str(rport) != row["code_port"]) or (rhost != row["code_host"])
    return row


# ---------------------------------------- grid -------------------------------------------------
CASES: list[dict] = []


def add(dim, id_, argv, hosts="", origins="", public=None, uh=None, up=None):
    CASES.append(dict(dim=dim, id=f"{dim}:{id_}", argv=argv, hosts=hosts, origins=origins,
                      public=public, uh=uh, up=up))


def listings(name: str, port: int):
    """Allow-list pairs relative to a concrete bind `name` (already bracketed) and `port`."""
    def hh(s):
        return name if port == (80 if s == "http" else 443) else f"{name}:{port}"
    L = {"none": ("", ""), "star-h": ("*", ""), "star-o": ("", "*"), "comma": (",", ""),
         "h-bare": (name, ""), "h-port": (f"{name}:{port}", ""),
         "h-dot": (f"{name}.:{port}", ""), "h-upper": (f"{name}:{port}".upper(), ""),
         "star+h-port": (f"*,{name}:{port}", ""),
         "o-other": ("", "https://other.example"), "h-other": ("other.example", "")}
    for s in ("http", "https"):
        L[f"o-{s}-port"] = ("", f"{s}://{name}:{port}")
        L[f"o-{s}-noport"] = ("", f"{s}://{name}")
        L[f"o-{s}-browser"] = ("", f"{s}://{hh(s)}")
        L[f"ho-{s}-browser"] = (hh(s), f"{s}://{hh(s)}")
        L[f"o-{s}-slash-upper"] = ("", f"{s.upper()}://{hh(s).upper()}/")
        L[f"o-{s}-dot"] = ("", f"{s}://{name}.:{port}")
        L[f"h-{s}-browser+o-wrong-scheme"] = (hh(s), f"{'https' if s == 'http' else 'http'}://{hh(s)}")
    return L


BINDS = ["10.0.0.5", "2001:db8::5", "2001:DB8::5", "intranet.example", "INTRANET.Example",
         "intranet.example.", "127.0.0.1", "localhost", "LOCALHOST", "::1", "127.0.0.2",
         "127.1", "::ffff:127.0.0.1", "0:0:0:0:0:0:0:1", "[::1]", "[2001:db8::5]",
         "fe80::1%lo", "10.0.0.5 "]
PORTS = [None, 80, 443, 8443]
for b in BINDS:
    for p in PORTS:
        argv = ["--host", b] + (["--port", str(p)] if p else [])
        for lid, (h, o) in listings(brk(b), p or 8000).items():
            add("A-bind-x-port-x-lists", f"{b!r}/{p}/{lid}", argv, h, o)

# B: option spelling / port source / host source (concrete 10.0.0.5, origin for port 8443)
O8443 = ("", "https://10.0.0.5:8443")
O8000 = ("", "https://10.0.0.5:8000")
PS = [("--port 8443", ["--port", "8443"], None), ("--port=8443", ["--port=8443"], None),
      ("env only", [], "8443"), ("argv beats env", ["--port=8443"], "9"),
      ("env 8443 argv 9 (argv wins)", ["--port", "9"], "8443"),
      ("repeat last wins", ["--port", "1", "--port", "8443"], None),
      ("repeat first right", ["--port", "8443", "--port", "1"], None),
      ("leading zero", ["--port", "08443"], None), ("leading zero =", ["--port=08443"], None),
      ("space-padded argv", ["--port", " 8443"], None), ("space-padded env", [], " 8443 "),
      ("nonnumeric env", [], "abc"), ("nonnumeric argv + good env", ["--port", "abc"], "8443"),
      ("empty env", [], ""), ("empty argv=", ["--port="], "8443"),
      ("--port last no value + env", ["--port"], "8443"), ("superscript digit", ["--port", "²"], None),
      ("fullwidth digits", ["--port", "８４４３"], None), ("plus sign", ["--port", "+8443"], None),
      ("underscore", ["--port", "8_443"], None), ("port 0", ["--port", "0"], None),
      ("port 65536", ["--port", "65536"], None), ("negative", ["--port", "-1"], None),
      ("default 8000", [], None), ("env 8000", [], "8000")]
for lbl, extra, up in PS:
    for oname, (h, o) in (("o8443", O8443), ("o8000", O8000), ("h8443", ("10.0.0.5:8443", "")),
                          ("h-bare", ("10.0.0.5", ""))):
        add("B-port-spelling", f"{lbl}/{oname}", ["--host", "10.0.0.5", *extra], h, o, up=up)
HS = [("--host V", ["--host", "10.0.0.5"], None), ("--host=V", ["--host=10.0.0.5"], None),
      ("repeat last", ["--host", "10.9.9.9", "--host=10.0.0.5"], None),
      ("repeat first", ["--host", "10.0.0.5", "--host=10.9.9.9"], None),
      ("env only", [], "10.0.0.5"), ("argv beats env", ["--host", "10.0.0.5"], "10.9.9.9"),
      ("env beats nothing but argv wins", ["--host", "10.9.9.9"], "10.0.0.5"),
      ("--host last no value + env", ["--host"], "10.0.0.5"),
      ("--host= empty + env", ["--host="], "10.0.0.5"), ("--host '' + env", ["--host", ""], "10.0.0.5"),
      ("env empty (click: unset -> 127.0.0.1)", [], ""),
      ("env empty + public", [], ""), ("padded argv", ["--host", " 10.0.0.5 "], None),
      ("padded env", [], " 10.0.0.5 "), ("--host --port swallow", ["--host", "--port", "8443"], None),
      ("no host at all (default 127.0.0.1)", [], None)]
for lbl, extra, uh in HS:
    for oname, (h, o, pub) in (
            ("o8443", (*O8443, None)), ("o8000", ("", "https://10.0.0.5:8000", None)),
            ("h-bare", ("10.0.0.5", "", None)), ("other-host-listed", ("at.example", "", None)),
            ("pub-qa-listed", ("", "https://qa.example.com", "https://qa.example.com")),
            ("pub-qa-unlisted", ("at.example", "", "https://qa.example.com"))):
        add("B-host-spelling", f"{lbl}/{oname}", [*extra, "--port", "8443"], h, o, public=pub, uh=uh)

# C: wildcard spellings
SPELL = ["0.0.0.0", "::", "", "*", "0", "::0", "0:0:0:0:0:0:0:0", "[::]", "0.0.0.00", " 0.0.0.0",
         "0.0.0.0 ", "::ffff:0.0.0.0", "::FFFF:0.0.0.0", "00.0.0.0", "0x0.0.0.0", "0.0.0", "0.0",
         "0000:0000:0000:0000:0000:0000:0000:0000", "::0.0.0.0", " ::", ":: ", "0.0.0.0\t",
         "0.00.0.0", "::0:0", "0::", "0:0::0"]
QA, LAN = "https://qa.example.com", "http://192.168.1.20:8000"
for sp in SPELL:
    for pub in (QA, LAN, None):
        pb = intended(pub) if pub else None
        lists = {"o-canon": ("", f"{pb[0]}://{pb[1]}") if pb else ("", QA),
                 "h-canon": (pb[1] if pb else "qa.example.com", ""),
                 "ho-canon": ((pb[1], f"{pb[0]}://{pb[1]}") if pb else ("qa.example.com", QA))}
        nm = brk(sp)
        lists["own-listed"] = (f"{nm}:8000", f"http://{nm}:8000")
        lists["own-listed-noport80"] = (nm, f"http://{nm}")
        for lid, (h, o) in lists.items():
            add("C-wildcard-spelling", f"{sp!r}/pub={pub}/{lid}", ["--host", sp, "--port", "8000"],
                h, o, public=pub)
    # same via env + via =
    add("C-wildcard-spelling", f"{sp!r}/env/QA", [], "", QA, public=QA, uh=sp)
    add("C-wildcard-spelling", f"{sp!r}/eq/QA", [f"--host={sp}"], "", QA, public=QA)

# D: PUBLIC_ORIGIN variants
PUBV = [
    "https://qa.example.com", "http://qa.example.com", "https://qa.example.com:443",
    "http://qa.example.com:80", "https://qa.example.com:80", "http://qa.example.com:443",
    "https://qa.example.com:8443", "http://192.168.1.20:8000", "HTTPS://QA.Example.COM",
    "https://qa.example.com/", "https://qa.example.com//", "https://qa.example.com.",
    "https://qa.example.com./", "https://[2001:db8::5]", "https://[2001:db8::5]:8443",
    "http://[2001:DB8::5]:8000", "http://localhost:8000", "http://127.0.0.1:8000",
    "http://[::1]:8000", "  https://qa.example.com  ", "https://qa.example.com:0443",
    "https://qa.example.com:00443", "https://qa.example.com:", "https://b\u00fccher.example",
    "https://xn--bcher-kva.example", "https://qa.example.com/app", "https://qa.example.com/?x=1",
    "https://qa.example.com?x=1", "https://qa.example.com#f", "https://me@qa.example.com",
    "https://@qa.example.com", "https://:pw@qa.example.com", "https://me:pw@qa.example.com",
    "*", "", "   ", "https://qa .example.com", "https://qa.exa\tmple.com", "qa.example.com",
    "//qa.example.com", "ftp://qa.example.com", "https://", "http://", "https:///", "https://:443",
    "https://qa.example.com:abc", "https://qa.example.com:99999", "https://qa.example.com:65536",
    "https://qa.example.com:0", "https://qa.example.com:-1", "https://qa.example.com:+443",
    "https://a.example https://b.example", "https://a.example,https://b.example",
    "https://a.example, https://b.example", "https://qa.example.com\\", "https:/qa.example.com",
    "https:qa.example.com", "HtTpS://qa.example.com", "https://qa_example.com",
    "https://qa.example.com:443/", "https://[::1", "https://[]", "https://[qa.example.com]",
    "https://qa.example.com%2f", "https://0.0.0.0:8000", "https://[::]:8000", "http://::1:8000",
]
BINDS_D = [("wildcard 0.0.0.0", ["--host", "0.0.0.0"], False),
           ("wildcard ::", ["--host", "::"], False),
           ("concrete 10.0.0.5:8443", ["--host", "10.0.0.5", "--port", "8443"], True),
           ("loopback 127.0.0.1", ["--host", "127.0.0.1"], False),
           ("loopback ::1", ["--host", "::1"], False)]
for lbl, argv, conc in BINDS_D:
    for pv in PUBV:
        pb = intended(pv) if pv.strip() else None
        pairs = {"none-listed": ("at.example", "") if not conc else ("", "https://10.0.0.5:8443")}
        base_o = "https://10.0.0.5:8443" if conc else ""
        if pb:
            oc = f"{pb[0]}://{pb[1]}"
            pairs.update({"o-canon": ("", f"{base_o} {oc}".strip()),
                          "h-canon": (pb[1], base_o), "ho-canon": (pb[1], f"{base_o} {oc}".strip())})
        pairs["o-raw"] = ("", f"{base_o} {pv.strip()}".strip())
        for lid, (h, o) in pairs.items():
            add("D-public-origin", f"{lbl}/{pv!r}/{lid}", argv, h, o, public=pv)

# E: allow-list syntax x wildcard/public
for lid, (h, o) in {"star": ("*", ""), "comma": (",", ""), "star+origin": ("", f"*,{QA}"),
                    "upper": ("", QA.upper()), "slash": ("", QA + "/"), "dot": ("", "https://qa.example.com."),
                    "port443": ("", QA + ":443"), "space-sep": ("", f"https://x.example {QA}"),
                    "comma-sep": ("", f"https://x.example,{QA}"), "tab": ("", f"https://x.example\t{QA}"),
                    "host-port443": (f"qa.example.com:443", ""), "host-bare": ("qa.example.com", ""),
                    "host-upper": ("QA.EXAMPLE.COM", ""), "host-dot": ("qa.example.com.", "")}.items():
    for pub in (QA, QA + "/", QA + ":443", "https://qa.example.com."):
        add("E-list-syntax-wildcard", f"{lid}/pub={pub}", ["--host", "0.0.0.0"], h, o, public=pub)

# --------------------------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    shard, nshard = (int(x) for x in os.environ.get("FUZZ_SHARD", "0/1").split("/"))
    size = -(-len(CASES) // nshard)
    mine = CASES[shard * size:(shard + 1) * size]
    suffix = f".{shard}" if nshard > 1 else ""
    rows = [run_case(c) for c in mine]
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(OUT / f"cases{suffix}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    (OUT / f"cases{suffix}.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    summ = {"total": len(rows), "by_dim": Counter(r["dim"] for r in rows),
            "by_verdict": Counter(r["verdict"] for r in rows),
            "by_dim_verdict": {d: dict(Counter(r["verdict"] for r in rows if r["dim"] == d))
                               for d in sorted({r["dim"] for r in rows})},
            "bind_parse_mismatch": sum(1 for r in rows if r.get("bind_parse_mismatch"))}
    (OUT / f"summary{suffix}.json").write_text(json.dumps(summ, indent=1, default=dict), encoding="utf-8")
    print(json.dumps(summ, indent=1, default=dict))
    mp.undo()
    shutil.rmtree(TMP, ignore_errors=True)
