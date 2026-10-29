import subprocess, sys, os, shutil
WT = os.environ.get("MUTATE_WT", "D:/autoTesting/.claude/worktrees/mongo-u6a")
PY = os.environ.get("MUTATE_PY", "D:/autoTesting/.claude/worktrees/mongo-u1/.venv/Scripts/python.exe")
A = "src/autotester/auth/"
# (id, file, old, new, killer test file, -k expr or "")
M = [
 ("S1", A+"store_sqlite.py", "\"AND u.disabled = 0\", (digest, now))", "\"\", (digest, now))", "tests/test_auth_store_seam.py", "disabled_account"),
 ("S2", A+"store_sqlite.py", "        db.ensure_an_admin_remains(self._c, after_delete=after_delete)", "        return None", "tests/test_auth_store_seam.py", "last_admin or last_two"),
 ("S3", A+"accounts.py", "        return tx.count_users() == 0\n    return address", "        return True\n    return address", "tests/test_auth_store_seam.py", "first_signups"),
 ("S4", A+"accounts.py", "    if tx.admin_has_member():\n        return \"an administrator already exists\"\n", "", "tests/test_auth_store_seam.py", "concurrent_claims"),
 ("S5", A+"accounts.py", "raise AccountError(\"an account with this email already exists\")", "raise AccountError(\"an account with this email already exists \" + password_hash)", "tests/test_auth_store_seam.py", "hash_never"),
 ("S6", A+"sessions.py", "        tx.insert_session(_digest(token), user_id,", "        tx.insert_session(token, user_id,", "tests/test_auth_store_seam.py", "round_trip"),
 ("S7", A+"store_sqlite.py", "        with db.transaction() as conn:\n            yield SqliteAuthTx(conn)", "        with db.reading() as conn:\n            yield SqliteAuthTx(conn)", "tests/test_auth_store_seam.py", "concurrent or last_admin"),
 ("S8", A+"access.py", "    if admin in tx.user_group_ids(user_id):\n        require_admin(", "    if False:\n        require_admin(", "tests/test_ui_auth_escalation.py", ""),
 ("S9", A+"store_sqlite.py", "    def has_session(self, digest: str) -> bool:", "    def has_session_x(self, digest: str) -> bool:", "tests/test_auth_store_seam.py", "implements_every"),
 ("S10", A+"groups.py", "from autotester.auth import access\n", "import sqlite3  # noqa\nfrom autotester.auth import access\n", "tests/test_auth_store_seam.py", "hold_no_sql"),
 ("S11", A+"store_sqlite.py", "        return self._c.execute(\"DELETE FROM users WHERE id = ?\", (user_id,)).rowcount > 0", "        return self._c.execute(\"DELETE FROM users WHERE id = ?\", (user_id,)).rowcount > 0 and False", "tests/test_ui_auth_accounts.py", ""),
]
only = sys.argv[1:]
os.chdir(WT)
env = dict(os.environ, PYTHONPATH=WT + "/src")
for mid, f, old, new, test, k in M:
    if only and mid not in only: continue
    src = open(f, encoding="utf-8").read()
    if old not in src:
        print(mid, "PATTERN-NOT-FOUND"); continue
    open(f, "w", encoding="utf-8").write(src.replace(old, new, 1))
    try:
        cmd = [PY, "-m", "pytest", test, "-o", "addopts=", "-p", "no:cacheprovider", "-q", "-x"] + (["-k", k] if k else [])
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        tail = [l for l in r.stdout.strip().splitlines() if "passed" in l or "failed" in l or "error" in l.lower()][-1:]
        print(mid, f, "KILLED" if r.returncode != 0 else "SURVIVED", "|", test, k, "|", tail, flush=True)
    finally:
        open(f, "w", encoding="utf-8").write(src)
