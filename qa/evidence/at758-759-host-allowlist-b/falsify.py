import shutil, subprocess, sys, os
from pathlib import Path
S=Path(sys.argv[1]); base=S/"base"; PY="D:/autoTesting/.venv/Scripts/python.exe"
H="src/autotester/ui/helpers.py"; EC="src/autotester/stages/explore_consent.py"
T1="tests/test_ui_origin_guard.py"; T4="tests/test_credential_run_approval.py"
M=[
 ("C1a","helpers",H,'or not _host_allowed(headers["host"])','or False',[f"{T1}::test_the_rebinding_repro_cannot_read_a_saved_credential_but_loopback_can"]),
 ("C1b","helpers",H,'return host in _listed("AUTOTESTER_ALLOWED_HOSTS") | set(origins)','return True',[f"{T1}::test_hosts_of_the_allowed_origins_and_the_hosts_variable_are_added_exactly"]),
 ("C1c","helpers (GET exempt from Host check)",H,'if (names.count("host") != 1 or names.count("origin") > 1\n                    or not _host_allowed(headers["host"])):','if scope["method"] in _UNSAFE_METHODS and (names.count("host") != 1 or names.count("origin") > 1\n                    or not _host_allowed(headers["host"])):',[f"{T1}::test_a_host_outside_the_allow_list_gets_an_empty_403_on_every_method"]),
 ("C2a","origin port",H,'_ = parts.port  # AT-760: raises','_ = None  # AT-760: raises',[f"{T1}::test_an_origin_with_an_unparsable_port_is_refused"]),
 ("C2b","host port",H,'        parts = urlparse("//" + host)\n        _ = parts.port','        parts = urlparse("//" + host)\n        _ = None',[f"{T1}::test_a_host_outside_the_allow_list_gets_an_empty_403_on_every_method"]),
 ("C3a","dup origin",H,'names.count("origin") > 1','names.count("origin") > 2',[f"{T1}::test_more_than_one_origin_or_host_header_is_refused"]),
 ("C3b","dup host",H,'names.count("host") != 1','names.count("host") == 0',[f"{T1}::test_more_than_one_origin_or_host_header_is_refused"]),
 ("C4a","fallback sees derived rows",EC,"        try:  # credentials unavailable: a human-granted row can still cover it, as before D-068\n            return _require(human,","        try:  # credentials unavailable: a human-granted row can still cover it, as before D-068\n            return _require(rows,",[f"{T4}::test_an_account_row_stops_covering_when_its_credential_is_gone"]),
 ("C4b","no-secrets path sees derived rows",EC,"        return _require(human, project, kind, bounds)\n    try:","        return _require(rows, project, kind, bounds)\n    try:",[f"{T4}::test_an_account_row_stops_covering_when_its_credential_is_gone"]),
]
out=[]
def run(cwd, nodes):
    env=dict(os.environ); env["PYTHONPATH"]=str(cwd/"src"); env.pop("AUTOTESTER_ALLOWED_HOSTS",None)
    r=subprocess.run([PY,"-m","pytest","-p","no:xdist","-p","no:cacheprovider",*nodes],cwd=cwd,env=env,capture_output=True,text=True)
    tail=[l for l in r.stdout.splitlines() if l.strip()][-1]
    fails=[l for l in r.stdout.splitlines() if l.startswith("FAILED")]
    return r.returncode, tail, fails, r.stdout
for cid,name,f,old,new,nodes in M:
    d=S/f"mut-{cid}"; shutil.rmtree(d,ignore_errors=True)
    shutil.copytree(base,d,ignore=shutil.ignore_patterns("__pycache__",".venv",".pytest_cache"))
    g=run(d,nodes)
    p=d/f; t=p.read_text(encoding="utf-8")
    assert t.count(old)==1,(cid,t.count(old)); p.write_text(t.replace(old,new),encoding="utf-8")
    r=run(d,nodes)
    # failing reason: assertion vs import error
    import_err = "ImportError" in r[3] or "SyntaxError" in r[3] or "collected 0" in r[3]
    line=f"{cid} [{name}] green-before: rc={g[0]} '{g[1]}' | after: rc={r[0]} '{r[1]}' importerr={import_err} failed={len(r[2])}"
    print(line, flush=True); out.append(line)
    if r[2]: print("   e.g.", r[2][0][:170])
    shutil.rmtree(d,ignore_errors=True)
Path(S/"falsify_out.txt").write_text("\n".join(out))
