"""R1-B item 2: happy path, expose off vs on, real headless Chromium, local 127.0.0.1 page only."""
import json, os, socket, subprocess, sys, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
SRC = os.environ["R1B_SRC"]; sys.path.insert(0, SRC + "/src"); sys.path.insert(0, SRC + "/tests")
import autotester
from test_browser import make_project, make_store
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
WORK = Path(os.environ["R1B_WORK"]); WORK.mkdir(parents=True, exist_ok=True)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        b = b"<html><title>local page</title><body>hello</body></html>"
        self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
web = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=web.serve_forever, daemon=True).start()
PAGE = f"http://127.0.0.1:{web.server_address[1]}/"

def ps(cmd): return subprocess.run(["powershell","-NoProfile","-Command",cmd],capture_output=True,text=True,timeout=90).stdout
def browser_pids(profile):
    n = str(profile).lower().replace("'", "''")
    out = ps("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.ToLower().Contains('%s') -and $_.Name -notlike 'powershell*' } | ForEach-Object { $_.ProcessId }" % n)
    return [int(x) for x in out.split() if x.isdigit()]
def listeners(pids):
    if not pids: return []
    out = ps("Get-NetTCPConnection -State Listen | Where-Object { @(%s) -contains $_.OwningProcess } | ForEach-Object { '{0}:{1}' -f $_.LocalAddress,$_.LocalPort }" % ",".join(map(str,pids)))
    return sorted(set(out.split()))
def acc(host, port):
    fam = socket.AF_INET6 if ":" in host else socket.AF_INET
    s = socket.socket(fam); s.settimeout(3)
    try: s.connect((host, port)); return True
    except OSError as e: return False
    finally: s.close()
def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(("192.0.2.1", 9)); return s.getsockname()[0]
    finally: s.close()

def run(expose, tag):
    from autotester.schema.project import Project
    from autotester.schema.secrets import SecretRef  # may not exist
    return None
def mk(root, expose):
    import autotester.schema.project as sp
    proj = make_project(headed=False)
    proj = proj.model_copy(update={"allowed_domains": ["127.0.0.1"], "base_url": PAGE})
    return BrowserSession(proj, make_store(root), root/"run", ProjectPaths("pathlynks", root), expose_cdp=expose)

for expose in (False, True):
    root = WORK / f"exp{int(expose)}"; root.mkdir(parents=True, exist_ok=True)
    profile = root/"profiles"/"pathlynks"
    s = mk(root, expose); rec = {"src": SRC.split("/")[-1], "expose": expose}
    s.start()
    try:
        s.goto(PAGE)
        pids = browser_pids(profile); rec["browser_pids"] = len(pids)
        rec["cdp_url"] = s.cdp_url
        pf = profile/"DevToolsActivePort"; rec["port_file"] = pf.read_text().splitlines() if pf.exists() else None
        rec["listening_sockets_of_browser_tree"] = listeners(pids)
        if expose:
            port = int(s.cdp_url.rsplit(":",1)[1]); lan = lan_ip(); rec["lan_ip"]=lan
            rec["accepts"] = {h: acc(h, port) for h in ("127.0.0.1","127.0.0.2",lan,"::1")}
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            v = json.load(opener.open(s.cdp_url+"/json/version", timeout=5))
            ws = v["webSocketDebuggerUrl"]; rec["ws_path_matches_file"] = ws.endswith(rec["port_file"][1]); rec["ws"]=ws.replace(str(port),"<port>")
            lst = json.load(opener.open(s.cdp_url+"/json/list", timeout=5)); rec["page_urls_via_cdp"] = [t["url"] for t in lst if t.get("type")=="page"]
            rec["port"] = port
    finally:
        s.close()
    time.sleep(1.5)
    rec["after_close"] = {"cdp_url": s.cdp_url, "port_file_exists": (profile/"DevToolsActivePort").exists(), "procs": browser_pids(profile)}
    if expose: rec["after_close"]["port_accepts"] = acc("127.0.0.1", rec["port"])
    print(json.dumps(rec), flush=True)
web.shutdown()
