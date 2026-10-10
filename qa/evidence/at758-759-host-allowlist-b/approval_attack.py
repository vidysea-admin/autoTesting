import os, sys, tempfile, shutil, json
from pathlib import Path
root = Path(tempfile.mkdtemp(prefix="atb-appr-")); os.environ["AUTOTESTER_ROOT"]=str(root)
sys.path.insert(0, os.environ["TESTS_DIR"])
from autotester.core.consent import ApprovalRequired, is_account_derived
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import ApprovalKind as K
from autotester.schema.project import Project, SecretRef
from autotester.stages.explore_consent import covering_approval
from autotester.store.project_store import ProjectStore
from run_approval_fixture import grant_live_case_approval
import autotester.stages.explore_consent as EC; print("from", EC.__file__)
def proj(slug="demo", domains=("demo.test",), declared=True, keys=("DEMO_USER",)):
    refs=[SecretRef(key=k, domains=list(domains)) for k in keys] if declared else []
    return Project(slug=slug,name=slug,base_url="https://demo.test/app",allowed_domains=["demo.test"],secrets=refs)
def cover(store, kind=K.CRAWL, **kw):
    p=store.load_project(); return covering_approval(p,store,CrawlBounds(max_actions=50),kind=kind,**kw)
def refused(store, kind=K.CRAWL, **kw):
    try: cover(store,kind,**kw); return False
    except ApprovalRequired: return True
res=[]
def rec(name, ok): res.append(ok); print(("OK " if ok else "BAD"), name)
def fresh(slug="demo", **kw):
    shutil.rmtree(root, ignore_errors=True); root.mkdir()
    st=ProjectStore(slug, root); st.save_project(proj(slug,**kw)); (root/".env").write_text("DEMO_USER=v\nDEMO_PASS=w\n"); return st
for kind in (K.CRAWL,K.LIVE_CASE,K.READ):
    st=fresh(); row=cover(st,kind); assert is_account_derived(row)
    (root/".env").write_text(""); rec(f"{kind.name}: credential removed -> refused", refused(st,kind))
    (root/".env").write_text("DEMO_USER=v\n"); rec(f"{kind.name}: credential back -> covers again", not refused(st,kind))
st=fresh(); cover(st); st.save_project(proj(domains=("other.test",))); rec("re-scoped domain -> refused", refused(st))
st=fresh(); cover(st); st.save_project(proj(declared=False)); rec("declaration dropped -> refused", refused(st))
st=fresh(); cover(st); rec("ADVERSARIAL with derived row -> refused", refused(st,K.ADVERSARIAL))
# stale expired derived row
st=fresh(); r=cover(st); rows=[json.loads(l) for l in st.paths.approvals_file.read_text().splitlines()] if hasattr(st.paths,"approvals_file") else None
print("approvals path attr:", [a for a in dir(st.paths) if "approv" in a])
# row for another project copied in
st=fresh(); r=cover(st); other=ProjectStore("other",root); other.save_project(proj("other"))
(root/".env").write_text("")
src=[a for a in dir(st.paths) if "approv" in a][0]
sp=getattr(st.paths,src); op=getattr(other.paths,src)
op.parent.mkdir(parents=True,exist_ok=True); shutil.copy(sp,op)
rec("another project's derived row copied in + no credential -> refused", refused(other))
# human row still covers, plus remove credential
st=fresh(); grant_live_case_approval(st,project="demo",target="https://demo.test/app",run_kind=K.CRAWL)
cover(st); (root/".env").write_text("")
try: row=cover(st); rec("human row covers w/o credential (not derived)", not is_account_derived(row))
except ApprovalRequired: rec("human row covers w/o credential", False)
# human row too narrow + derived present + no credential
st=fresh(); cover(st); grant_live_case_approval(st,project="demo",target="https://demo.test/app",run_kind=K.CRAWL,max_actions=1)
(root/".env").write_text(""); rec("narrow human + derived + no cred -> refused", refused(st))
# run references an unprovisioned key
st=fresh(); cover(st); (root/".env").write_text("DEMO_USER=v\n")
rec("run narrowed to an unprovisioned key -> refused", refused(st, account_keys={"DEMO_PASS"}))
# unsigned/tampered derived row with credential removed
st=fresh(); cover(st); (root/".env").write_text("")
p=getattr(st.paths,src); t=p.read_text().replace('"max_actions": 50','"max_actions": 5000000'); p.write_text(t)
rec("tampered derived row + no cred -> refused", refused(st))
print("ALL OK" if all(res) else "SOME BAD")
