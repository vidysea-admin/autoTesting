"""Input 4: HTTP. generate refusal page, run?priority=, QueueEntry.priorities. Fake secret, throwaway root."""
import html, json, sys
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0, str(Path(__file__).parent))
from common import S, mk_root, raw_in, seed
import autotester
print("autotester.__file__ =", autotester.__file__)
from fastapi.testclient import TestClient
from autotester.ui.app import app

def forms(x):  # every recoverable rendering of S
    return {"raw": S, "html-escaped": html.escape(S), "html-escaped-noquote": html.escape(S, quote=False),
            "py-repr": repr(S)[1:-1], "json-esc": json.dumps(S, ensure_ascii=False)[1:-1],
            "json-ascii": json.dumps(S)[1:-1], "urlenc": quote(S)}
def hits(text):
    return [k for k, v in forms(S).items() if v in text]

root = mk_root("p3")
store = seed(root, f"Login {S} flow")
c = TestClient(app)

# ---- generate refusal (HAPPY not approved) ----
r = c.post("/projects/demo/cases/generate", follow_redirects=False)
print("[4a] generate (no approval):", r.status_code, r.headers.get("content-type"), "| secret forms in body:", hits(r.text))
import re
print("     message:", re.sub(r"<[^>]+>", " ", r.text.split("Case proposals need human review",1)[-1])[:170].split("Review/prune")[0].strip() if "Case proposals" in r.text else r.text[:100])
print("     case_proposals.jsonl written by the button:", raw_in(store.paths.case_proposals), "(", len(store.list_case_proposals()), "rows )")

# ---- generate refusal where a stored row is unreadable: reviewed_by carries the secret (stored by CLI --by) ----
from typer.testing import CliRunner
from autotester.cli import app as cli
hp = next(x for x in store.list_case_proposals() if x.case_class.value == "happy")
o = CliRunner().invoke(cli, ["expand", "demo", "--approve", hp.id, "--by", S])
print("[4b] CLI --approve --by <secret> exit", o.exit_code, "| stdout forms:", hits(o.output))
p = store.paths.case_proposals
rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
for row in rows:
    if row.get("reviewed_by"):
        row.pop("reviewed_at", None)          # hand-damaged row: approved, no timestamp
p.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
r = c.post("/projects/demo/cases/generate", follow_redirects=False)
print("[4b] generate with a damaged row:", r.status_code, "| secret forms in body:", hits(r.text))
i = r.text.find("validation error"); print("     excerpt:", html.unescape(re.sub(r"<[^>]+>", " ", r.text[i-80:i+420]))[:380].replace("\n"," ") if i>0 else "no pydantic text")
o = CliRunner().invoke(cli, ["expand", "demo", "--proposals"])
print("[4b] CLI --proposals on damaged row: exit", o.exit_code, "| output forms:", hits(o.output), "| out:", o.output.strip()[:200].replace("\n"," "))

# ---- run?priority= ----
for label, qs in (("priority=<secret>", f"priority={quote(S)}"), ("priority=p0&priority=<secret>", f"priority=p0&priority={quote(S)}"),
                  ("priority=p1 (valid)", "priority=p1")):
    r = c.post(f"/projects/demo/run?{qs}", follow_redirects=False)
    print(f"[4c] POST run?{label}: {r.status_code} {r.headers.get('content-type')} | secret forms in body: {hits(r.text)} | body[:200]={r.text[:200]!r}")
r = c.post(f"/projects/demo/run?priority={quote(S)}", headers={"accept": "text/html"}, follow_redirects=False)
print("[4c] same, Accept:text/html:", r.status_code, hits(r.text))
print("     .work/run_queue.json exists:", (root/".work"/"run_queue.json").exists())

# ---- QueueEntry / RunQueue persistence ----
from autotester.schema.run_queue import QueueEntry
try:
    QueueEntry(id="r1", project="demo", priorities=[S]); print("[4d] QueueEntry(priorities=[S]) ACCEPTED (!)")
except Exception as exc:
    print("[4d] QueueEntry(priorities=[S]) -> REJECTED", type(exc).__name__, "| str(exc) forms:", hits(str(exc)))
from autotester.ui.run_queue import RunQueue
qf = root / "q" / "run_queue.json"
q = RunQueue(limit=lambda: 0, spawn=lambda j: None, runner=lambda e: None, path=lambda: qf)
try:
    q.submit("demo", run_id="run-1", priorities=[S]); print("[4d] submit ACCEPTED (!)")
except Exception as exc:
    print("[4d] RunQueue.submit(priorities=[S]) -> REJECTED", type(exc).__name__, "| persisted file exists:", qf.exists(), "| in-memory entries:", len(q._entries))
q.submit("demo", run_id="run-2", priorities=["p0", "p1"])
print("[4d] valid submit persisted:", json.loads(qf.read_text())["entries"][0].get("priorities"), "| secret in file:", raw_in(qf))
# tampered queue file with bad priority: recover path
d = json.loads(qf.read_text()); d["entries"][0]["priorities"] = [S]; qf.write_text(json.dumps(d), encoding="utf-8")
import logging, io
buf = io.StringIO(); h = logging.StreamHandler(buf); lg = logging.getLogger("autotester.ui.run_queue"); lg.addHandler(h); lg.setLevel(logging.DEBUG)
logging.getLogger().addHandler(h)
q2 = RunQueue(limit=lambda: 0, spawn=lambda j: None, runner=lambda e: None, path=lambda: qf)
ents = q2._load()
print("[4d] tampered run_queue.json (priorities=[S]) -> _load entries:", len(ents), "| log text forms:", hits(buf.getvalue()))
print("     logger name:", lg.name, "| first log line:", buf.getvalue()[:140].replace("\n"," "))
