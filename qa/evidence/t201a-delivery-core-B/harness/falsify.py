"""One named falsification per criterion, each in its own throwaway copy on C:. Green before, red after."""
import json, os, shutil, subprocess, sys
from pathlib import Path

SP = Path(__file__).parent.parent
PY = str(SP / "src" / ".venv" / "Scripts" / "python.exe")
BASE = SP / "falsB" / "base"
T = "tests/test_delivery_smtp.py", "tests/test_report_email.py", "tests/test_delivery_failure.py"

# criterion: (file, old, new, nodes)
CASES = {
    "C1": ("src/autotester/delivery/email.py", "return bool(pref and pref.email_run_reports and can_view_report)",
           "return bool(pref and pref.email_run_reports)",
           ["tests/test_report_email.py::test_a_report_is_mailed_only_when_ticked_and_still_allowed_to_view_it"]),
    "C2": ("src/autotester/delivery/message.py", '"label": summary.label.value,', '"label": "green",',
           ["tests/test_report_email.py::test_body_carries_exactly_the_ho28_fields"]),
    "C3": ("src/autotester/delivery/email.py", "    if config is None:\n        return OutboxAdapter(outbox_dir)",
           "    if False:\n        return OutboxAdapter(outbox_dir)",
           ["tests/test_report_email.py::test_default_selection_without_credentials_is_the_outbox_and_sends_nothing"]),
    "C4": ("src/autotester/delivery/email.py", '            if cfg.tls == "starttls":\n                client.starttls(context=ssl.create_default_context())\n',
           '            if cfg.tls == "starttls":\n                pass\n',
           ["tests/test_delivery_smtp.py::test_starttls_then_login_then_send_with_certificate_verification_on"]),
    "C5": ("src/autotester/delivery/inbox.py", "import json\n", "import json\nfrom smtplib import SMTP  # noqa: F401\n",
           ["tests/test_delivery_smtp.py::test_only_the_email_adapter_imports_smtplib"]),
    "C7": ("src/autotester/delivery/inbox.py", "RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))",
           "RETRY_DELAYS = (timedelta(minutes=30), timedelta(minutes=5), timedelta(minutes=1))",
           ["tests/test_delivery_failure.py::test_backoff_is_a_pure_increasing_bounded_schedule"]),
    "C8": ("src/autotester/delivery/inbox.py", "    except Exception as exc:\n        text =", "    except (TransportError, OSError) as exc:\n        text =",
           ["tests/test_delivery_failure.py::test_an_unexpected_exception_is_contained_recorded_and_scrubbed"]),
    "C9": ("src/autotester/delivery/email.py", "    return type(exc).__name__ + (f\" {code}\" if isinstance(code, int) else \"\")",
           "    return type(exc).__name__ + (f\" {code}\" if isinstance(code, int) else \"\") + \" \" + str(exc)",
           ["tests/test_delivery_smtp.py::test_authentication_failure_text_carries_neither_password_nor_server_words"]),
    "C10": ("src/autotester/schema/delivery.py", '_URL = re.compile(r"(?:https?://[A-Za-z0-9.-]+(?::\\d{1,5})?)?/[A-Za-z0-9._~/-]*")',
            '_URL = re.compile(r".*")',
            ["tests/test_report_email.py::test_summary_fields_refuse_injection_paths_tokens_and_odd_links"]),
    "C11": ("src/autotester/delivery/inbox.py",
            '        return _create_once(self.attempts_dir / f"{key}.{attempt:02d}.json",\n                            json.dumps({"started_at": now.isoformat()}))',
            '        _create_once(self.attempts_dir / f"{key}.{attempt:02d}.json",\n                     json.dumps({"started_at": now.isoformat()}))\n        return True',
            ["tests/test_delivery_failure.py::test_two_workers_racing_for_one_attempt_send_exactly_once"]),
    "C6": ("src/autotester/delivery/inbox.py", "error = scrub(text)[:ERROR_LIMIT]", "error = text[:ERROR_LIMIT]",
           ["tests/test_delivery_failure.py::test_failure_text_is_redacted_in_the_record_and_on_disk"]),
    "C6b-os-replace": ("src/autotester/delivery/inbox.py",
           "    try:\n        os.link(tmp, path)\n        return True\n    except FileExistsError:\n        return False\n    finally:",
           "    try:\n        os.replace(tmp, path)\n        return True\n    except FileExistsError:\n        return False\n    finally:",
           ["tests/test_delivery_failure.py", "tests/test_delivery_smtp.py", "tests/test_report_email.py"]),
    "C12": ("src/autotester/schema/delivery.py", "    if any(ord(c) < 32 or ord(c) == 127 for c in value):\n        raise ValueError(\"control characters (including line breaks) are not allowed\")\n",
            "",
            ["tests/test_delivery_smtp.py::test_rendered_message_refuses_a_line_break_in_the_subject",
             "tests/test_delivery_smtp.py::test_sender_name_with_a_line_break_is_refused_at_config"]),
}


def run(copy, nodes):
    env = dict(os.environ, PYTHONPATH=str(copy / "src"))
    env.pop("VIRTUAL_ENV", None)
    code = "import autotester,sys;print(autotester.__file__)"
    where = subprocess.run([PY, "-c", code], cwd=copy, env={**env, "PYTHONPATH": str(copy / "src")}, capture_output=True, text=True).stdout.strip()
    r = subprocess.run([PY, "-m", "pytest", *nodes, "-p", "no:xdist", "-p", "no:cacheprovider", "-o", "addopts=", "-q", "--tb=line"],
                       cwd=copy, env=env, capture_output=True, text=True, timeout=240)
    tail = [l for l in r.stdout.splitlines() if l.strip()][-6:]
    return r.returncode, where, tail


only = sys.argv[1:] or list(CASES)
out = {}
for cid in only:
    f, old, new, nodes = CASES[cid]
    copy = SP / "falsB" / cid
    shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(BASE, copy)
    p = copy / f
    s = p.read_text("utf-8")
    assert s.count(old) == 1, (cid, "pattern count", s.count(old))
    rc0, where, tail0 = run(copy, nodes)
    p.write_text(s.replace(old, new), "utf-8")
    rc1, _, tail1 = run(copy, nodes)
    out[cid] = dict(file=f, before_rc=rc0, after_rc=rc1, inside_copy=str(copy).replace("\\", "/") in where.replace("\\", "/"),
                    before=tail0[-1] if tail0 else "", after=tail1[-3:])
    print(cid, json.dumps(out[cid]), flush=True)
    shutil.rmtree(copy, ignore_errors=True)
