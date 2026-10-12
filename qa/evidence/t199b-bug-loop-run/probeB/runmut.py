import subprocess, sys, os
P="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/probeB/"
V="C:/Users/Lenovo/AppData/Local/Temp/ck_t199b_1908911042/venv/Scripts/python.exe"
N={"tb9":"test_tb9_no_write_without_a_confirmation_and_none_after_the_plan_changed","tb10":"test_tb10_a_cell_a_human_edited_is_not_overwritten_and_the_conflict_is_reported","tb11":"test_tb11_syncing_twice_makes_no_duplicate_rows_and_the_second_plan_is_empty","tb13":"test_tb13_a_planted_secret_is_in_neither_the_plan_nor_its_rendering_nor_the_sheet"}
def run(tree, node):
    env={k:v for k,v in os.environ.items() if k!="VIRTUAL_ENV"}; env["PYTHONPATH"]=P+tree+"/src"; env["PYTHONDONTWRITEBYTECODE"]="1"
    w=subprocess.run([V,"-c","import autotester;print(autotester.__file__)"],cwd=P+tree,env=env,capture_output=True,text=True,timeout=170).stdout.strip()
    r=subprocess.run([V,"-m","pytest","-p","no:xdist","-p","no:cacheprovider","-o","addopts=","tests/test_sheet_plan.py::"+node,"-x","--tb=short"],cwd=P+tree,env=env,capture_output=True,text=True,timeout=170)
    return w, r.stdout
for m,node in N.items():
    if len(sys.argv)>1 and m not in sys.argv[1:]: continue
    print("########",m,node)
    w,o=run("mut_base",node); print(" BASE __file__:",w); print("\n".join(o.strip().splitlines()[-2:]))
    w,o=run("mut_"+m,node); print(" MUT  __file__:",w); L=o.strip().splitlines()
    print("\n".join(l for l in L if l.startswith(("E ","tests/","> ")) or "passed" in l or "failed" in l or "error" in l.lower())[:1500])
