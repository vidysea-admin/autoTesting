import sys, tempfile, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from atk2 import mk
from autotester.stages.schedule_store import claim, append_record, purge_project, list_claims, project_records_path
import autotester; print("autotester.__file__ =", autotester.__file__)
import re
slug = re.compile(r"^[a-z][a-z0-9-]*$")
for names, label in ((["a","ab","a-b","a1"], "valid slugs"), (["a","a:x"], "hypothetical ':' name (not a valid slug)")):
    b = Path(tempfile.mkdtemp(prefix="atk6-", dir=sys.argv[1]))
    for n in names:
        k,c,r = mk(n,0); claim(b/"claims",k,c); append_record(project_records_path(b/"records",n), r)
    purge_project(b/"claims", project_records_path(b/"records","a"), "a")
    left = sorted(list_claims(b/"claims"))
    print(f"{label}: slug-valid={[bool(slug.fullmatch(n)) for n in names]} | after purge('a') claims left={left} | record files={sorted(x.name for x in (b/'records').iterdir())}")
    shutil.rmtree(b, ignore_errors=True)
