"""Local two-account fixture app for the live role port (G11 integration, PW1..PW4).

One stdlib HTTP server on `a.localhost` with a real server-side session per sign-in and one page
per oracle, each carrying exactly one planted fault (synthetic data only, MPI2; no real product):

  /home       copy: a misspelt brand, a forbidden string and a UTC timestamp; a canary email and
              phone number (another person's data) and, for alice, her password echoed on the page
  /dashboard  shows "Saved" while POST /api/save answers 500, then pings /api/ping 25 times
              40 ms apart (a hidden API error, over the request budget, polling too fast)
  /settings   a form whose `title` max length (10) is enforced for alice and not for bob
  /orders     a counter and an Add button; with `persist` off the server forgets the add
  /reports    a 900 px wide block and a control 700 px from the left edge (overflows at 390 px)

and, for the authorisation probes (g11-oracle-wiring), JSON and one role-assign control:
  /api/rows         alice's list also holds bob's row b1 (a planted cross-tenant leak); bob's is
                    clean
  /api/rows/<id>    one row by id, any id, for any signed-in role (the id swap succeeds)
  /api/admin/users  answers alice 200 (a planted privilege hole); /api/admin/audit refuses her 403
  /assign           alice may press #make-admin (role becomes admin, `#now-admin`) and #undo-admin
  /assign-locked    no control for alice; /go-away redirects to another host; /api/expire?u=NAME
                    ends that user's server-side sessions (a logged-out role)
"""

from __future__ import annotations

import http.cookies
import http.server
import json
import secrets
import threading
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs

from autotester.schema.platform import Platform
from autotester.schema.project import Project, SecretRef
from autotester.schema.role_account import RoleAccount

HOST = "a.localhost"
PASSWORDS = {"alice": "alice-port-pw", "bob": "bob-port-pw"}
PII_EMAIL, PII_PHONE = "canary.person@example.org", "+1 415 555 0142"
ACCOUNTS = {"alice": "alice-app", "bob": "bob-app"}
_NAV = ("<a href=/home>h</a> <a href=/dashboard>d</a> <a href=/settings>s</a> "
        "<a href=/orders>o</a> <a href=/reports>r</a>")


@dataclass
class PortApp:
    """A running app: its port, sessions, the order count and the `persist` fault switch."""

    port: int
    server: http.server.ThreadingHTTPServer
    sessions: dict[str, str] = field(default_factory=dict)
    orders: int = 0
    persist: bool = True
    roles: dict[str, str] = field(default_factory=lambda: {"alice": "user", "bob": "admin"})
    reads: list[str] = field(default_factory=list)
    offsite_hits: int = 0

    def url(self, path: str = "/") -> str:
        return f"http://{HOST}:{self.port}{path}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def _pages(user: str) -> dict[str, str]:
    debug = f"debug pw={PASSWORDS[user]}" if user == "alice" else "debug off"
    return {
        "/home": (f"<h1>Welcome</h1><span id=signed>signed in</span> "
                  f"<span id=who>user:{user}</span>"
                  "<p id=copy>Welcome to the Vidysia portal. lorem ipsum dolor. "
                  "Updated 10:30 UTC.</p>"
                  f"<p id=contact>Contact: {PII_EMAIL} or {PII_PHONE}</p><p id=debug>{debug}</p>"
                  + _NAV),
        "/dashboard": (
            "<h1>Dashboard</h1><p id=ok>Saved</p><script>fetch('/api/save',{method:'POST'});"
            "for(let i=0;i<25;i++)setTimeout(()=>fetch('/api/ping'),i*40);</script>"),
        "/settings": ("<h1>Settings</h1><form method=post action=/settings><input name=title "
                      "id=title><button id=submit>Save</button></form>"),
        "/reports": ("<h1>Reports</h1><div style='width:900px;background:#ddd'>wide table</div>"
                     "<button id=far style='margin-left:700px'>Far</button>"),
    }


ROWS = {"a1": "ZZNAME-alice-1", "a2": "ZZNAME-alice-2", "b1": "ZZNAME-bob-1"}
_ASSIGN = ("<h1>Team</h1><span id=role>{role}</span><button id=make-admin>Make admin</button>"
           "<button id=undo-admin>Undo</button><script>const say=(id)=>{{const e="
           "document.createElement('span');e.id=id;e.textContent=id;document.body.append(e)}};"
           "document.getElementById('make-admin').onclick=()=>fetch('/api/role?set=admin',"
           "{{method:'POST'}}).then(()=>say('now-admin'));"
           "document.getElementById('undo-admin').onclick=()=>fetch('/api/role?set=user',"
           "{{method:'POST'}}).then(()=>say('now-user'))</script>")


def _json(rows: object) -> str:
    return json.dumps(rows)


def _handler_for(app: dict) -> type[http.server.BaseHTTPRequestHandler]:
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

        def _send(self, body: str, status: int = 200, headers: dict | None = None) -> None:
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def _user(self) -> str | None:
            jar = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
            return app["handle"].sessions.get(jar["sid"].value) if "sid" in jar else None

        def _form(self) -> dict[str, list[str]]:
            size = int(self.headers.get("Content-Length") or 0)
            return parse_qs(self.rfile.read(size).decode("utf-8"), keep_blank_values=True)

        def do_POST(self) -> None:
            handle, path, user = app["handle"], self.path.split("?")[0], self._user()
            form = self._form()
            if path == "/login":
                name, pw = form.get("u", [""])[0], form.get("p", [""])[0]
                if PASSWORDS.get(name) != pw:
                    return self._send("<p id=bad>bad login</p>", 401)
                token = secrets.token_hex(8)
                handle.sessions[token] = name
                return self._send("", 302, {"Location": "/home",
                                            "Set-Cookie": f"sid={token}; Path=/; HttpOnly"})
            if path == "/api/role" and user:
                handle.roles[user] = parse_qs(self.path.partition("?")[2]).get("set", ["user"])[0]
                return self._send("{}")
            if path == "/api/save":
                return self._send("error", 500)
            if path == "/api/orders":
                handle.orders += 1 if handle.persist else 0
                return self._send("{}")
            if path == "/settings" and user:
                title = form.get("title", [""])[0]
                if not title or (user == "alice" and len(title) > 10):
                    return self._send("<p id=err>rejected</p>", 422)
                return self._send("<p id=saved>saved</p>")
            self._send("<h1>not found</h1>", 404)

        def _api(self, user: str, path: str) -> None:
            rows = [{"id": i, "name": n} for i, n in ROWS.items()
                    if i.startswith(user[0]) or (user == "alice" and i == "b1")]
            if path == "/api/rows":
                return self._send(_json({"results": rows}))
            if path.startswith("/api/rows/"):
                row = ROWS.get(path.rsplit("/", 1)[1])
                body = _json({"id": path.rsplit("/", 1)[1], "name": row})
                return self._send(body, 200 if row else 404)
            if path == "/api/admin/users":
                return self._send(_json([{"id": "u1", "name": "ZZNAME-admin"}]))
            self._send(_json({}), 403)

        def do_GET(self) -> None:
            handle, path, user = app["handle"], self.path.split("?")[0], self._user()
            if path == "/login":
                return self._send("<form method=post action=/login><input id=u name=u>"
                                  "<input id=p name=p type=password>"
                                  "<button id=go>Go</button></form>")
            if path == "/api/ping":
                return self._send("{}")
            if path == "/api/expire":
                gone = parse_qs(self.path.partition("?")[2]).get("u", [""])[0]
                handle.sessions = {k: v for k, v in handle.sessions.items() if v != gone}
                return self._send("{}")
            if not self.headers.get("Host", "").startswith(HOST):  # left the platform
                handle.offsite_hits += 1
                return self._send("{}")
            if user is None:
                return self._send("", 302, {"Location": "/login"})
            if path == "/orders":
                return self._send(
                    f"<h1>Orders</h1><span id=count>{handle.orders}</span>"
                    "<button id=add>Add</button>"
                    "<script>document.getElementById('add').onclick=()=>fetch('/api/orders',"
                    "{method:'POST'}).then(()=>{const c=document.getElementById('count');"
                    "c.textContent=String(+c.textContent+1)})</script>")
            if path.startswith("/api/"):
                handle.reads.append(f"{user}:{path}")
                return self._api(user, path)
            if path == "/assign" and user == "alice":
                return self._send(_ASSIGN.format(role=handle.roles[user]))
            if path == "/assign-locked":
                return self._send("<h1>Team</h1><p>Admins only.</p>")
            if path == "/go-away":
                return self._send("", 302, {"Location": f"http://127.0.0.1:{handle.port}/x"})
            page = _pages(user).get(path)
            self._send(page, 200) if page else self._send("<h1>not found</h1>", 404)

    return Handler


def start_app() -> PortApp:
    """Start the app on an ephemeral loopback port; the caller must `stop()` it."""
    app: dict = {}
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _handler_for(app))
    app["handle"] = PortApp(port=server.server_address[1], server=server)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return app["handle"]


def build_project(app: PortApp, tmp_path: Path, *, bob_password: str | None = None) -> Project:
    """One platform, two accounts (alice, bob) and a `.env` of synthetic values at `tmp_path`.

    `bob_password` overrides the value written to `.env` (a wrong one makes bob's sign-in fail)."""
    platform = Platform(id="app", name="app", base_url=app.url("/"), allowed_domains=[HOST],
                        include_subdomains=False)
    accounts = [RoleAccount(id=rid, role=who.title(), platform_id="app",
                            username_key=f"{who.upper()}_USER", password_key=f"{who.upper()}_PASS")
                for who, rid in ACCOUNTS.items()]
    refs = [SecretRef(key=f"{who.upper()}_{kind}", domains=[HOST])
            for who in ACCOUNTS for kind in ("USER", "PASS")]
    passwords = {**PASSWORDS, **({"bob": bob_password} if bob_password else {})}
    (tmp_path / ".env").write_text("".join(
        f"{who.upper()}_USER={who}\n{who.upper()}_PASS={passwords[who]}\n" for who in ACCOUNTS))
    return Project(slug="g11port", name="G11 port", base_url=app.url("/"), headed=False,
                   allowed_domains=[HOST], platforms=[platform], role_accounts=accounts,
                   secrets=refs)
