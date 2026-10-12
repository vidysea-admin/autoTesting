"""OUTSIDE the seam: raw headless Chromium asked to bind 0.0.0.0, to see what _reaches_past_loopback reports."""
import json, tempfile, time, socket
from pathlib import Path
import h
from autotester.browser import launch as L
from playwright.sync_api import sync_playwright
tmp = Path(tempfile.mkdtemp(prefix="r2b-raw-"))
out = {}
with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(str(tmp / "p"), headless=True,
        args=["--remote-debugging-address=0.0.0.0", "--remote-debugging-port=0", "--no-sandbox"])
    pf = tmp / "p" / "DevToolsActivePort"
    for _ in range(100):
        if pf.exists() and len(pf.read_text().splitlines()) >= 2: break
        time.sleep(0.1)
    port = int(pf.read_text().splitlines()[0]); out["port"] = port
    out["accepts_127.0.0.1"] = h.accepts("127.0.0.1", port, 2)
    out["accepts_127.0.0.2"] = h.accepts("127.0.0.2", port, 2)
    lan = socket.gethostbyname(socket.gethostname()); out["lan_ip"] = lan
    out["accepts_lan_ip"] = h.accepts(lan, port, 2)
    t = time.monotonic(); out["_reaches_past_loopback"] = L._reaches_past_loopback(port); out["rpl_s"] = round(time.monotonic() - t, 2)
    ctx.close()
print(json.dumps(out, indent=1))
