"""Family 4: CSRF/Origin guard and Host header attacks as Admin. Usage: python f4_csrf.py <mode> <scratch>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common as C

mode, scratch = sys.argv[1], Path(sys.argv[2])
C.setup(mode, scratch)
ids = C.seed()
from autotester.auth.ratelimit import login_limiter, signup_limiter  # noqa: E402

G = C.good_origin()
H = C.host()
EV = "http://evil.example"
UNSAFE = ["POST", "PUT", "PATCH", "DELETE"]
HT = [("accept", "text/html")]
ids2 = dict(ids)
ids2["admin"] = 9999
ids2["_admin_group"] = 9999


def p4(tpl):
    return (C.fill(tpl, ids2, True).replace("/projects/alpha", "/projects/gamma")
            .replace("ALPHA_PASSWORD", "GAMMA_PASSWORD"))


URLENC = [("content-type", "application/x-www-form-urlencoded")]
TXT = [("content-type", "text/plain")]
MP = [("content-type", "multipart/form-data; boundary=BB")]
MPBODY = b'--BB\r\nContent-Disposition: form-data; name="a"\r\n\r\nb\r\n--BB--\r\n'
portbad = (G.rsplit(":", 1)[0] + ":80.evil.com") if mode == "loopback" else G + ":80.evil.com"
# name, headers, content headers, body, expect_blocked (None = report only)
V = [
    ("a_no_origin_no_referer", [], URLENC, b"", False),
    ("b_origin_evil", [("origin", EV)], URLENC, b"", True),
    ("c_origin_null", [("origin", "null")], URLENC, b"", True),
    ("d_origin_good", [("origin", G)], URLENC, b"", False),
    ("e_referer_only_evil", [("referer", EV + "/page")], URLENC, b"", True),
    ("e2_referer_only_good", [("referer", G + "/page")], URLENC, b"", False),
    ("e3_referer_garbage", [("referer", "not a url")], URLENC, b"", True),
    ("f1_textplain_origin_evil", [("origin", EV)], TXT, b"a=b", True),
    ("f2_multipart_origin_evil", [("origin", EV)], MP, MPBODY, True),
    ("f3_textplain_no_origin", [], TXT, b"a=b", False),
    ("f4_multipart_no_origin", [], MP, MPBODY, False),
    ("f5_textplain_referer_evil", [("referer", EV + "/")], TXT, b"a=b", True),
    ("g1_dup_origin_good_evil", [("origin", G), ("origin", EV)], URLENC, b"", True),
    ("g2_dup_origin_evil_good", [("origin", EV), ("origin", G)], URLENC, b"", True),
    ("g3_origin_nonnumeric_port", [("origin", portbad)], URLENC, b"", True),
    ("g4_origin_star", [("origin", "*")], URLENC, b"", True),
    ("g5_origin_empty", [("origin", "")], URLENC, b"", True),
    ("g6_origin_localhost_at_evil", [("origin", "http://localhost@evil.example")], URLENC, b"", True),
    ("g7_origin_evil_at_localhost", [("origin", "http://evil.example@localhost")], URLENC, b"", True),
    ("g8_sfs_cross_site_no_origin", [("sec-fetch-site", "cross-site")], URLENC, b"", True),
    ("g9_sfs_same_site_no_origin", [("sec-fetch-site", "same-site")], URLENC, b"", True),
    ("g10_origin_good_sfs_cross", [("origin", G), ("sec-fetch-site", "cross-site")], URLENC, b"", False),
    ("g11_origin_upper", [("origin", G.upper())], URLENC, b"", False),
    ("g12_origin_trailing_slash", [("origin", G + "/")], URLENC, b"", False),
    ("g13_origin_with_path", [("origin", G + "/x")], URLENC, b"", True),
    ("g14_origin_localhost_evil_com", [("origin", "http://localhost.evil.com")], URLENC, b"", True),
    ("g15_origin_127_evil_io", [("origin", "http://127.0.0.1.evil.io")], URLENC, b"", True),
    ("g16_origin_evil_referer_good", [("origin", EV), ("referer", G + "/")], URLENC, b"", True),
    ("g17_origin_good_referer_evil", [("origin", G), ("referer", EV + "/")], URLENC, b"", False),
    ("g18_origin_ftp", [("origin", "ftp://localhost")], URLENC, b"", True),
    ("g19_origin_0000", [("origin", "http://0.0.0.0")], URLENC, b"", True),
    ("g20_origin_127_1", [("origin", "http://127.1")], URLENC, b"", True),
    ("g21_origin_localhost_dot", [("origin", "http://localhost.")], URLENC, b"", True),
    ("g22_origin_file", [("origin", "file://")], URLENC, b"", True),
    ("g23_origin_evil_path_localhost", [("origin", "http://evil.example:8000/localhost")], URLENC, b"", True),
    ("g24_origin_evil_hash_localhost", [("origin", "http://evil.example#@localhost")], URLENC, b"", True),
    ("g25_origin_backslash", [("origin", "http://evil.example\\@localhost")], URLENC, b"", True),
    ("g26_origin_tab", [("origin", "http://evil.example\t.localhost")], URLENC, b"", True),
    ("g27_origin_https_same_host", [("origin", "https://" + H)], URLENC, b"", None),
]


def run_one(method, path, hdrs, ctype, body):
    login_limiter.reset()
    signup_limiter.reset()
    ck = C.session_cookie(ids["admin"])
    return C.call(method, path, [("cookie", ck)] + HT + hdrs + ctype, body=body)


def guard_block(r):
    return r.status == 403 and ("cross-site request refused" in r.text or r.text == "")


unsafe_routes = sorted({(m, tpl) for ms, tpl, _ in C.routes() for m in ms if m in UNSAFE})
n0 = C.STATE["n"]
res = {}
viol = []
for name, hdrs, ctype, body, expect in V:
    b = a = 0
    for m, tpl in unsafe_routes:
        r = run_one(m, p4(tpl), hdrs, ctype, body)
        blk = guard_block(r)
        b += blk
        a += (not blk)
        if expect is True and not blk:
            viol.append((name, m, tpl, r.status, r.text[:80]))
        if expect is False and blk:
            viol.append(("UNEXPECTED-BLOCK " + name, m, tpl, r.status, r.text[:80]))
    res[name] = {"guard_blocked": b, "passed_guard": a, "expected_block": expect}
# PUT/PATCH/DELETE/POST on every path with cross-site origin and none
extra = []
for ms, tpl, _ in C.routes():
    for m in ("PUT", "PATCH", "DELETE", "POST"):
        for nm, hdrs in (("evil", [("origin", EV)]), ("null", [("origin", "null")]), ("none", [])):
            r = run_one(m, p4(tpl), hdrs, URLENC, b"")
            extra.append((m, tpl, nm, r.status, guard_block(r)))
extra_bad = [e for e in extra if e[2] in ("evil", "null") and not e[4]]
# every GET as admin: does any GET change the data root?
snapG0 = C.snapshot(scratch)
for ms, tpl, _ in C.routes():
    if "GET" in ms:
        run_one("GET", p4(tpl), [], [], b"")
snapG1 = C.snapshot(scratch)
getdiff = [x for x in C.diff(snapG0, snapG1) if x[1] not in (".auth/auth.sqlite3",)]
# Host header attacks as Admin on the env page
hostres = []
base = run_one("GET", "/projects/alpha/env", [], [], b"")
hostres.append(("baseline-good-host", base.status, C.leaks(base)))
for hv in ("evil.example", "localhost.evil.com", "127.0.0.1.evil.io", "localhost:8000.evil.com",
           "testserver.evil.com", "testserver:8000", "TESTSERVER", "evil.example:80", "localhost@evil.example",
           "evil.example#@localhost", "evil.example/localhost", "localhost/x", " localhost ", "[::1]",
           "[::1]:8000", "127.0.0.1", "localhost.", "0.0.0.0", "evil.example\\localhost", "", "xn--evil",
           "testserver\t"):
    ck = C.session_cookie(ids["admin"])
    r = C.call("GET", "/projects/alpha/env", [("cookie", ck)] + HT, host_override=hv)
    hostres.append((hv, r.status, C.leaks(r)))
ck = C.session_cookie(ids["admin"])
r = C.call("GET", "/projects/alpha/env", [("cookie", ck), ("host", H), ("host", "evil.example")] + HT,
           with_host=False)
hostres.append(("dup-host-good+evil", r.status, C.leaks(r)))
r = C.call("GET", "/projects/alpha/env", [("cookie", ck), ("host", "evil.example"), ("host", H)] + HT,
           with_host=False)
hostres.append(("dup-host-evil+good", r.status, C.leaks(r)))
r = C.call("GET", "/projects/alpha/env", [("cookie", ck)] + HT, with_host=False)
hostres.append(("no-host", r.status, C.leaks(r)))
for hdr in ("x-forwarded-host", "forwarded", "x-host", "x-original-host"):
    r = C.call("GET", "/projects/alpha/env", [("cookie", ck), (hdr, "evil.example")] + HT)
    hostres.append((hdr + ": evil.example (Host good)", r.status, C.leaks(r)))
print(mode, "requests", C.STATE["n"] - n0, "unsafe routes", len(unsafe_routes))
for k, v in res.items():
    print(f"  {k}: {v}")
print("violations:", viol[:10], len(viol))
print("extra method/origin bad:", extra_bad[:10], len(extra_bad))
print("GET state-change diff (excl sqlite):", getdiff)
for h in hostres:
    print("  host", h)
C.dump("f4", {"variants": res, "violations": viol, "extra_bad": extra_bad, "get_diff": getdiff,
              "host": hostres, "unsafe_routes": len(unsafe_routes)})
