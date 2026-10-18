"""Local two-account fixture app for the multi-role session tests (T-210, MP11/MP12).

One stdlib HTTP server answers for several `*.localhost` hosts (Chromium resolves them to
loopback), one per fixture platform. It keeps a real server-side session per sign-in, so a
sign-out in one browser context ends only that context's session, and it serves the link hops
MP12 needs: a plain redirect, an SSO-style meta-refresh hop, a control click, an off-platform
redirect, an off-platform hop in the middle of a redirect chain, and a 404 landing. Test-only:
no real product, no external service; the passwords are synthetic strings.
"""

from __future__ import annotations

import http.cookies
import http.server
import secrets
import threading
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs

from autotester.schema.multi_role_enums import LinkKind
from autotester.schema.platform import Platform
from autotester.schema.platform_link import PlatformLink
from autotester.schema.project import Project, SecretRef
from autotester.schema.role_account import RoleAccount

PARENT_HOST, SCHOOL_HOST, PORTAL_HOST, EVIL_HOST = (
    "a.localhost", "b.localhost", "c.localhost", "evil.localhost")
PASSWORDS = {"alice": "alice-fixture-pw", "bob": "bob-fixture-pw", "carol": "carol-fixture-pw"}


@dataclass
class AppHandle:
    """A running fixture app: its port, its server-side sessions and every request it served."""

    port: int
    server: http.server.ThreadingHTTPServer
    sessions: dict[str, str] = field(default_factory=dict)
    hits: list[tuple[str, str]] = field(default_factory=list)

    def url(self, host: str, path: str = "/") -> str:
        return f"http://{host}:{self.port}{path}"

    def hits_on(self, host: str) -> list[str]:
        return [path for h, path in self.hits if h == host]

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def _handler_for(app: dict) -> type[http.server.BaseHTTPRequestHandler]:
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

        def _host(self) -> str:
            return self.headers.get("Host", "").split(":")[0].lower()

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

        def _redirect(self, location: str, cookie: str | None = None) -> None:
            extra = {"Location": location, **({"Set-Cookie": cookie} if cookie else {})}
            self._send("", 302, extra)

        def _user(self) -> str | None:
            jar = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
            return app["handle"].sessions.get(jar["sid"].value) if "sid" in jar else None

        def do_POST(self) -> None:
            app["handle"].hits.append((self._host(), "POST " + self.path))
            size = int(self.headers.get("Content-Length") or 0)
            form = parse_qs(self.rfile.read(size).decode())
            user, password = form.get("u", [""])[0], form.get("p", [""])[0]
            if PASSWORDS.get(user) != password:
                return self._send("<p id=who>bad login</p>", 401)
            token = secrets.token_hex(8)
            app["handle"].sessions[token] = user
            self._redirect("/me", f"sid={token}; Path=/; HttpOnly")

        def do_GET(self) -> None:
            handle, host = app["handle"], self._host()
            handle.hits.append((host, self.path))
            path, port = self.path.split("?")[0], handle.port
            school, evil = handle.url(SCHOOL_HOST), handle.url(EVIL_HOST)
            routes = {
                "/login": lambda: self._send(
                    "<form method=post action=/login><input id=u name=u><input id=p name=p "
                    "type=password><button id=go>Sign in</button></form>"),
                "/me": self._me,
                "/logout": self._logout,
                "/storage": lambda: self._send(
                    "<p id=stored></p><script>document.getElementById('stored').textContent="
                    "localStorage.getItem('who')||'none'</script>"),
                "/home": lambda: self._send(f"<h1 id=where>landing:{host}:{port}</h1>"),
                "/": lambda: self._send('<a href="/go/redirect">Open school portal</a>'),
                "/go/redirect": lambda: self._redirect(school + "/home"),
                "/go/sso": lambda: self._send(
                    f'<meta http-equiv="refresh" content="0;url={school}/sso/accept?t=1">sso'),
                "/sso/accept": lambda: self._redirect("/home", "sso=1; Path=/"),
                "/go/offsite": lambda: self._redirect(evil + "/phish"),
                "/go/hidden": lambda: self._redirect(school + "/bounce"),
                "/bounce": lambda: self._redirect(evil + "/phish"),
                "/phish": lambda: self._send("<h1>stray host</h1>"),
                "/go/gone": lambda: self._redirect(school + "/nothing-here"),
            }
            if path in routes:
                return routes[path]()
            self._send("<h1>not found</h1>", 404)

        def _me(self) -> None:
            user = self._user()
            script = f"<script>localStorage.setItem('who','{user}')</script>" if user else ""
            self._send(f"<p id=who>{'signed-in-as:' + user if user else 'anonymous'}</p>{script}")

        def _logout(self) -> None:
            jar = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
            if "sid" in jar:
                app["handle"].sessions.pop(jar["sid"].value, None)
            self._redirect("/me", "sid=; Path=/; Max-Age=0")

    return Handler


def start_app() -> AppHandle:
    """Start the app on an ephemeral loopback port; the caller must `stop()` it."""
    app: dict = {}
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _handler_for(app))
    app["handle"] = AppHandle(port=server.server_address[1], server=server)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return app["handle"]


def build_project(app: AppHandle, tmp_path: Path) -> Project:
    """A three-platform project with link hops, plus a `.env` of synthetic values at `tmp_path`."""
    hosts = {"parent": PARENT_HOST, "school": SCHOOL_HOST, "portal": PORTAL_HOST}
    platforms = [Platform(id=pid, name=pid, base_url=app.url(host, "/"), allowed_domains=[host],
                          include_subdomains=False) for pid, host in hosts.items()]
    land = f"{SCHOOL_HOST}:{app.port}"

    def link(trigger: dict, src: str = "parent",
             kind: LinkKind = LinkKind.REDIRECT) -> PlatformLink:
        return PlatformLink(from_platform=src, to_platform="school", kind=kind,
                            expected_landing_host=land, **trigger)

    links = [
        link({"url_template": "/go/redirect"}),
        link({"url_template": "/go/sso"}, kind=LinkKind.SSO),
        link({"control_name": "Open school portal"}, kind=LinkKind.HANDOFF),
        link({"url_template": "/go/offsite"}),
        link({"url_template": "/go/hidden"}),
        link({"url_template": "/go/gone"}),
        link({"url_template": "/go/redirect"}, src="portal"),
    ]
    accounts = [RoleAccount(id=f"{who}-{pid}", role=role, platform_id=pid,
                            username_key=f"{who.upper()}_USER", password_key=f"{who.upper()}_PASS")
                for who, pid, role in (("alice", "parent", "Parent"), ("bob", "parent", "Teacher"),
                                       ("carol", "school", "Principal"))]
    secrets_ = [SecretRef(key=f"{who.upper()}_{kind}", domains=[hosts[pid]])
                for who, pid in (("alice", "parent"), ("bob", "parent"), ("carol", "school"))
                for kind in ("USER", "PASS")]
    (tmp_path / ".env").write_text("".join(
        f"{who.upper()}_USER={who}\n{who.upper()}_PASS={PASSWORDS[who]}\n" for who in PASSWORDS))
    return Project(slug="t210", name="T210", base_url=app.url(PARENT_HOST, "/"), headed=False,
                   allowed_domains=list(hosts.values()), platforms=platforms,
                   platform_links=links, role_accounts=accounts, secrets=secrets_)
