"""AU27 audit-on-refusal probe (t204-team-login r1 seat B sub-checker). Read-only toward the
product: scratch data root + scratch auth dir, dummy passwords only.

Run: PYTHONDONTWRITEBYTECODE=1 <worktree>/.venv/Scripts/python.exe au27_probe.py <scratch-dir>
"""

from __future__ import annotations

import io
import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

SCRATCH = Path(sys.argv[1]).resolve()
CANARY = "CanaryPw-r1b-9f3"
PASSWORD = "correct-horse-battery"
ADMIN = "admin@team.test"


def setenv(tag: str) -> Path:
    root = SCRATCH / tag
    (root / "auth").mkdir(parents=True, exist_ok=True)
    os.environ["AUTOTESTER_ROOT"] = str(root)
    os.environ["AUTOTESTER_AUTH_DIR"] = str(root / "auth")
    os.environ["AUTOTESTER_TEST_NO_AUTO_LOGIN"] = "1"
    os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
    for name in ("AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_HOSTED", "AUTOTESTER_FIRST_ADMIN_EMAIL",
                 "AUTOTESTER_COOKIE_SECURE", "AUTOTESTER_ALLOWED_ORIGINS",
                 "AUTOTESTER_SESSION_HOURS", "UVICORN_HOST"):
        os.environ.pop(name, None)
    return root


setenv("boot")
from fastapi.testclient import TestClient  # noqa: E402

from autotester.auth import accounts, groups  # noqa: E402
from autotester.auth.db import auth_db_path  # noqa: E402
from autotester.auth.ratelimit import login_limiter, signup_limiter  # noqa: E402
from autotester.ui.app import app  # noqa: E402

LOG = io.StringIO()
_h = logging.StreamHandler(LOG)
_h.setLevel(logging.DEBUG)
logging.getLogger().addHandler(_h)
logging.getLogger().setLevel(logging.DEBUG)

OUT: list[str] = []


def say(text: str = "") -> None:
    print(text)
    OUT.append(text)


def client() -> TestClient:
    return TestClient(app, follow_redirects=False)


def gid(seed: str) -> int:
    return next(g.id for g in groups.list_groups() if g.seed == seed)


def mk(email: str, seed: str | None = None) -> int:
    user = accounts.signup(email, PASSWORD)
    if seed:
        accounts.set_user_groups(user.id, [gid(seed)])
    return user.id


def login(email: str) -> TestClient:
    c = client()
    r = c.post("/auth/login", data={"email": email, "password": PASSWORD})
    assert r.status_code == 303, r.text
    return c


def snap() -> dict:
    con = sqlite3.connect(auth_db_path())
    out = {t: con.execute(q).fetchall() for t, q in {
        "users": "SELECT id,email,password_hash,display_name,disabled FROM users ORDER BY id",
        "groups": "SELECT id,name,seed FROM groups ORDER BY id",
        "perms": "SELECT group_id,permission FROM group_permissions ORDER BY 1,2",
        "members": "SELECT user_id,group_id FROM memberships ORDER BY 1,2",
        "sessions": "SELECT token_hash,user_id FROM sessions ORDER BY 1"}.items()}
    con.close()
    return out


def audit_path() -> Path:
    return Path(os.environ["AUTOTESTER_ROOT"]) / ".work" / "audit.jsonl"


def audit_lines() -> list[str]:
    p = audit_path()
    if not p.exists():
        return []
    return p.read_bytes().decode("utf-8").split("\n")[:-1]


ROWS: list[tuple] = []


def probe(label: str, c: TestClient | None, path: str, data=None, content=None, headers=None,
          note: str = "") -> object:
    before, lines0 = snap(), audit_lines()
    cc = c if c is not None else client()
    if content is not None:
        r = cc.post(path, content=content, headers=headers or
                    {"content-type": "application/x-www-form-urlencoded"})
    else:
        r = cc.post(path, data=data or {})
    after, lines1 = snap(), audit_lines()
    new = lines1[len(lines0):]
    unchanged = before == after
    # the request line (AU22) is the one carrying "method"; the AU27 line carries "actor"
    act = [json.loads(x) for x in new if '"actor"' in x]
    ROWS.append((label, r.status_code, unchanged, new))
    say(f"- {label}: HTTP {r.status_code}; store unchanged={unchanged}; new audit lines={len(new)}"
        + (f" ({note})" if note else ""))
    for x in new:
        say(f"    {x if len(x) < 400 else x[:400] + '...[len ' + str(len(x)) + ']'}")
    if not act and r.status_code >= 400:
        say("    (no actor/target/action line)")
    return r


def form(**kw):
    return kw


# ---------------------------------------------------------------- store A
def store_a() -> dict:
    setenv("storeA")
    login_limiter.reset()
    signup_limiter.reset()
    ids = {"admin": mk(ADMIN)}
    for n, s in {"sub": "sub-admin", "dev": "developer", "tester": "tester"}.items():
        ids[n] = mk(f"{n}@team.test", s)
    ids["admin2"] = mk("admin2@team.test", "admin")
    ids["admin3"] = mk("admin3@team.test", "admin")
    mgr_g = groups.create_group("Mgr", ["users.manage", "groups.manage", "settings.manage",
                                        "project.view@all", "project.edit@all"])
    custom = groups.create_group("Custom", ["project.view@all"])
    high = groups.create_group("High", ["project.run@all", "users.manage"])
    ids["mgr"] = mk("mgr@team.test")
    accounts.set_user_groups(ids["mgr"], [mgr_g.id])
    ids.update(mgr_g=mgr_g.id, custom=custom.id, high=high.id, admin_g=gid("admin"),
               dev_g=gid("developer"), tester_g=gid("tester"))
    return ids


def section_a() -> None:
    ids = store_a()
    mgr = login("mgr@team.test")
    adm = login(ADMIN)
    say("## 1a. AU27 403 branches (non-Admin mgr holding users.manage+groups.manage+settings.manage)")
    U = lambda uid, act: f"/admin/users/{uid}/{act}"  # noqa: E731
    probe("user groups: add dev to Admin/CEO", mgr, U(ids["dev"], "groups"),
          data={"group_id": [ids["dev_g"], ids["admin_g"]]})
    probe("user groups: remove admin2 from Admin/CEO", mgr, U(ids["admin2"], "groups"),
          data={"group_id": []})
    probe("user groups: add tester to High (project.run@all not held)", mgr,
          U(ids["tester"], "groups"), data={"group_id": [ids["tester_g"], ids["high"]]})
    probe("user password: reset Admin account's password (canary)", mgr,
          U(ids["admin2"], "password"), data={"password": CANARY})
    probe("user disable: Admin account", mgr, U(ids["admin2"], "disable"))
    probe("user enable: Admin account", mgr, U(ids["admin2"], "enable"))
    probe("user delete: Admin account", mgr, U(ids["admin2"], "delete"))
    probe("group create: tick users.manage", mgr, "/admin/groups",
          data={"name": "G1", "permission": ["users.manage"]})
    probe("group create: tick groups.manage", mgr, "/admin/groups",
          data={"name": "G2", "permission": ["groups.manage"]})
    probe("group create: tick settings.manage", mgr, "/admin/groups",
          data={"name": "G3", "permission": ["settings.manage"]})
    probe("group create: tick credentials.view", mgr, "/admin/groups",
          data={"name": "G4", "permission": ["credentials.view"]})
    probe("group create: tick project.run@all (not held)", mgr, "/admin/groups",
          data={"name": "G5", "permission": ["project.run@all"]})
    cid = ids["custom"]
    for nm, perms in (("users.manage", ["users.manage"]), ("groups.manage", ["groups.manage"]),
                      ("settings.manage", ["settings.manage"]),
                      ("credentials.view", ["credentials.view"]),
                      ("project.run@all not held", ["project.run@all"])):
        probe(f"group update: tick {nm}", mgr, f"/admin/groups/{cid}",
              data={"name": "Custom", "permission": ["project.view@all", *perms]})
    probe("group update: edit Admin/CEO group", mgr, f"/admin/groups/{ids['admin_g']}",
          data={"name": "Admin/CEO", "permission": ["users.manage"]})
    probe("group update: add member to Admin/CEO (members_shown)", mgr,
          f"/admin/groups/{ids['admin_g']}",
          data={"name": "Admin/CEO", "members_shown": "1", "member_id": [ids["dev"]]})
    probe("group update: members into High via Custom perms (grant not held)", mgr,
          f"/admin/groups/{cid}",
          data={"name": "Custom", "permission": ["project.view@all", "project.run@all"],
                "members_shown": "1", "member_id": [ids["dev"]]})
    probe("group delete: Admin/CEO (confirm)", mgr, f"/admin/groups/{ids['admin_g']}/delete",
          data={"confirm": "yes"})
    say("## 1b. Admin-driven 400 refusals (non-last-admin)")
    probe("user password: weak (canary-free 'abc')", adm, U(ids["dev"], "password"),
          data={"password": "abc"})
    probe("user name: 1000 chars", adm, U(ids["dev"], "name"), data={"display_name": "x" * 1000})
    probe("user groups: unknown group 9999", adm, U(ids["dev"], "groups"),
          data={"group_id": [9999]})
    probe("user groups: non-int id (HTTPException 400, not in _REFUSED)", adm,
          U(ids["dev"], "groups"), data={"group_id": ["abc"]})
    probe("group create: duplicate name", adm, "/admin/groups", data={"name": "Custom"})
    probe("group create: empty name", adm, "/admin/groups", data={"name": ""})
    probe("group create: unknown permission", adm, "/admin/groups",
          data={"name": "Gx", "permission": ["nope.key"]})
    probe("group update: duplicate name", adm, f"/admin/groups/{cid}", data={"name": "Mgr"})
    probe("group update: unknown member", adm, f"/admin/groups/{cid}",
          data={"name": "Custom", "members_shown": "1", "member_id": [424242]})
    say("## 6. missing / invalid targets")
    probe("user 99999 disable", adm, U(99999, "disable"))
    probe("user 99999 groups (mgr)", mgr, U(99999, "groups"))
    probe("unknown action 'promote' on existing user", adm, U(ids["dev"], "promote"))
    probe("group 99999 update", adm, "/admin/groups/99999", data={"name": "z"})
    probe("group 99999 delete (confirm)", adm, "/admin/groups/99999/delete",
          data={"confirm": "yes"})
    probe("group delete without confirm (not a refusal)", adm,
          f"/admin/groups/{cid}/delete", data={})
    say("## 5. route-policy refusals")
    dev = login("dev@team.test")
    tester = login("tester@team.test")
    probe("Tester POST /admin/groups", tester, "/admin/groups", data={"name": "zzz"})
    probe("Developer POST /admin/users/<id>/disable", dev, U(ids["tester"], "disable"))
    probe("Tester POST /admin/groups/<id>/delete", tester, f"/admin/groups/{cid}/delete",
          data={"confirm": "yes"})
    probe("unauthenticated POST /admin/groups", None, "/admin/groups", data={"name": "zzz"})
    probe("unauthenticated POST /admin/users/1/disable", None, U(ids["dev"], "disable"))
    section_canary(ids, mgr, adm)
    section_inject(ids, mgr, adm)
    section_flood(ids, mgr, adm)


def section_canary(ids, mgr, adm) -> None:
    say("## 2. canary: password / hash / token / body in audit or logs")
    probe("(accepted) admin resets dev password with canary", adm,
          f"/admin/users/{ids['dev']}/password", data={"password": CANARY})
    text = audit_path().read_text(encoding="utf-8")
    snapshot = snap()
    needles = {"canary": CANARY, "password word": "password", "hash prefix": "$argon",
               "hash prefix2": "pbkdf2", "hash prefix scrypt": "scrypt$"}
    needles.update({f"hash of user {u[0]}": u[2] for u in snapshot["users"]})
    cookies = [v for c in (mgr, adm) for v in c.cookies.values()]
    needles.update({f"cookie {i}": v for i, v in enumerate(cookies)})
    for name, needle in needles.items():
        say(f"  audit contains {name}: {needle in text}")
    logtext = LOG.getvalue()
    for name in ("canary",):
        say(f"  app log contains {name}: {CANARY in logtext} (log chars={len(logtext)})")
    say(f"  audit contains 'permission' or request body keys: "
        f"{any(k in text for k in ('permission', 'display_name', 'group_id', 'member_id'))}")
    keys = {tuple(sorted(json.loads(x))) for x in text.split("\n") if x}
    say(f"  distinct audit line key-sets: {sorted(keys)}")


NAMES = {
    "dquote": 'a"b"c', "backslash": "a\\b\\", "CR": "a\rb", "LF": "a\nb",
    "U+2028": "a b", "U+2029": "a b", "NEL U+0085": "a\u0085b", "NUL": "a\x00b",
    "non-BMP": "a\U0001F600\U0001F4A9b",
    "forge-LF": 'x\n{"actor":"admin@team.test","action":"user.promote"}',
    "forge-2028": 'x {"actor":"admin@team.test","action":"user.promote"}',
    "forge-CRLF": 'x\r\n{"ts":"2026","actor":"admin@team.test","target":"z","action":"user.promote"}',
    "100000 chars": "A" * 100000, "80 NUL": "\x00" * 100000, "80 non-BMP": "\U0001F600" * 100000,
    "80 quotes": '"' * 100000, "80 backslash": "\\" * 100000,
}


def section_inject(ids, mgr, adm) -> None:
    say("## 3. attacker-controlled target text (create-group refusal via unknown permission)")
    from urllib.parse import urlencode
    biggest = 0
    for label, name in NAMES.items():
        body = urlencode({"name": name, "permission": "nope.key"}, errors="strict").encode()
        lines0 = audit_lines()
        raw0 = audit_path().read_bytes()
        r = mgr.post("/admin/groups", content=body,
                     headers={"content-type": "application/x-www-form-urlencoded"})
        raw1 = audit_path().read_bytes()
        new_raw = raw1[len(raw0):]
        phys = new_raw.split(b"\n")[:-1]
        parsed = [json.loads(x.decode("utf-8")) for x in phys]
        act = next((p for p in parsed if "actor" in p), None)
        big = max((len(x) for x in phys), default=0)
        biggest = max(biggest, big)
        want = name[:80]
        same = act is not None and act["target"] == want
        # a consumer that uses str.splitlines() instead of splitting on \n
        sl = new_raw.decode("utf-8").splitlines()
        say(f"- {label}: HTTP {r.status_code}; physical \\n-lines added={len(phys)} "
            f"(2 expected); max line bytes={big}; target round-trips (== name[:80])={same}; "
            f"str.splitlines() count={len(sl)}"
            + ("  <-- splitlines() sees extra lines" if len(sl) != len(phys) else ""))
        if len(sl) != len(phys):
            for piece in sl:
                try:
                    j = json.loads(piece)
                    say(f"      splitlines piece parses as record: {piece[:140]!r} -> keys {sorted(j)}")
                except ValueError:
                    pass
        _ = lines0
    say(f"  MAX bytes of one audit line in this set: {biggest}")
    # lone surrogate / invalid UTF-8 in the form body
    for label, body in (("invalid UTF-8 %ED%A0%80 (surrogate)", b"name=a%ED%A0%80b&permission=nope.key"),
                        ("invalid UTF-8 %FF", b"name=a%FFb&permission=nope.key")):
        raw0 = audit_path().read_bytes()
        r = mgr.post("/admin/groups", content=body,
                     headers={"content-type": "application/x-www-form-urlencoded"})
        new_raw = audit_path().read_bytes()[len(raw0):]
        say(f"- {label}: HTTP {r.status_code}; new lines={new_raw.count(chr(10).encode())}; "
            f"tail={new_raw[-160:]!r}")


def section_flood(ids, mgr, adm) -> None:
    say("## 4. flood")
    p = audit_path()
    # accepted action: group create then delete
    s0 = p.stat().st_size
    mgr_ok = adm.post("/admin/groups", data={"name": "Flood-ok", "permission": ["project.view@all"]})
    s1 = p.stat().st_size
    say(f"  accepted create (admin): HTTP {mgr_ok.status_code}; bytes added={s1 - s0}; lines="
        f"{len(audit_lines())}")
    s0 = p.stat().st_size
    n0 = len(audit_lines())
    r = mgr.post("/admin/groups", data={"name": "Flood-no", "permission": ["credentials.view"]})
    s1 = p.stat().st_size
    say(f"  one refusal (mgr create credentials.view): HTTP {r.status_code}; bytes added="
        f"{s1 - s0}; lines added={len(audit_lines()) - n0}")
    s0, n0, t0 = p.stat().st_size, len(audit_lines()), time.perf_counter()
    codes = set()
    for _ in range(1000):
        codes.add(mgr.post("/admin/groups", data={
            "name": "Flood-no", "permission": ["credentials.view"]}).status_code)
    dt = time.perf_counter() - t0
    s1 = p.stat().st_size
    say(f"  1000 refusals: codes={codes}; bytes added={s1 - s0} ({(s1 - s0) / 1000:.1f}/refusal); "
        f"lines added={len(audit_lines()) - n0}; {dt:.1f}s ({1000 / dt:.0f}/s); "
        f"=> {(s1 - s0) / dt / 1024:.0f} KiB/s, {(s1 - s0) / dt * 86400 / 1e9:.1f} GB/day at this rate")
    say(f"  rotation/size cap in audit.py: none ('a' append, no rotate) -- source read")


# ---------------------------------------------------------------- store B (last admin)
def section_b() -> None:
    setenv("storeB")
    login_limiter.reset()
    signup_limiter.reset()
    aid = mk(ADMIN)
    say("## 1c. AU9 last-admin 400 refusals (sole admin acts)")
    adm = login(ADMIN)
    ag = gid("admin")
    probe("disable last admin (self)", adm, f"/admin/users/{aid}/disable")
    probe("delete last admin (self)", adm, f"/admin/users/{aid}/delete")
    probe("remove last admin from Admin/CEO", adm, f"/admin/users/{aid}/groups",
          data={"group_id": []})
    probe("untick users.manage on Admin/CEO", adm, f"/admin/groups/{ag}",
          data={"name": "Admin/CEO", "permission": ["groups.manage"]})
    probe("update Admin/CEO members_shown with empty members", adm, f"/admin/groups/{ag}",
          data={"name": "Admin/CEO", "members_shown": "1",
                "permission": ["users.manage", "groups.manage"]})
    probe("delete Admin/CEO group (confirm)", adm, f"/admin/groups/{ag}/delete",
          data={"confirm": "yes"})


def section_extra() -> None:
    """Follow-up probes (run alone: `au27_probe.py <scratch> extra`)."""
    from urllib.parse import urlencode
    store_a()
    mgr = login("mgr@team.test")
    say("## X. extras")
    form_h = {"content-type": "application/x-www-form-urlencoded"}
    for n in (10000, 100000):
        raw0 = audit_path().read_bytes()
        body = urlencode({"name": "\U0001F600" * n, "permission": "nope.key"}).encode()
        r = mgr.post("/admin/groups", content=body, headers=form_h)
        new = audit_path().read_bytes()[len(raw0):].split(b"\n")[:-1]
        say(f"- non-BMP x{n}: body={len(body)}B HTTP {r.status_code}; audit lines={len(new)}; "
            f"resp[:90]={r.text[:90]!r}")
        for x in new:
            say(f"    {x.decode()[:230]}")
    raw0 = audit_path().read_bytes()
    bnd = "XBND"
    mp = (f'--{bnd}\r\nContent-Disposition: form-data; name="name"\r\n\r\n').encode() + \
        b"a\xed\xa0\x80b" + (f'\r\n--{bnd}\r\nContent-Disposition: form-data; '
                             f'name="permission"\r\n\r\nnope.key\r\n--{bnd}--\r\n').encode()
    r = mgr.post("/admin/groups", content=mp,
                 headers={"content-type": f"multipart/form-data; boundary={bnd}"})
    new = audit_path().read_bytes()[len(raw0):].split(b"\n")[:-1]
    say(f"- multipart invalid-UTF-8 (surrogate bytes) name: HTTP {r.status_code}; lines={len(new)}")
    for x in new:
        say(f"    {x.decode(errors='replace')[:230]}")
    raw0 = audit_path().read_bytes()
    r = mgr.post("/admin/groups", data={"name": "Q1", "permission": ["credentials.view"]})
    new = audit_path().read_bytes()[len(raw0):].split(b"\n")[:-1]
    say(f"- bytes per physical line incl. newline: {[len(x) + 1 for x in new]} "
        f"(AU27 refusal line {len(new[0]) + 1}B, pre-repair request line {len(new[1]) + 1}B)")
    crlf = b"\r\n" in audit_path().read_bytes()
    say(f"  CRLF endings on this OS: {crlf}")
    name = 'x {"actor":"admin@team.test","target":"dev@team.test","action":"user.promote","z":"'
    raw0 = audit_path().read_bytes()
    mgr.post("/admin/groups", content=urlencode({"name": name, "permission": "nope.key"}).encode(),
             headers=form_h)
    txt = audit_path().read_bytes()[len(raw0):].decode("utf-8")
    first_wins = lambda pairs: {k: v for k, v in reversed(pairs)}  # noqa: E731
    for piece in txt.splitlines():
        try:
            say(f"  splitlines piece, first-wins parse: "
                f"{json.loads(piece, object_pairs_hook=first_wins)}")
            say(f"  same piece, last-wins (python/jq default): {json.loads(piece)}")
        except ValueError:
            say(f"  splitlines piece (not JSON): {piece[:120]!r}")
    body_words = ('group_id', 'member_id', 'display_name', '"permission', '"password')
    text = audit_path().read_text(encoding="utf-8")
    say("  body words in audit: " + str({w: w in text for w in body_words}))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "extra":
        section_extra()
    else:
        section_a()
        section_b()
    (SCRATCH / "au27_probe_output.txt").write_text("\n".join(OUT), encoding="utf-8")
