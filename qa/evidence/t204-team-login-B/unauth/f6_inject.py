"""Family 6: HTML/script injection via emails, display names, group titles, project names.
Usage: python f6_inject.py <mode> <scratch>"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
import common as C

mode, scratch = sys.argv[1], Path(sys.argv[2])
C.setup(mode, scratch)
ids = C.seed()
from autotester.auth import accounts, groups  # noqa: E402
from autotester.auth.access import set_owner  # noqa: E402
from autotester.auth.ratelimit import login_limiter, signup_limiter  # noqa: E402
from autotester.schema.project import Project  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402


class _Dom(HTMLParser):
    """Finds DOM-level injection: tags/attributes/script text carrying our xss tokens."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found, self._script = [], False

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._script = True
        for k, v in attrs:
            if (k.startswith("on") and "xss" in (v or "")) or k in ("xss2", "xss4", "xss7", "xss8", "xss12"):
                self.found.append(f"<{tag} {k}={v!r}>")
            if k == "autofocus" or (k.startswith("on") and k in ("onfocus", "onerror", "onload", "onmouseover") and "xss" in (v or "")):
                self.found.append(f"<{tag} {k}>")
        if tag in ("img", "svg") and any("xss" in (v or "") or "xss" in k for k, v in attrs):
            self.found.append(f"<{tag} attrs={attrs!r}>")
        if tag == "b" and any("xss12" in (v or "") or "xss12" in k for k, v in attrs):
            self.found.append("<b onmouseover=xss12>")

    def handle_endtag(self, tag):
        if tag == "script":
            self._script = False

    def handle_data(self, data):
        if self._script and re.search(r"alert\((1|11)\)", data) and "<script>alert" in data:
            self.found.append("script text: " + data[:60])
        if self._script and re.search(r"alert\((1|11)\)", data):
            self.found.append("script text has alert(): " + data[:60])


def dom_hits(body):
    p = _Dom()
    p.feed(body)
    return p.found


G = C.good_origin()
HT = [("accept", "text/html")]
URLENC = [("content-type", "application/x-www-form-urlencoded")]
n0 = C.STATE["n"]
adm = C.session_cookie(ids["admin"])

# payloads (emails are lower-cased and may not contain whitespace)
EMAILS = {"e1": "<script>alert(1)</script>@x.test", "e2": "\"><img/src=x/onerror=xss2>@x.test",
          "e3": "'onmouseover='xss3'@x.test", "e4": "<svg/onload=xss4>@x.test",
          "e5": "&lt;b&gt;&amp;@x.test", "e6": "a\"onfocus=\"xss6@x.test"}
signup = {}
for k, em in EMAILS.items():
    login_limiter.reset()
    signup_limiter.reset()
    r = C.call("POST", "/auth/signup", HT + URLENC + [("origin", G)],
               body=("email=" + quote(em, safe="") + "&password=" + quote(C.PW)).encode())
    signup[k] = (r.status, r.location, re.sub(r"[\w-]{30,}", "<tok>", r.text[:0]))
print("signup payload emails ->", {k: v[:2] for k, v in signup.items()})
created = {k: accounts.find_user(em.lower()) for k, em in EMAILS.items()}
# admin: display names, groups, project names
DISPLAY = "<img src=x onerror=xss7>"
GROUP = "'><svg onload=xss8>"
GROUP2 = "x' onfocus='xss9"
PROJECT_NAME = "\" autofocus onfocus=\"xss10"
PROJECT_NAME2 = "<script>alert(11)</script>"
nog = ids["nogroup"]
r = C.call("POST", f"/admin/users/{nog}/name", HT + URLENC + [("cookie", adm), ("origin", G)],
           body=("display_name=" + quote(DISPLAY)).encode())
print("set display name ->", r.status)
for g in (GROUP, GROUP2):
    r = C.call("POST", "/admin/groups", HT + URLENC + [("cookie", adm), ("origin", G)],
               body=("name=" + quote(g) + "&permission=project.view%40shared").encode())
    print("create group", g, "->", r.status, r.location)
for slug, nm in (("inj-a", PROJECT_NAME), ("inj-b", PROJECT_NAME2)):
    ProjectStore(slug, scratch).save_project(Project(slug=slug, name=nm, base_url="https://inj.test",
                                                      allowed_domains=["inj.test"]))
    set_owner(slug, ids["admin"])
# onboard route with payload name (validation may reject)
r = C.call("POST", "/onboard", HT + URLENC + [("cookie", adm), ("origin", G)],
           body=("slug=inj-c&name=" + quote("<b onmouseover=xss12>x</b>") +
                 "&base_url=https%3A%2F%2Finj.test&allowed_domains=inj.test").encode())
print("onboard payload name ->", r.status, r.location, r.text[:0])
# share alpha with payload-email users and put e1 in a group so emails show in access/admin pages
for k in ("e1", "e2", "e3"):
    login_limiter.reset()
    C.call("POST", "/projects/alpha/access", HT + URLENC + [("cookie", adm), ("origin", G)],
           body=("email=" + quote(EMAILS[k].lower(), safe="") + "&relation=shared&change=add").encode())
gl = {g.name: g.id for g in groups.list_groups()}
gid1 = gl.get(GROUP)
tests_g = [g.id for g in groups.list_groups()]
for k in ("e1", "e2", "e4"):
    if created[k]:
        accounts.set_user_groups(created[k].id, [gl["Tester"]])
PAYLOADS = ["<script>alert(1)</script>", "<img/src=x/onerror=xss2>", "onmouseover='xss3", "<svg/onload=xss4>",
            "onfocus=\"xss6", "<img src=x onerror=xss7>", "<svg onload=xss8>", "onfocus='xss9", "autofocus onfocus=\"xss10",
            "<script>alert(11)</script>", "<b onmouseover=xss12>", "\"><img", "'><svg", "<script>"]
BAD_GENERIC = re.compile(r"on(error|load|focus|mouseover)\s*=\s*['\"]?xss\d+|<script>alert\((1|11)\)</script>", re.I)
# accounts that view pages
cookies = {"admin": adm, "dev": C.session_cookie(ids["dev"]), "tester": C.session_cookie(ids["tester"]),
           "nogroup(display-name payload)": C.session_cookie(ids["nogroup"])}
for k in ("e1", "e2", "e3", "e4"):
    if created[k]:
        cookies[f"payload-email {k}"] = C.session_cookie(created[k].id)
gid = gl.get("Tester")
PAGES = ["/", "/onboard", "/admin/users", "/admin/groups", f"/admin/groups/{gl.get('Tester')}",
         f"/admin/groups/{gid1}" if gid1 else "/admin/groups/1", "/projects/inj-a", "/projects/inj-b",
         "/projects/inj-a/edit", "/projects/inj-b/access", "/projects/alpha/access", "/projects/alpha/env",
         "/projects/inj-a/env", "/projects/inj-b/report", "/projects/inj-a/catalog", "/projects/inj-a/sources",
         "/projects/inj-b/flowspec", "/projects/inj-a/cases", "/settings/providers", "/live", "/auth/waiting",
         "/auth/login?next=" + quote("/'><svg onload=xss13>", safe=""), "/auth/login", "/auth/signup",
         "/nosuchpage", "/projects/%3Cimg%20src%3Dx%20onerror%3Dxss14%3E",
         "/projects/x%27onmouseover%3D%27xss15", "/projects/%3Cscript%3Ealert(1)%3C%2Fscript%3E/env",
         "/admin/users/%3Cscript%3E", "/admin/groups/%3Cimg%3E"]
checked = []
hits = []
for who, ck in cookies.items():
    for pg in PAGES:
        path, _, q = pg.partition("?")
        r = C.call("GET", path, HT + [("cookie", ck)], query=q)
        body = r.text
        raw_hits = []
        gen = dom_hits(body)
        esc_seen = ("&lt;" in body) or ("&#x27;" in body) or ("&quot;" in body)
        checked.append((who, pg, r.status, len(body), bool(raw_hits), bool(gen), esc_seen))
        if raw_hits or gen:
            i = min([body.lower().find(p.lower()) for p in raw_hits if p.lower() in body.lower()] or [0])
            hits.append((who, pg, r.status, raw_hits, body[max(0, i - 80):i + 100].replace("\n", " ")))
# POST error pages that echo: signup w/ bad email, group create error page, admin user action error
login_limiter.reset()
signup_limiter.reset()
errs = []
for path, body in (("/auth/signup", "email=%3Cscript%3Ealert(1)%3C%2Fscript%3E&password=short"),
                   ("/auth/signup", "email=a%40b.test&password=" + quote("<img src=x onerror=xss16>")),
                   ("/auth/login", "email=%3Cscript%3Ealert(1)%3C%2Fscript%3E%40x.test&password=%3Cimg%3E"),
                   ("/admin/groups", "name=%3Cscript%3Ealert(1)%3C%2Fscript%3E&permission=nope%40all"),
                   ("/admin/groups", "name=&permission=project.view%40all"),
                   ("/admin/users/%d/password" % ids["dev"], "password=%3Cscript%3Ealert(1)%3C%2Fscript%3E"),
                   ("/projects/alpha/access", "email=%3Cscript%3Ealert(1)%3C%2Fscript%3E&relation=shared"),
                   ("/projects/alpha/access", "email=a%40b.test&relation=%3Cscript%3Ealert(1)%3C%2Fscript%3E")):
    login_limiter.reset()
    signup_limiter.reset()
    r = C.call("POST", path, HT + URLENC + [("cookie", adm), ("origin", G)], body=body.encode())
    raw = bool(dom_hits(r.text)) or "<script>alert(1)</script>" in r.text or "<img src=x onerror=xss16>" in r.text
    errs.append((path, r.status, raw))
# security headers (info)
r = C.call("GET", "/auth/login", HT)
hdr = {k: r.h(k) for k in ("content-security-policy", "x-frame-options", "x-content-type-options",
                           "referrer-policy", "cache-control", "content-type")}
print(mode, "requests", C.STATE["n"] - n0, "page views", len(checked))
print("pages with DOM-level injection:", len(hits), "; pages escaping seen:", sum(1 for c in checked if c[6]))
for h in hits[:12]:
    print("HIT", h)
print("error/echo POSTs (path, status, raw payload echoed):", errs)
# evidence that escaping is applied: show one admin users snippet
r = C.call("GET", "/admin/users", HT + [("cookie", adm)])
m = re.search(r".{0,40}script.{0,60}", r.text)
print("admin/users snippet:", m.group(0) if m else None)
r = C.call("GET", "/auth/waiting", HT + [("cookie", cookies["nogroup(display-name payload)"])])
m = re.search(r"signed in as.{0,120}", r.text)
print("waiting (display name user) snippet:", m.group(0) if m else None)
r = C.call("GET", "/", HT + [("cookie", cookies["nogroup(display-name payload)"])])
r2 = C.call("GET", "/", HT + [("cookie", cookies.get("payload-email e1", adm))])
m = re.search(r"class='pill' title='signed in'>.{0,80}", r2.text)
print("identity chip (payload email e1):", m.group(0) if m else None)
r = C.call("GET", "/admin/users", HT + [("cookie", adm)])
m = re.search(r"<td>[^<]*(&lt;|alert)[^<]*</td>", r.text)
print("security headers:", hdr)

# detector self-test (must flag a synthetic unescaped payload) and display-name chip on a page the user can see
print("detector self-test:", dom_hits("<p><img src=x onerror=xss2></p><b onmouseover=xss12>x</b><script>alert(1)</script>"))
C.call("POST", f"/admin/users/{ids['dev']}/name", HT + URLENC + [("cookie", adm), ("origin", G)],
       body=("display_name=" + quote(DISPLAY)).encode())
rr = C.call("GET", "/", HT + [("cookie", cookies["dev"])])
m = re.search(r"class='pill' title='signed in'>.{0,60}", rr.text)
print("identity chip (display-name payload on dev):", m.group(0) if m else None, "| DOM hits:", dom_hits(rr.text))
ru = C.call("GET", "/admin/users", HT + [("cookie", adm)])
print("admin/users has escaped payload emails:", "&lt;script&gt;alert(1)&lt;/script&gt;@x.test" in ru.text,
      "| escaped display name:", "&lt;img src=x onerror=xss7&gt;" in ru.text, "| DOM hits:", dom_hits(ru.text))
rg = C.call("GET", "/admin/groups", HT + [("cookie", adm)])
print("admin/groups escaped title:", "&#x27;&gt;&lt;svg onload=xss8&gt;" in rg.text, "| DOM hits:", dom_hits(rg.text))
ra = C.call("GET", "/projects/alpha/access", HT + [("cookie", adm)])
print("access page escaped e1 email:", "&lt;script&gt;alert(1)&lt;/script&gt;@x.test" in ra.text, "| DOM hits:", dom_hits(ra.text))
rw = C.call("GET", "/auth/waiting", HT + [("cookie", C.session_cookie(created["e2"].id if created["e2"] else ids["nogroup"]))])
print("waiting page e2 (groups: Tester, so redirect?) status", rw.status)
rn = C.call("GET", "/auth/waiting", HT + [("cookie", C.session_cookie(created["e5"].id))])
print("waiting page for no-group payload email e5:", rn.status, re.search(r"signed in as.{0,80}", rn.text).group(0) if rn.status == 200 else rn.location)
C.dump("f6", {"signup": {k: v[:2] for k, v in signup.items()}, "hits": hits, "errs": errs,
              "views": len(checked), "headers": hdr})
