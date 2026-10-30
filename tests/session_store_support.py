"""mongo-store U12 test rig: planted canaries, fake browser contexts, a role session double.
Every value is synthetic; `sample()` mixes in-scope and out-of-scope cookies and origins.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar

from credential_store_support import CredRig

from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.platform import Platform
from autotester.schema.project import Project
from autotester.schema.role_account import RoleAccount

SID = "Zk9-session-canary-A1"
TOK = "Zk9-local-token-canary-B2"
BLOB_LEAF = "Zk9-json-leaf-canary-C3"
EVIL = "Zk9-evil-cookie-canary-D4"
PARENT = "Zk9-parent-domain-canary-E5"
NOW = time.time()  # cookies live an hour past import; the real clock runs a few seconds
PROJECT = Project(slug="pl", name="pl", base_url="https://app.pl.test",
                  allowed_domains=["app.pl.test"],
                  platforms=[Platform(id="web", name="web", base_url="https://app.pl.test/",
                                      allowed_domains=["app.pl.test"], include_subdomains=False)],
                  role_accounts=[RoleAccount(id=a, role=a, platform_id="web",
                                             username_key=f"{a.upper()}_U",
                                             password_key=f"{a.upper()}_P") for a in ("t1", "t2")])


def cookie(name: str, value: str, domain: str = "app.pl.test",
           expires: float = NOW + 3600) -> dict:
    return {"name": name, "value": value, "domain": domain, "path": "/", "expires": expires,
            "httpOnly": True, "secure": True, "sameSite": "Lax"}


def sample() -> dict[str, Any]:
    return {"cookies": [cookie("sid", SID), cookie("e", EVIL, "evil.example"),
                        cookie("par", PARENT, ".pl.test"), cookie("lang", "en", ".app.pl.test")],
            "origins": [
                {"origin": "https://app.pl.test", "localStorage": [
                    {"name": "tok", "value": TOK}, {"name": "n", "value": "1"},
                    {"name": "blob", "value": json.dumps({"a": {"jwt": BLOB_LEAF}, "x": 1})}]},
                {"origin": "https://evil.example", "localStorage": [{"name": "t", "value": EVIL}]}]}


class Ctx:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state, self.cookies, self.scripts = state, [], []

    def storage_state(self, **kw: Any) -> dict[str, Any]:
        assert "path" not in kw, "storage_state must stay in memory"
        return json.loads(json.dumps(self.state))

    def add_cookies(self, cookies: list) -> None:
        self.cookies += cookies

    def add_init_script(self, script: str) -> None:
        self.scripts.append(script)


def make_session(root: Path, slug: str = "pl-role-t1",
                 state: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(_context=Ctx(state or sample()), paths=ProjectPaths(slug, root),
                           secrets=SecretStore(PROJECT, {}))


def docs(rig: CredRig) -> list[dict]:
    return rig.collection("browser_sessions")


def elsewhere(rig: CredRig) -> str:
    """Everything the fake server holds outside `browser_sessions`."""
    return repr([(n, c.docs) for db in rig.server.databases.values()
                 for n, c in db.collections.items() if n != "browser_sessions"])


class RoleFake:
    """A role session that logs in by setting its context's state when `click` is called."""
    made: ClassVar[dict[str, RoleFake]] = {}

    def __init__(self, project, secrets, run_dir, paths=None, **_kw) -> None:
        self.paths, self.secrets, self.state = paths, secrets, SimpleNamespace(evidence_prefix="")
        self._context = Ctx({"cookies": [], "origins": []})
        RoleFake.made[paths.slug] = self

    def start(self) -> RoleFake:
        return self

    def close(self) -> None:
        return None

    def goto(self, url: str) -> None:
        return None

    def fill(self, *_a: Any, **_kw: Any) -> None:
        return None

    def settle(self, *_a: Any, **_kw: Any) -> None:
        return None

    def click(self, *_a: Any, **_kw: Any) -> None:
        self._context.state = sample()
