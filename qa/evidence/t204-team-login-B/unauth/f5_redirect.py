"""Family 5: open redirect via next=. Usage: python f5_redirect.py <mode> <scratch>"""
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
import common as C

mode, scratch = sys.argv[1], Path(sys.argv[2])
C.setup(mode, scratch)
ids = C.seed()
from autotester.auth.ratelimit import login_limiter, signup_limiter  # noqa: E402

G = C.good_origin()
HT = [("accept", "text/html")]
URLENC = [("content-type", "application/x-www-form-urlencoded")]
NEXTS = ["https://evil.example", "http://evil.example/x", "//evil.example", "///evil.example", "/\\evil.example",
         "\\\\evil.example", "\\/evil.example", "javascript:alert(1)", "data:text/html,<script>1</script>",
         "%2f%2fevil.example", "%2F%2Fevil.example", "/\t/evil.example", "/\n/evil.example",
         "/\r\nSet-Cookie: pwn=1", "https:evil.example", "https:/evil.example", "/@evil.example",
         "@evil.example", "/%2f/evil.example", "/.//evil.example", "/../../evil.example", "/ /evil.example",
         "/\x7f/evil.example", "/​/evil.example", "/∕evil.example", "/／evil.example",
         "evil.example", "", "/", "/projects/alpha", "/projects/alpha?x=//evil.example", "/#//evil.example",
         "/?next=//evil.example", "/" + "a" * 3000, "/ok\\..\\..\\evil", "/%5Cevil.example", "/%09/evil.example",
         "/\u0000/evil", "/auth/login?next=//evil.example", "/;@evil.example"]
rows = []
bad = []
n0 = C.STATE["n"]


def same_site_relative(loc: str) -> bool:
    return (loc.startswith("/") and not loc.startswith("//") and "\\" not in loc
            and not re.search(r"[\x00-\x1f\x7f]", loc))


def sample(v):
    return (v[:60] + f"...(len {len(v)})") if len(v) > 80 else v


for nx in NEXTS:
    # POST login success (admin, dev: has access; nogroup: waiting)
    for who in ("dev", "nogroup"):
        login_limiter.reset()
        signup_limiter.reset()
        body = ("email=" + quote(f"{who}-b@scratch.test") + "&password=" + quote(C.PW) + "&next="
                + quote(nx, safe="")).encode()
        r = C.call("POST", "/auth/login", HT + URLENC + [("origin", G)], body=body)
        loc = r.location
        rows.append(("POST login " + who, sample(nx), r.status, sample(loc or "")))
        if r.status != 303:
            bad.append(("login not 303", who, nx[:30], r.status))
        elif not same_site_relative(loc):
            bad.append(("POST Location not same-site relative", who, sample(nx), sample(loc)))
        if r.h("set-cookie") and "pwn" in " ".join(r.h("set-cookie")):
            bad.append(("header injection", nx))
    # GET login page: hidden next value
    for q in ("next=" + quote(nx, safe=""),):
        r = C.call("GET", "/auth/login", HT, query=q)
        m = re.search(r"name='next' value='([^']*)'", r.text)
        val = m.group(1) if m else None
        rows.append(("GET login hidden", sample(nx), r.status, sample(val or "")))
        if val is not None and not (val == "/" or same_site_relative(val.replace("&#x27;", "'").replace("&amp;", "&"))):
            bad.append(("hidden next not same-site", sample(nx), sample(val)))
        if r.status != 200 or val is None:
            bad.append(("GET login odd", nx[:30], r.status))
# raw (single-encoded in query) forms, double-encoded forms
for raw in ("next=%2f%2fevil.example", "next=%252f%252fevil.example", "next=/%5cevil.example", "next=//evil.example",
            "next=https://evil.example", "next=%5c%5cevil.example", "next=/%09/evil.example", "next=%0d%0a/evil",
            "next=/ok&next=//evil.example", "next[]=//evil.example", "NEXT=//evil.example"):
    r = C.call("GET", "/auth/login", HT, query=raw)
    m = re.search(r"name='next' value='([^']*)'", r.text)
    rows.append(("GET raw " + raw, "", r.status, m.group(1) if m else None))
    if m and not same_site_relative(m.group(1)):
        bad.append(("GET raw hidden", raw, m.group(1)))
    # and posting that decoded value through a form
# the unauthenticated redirect: Location for odd request paths
unauth = []
for p in ("/projects/alpha/env", "//evil.example/x", "/\\evil.example", "/%2f%2fevil.example", "/projects/a%0d%0aSet-Cookie:x=1",
          "/%5Cevil.example", "/projects/alpha?next=//evil.example", "/x%00y", "/ü", "/@evil.example",
          "/" + "a" * 3000, "/a%09b", "/;//evil.example", "/projects/alpha/env%0a"):
    r = C.call("GET", p, HT)
    unauth.append((sample(p), r.status, sample(r.location or "")))
    loc = r.location or ""
    if r.status == 302:
        nxt = loc.split("next=", 1)[1] if "next=" in loc else None
        from urllib.parse import unquote
        dec = unquote(nxt) if nxt is not None else ""
        if not (loc.startswith("/auth/login?next=") and same_site_relative(dec)):
            bad.append(("unauth redirect odd", sample(p), sample(loc)))
    if "\r" in loc or "\n" in loc:
        bad.append(("CRLF in Location", p))
# signup flow with next (signup ignores next -> "/")
r = C.call("POST", "/auth/signup", HT + URLENC + [("origin", G)],
           body=("email=redir-b%40scratch.test&password=" + quote(C.PW) + "&next=//evil.example").encode())
rows.append(("POST signup", "//evil.example", r.status, r.location))
# already-logged-in user hitting login with next: no auto redirect?
ck = C.session_cookie(ids["dev"])
r = C.call("GET", "/auth/login", HT + [("cookie", ck)], query="next=//evil.example")
rows.append(("GET login while signed in", "//evil.example", r.status, r.location))
print(mode, "requests", C.STATE["n"] - n0, "rows", len(rows), "BAD", len(bad))
for b in bad[:20]:
    print("BAD", b)
show = {"https://evil.example", "//evil.example", "/\\evil.example", "\\\\evil.example", "javascript:alert(1)",
        "%2f%2fevil.example", "/\t/evil.example", "https:evil.example", "/@evil.example", "/%2f/evil.example",
        "data:text/html,<script>1</script>", "/projects/alpha", "/\r\nSet-Cookie: pwn=1"}
for r in rows:
    if r[0] == "POST login dev" and r[1] in show:
        print(r)
for r in rows:
    if r[0] == "GET login hidden" and r[1] in {"//evil.example", "/projects/alpha", "/@evil.example"}:
        print(r)
for r in rows:
    if r[0].startswith(("GET raw", "POST signup", "GET login while")):
        print(r)
for u in unauth:
    print("UNAUTH", u)
C.dump("f5", {"bad": bad, "rows": rows, "unauth": unauth})
