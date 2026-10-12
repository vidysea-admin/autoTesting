import json, os, re, subprocess, sys, shutil, hashlib, zipfile, concurrent.futures as cf
from pathlib import Path
S = Path(os.environ["SCR"]); R = os.environ["RAND"]; PR = S / "probes"
MEDIA = PR / "media-rec.mp4"; MEDIA2 = PR / "media-rec2.mp4"
def copy_dir(n): return S / f"mr1B-{n}-{R}"
TS = re.compile(r"\d{4}-\d\d-\d\d[T ][\d:.]+(?:Z|[+-]\d\d:?\d\d)?")
def norm(text, world, copy):
    for base, tag in ((str(world), "<W>"), (str(copy), "<C>")):
        for v in (base, base.replace("\\", "/"), base.replace("\\", "\\\\"), base.replace("\\", "/").replace("/", "\\\\")):
            text = text.replace(v, tag)
        text = text.replace(base.lower(), tag).replace(base.lower().replace("\\", "/"), tag)
    text = text.replace(str(S), "<S>").replace(str(S).replace("\\", "/"), "<S>")
    return TS.sub("<TS>", text)
def listing(world, copy):
    out = {}
    root = world / "projects"
    for p in sorted(root.rglob("*")) if root.exists() else []:
        rel = p.relative_to(world).as_posix()
        if p.is_dir(): out[rel + "/"] = "dir"; continue
        if "media/" in rel: continue
        if p.suffix in (".json", ".jsonl", ".md", ".html", ".txt"):
            out[rel] = hashlib.sha256(norm(p.read_text("utf-8", "replace"), world, copy).encode()).hexdigest()[:12]
        else: out[rel] = f"size={p.stat().st_size}"
    return out
def run_row(copy_name, row):
    copy = copy_dir(copy_name); py = copy / ".venv" / "Scripts" / "python.exe"
    world = PR / "work" / copy_name / row["id"]
    if world.exists(): shutil.rmtree(world)
    world.mkdir(parents=True)
    for name, data in row.get("files", {}).items():
        fp = world / "files" / name; fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(data(world) if callable(data) else data)
    env = {**os.environ, "DRV_FAKE": row.get("fake", ""), "DRV_TESTS": str(copy / "tests")}
    env.pop("VIRTUAL_ENV", None)
    if not row.get("fake"): env.pop("DRV_FAKE")
    if row.get("drive"): env["DRV_DRIVE"] = json.dumps(row["drive"](world))
    steps = [row["args"]] + row.get("then", [])
    recs = []
    for i, args in enumerate(steps):
        cmd = [str(py), "-I", str(PR / "drv.py"), "both" if i == 0 else "run", str(world)]
        if i == 0: cmd += [str(MEDIA), row.get("variant", "approved")]
        cmd += ["--", *args]
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=240, cwd=str(PR / "work"))
            code, so, se = cp.returncode, cp.stdout, cp.stderr
        except subprocess.TimeoutExpired as e:
            code, so, se = "TIMEOUT", "", ""
        recs.append({"args": args, "exit": code, "stdout": norm(so, world, copy), "stderr": norm(se, world, copy)})
        if row.get("mutate") and i == 0: row["mutate"](world)
    af = (world / "AT_FILE").read_text() if (world / "AT_FILE").exists() else "MISSING"
    spy = json.loads((world / "spy.json").read_text()) if (world / "spy.json").exists() else None
    return {"id": row["id"], "at_file": af, "at_file_ok": af.startswith(str(copy)), "steps": recs, "spy": spy,
            "listing": listing(world, copy)}
def run_all(copy_name, rows, workers=6):
    with cf.ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda r: run_row(copy_name, r), rows))
    return res
