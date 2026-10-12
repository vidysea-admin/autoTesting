"""Exit-path table for `autotester ingest review` through the real CLI (subprocess)."""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
SP = HERE.parent
W = SP / "r2b-copy"
sys.path.insert(0, str(W / "tests"))
PY = str(W / ".venv" / "Scripts" / "python.exe")
OUT = Path(os.environ.get("R2B_OUT", str(SP / "r2b-out")))
CASES_ROOT = SP / "r2b-cases"
KEY = "r2b-scratch-signing-key-not-a-secret"
os.environ["AUTOTESTER_APPROVAL_KEY"] = KEY
PYB = "C:/Users/Lenovo/AppData/Roaming/uv/python/cpython-3.11-windows-x86_64-none/python.exe"
VIDEO = SP / "r2b-video" / "rec.mp4"
CANARY = "hunter2-canary-xyz"


def make_video():
    VIDEO.parent.mkdir(exist_ok=True)
    if not VIDEO.exists():
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=1:d=130",
                        "-c:v", "libx264", "-preset", "veryfast", str(VIDEO)],
                       check=True, capture_output=True, timeout=120)


def setup(name, grant=True, bad=False, secret=False):
    from run_approval_fixture import grant_live_case_approval
    from autotester.schema.enums import ApprovalKind
    from autotester.schema.project import Project, SecretRef
    from autotester.stages.ingest import register_source
    from autotester.store.project_store import ProjectStore
    root = CASES_ROOT / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    os.environ["AUTOTESTER_ROOT"] = str(root)
    store = ProjectStore("demo", root)
    proj = Project(slug="demo", name="Demo", base_url="https://demo.test",
                   allowed_domains=["demo.test"])
    store.save_project(proj)
    if secret:
        (root / ".env").write_text(f"DEMO_PASSWORD={CANARY}\n", encoding="utf-8")
        store.save_project(proj.model_copy(update={"secrets": [
            SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]}))
    if bad:
        v = root / "rec.mp4"
        v.write_bytes(b"this is not a video")
    else:
        v = root / "rec.mp4"
        shutil.copyfile(VIDEO, v)
    src = register_source(store, v, label="rec")
    if grant:
        grant_live_case_approval(store, project="demo", target="fake", max_actions=500,
                                 run_kind=ApprovalKind.VIDEO_REVIEW)
    return root, src.id


def env_for(root, src, mode):
    e = dict(os.environ)
    e.update(AUTOTESTER_ROOT=str(root), R2B_ROOT=str(root), R2B_MODE=mode, R2B_SRC=src,
             AUTOTESTER_APPROVAL_KEY=KEY, PYTHONIOENCODING="utf-8", NO_COLOR="1")
    return e


def docs_of(text):
    dec, i, out = json.JSONDecoder(), 0, []
    n = len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        try:
            d, j = dec.raw_decode(text, i)
        except ValueError:
            return out, text[i:i + 80]
        out.append(d)
        i = j
    return out, ""


def leftovers(root):
    left = []
    proj = root / "projects" / "demo"
    for p in sorted(proj.rglob("*")):
        rel = p.relative_to(proj).as_posix()
        if rel.startswith("sources") or rel.startswith("approvals") or p.name in (
                "project.json", "approvals.jsonl"):
            continue
        if p.is_file() or not any(p.iterdir()) or p.parent.name == "reviews":
            left.append(rel)
    return left


def finish(case, root, src, args, mode, rc, so, se, note=""):
    docs, garbage = docs_of(so)
    first = docs[0] if docs else {}
    leak = [s for s in (CANARY, str(root / "rec.mp4"), "rec.mp4", str(root)) if s in so + se]
    calls = (root / "_calls.jsonl")
    ncalls = len(calls.read_text().splitlines()) if calls.exists() else 0
    row = {
        "case": case, "args": " ".join(args), "mode": mode, "exit": rc, "stdout_docs": len(docs),
        "trailing_garbage": garbage, "status": first.get("status", "-" if docs else "NO-DOC"),
        "doc_exit_code": first.get("exit_code", "-" if docs else "NO-DOC"),
        "exit_matches": (first.get("exit_code") == rc) if docs else None,
        "stderr_first": (se.strip().splitlines() or [""])[-1][:110] if se.strip() else "",
        "traceback": "Traceback" in se or "Traceback" in so, "leak_in_output": leak,
        "provider_calls": ncalls, "left": leftovers(root), "note": note,
    }
    return row


def run(case, args, mode="ok", **setup_kw):
    root, src = setup(case, **setup_kw)
    a = [x.replace("{SRC}", src).replace("{ROOT}", str(root)) for x in args]
    p = subprocess.run([PY, str(HERE / "drv.py"), "ingest", "review", *a],
                       env=env_for(root, src, mode), capture_output=True, text=True,
                       encoding="utf-8", timeout=180)
    return finish(case, root, src, a, mode, p.returncode, p.stdout, p.stderr)


def run_signal(case, args, sig, **setup_kw):
    root, src = setup(case, **setup_kw)
    a = [x.replace("{SRC}", src) for x in args]
    e = env_for(root, src, "hang")
    e["PYTHONPATH"] = str(W / "src") + os.pathsep + str(W / ".venv" / "Lib" / "site-packages")
    proc = subprocess.Popen([PYB, str(HERE / "drv.py"), "ingest", "review", *a],
                            env=e, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            creationflags=0x08000000)
    t0 = time.time()
    while not (root / "_ready").exists() and time.time() - t0 < 90 and proc.poll() is None:
        time.sleep(0.3)
    mid = leftovers(root)
    real = int((root / "_ready").read_text()) if (root / "_ready").exists() else proc.pid
    h = subprocess.run([PYB, str(HERE / "sendctrl.py"), str(real), sig], capture_output=True,
                       text=True, creationflags=0x08000000, timeout=30)
    ok = "attach 1" in h.stdout
    try:
        so, se = proc.communicate(timeout=60)
        rc = proc.returncode
        killed = False
    except subprocess.TimeoutExpired:
        proc.kill()
        so, se = proc.communicate()
        rc, killed = proc.returncode, True
    row = finish(case, root, src, a, "hang", rc, so, se,
                 note=f"attach={bool(ok)} sig=CTRL_{sig} killed_after_timeout={killed} "
                      f"mid_run_tree={len(mid)}f")
    row["mid_run"] = mid
    return row


def main():
    make_video()
    OUT.mkdir(exist_ok=True)
    rows = []
    J = ["--output", "json"]
    ptr_bad = CASES_ROOT / "ptr_bad.txt"
    CASES_ROOT.mkdir(exist_ok=True)
    ptr_bad.write_text("99:99\n14:00-12:30\n", encoding="utf-8")
    ptr_ok = CASES_ROOT / "ptr_ok.txt"
    ptr_ok.write_text("1:00 | note\n", encoding="utf-8")
    big = CASES_ROOT / "ptr_big.txt"
    big.write_bytes(b"0:10 | " + b"z" * 33000 + b"\n")
    only = sys.argv[1:]

    def go(case, args, mode="ok", **kw):
        if only and not any(case.startswith(o) for o in only):
            return
        r = run(case, args, mode, **kw)
        rows.append(r)
        print(json.dumps({k: r[k] for k in ("case", "exit", "stdout_docs", "status",
                                            "doc_exit_code", "exit_matches")}), flush=True)

    S = ["demo", "{SRC}"]
    go("ok-json", [*S, *J])
    go("ok-text", [*S])
    go("dryrun-json", [*S, *J, "--dry-run"], grant=False)
    go("dryrun-text", [*S, "--dry-run"], grant=False)
    go("partial-cap-json", [*S, *J, "--max-cost", "1e-9"])
    go("failed-cap0-json", [*S, *J, "--max-cost", "0"])
    go("pointer-errors-json", [*S, *J, "--pointers", str(ptr_bad)])
    go("pointer-errors-text", [*S, "--pointers", str(ptr_bad)])
    go("pointer-oversize-json", [*S, *J, "--pointers", str(big)])
    go("refused-no-approval-json", [*S, *J], grant=False)
    go("refused-no-approval-text", [*S], grant=False)
    go("unreadable-json", [*S, *J], bad=True)
    go("unreadable-text", [*S], bad=True)
    go("unknown-source-json", ["demo", "src_nope", *J])
    go("unknown-project-json", ["ghost", "src_x", *J])
    go("provider-unavailable-json", [*S, *J], mode="unavailable")
    go("missing-pointer-file-json", [*S, *J, "--pointers", str(CASES_ROOT / "nope.txt")])
    go("nan-cap-json", [*S, *J, "--max-cost", "nan"])
    go("inf-cap-json", [*S, *J, "--max-cost", "inf"])
    go("neg-cap-json", [*S, *J, "--max-cost", "-1"])
    # click usage errors, every form
    bads = {"cap-abc": ["--max-cost", "abc"], "cap-empty": ["--max-cost", ""],
            "cap-0x10": ["--max-cost", "0x10"], "unknown-opt": ["--bogus"],
            "output-novalue": ["--output"]}
    for k, extra in bads.items():
        go(f"u-{k}-spaced-after", [*S, *J, *extra])
        go(f"u-{k}-spaced-before", [*extra, *S, *J] if k != "output-novalue" else [*J, *S, *extra])
        go(f"u-{k}-equals-after", [*S, "--output=json", *extra])
        go(f"u-{k}-equals-before", ["--output=json", *extra, *S])
        go(f"u-{k}-text", [*S, *extra] if k != "output-novalue" else [*S, "--output"])
    go("u-missing-arg-json", ["demo", *J])
    go("u-missing-arg-equals", ["demo", "--output=json"])
    go("u-missing-arg-text", ["demo"])
    go("u-no-args-json", [*J])
    go("u-output-xml", [*S, "--output", "xml"])
    go("u-output-JSON-upper", [*S, "--output", "JSON"])
    go("u-bare-output-only", [*S, "--output"])
    go("u-cap-eats-output-flag", [*S, "--max-cost", "--output", "json"])
    go("u-pointers-eats-output-flag", [*S, "--pointers", "--output", "json"])
    go("u-extra-positional-json", [*S, "extra", *J])
    go("u-redact-malformed-json", [*S, *J, "--redact", "zz"])
    go("u-help-json", [*J, "--help"])
    # provider failures
    go("provider-runtime-json", [*S, *J], mode="runtime", secret=True)
    go("provider-oserror-json", [*S, *J], mode="oserror", secret=True)
    go("provider-runtime-text", [*S], mode="runtime", secret=True)
    go("provider-runtime-redact-json", [*S, *J, "--redact", "1:00-1:10"], mode="runtime",
       secret=True)
    # real signals
    if not only or any("sig" in o for o in only):
        pick = os.environ.get("R2B_SIG", "")
        for sig in ("C", "BREAK"):
            for fmt, extra in (("json", J), ("text", [])):
                if pick and pick != f"{sig}:{fmt}":
                    continue
                r = run_signal(f"sig-ctrl{sig}-{fmt}", [*S, *extra, "--redact", "1:00-1:10"], sig)
                rows.append(r)
                print(json.dumps({k: r[k] for k in ("case", "exit", "stdout_docs", "status",
                                                    "doc_exit_code", "exit_matches", "note")}),
                      flush=True)
    (OUT / f"exit-path-table-{os.environ.get('R2B_TAG','all')}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
