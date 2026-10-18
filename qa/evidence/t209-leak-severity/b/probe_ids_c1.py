"""Checker B cycle 1: random opaque ids through templatise_url AND the bytes write_finding writes.

All ids are synthetic. Run with the worktree venv python; TMP/TEMP=D:/autoTesting/.work/tmp.
"""
import os
import random
import string
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, r"D:\autoTesting\.worktrees\t209-leak-severity\src")
os.environ["AUTOTESTER_LEAK_EVIDENCE_KEY"] = "synthetic-checker-b-master-key-c1"
from autotester.schema.leak_evidence import LeakEvidence, validate_url_template  # noqa: E402
from autotester.schema.multi_role_enums import FindingClass  # noqa: E402
from autotester.schema.multi_role_finding import MultiRoleFinding  # noqa: E402
from autotester.stages import leak_evidence as stage  # noqa: E402

random.seed(11)
b62 = string.ascii_letters + string.digits
b64u = b62 + "-_"
crock = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
low36 = string.ascii_lowercase + string.digits
FMTS = {
    "nanoid21": lambda: "".join(random.choices(b64u, k=21)),
    "base62-22": lambda: "".join(random.choices(b62, k=22)),
    "stripe-like cus_+14": lambda: "cus_" + "".join(random.choices(b62, k=14)),
    "cuid2-24": lambda: random.choice(string.ascii_lowercase) + "".join(random.choices(low36, k=23)),
    "ULID-26": lambda: "".join(random.choices(crock, k=26)),
    "objectid-24 hex": lambda: "".join(random.choices("0123456789abcdef", k=24)),
    "uuid4": lambda: str(uuid.uuid4()),
    "numeric 1-9 digits": lambda: str(random.randint(1, 10**9)),
    # extra, beyond the maker's list
    "hex8": lambda: "".join(random.choices("0123456789abcdef", k=8)),
    "letters-only-22": lambda: "".join(random.choices(string.ascii_letters, k=22)),
    "short-alpha-5": lambda: "".join(random.choices(string.ascii_lowercase, k=5)),
    "short-token-6 b62": lambda: "".join(random.choices(b62, k=6)),
    "name-slug john-smith": lambda: random.choice(["john", "mary", "zorblax"]) + "-" + random.choice(["smith", "quimby", "lee"]),
    "name.dotted": lambda: "jane.doe" + str(random.randint(0, 9)),
    "name%20encoded": lambda: "Jane%20Doe",
    "ext json": lambda: "".join(random.choices(low36, k=10)) + ".json",
    "semicolon param": lambda: "x;jsessionid=" + "".join(random.choices(low36, k=12)),
}
N = 1000
run = Path(tempfile.mkdtemp(prefix="chkb-c1-", dir=r"D:\autoTesting\.work\tmp"))
print("per format: kept-in-template / refused-by-validate-accepted / bytes-in-written-file (N=%d)" % N)
total_bad = 0
for name, g in FMTS.items():
    kept = acc = wr = 0
    for i in range(N):
        raw = g()
        out = stage.templatise_url(f"https://a.test/students/{raw}/profile")
        if raw in out:
            kept += 1
        try:
            validate_url_template(f"/students/{raw}")
            acc += 1
        except ValueError:
            pass
        if i < 40:
            ev = stage.collect_leak_evidence(
                project_slug="demo", run_dir=run, finding_id=f"leak-{i}", rows=[{"id": raw, "Name": "X"}],
                id_field="id", url=f"https://a.test/students/{raw}?id={raw}&n=Jane")
            f = MultiRoleFinding(
                finding_id=f"leak-{i}", finding_class=FindingClass.DATA_LEAK, title="t", role="Parent",
                platform_id="parent", url_template=ev.url_template, count=1,
                steps=["login as Parent"], leak_evidence=ev)
            p = stage.write_finding(run, f)
            import json
            doc = json.loads(p.read_text(encoding="utf-8"))
            doc["leak_evidence"]["hashed_ids"] = []  # hex hashes can contain decimal substrings by chance
            if raw in json.dumps(doc):
                wr += 1
    total_bad += kept + acc + wr
    print(f"{name:24s} template-kept {kept}/{N}  validate-accepted {acc}/{N}  file-has-raw {wr}/40")
# grep every written byte under the run dir for any raw id generated
print("TOTAL violations:", total_bad)
print("run dir files:", sum(1 for _ in run.rglob('*') if _.is_file()))

# named residual: a route word as an id value, and case/extension variants
for seg in ["students", "Students", "STUDENTS", "settings", "students.json", "task", "test"]:
    print("route-word probe", seg, "->", stage.templatise_url(f"https://a.test/x/{seg}"))
# query keys and host
for u in ["https://a.test/students?JohnSmith=1&V1StGXR8_Z5jdHi6B-myT=2&abcdefghijklmnopqrstuv=3",
          "https://jane-doe.tenant.test:8443/students/{id}", "https://u:pw@a.test/students#frag"]:
    t = stage.templatise_url(u)
    try:
        validate_url_template(t)
        ok = "accepted"
    except ValueError as e:
        ok = f"refused({e})"
    print("url probe", u, "->", t, ok)
