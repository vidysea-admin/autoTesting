import json, os, sys, time, threading, socket, subprocess
from pathlib import Path
SRC = os.environ["R1B_SRC"]; sys.path.insert(0, SRC + "/src"); sys.path.insert(0, SRC + "/tests")
from test_browser import make_project, make_store
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
root = Path(os.environ["R1B_WORK"]); root.mkdir(parents=True, exist_ok=True)
profile = root/"profiles"/"pathlynks"
def ps(c): return subprocess.run(["powershell","-NoProfile","-Command",c],capture_output=True,text=True,timeout=90).stdout
def pids():
    n=str(profile).lower().replace("'","''")
    return [x for x in ps("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.ToLower().Contains('%s') -and $_.Name -notlike 'powershell*' } | ForEach-Object { '{0}:{1}' -f $_.ProcessId,$_.Name }"%n).split() if ":" in x]
def acc(h,p):
    try: socket.create_connection((h,p),timeout=3).close(); return True
    except OSError: return False
T0=time.monotonic()
def log(**k): print(json.dumps({"t":round(time.monotonic()-T0,1),**k}),flush=True)
proj = make_project(headed=True)
s = BrowserSession(proj, make_store(root), root/"run", ProjectPaths("pathlynks", root), expose_cdp=True)
try:
    s.start(); u=s.cdp_url; log(ev="started", cdp_url=u, procs=pids())
    port=int(u.rsplit(":",1)[1]); log(ev="accepts", a127_1=acc("127.0.0.1",port), a127_2=acc("127.0.0.2",port), lan=acc("192.168.1.4",port))
    time.sleep(3)
except BaseException as e:
    log(ev="start_raised", exc=f"{type(e).__name__}: {e}", procs=pids()); 
    sys.exit(3)
log(ev="close_begin")
s.close()
log(ev="close_returned", procs=pids(), port_file=(profile/"DevToolsActivePort").exists(), port_accepts=acc("127.0.0.1",port))
