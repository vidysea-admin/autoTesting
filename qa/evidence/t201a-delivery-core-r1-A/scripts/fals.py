"""Checker A: one falsification per repaired item, each in its own throwaway copy. Throwaway."""
import os, shutil, subprocess, sys, pathlib
W = pathlib.Path(sys.argv[1]); PY = W / ".venv" / "Scripts" / "python.exe"
OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(exist_ok=True)
FILES = ["delivery_inbox"]
rows = [
 ("F1a key-injectivity C11", "src/autotester/delivery/inbox.py",
  '    return "".join("_0" if c == "_" else f"_{c.lower()}" if c.isupper() else c\n                   for c in safe_id(value))',
  '    return safe_id(value)',
  "tests/test_delivery_failure.py", "injective or spell_the_separator"),
 ("F1b exact-match C11", "src/autotester/delivery/inbox.py",
  'return self._load(re.compile(re.escape(key) + r"\.\d+\.json"))',
  'return self._load(re.compile(re.escape(key) + r"\..*\.json"))',
  "tests/test_delivery_failure.py", "dotted_prefix or whole_file_names"),
 ("F2 append-race C8", "src/autotester/delivery/inbox.py",
  '        record = DeliveryRecord(run_id=run_id, channel=channel, recipient_user_id=to.user_id,\n                                status=transport.outcome, attempts=attempt)\n    try:\n        log.append(key, record)\n    except FileExistsError:',
  '        record = DeliveryRecord(run_id=run_id, channel=channel, recipient_user_id=to.user_id,\n                                status=transport.outcome, attempts=attempt)\n    try:\n        log.append(key, record)\n    except ZeroDivisionError:',
  "tests/test_delivery_failure.py", "clock_skewed"),
 ("F3a protocol-relative C10", "src/autotester/schema/delivery.py", "/(?!/)[A-Za-z0-9._~/-]*", "/[A-Za-z0-9._~/-]*",
  "tests/test_report_email.py", "report_url and (evil or x.test//)"),
 ("F3b port-range C10", "src/autotester/schema/delivery.py", "not 1 <= int(match.group(1)) <= 65535", "not 0 <= int(match.group(1)) <= 99999",
  "tests/test_report_email.py", "report_url and (65536 or 99999 or :0)"),
]
env = dict(os.environ); env.pop("VIRTUAL_ENV", None)
def run(copy, test, k):
    e = dict(env, PYTHONPATH=str(copy / "src"))
    chk = subprocess.run([str(PY), "-I", "-c", "import sys;sys.path.insert(0,r'%s');import autotester;print(autotester.__file__)" % (copy / "src")], capture_output=True, text=True, env=e)
    r = subprocess.run([str(PY), "-m", "pytest", test, "-k", k, "-p", "no:xdist", "-p", "no:cacheprovider", "-o", "addopts=", "--rootdir", str(copy)], cwd=copy, capture_output=True, text=True, env=e, timeout=200)
    tail = [l for l in r.stdout.splitlines() if l.strip()][-1]
    return chk.stdout.strip(), r.returncode, tail, r.stdout
for name, f, old, new, test, k in rows:
    copy = OUT / ("m_" + name.split()[0]); shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(W, copy, ignore=shutil.ignore_patterns(".venv", ".ev", "__pycache__", ".git"))
    src = (copy / f).read_text("utf-8"); assert src.count(old) == 1, (name, src.count(old))
    where_b, rc_b, tail_b, _ = run(copy, test, k)
    (copy / f).write_text(src.replace(old, new), "utf-8")
    where_a, rc_a, tail_a, out_a = run(copy, test, k)
    failed = [l.split(" ")[1] for l in out_a.splitlines() if l.startswith("FAILED")]
    print(f"{name}: copy={'IN-COPY' if str(copy).lower() in where_b.lower() else 'OUTSIDE'} BEFORE rc={rc_b} [{tail_b}] AFTER rc={rc_a} [{tail_a}]")
    for n in failed: print("    red:", n[:150])
