"""Section 2: NAVIGATE destination table through dispatch, per policy. Run once per copy:
<copy>/.venv/Scripts/python -I s2_nav.py <copy-root> <out.json>
Records refused/allowed + class; for HEAD also classifies every READ_ONLY-allowed one as a plain read
with an INDEPENDENT urllib classifier; always records what the REAL BrowserSession.goto of that copy does."""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_lib as L  # noqa: E402

L.confirm_copy(sys.argv[1])
from autotester.schema.enums import Action  # noqa: E402

ZW = "​"
DEST = [
    # scheme case / odd schemes
    "https://app.test/home", "HTTPS://app.test/home", "HtTpS://APP.TEST/home", "http://app.test/home",
    "javascript:alert(1)", "JAVASCRIPT:alert(1)", "data:text/html,hi", "file:///etc/passwd",
    "ftp://app.test/", "view-source:https://app.test/", "blob:https://app.test/x", "about:blank",
    "mailto:a@app.test", "http:app.test", "https:/app.test", "https:///app.test/", "http:\\\\app.test",
    "https://app.test:443/x", "ws://app.test/", "chrome://settings",
    # protocol relative
    "//app.test/x", "//evil.test/x", "///evil.test/x", "//app.test.evil.test/",
    # userinfo / backslash
    "https://app.test@evil.test/", "https://evil.test@app.test/", "https://user:pw@app.test/",
    "https://app.test\\@evil.test/", "https://evil.test\\app.test/", "https://evil.test\\.app.test/",
    # fragments / encodings
    "https://app.test/home#frag", "https://app.test/#/logout", "https://evil.test%2f@app.test/",
    "https://app.test%2eevil.test/", "https://app.test%00.evil.test/", "https://app.test/%0d%0aX",
    "https://app.test/%252flogout", "https://app%2Etest/home", "https://evil.test#@app.test/",
    "https://evil.test?@app.test/", "https://evil.test/@app.test",
    # IDN / punycode / dots / case
    "https://xn--pp-0ka.test/", "https://äpp.test/", "https://аpp.test/", "https://app.test./home",
    "https://APP.TEST/home", "https://app.test../x", "https://.app.test/", "https://app..test/",
    # ports
    "https://app.test:8080/", "https://app.test:99999/", "https://app.test:abc/", "https://app.test:/x",
    "https://app.test:0/",
    # lookalikes / subdomains (suffix match by design)
    "https://evilapp.test/", "https://app.test.evil.com/", "https://app.testx/", "https://xapp.test/",
    "https://app-test/", "https://a.app.test/", "https://a.b.app.test/", "https://evil.test/app.test",
    "https://notapp.test/", "https://app.test.app.test/",
    # control characters / whitespace
    "https://app.test/ho\tme", "https://app.test/home\n", "https://app.test/ho\x00me", "https://app.test/ho\x7fme",
    f"https://app{ZW}.test/", f"https://app.test/ho{ZW}me", " https://app.test/home", "https://app.test/home ",
    "\thttps://app.test/home", "https://app.test/ho me",
    # bare / description / empty
    "/reports", "reports", "./x", "../x", "?q=1", "#frag", "Admin portal URL", "", "   ", "home",
    # placeholders
    "{{SECRET:APP_PASS}}", "https://app.test/?t={{SECRET:APP_PASS}}", "https://{{SECRET:APP_USER}}/",
    "https://app.test/{{SECRET:APP_USER}}", "{{SECRET:NOPE}}", "https://{{SECRET:NOPE}}/",
    # queries
    "https://app.test/home?page=2", "https://app.test/home?id=1&confirm=1", "https://app.test/home?",
    "https://app.test/home?#x", "https://app.test/search?q=logout",
    # paths naming logout / delete etc.
    "https://app.test/logout", "https://app.test/Log-Out", "https://app.test/log_out", "https://app.test/sign-out",
    "https://app.test/signout", "https://app.test/LOGOUT", "https://app.test/log%6Fut", "https://app.test/log%256Fut",
    "https://app.test/account/delete", "https://app.test/account/Delete/", "https://app.test/api/close-account",
    "https://app.test/delete-account", "https://app.test/users/1/destroy", "https://app.test/remove/1",
    "https://app.test/pay", "https://app.test/send", "https://app.test/x;jsessionid=1/logout",
    "https://app.test/हटाएं", "https://app.test/删除", "https://app.test/home/%E5%88%A0%E9%99%A4",
    "https://app.test/users/1/deactivate", "https://app.test/cancel-subscription", "https://app.test/api/v1/orders/submit",
]


def plain_read(url: str) -> tuple[bool, str]:
    """INDEPENDENT classifier: a plain in-domain read per WHATWG-ish rules."""
    s = url.strip()
    if re.search(r"[\x00-\x1f\x7f]", url):
        return False, "control char"
    if "\\" in s:
        return False, "backslash"
    try:
        p = urlsplit(s)
    except ValueError:
        return False, "unparseable"
    if p.scheme.lower() not in ("http", "https"):
        return False, f"scheme {p.scheme!r}"
    if p.username is not None or p.password is not None:
        return False, "userinfo"
    host = (p.hostname or "").lower()
    if not (host == "app.test" or host.endswith(".app.test")):
        return False, f"host {host!r}"
    if p.query or "?" in s:
        return False, "query"
    if "{{" in s:
        return False, "placeholder"
    low = unquote(p.path + " " + p.fragment).lower()
    if re.search(r"log[\W_]*out|sign[\W_]*out|delete|remove|destroy|\bpay|\bsend", low):
        return False, "deny word in path"
    return True, "ok"


rows = []
for pol in L.POLICIES:
    for dest in DEST:
        env = L.make_env(pol, [[L.step(1, Action.NAVIGATE, dest)]])
        r = L.run_case_row(env)
        g = L.goto_would_refuse(env.ctx.project, env.ctx.secrets, dest) if dest else "NavigationRefused"
        pr, why = plain_read(dest)
        rows.append({"policy": pol.value, "dest": L.label(dest), "executed": r["executed"], "refusal": r["refusal"],
                     "sessions": r["sessions"], "run_case_calls": r["run_case_calls"], "files": r["n_files_written"],
                     "raised": r["raised"], "goto": g, "plain_read": pr, "plain_why": why})
L.dump(sys.argv[2], rows)
print("rows", len(rows), "destinations", len(DEST))
