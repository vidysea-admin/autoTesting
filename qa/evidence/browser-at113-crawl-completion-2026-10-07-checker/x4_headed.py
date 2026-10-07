"""Checker-owned headed X4 fixture. root -> /fill-child -> FILL #trigger -> /fill-out (depth 2).
With max_depth=1 the depth bound latches at the FILL; nothing browser-side may happen after it:
no FILL #second, no navigation back to /fill-child. Server-side request log is the witness."""
import functools
import http.server
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])           # evidence dir
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

from autotester.browser.observe import PageObserver  # noqa: E402
from autotester.browser.secrets import SecretStore  # noqa: E402
from autotester.browser.session import BrowserSession  # noqa: E402
from autotester.core.paths import ProjectPaths  # noqa: E402
from autotester.schema.crawl import CrawlBounds, SafetyPolicy  # noqa: E402
from autotester.schema.enums import TraversalStrategy, WritePolicy  # noqa: E402
from autotester.schema.project import Project  # noqa: E402
from autotester.stages.explore import run_crawl  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402
import os; os.environ["AUTOTESTER_APPROVAL_KEY"] = "checker-local-fixture-only-key"
import crawl_live  # noqa: E402
import autotester; print("AUTOTESTER", autotester.__file__)

PAGES = {
    "/": '<html><body><h1>root</h1><a href="/fill-child">child</a></body></html>',
    "/fill-child": (
        '<html><body><h1>child</h1>'
        '<input id="trigger" type="text" aria-label="Trigger">'
        '<input id="second" type="text" aria-label="Second">'
        '<script>'
        'document.getElementById("trigger").addEventListener("input",function(){'
        'fetch("/log?field=trigger").finally(function(){location.href="/fill-out";});});'
        'document.getElementById("second").addEventListener("input",function(){'
        'fetch("/log?field=second");});'
        '</script></body></html>'),
    "/fill-out": '<html><body><h1>out</h1><a href="/deeper">deeper</a></body></html>',
    "/deeper": '<html><body><h1>deeper</h1></body></html>',
}
LOG: list[tuple[float, str]] = []


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        LOG.append((time.time(), self.path))
        path = self.path.split("?")[0]
        if path == "/log":
            body, ctype = b"ok", "text/plain"
        elif path in PAGES:
            body, ctype = PAGES[path].encode(), "text/html"
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def run(strategy: TraversalStrategy) -> dict:
    LOG.clear()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    bounds = CrawlBounds(max_screens=20, max_actions=50, wall_clock_s=120.0, max_depth=1,
                         dialog_repeat_limit=2)
    policy = SafetyPolicy(write_policy=WritePolicy.TEST_ACCOUNT, synthetic_typing=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        slug = f"x4-{strategy.value}"
        project = Project(slug=slug, name=slug, base_url=base + "/",
                          allowed_domains=["127.0.0.1"], headed=True,
                          write_policy=WritePolicy.TEST_ACCOUNT)
        paths = ProjectPaths(slug, tmp); paths.ensure()
        env = tmp / ".env"; env.write_text("", encoding="utf-8")
        secrets = SecretStore.load(project, env, strict=False)
        store = ProjectStore(slug, tmp)
        crawl_live.grant(store, project, bounds)
        obs = PageObserver()
        session = BrowserSession(project, secrets, tmp / "shots", paths, observer=obs)
        session.start()
        try:
            crawl = run_crawl(project, session, store, observer=obs, bounds=bounds,
                              policy=policy, strategy=strategy)
        finally:
            session.close()
        nodes = [(n.url_template, n.depth, n.status.value) for n in store.list_nodes(crawl.id)]
        edges = [(e.action.value, e.selector if hasattr(e, "selector") else None,
                  e.outcome.value) for e in store.list_edges(crawl.id)] if hasattr(store, "list_edges") else None
    server.shutdown(); server.server_close()
    reqs = [p for _, p in LOG]
    out_idx = next((i for i, p in enumerate(reqs) if p.startswith("/fill-out")), None)
    after_out = reqs[out_idx + 1:] if out_idx is not None else None
    return {"strategy": strategy.value, "status": crawl.status.value, "stop_reason": crawl.stop_reason,
            "actions": crawl.actions, "requests": reqs, "after_fill_out_requests": after_out,
            "second_filled": any(p.startswith("/log?field=second") for p in reqs),
            "trigger_filled": any(p.startswith("/log?field=trigger") for p in reqs),
            "fill_child_loads": sum(1 for p in reqs if p == "/fill-child"),
            "nodes": nodes, "edges": edges}


res = [run(s) for s in (TraversalStrategy.BFS, TraversalStrategy.HYBRID)]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "report.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
print(json.dumps(res, indent=2))
