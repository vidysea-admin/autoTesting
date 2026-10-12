"""Blind-check A: one named falsification per criterion (+ security mutants), each in its own throwaway copy on C:."""
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

SP = Path(os.environ["SP"]); SRC = SP / "t"; PY = SP / "venv" / "Scripts" / "python.exe"
FILES = "tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py".split()
E = "src/autotester/delivery/email.py"; I = "src/autotester/delivery/inbox.py"; M = "src/autotester/delivery/message.py"; D = "src/autotester/schema/delivery.py"

ROWS = [  # id, file, old, new, selector (-k)
 ("C1", E, "return bool(pref and pref.email_run_reports and can_view_report)", "return bool(pref and (pref.email_run_reports or can_view_report))", "ticked or defaults_off"),
 ("C2", M, '"label": summary.label.value,', '"label": "green",', "carries_exactly or label_is_a_closed"),
 ("C3", E, 'if TEST_MARKER in os.environ and host not in LOOPBACK:', 'if False and host not in LOOPBACK:', "default_factory_never"),
 ("C4", E, 'if cfg.tls == "starttls":', 'if cfg.tls == "never":', "starttls_then_login"),
 ("C5", M, "from collections.abc import Callable", "import smtplib\nfrom collections.abc import Callable", "only_the_email_adapter"),
 ("C6", I, "os.link(tmp, path)", "os.replace(tmp, path)", "append_only"),
 ("C7", I, "return RETRY_DELAYS[attempts_made - 1] if attempts_made <= len(RETRY_DELAYS) else None", "return RETRY_DELAYS[min(attempts_made, len(RETRY_DELAYS)) - 1]", "backoff or attempt_limit"),
 ("C8", I, "    except Exception as exc:", "    except TransportError as exc:", "unexpected_exception"),
 ("C9", I, "error = scrub(text)[:ERROR_LIMIT]", "error = text[:ERROR_LIMIT]", "redacted_in_the_record or unexpected_exception"),
 ("C10", D, 'r"(?:https?://[A-Za-z0-9.-]+(?::\\d{1,5})?)?/[A-Za-z0-9._~/-]*")', 'r"(?:https?://[A-Za-z0-9.-]+(?::\\d{1,5})?)?/[A-Za-z0-9._~/?#-]*")', "refuse_injection_paths_tokens"),
 ("C11", I, "return _create_once(self.attempts_dir / f\"{key}.{attempt:02d}.json\",", "return True or _create_once(self.attempts_dir / f\"{key}.{attempt:02d}.json\",", "two_workers or crash_between"),
 ("C12", D, "if len(v) > 254 or not _ADDRESS.fullmatch(v):", "if False:", "address_validation"),
 # security-area mutants (L, beyond floor)
 ("M1-tls-unverified", E, "client.starttls(context=ssl.create_default_context())", "client.starttls(context=ssl._create_unverified_context())", "starttls_then_login"),
 ("M2-ssl-unverified", E, "context=ssl.create_default_context())\n    return smtplib.SMTP(", "context=ssl._create_unverified_context())\n    return smtplib.SMTP(", "implicit_ssl"),
 ("M3-plaintext-creds", D, 'if self.tls == "none" and self.user and self.host not in LOOPBACK:', 'if False:', "plain_text_login"),
 ("M4-error-leaks-server-words", E, 'return type(exc).__name__ + (f" {code}" if isinstance(code, int) else "")', 'return type(exc).__name__ + " " + str(getattr(exc, "args", ""))', "authentication_failure or recipient_refusal"),
 ("M5-password-in-repr", E, 'return f"SmtpAdapter(host={self._config.host!r}, tls={self._config.tls!r})"', 'return f"SmtpAdapter(host={self._config.host!r}, pw={self._password_source()!r})"', "nothing_is_logged or password_is_read"),
]


def pytest(copy, k, extra=()):
    env = dict(os.environ, PYTHONPATH=str(copy / "src"), PYTHONIOENCODING="utf-8")
    env.pop("VIRTUAL_ENV", None)
    cmd = [str(PY), "-m", "pytest", *FILES, "-p", "no:cacheprovider", "-p", "no:xdist", "-o", "addopts=", "-q", "-rf", "-k", k, *extra]
    p = subprocess.run(cmd, cwd=copy, env=env, capture_output=True, text=True, timeout=300)
    if p.returncode not in (0, 1): print("RC", p.returncode, p.stdout[-400:], p.stderr[-400:])
    tail = [l for l in p.stdout.splitlines() if re.search(r"passed|failed|error", l) and " in " in l][-1:]
    failed = [l.split(" - ")[0].replace("FAILED ", "") for l in p.stdout.splitlines() if l.startswith("FAILED")]
    return p.returncode, (tail[0].strip() if tail else p.stdout[-200:]), failed


only = sys.argv[1:]
out = []
for rid, f, old, new, k in ROWS:
    if only and rid not in only:
        continue
    copy = SP / "f" / rid.split("-")[0].lower()
    if copy.exists():
        shutil.rmtree(copy)
    copy.mkdir(parents=True)
    for part in ("src", "tests", "scripts"):
        shutil.copytree(SRC / part, copy / part, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(SRC / "pyproject.toml", copy / "pyproject.toml")
    probe = subprocess.run([str(PY), "-c", "import autotester;print(autotester.__file__)"], cwd=copy, capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=str(copy / "src")))
    rc0, t0, _ = pytest(copy, k)
    p = copy / f
    txt = p.read_text(encoding="utf-8")
    n = txt.count(old)
    if n != 1:
        out.append((rid, f"EDIT-NOT-APPLICABLE count={n}")); print(rid, "EDIT-NOT-APPLICABLE", n); shutil.rmtree(copy); continue
    p.write_text(txt.replace(old, new), encoding="utf-8")
    rc1, t1, failed = pytest(copy, k)
    p.write_text(txt, encoding="utf-8")
    rc2, t2, _ = pytest(copy, k)
    res = f"{rid}: copy_import={probe.stdout.strip()[-60:]} | green-before rc={rc0} [{t0}] | red-after rc={rc1} [{t1}] failed={failed} | restored rc={rc2}"
    print(res, flush=True); out.append((rid, res))
    shutil.rmtree(copy)
Path(SP / "falsify.out").write_text("\n".join(r for _, r in out), encoding="utf-8")
