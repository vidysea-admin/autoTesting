"""Blind sub-checker B, Part 2 runner: one mutant per row, in a throwaway COPY of the worktree.

Usage: falsify.py <row-id> [<row-id> ...]   (rows run strictly one after another)
Each row: assert the copy's file equals the pristine worktree file, run the named tests (must be
green), apply a single string replace (asserted to match exactly once), run again (expect red),
and ALWAYS restore the file from the pristine worktree copy. Never writes under the worktree.
Results are appended to results.jsonl next to this script.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

W = Path("D:/autoTesting/.worktrees/t204-team-login")
S = Path("C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/"
         "236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/t204b-verify")
C = S / "copy"
PY = str(W / ".venv/Scripts/python.exe")
OUT = Path(__file__).with_name("results.jsonl")
A = "tests/test_ui_auth_"
AUTH10 = [A + n + ".py" for n in ("login", "accounts", "groups", "surface", "escalation", "hardening",
                                  "cli_and_limits", "survivors", "host_and_consent")] \
    + ["tests/test_auth_deploy_files.py"]
MW, PW, SE, AC = ("src/autotester/ui/auth_middleware.py", "src/autotester/auth/passwords.py",
                  "src/autotester/auth/sessions.py", "src/autotester/auth/access.py")

# id -> (criterion, file, old, new, pytest args)
ROWS: dict[str, tuple[str, str, str, str, list[str]]] = {
    "AU16a": ("AU16", MW, 'if rule is not None and rule.kind == "public":',
              'if rule is not None and rule.kind in ("public", "session"):',
              [A + "surface.py::test_au16_only_the_public_set_answers_unsigned_in"]),
    "AU16b": ("AU16", MW, 'or value.startswith("//") or', 'or False or',
              [A + "surface.py", "-k", "test_au16_login_page_drops_unsafe_next or "
               "test_au16_redirect_never_points_off_site"]),
    "AU14a": ("AU14", "src/autotester/auth/policy.py",
              '("GET", "/onboard"): _key(K.PROJECT_CREATE), ("POST", "/onboard"): _key(K.PROJECT_CREATE),',
              '("GET", "/onboard"): _key(K.PROJECT_CREATE),',
              [A + "groups.py::test_au14_every_route_has_a_policy_row"]),
    "AU14b": ("AU14", MW, 'return await _error(request, 403, "this page is not available to your account")',
              'return None',
              [A + "groups.py::test_au14_an_undeclared_route_is_refused"]),
    "AU21a": ("AU21", "src/autotester/ui/routes_credentials.py",
              "shown = present.get(key, '') if show_values else ''  # AU21: no value, no length hint",
              "shown = present.get(key, '')  # MUT",
              [A + "surface.py::test_au21_values_only_for_credentials_view"]),
    "AU21b": ("AU21", "src/autotester/ui/routes_settings.py",
              "show = can_view_credentials()  # T-204 AU21: values only for credentials.view",
              "show = True  # MUT",
              [A + "surface.py::test_au21_settings_page_hides_values_and_counts_env_keys"]),
    "AU21c": ("AU21", "src/autotester/ui/routes_settings.py",
              'if present.get(key) or key in in_env', 'if present.get(key)',
              [A + "surface.py::test_au21_settings_page_hides_values_and_counts_env_keys"]),
    "AU3a": ("AU3", "src/autotester/ui/routes_auth.py", 'httponly=True, samesite="lax", secure=secure)',
             'httponly=False, samesite="lax", secure=secure)',
             [A + "login.py::test_au3_cookie_flags_plain_http"]),
    "AU3b": ("AU3", SE, '(now + timedelta(hours=session_hours())).isoformat()),',
             '(now + timedelta(hours=session_hours() * 100)).isoformat()),',
             [A + "login.py", A + "hardening.py", A + "cli_and_limits.py", A + "survivors.py",
              "-k", "test_au3_"]),
    "AU3c": ("AU3", SE, '"ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ? "',
             '"ON u.id = s.user_id WHERE s.token_hash = ? AND ? IS NOT NULL "',
             [A + "login.py::test_au3_bad_cookie_is_refused_and_creates_nothing"]),
    "AU5a": ("AU5", "src/autotester/auth/ratelimit.py",
             'return (len(self._recent(f"acct:{email}", now)) >= self._limits["acct"]',
             'return (len(self._recent(f"acct:{email}", now)) > self._limits["acct"]',
             [A + "login.py", "-k", "test_au5_"]),
    "AU5b": ("AU5", "src/autotester/ui/routes_auth.py", "    if login_limiter.blocked(account, address):",
             "    if False:",
             [A + "login.py::test_au5_lock_after_failures_even_with_the_right_password",
              A + "survivors.py::test_au5_the_address_limit_ignores_x_forwarded_for"]),
    "AU5c": ("AU5", "src/autotester/auth/ratelimit.py", "MAX_FAILURES_PER_ACCOUNT = 5",
             "MAX_FAILURES_PER_ACCOUNT = 50",
             [A + "login.py", "-k", "test_au5_"]),
    "AU1": ("AU1", PW, "_HASHER = PasswordHasher()",
            "_HASHER = PasswordHasher(memory_cost=1024, time_cost=1, parallelism=1)",
            [A + "login.py::test_au1_password_is_argon2id_and_never_stored"]),
    "AU2": ("AU2", "src/autotester/auth/accounts.py",
            'if not verify_password(stored, password) or row is None or row["disabled"]:',
            'if not verify_password(stored, password) or row is None:',
            [A + "login.py::test_au2_failures_are_identical"]),
    "AU4": ("AU4", SE, 'conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_digest(token),))',
            'conn.execute("DELETE FROM sessions WHERE token_hash = ? AND 0", (_digest(token),))',
            [A + "login.py::test_au4_logout_ends_the_session"]),
    "AU6": ("AU6", PW, "if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:",
            "if not MIN_PASSWORD_LENGTH <= len(password):",
            [A + "accounts.py::test_au6_signup_normalizes_and_validates"]),
    "AU7": ("AU7", "src/autotester/auth/config.py",
            '    return os.environ.get(FIRST_ADMIN_ENV, "").strip().lower()',
            '    return os.environ.get(FIRST_ADMIN_ENV, "").strip()',
            [A + "escalation.py::test_d074_the_fixed_email_is_compared_case_insensitively"]),
    "AU8": ("AU8", "src/autotester/ui/routes_admin.py",
            'accounts.set_disabled(user_id, action == "disable", who)',
            'accounts.set_disabled(user_id, action != "disable", who)',
            [A + "accounts.py::test_au8_admin_disables_enables_renames_and_regroups"]),
    "AU9a": ("AU9", "src/autotester/auth/db.py", "(admin, PermissionKey.USERS_MANAGE.value, admin),",
             "(admin, PermissionKey.PROJECT_CREATE.value, admin),",
             [A + "accounts.py::test_au9_last_admin_cannot_be_locked_out"]),
    "AU9b": ("AU9", "src/autotester/auth/db.py", 'WHERE m.group_id = ? AND u.disabled = 0)""",',
             'WHERE m.group_id = ?)""",',
             [A + "accounts.py::test_au9_last_admin_cannot_be_locked_out"]),
    "AU10": ("AU10", SE, '"ON p.group_id = m.group_id WHERE m.user_id = ?", (row["id"],)))',
             '"ON p.group_id = m.group_id WHERE m.user_id = ? AND m.group_id = "\n'
             '            "(SELECT MIN(group_id) FROM memberships WHERE user_id = m.user_id)", (row["id"],)))',
             [A + "groups.py::test_au10_union_and_untick"]),
    "AU11a": ("AU11", "src/autotester/auth/defaults.py",
              "_SHARED_READ = (K.PROJECT_VIEW, K.REPORT_VIEW, K.VIDEO_VIEW, K.COMMENT_CREATE)",
              "_SHARED_READ = (K.PROJECT_VIEW, K.REPORT_VIEW, K.VIDEO_VIEW)",
              [A + "groups.py", "-k", "test_au11_ or test_au12_scope_table or test_au13_"]),
    "AU11b": ("AU11", "src/autotester/auth/db.py",
              '    conn.execute("INSERT INTO meta (name, value) VALUES (\'seeded\', ?)", (now_iso(),))',
              "    pass",
              [A + "groups.py::test_au11_seeded_once_edits_survive_restart"]),
    "AU12": ("AU12", AC, "        return email in resource.assignees", "        return True",
             [A + "groups.py::test_au12_scope_table"]),
    "AU13": ("AU13", AC, "            if authorize(principal, PermissionKey.PROJECT_VIEW, resource_for(s))]",
             "            if True]", [A + "groups.py::test_au13_four_users_two_projects"]),
    "AU15": ("AU15", "src/autotester/ui/routes_crawls.py",
             '    except ApprovalRequired as exc:\n        return _crawl_error(slug, 403, "Crawl approval required", str(exc))\n'
             '    paths = ProjectPaths(slug)',
             '    except ApprovalRequired as exc:\n'
             '        if "project.run@all" in __import__("autotester.auth.context", fromlist=["x"]).current_principal().permissions:\n'
             '            return RedirectResponse(f"/projects/{slug}", status_code=303)\n'
             '        return _crawl_error(slug, 403, "Crawl approval required", str(exc))\n'
             '    paths = ProjectPaths(slug)',
             [A + "host_and_consent.py::test_au15_admin_and_developer_get_the_same_missing_approval_refusal"]),
    "AU17": ("AU17", "src/autotester/auth/config.py", "    return not hosted() and bind_host() in _LOOPBACK",
             "    return not hosted()",
             [A + "surface.py::test_au17_disabled_flag_is_refused_when_hosted"]),
    "AU18a": ("AU18", "src/autotester/ui/helpers.py",
              "        _ = parts.port  # AT-760: raises on `localhost:8000.evil.com`; urlparse alone ignores it",
              "        pass",
              [A + "host_and_consent.py", "-k", "test_au18_a_non_numeric_origin_port"]),
    "AU18b": ("AU18", "src/autotester/ui/helpers.py", 'names.count("origin") > 1', 'names.count("origin") > 99',
              [A + "host_and_consent.py", "-k", "test_au18_a_repeated_origin_or_host_header"]),
    "AU18c": ("AU18", "src/autotester/ui/helpers.py", 'names.count("origin") > 1', 'names.count("origin") > 99',
              ["tests/test_ui_origin_guard.py", "-k", "test_more_than_one_origin_or_host_header_is_refused"]),
    "AU19": ("AU19", "src/autotester/ui/helpers.py",
             "        if parts.hostname in _LOOPBACK_HOSTS:\n            return True",
             '        if parts.hostname.startswith(("localhost", "127.0.0.1")):\n            return True',
             [A + "host_and_consent.py::test_au19_a_foreign_host_gets_no_login_page_and_no_session"]),
    "AU20": ("AU20", "src/autotester/auth/config.py",
             '    if hosted() and not (os.environ.get("AUTOTESTER_ALLOWED_HOSTS", "").strip()',
             '    if not hosted() and not (os.environ.get("AUTOTESTER_ALLOWED_HOSTS", "").strip()',
             [A + "surface.py::test_au20_hosted_needs_an_allow_list"]),
    "AU22": ("AU22", MW, 'audit.record_request(who.email, scope["method"], template or "<unmatched>",',
             'audit.record_request(who.email, scope["method"], str(request.url),',
             [A + "survivors.py::test_au22_audit_line_holds_the_template_not_the_query_string"]),
    "AU23": ("AU23", ".dockerignore", "**/.auth/\n", "",
             ["tests/test_auth_deploy_files.py::test_au23_dockerignore_excludes_the_auth_state_at_any_depth"]),
    "AU25": ("AU25", AC, "        return key.value in principal.permissions", "        return False",
             ["tests/test_ui_project_intake.py"]),
    "AU27a": ("AU27", AC, 'return wanted in permissions or (bool(scope) and f"{key}@all" in permissions)',
              "return wanted in permissions or bool(scope)",
              [A + "escalation.py::test_p5_a_new_group_cannot_carry_more_than_its_creator_holds"]),
    "AU27b": ("AU27", AC, "    if admin in (old ^ new_groups):", "    if admin in (new_groups - old):",
              [A + "escalation.py::test_p5_users_manage_cannot_reset_disable_or_delete_an_admin"]),
}


def pytest(args: list[str], timeout: int = 900) -> tuple[int, str, float]:
    env = {**os.environ, "PYTHONPATH": str(C / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    start = time.time()
    proc = subprocess.run([PY, "-m", "pytest", "-p", "no:xdist", "-p", "no:cacheprovider",
                           "--tb=short", "-rfE", *args], cwd=C, env=env, capture_output=True,
                          text=True, timeout=timeout)
    return proc.returncode, proc.stdout + proc.stderr, time.time() - start


def summary(out: str) -> str:
    lines = [ln for ln in out.splitlines() if re.search(r"\d+ (passed|failed|error)", ln)]
    return lines[-1].strip() if lines else out.strip().splitlines()[-1]


def failures(out: str) -> dict[str, object]:
    fails = [ln[:230] for ln in out.splitlines() if ln.startswith(("FAILED ", "ERROR "))]
    e_lines = [ln.strip()[:200] for ln in out.splitlines() if ln.startswith("E   ")][:4]
    return {"failed": fails[:6], "assertion_text": e_lines}


def run_row(row_id: str) -> dict[str, object]:
    crit, rel, old, new, args = ROWS[row_id]
    pristine = (W / rel).read_bytes().decode("utf-8")
    target = C / rel
    assert target.read_bytes().decode("utf-8") == pristine, "copy differs from worktree"
    rec: dict[str, object] = {"row": row_id, "criterion": crit, "file": rel, "args": args}
    rc, out, secs = pytest(args)
    rec.update(green=summary(out), green_rc=rc, green_secs=round(secs, 1))
    if rc != 0:
        rec.update(verdict="BAD copy (not green before the edit)", **failures(out))
        return rec
    if "\r\n" in pristine:  # the file uses CRLF: make the multi-line edit match
        old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
    assert pristine.count(old) == 1, f"mutation text matched {pristine.count(old)} times"
    line = pristine[: pristine.index(old)].count("\n") + 1
    rec["line"] = line
    rec["edit"] = f"{old.strip()[:110]!r} -> {new.strip()[:110]!r}"
    try:
        target.write_bytes(pristine.replace(old, new).encode("utf-8"))
        rc2, out2, secs2 = pytest(args)
    finally:
        target.write_bytes(pristine.encode("utf-8"))
    rec.update(red=summary(out2), red_rc=rc2, red_secs=round(secs2, 1), **failures(out2))
    rec["verdict"] = "killed" if rc2 != 0 else "SURVIVED"
    return rec


if __name__ == "__main__":
    for rid in sys.argv[1:]:
        try:
            result = run_row(rid)
        except Exception as exc:  # noqa: BLE001 - recorded, never hidden
            result = {"row": rid, "verdict": f"RUNNER ERROR {type(exc).__name__}: {exc}"}
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result) + "\n")
        print(rid, result.get("verdict"), flush=True)
