import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, r"D:\autoTesting\.worktrees\t209-leak-severity\src")
os.environ["AUTOTESTER_LEAK_EVIDENCE_KEY"] = "synthetic-b-c1"
from autotester.schema.multi_role_enums import FindingClass
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.stages import leak_evidence as stage
run = Path(tempfile.mkdtemp(dir=r"D:\autoTesting\.work\tmp"))
raw = "cus_Nffrf7JkLm3pQw"
ev = stage.collect_leak_evidence(project_slug="d", run_dir=run, finding_id="s-1", rows=[{"id": raw}], id_field="id", url=f"https://a.test/students/{raw}")
f = MultiRoleFinding(finding_id="s-1", finding_class=FindingClass.DATA_LEAK, title="t", role="Parent", platform_id="parent",
    url_template=ev.url_template, count=1, steps=["login as Parent", f"goto /students/{raw}", "fill Name = Jane Doe"], leak_evidence=ev)
p = stage.write_finding(run, f)
t = p.read_text(encoding="utf-8")
print("raw id in steps persisted:", raw in t, "| 'Jane Doe' persisted:", "Jane Doe" in t)
