import httpx, re, subprocess, sys
from autotester.stages.bench_from_run import bench_from_run
from autotester.store.project_store import ProjectStore
from pathlib import Path
R = Path(r"D:\autoTesting\.work\tmp\bi-A\root")
store = ProjectStore("demo", R); bench_from_run(store, "demo", "run_1", crawl_ids=["crawl_1"])
B = "http://127.0.0.1:8765"; H = {"Origin": B}
c = httpx.Client(base_url=B, follow_redirects=False, timeout=60); c.post("/auth/login", data={"email":"editor@team.test","password":"correct-horse-battery"}, headers=H)
k = lambda p: re.findall(r"name='finding' value='([0-9a-f]{16})'", c.get(p).text)
ck, rk = sorted(set(k("/projects/demo/crawls/crawl_1"))), sorted(set(k("/projects/demo/runs/run_1")))
def cmp(label):
    o = subprocess.run([sys.executable, r"D:\autoTesting\.worktrees\bench-inputs-ui\scripts\check_acceptance_comparison.py", "demo", "--root", str(R)], capture_output=True, text=True)
    print(f"--- {label} rc={o.returncode}"); print("\n".join(l for l in o.stdout.splitlines() if "FP rate" in l or "fp_rate" in l))
cmp("no marks")
post = lambda key, v: c.post("/projects/demo/bench/marks", data={"finding":key,"verdict":v}, headers=H).status_code
post(ck[0], "false_positive"); cmp("1 crawl finding FP, other 2 unmarked")
post(rk[0], "real"); cmp("+ run finding real -> 1 real 1 fp, 1 unmarked")
post(ck[1], "real"); cmp("+ second crawl real -> 2 real 1 fp")
for key in (ck[0], rk[0], ck[1]): post(key, "clear")
cmp("all undone")
