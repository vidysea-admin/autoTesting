"""Checker A: AT-759 own scenarios. PYTHONPATH=<tree>/src; prints COVERS or REFUSED per scenario."""
import os
import sys
import tempfile
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix="atk759_"))
os.environ["AUTOTESTER_ROOT"] = str(root)
sys.path.insert(0, os.environ["TREE"] + "/tests")

import autotester  # noqa: E402
from autotester.core.consent import ApprovalRequired, is_account_derived  # noqa: E402
from autotester.schema.crawl import CrawlBounds  # noqa: E402
from autotester.schema.enums import ApprovalKind  # noqa: E402
from autotester.schema.project import Project, SecretRef  # noqa: E402
from autotester.stages.explore_consent import covering_approval  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402

print("tree:", autotester.__file__)


def project(domains=("demo.test",), declared=True):
    refs = [SecretRef(key="DEMO_USER", domains=list(domains))] if declared else []
    return Project(slug="demo", name="Demo", base_url="https://demo.test/app",
                   allowed_domains=["demo.test"], secrets=refs)


def cover(store, kind, **kw):
    p = store.load_project()
    return covering_approval(p, store, CrawlBounds(max_actions=50), kind=kind, **kw)


def fresh():
    import shutil
    d = Path(tempfile.mkdtemp(prefix="s_", dir=root))
    os.environ["AUTOTESTER_ROOT"] = str(d)
    st = ProjectStore("demo", d)
    st.save_project(project())
    (d / ".env").write_text("DEMO_USER=synthetic-account-value\n", encoding="utf-8")
    return st, d


def verdict(label, fn):
    try:
        a = fn()
        print(f"{label}: COVERS by {'account-derived' if is_account_derived(a) else 'human'} row {a.id[:8]}")
    except ApprovalRequired:
        print(f"{label}: REFUSED")


for kind in (ApprovalKind.CRAWL, ApprovalKind.LIVE_CASE, ApprovalKind.READ):
    st, d = fresh()
    minted = cover(st, kind)
    assert is_account_derived(minted), "setup: the minted row is account-derived"
    verdict(f"{kind.name} baseline (credential present)", lambda: cover(st, kind))
    (d / ".env").unlink()
    verdict(f"{kind.name} after .env removed", lambda: cover(st, kind))
    (d / ".env").write_text("DEMO_USER=synthetic-account-value\n", encoding="utf-8")
    st.save_project(project(domains=("x.test",)))
    verdict(f"{kind.name} after credential domain re-scoped", lambda: cover(st, kind))
    st.save_project(project(declared=False))
    verdict(f"{kind.name} after declaration dropped", lambda: cover(st, kind))
    st.save_project(project())
    (d / ".env").write_text("OTHER=1\n", encoding="utf-8")
    verdict(f"{kind.name} after value blanked (key absent)", lambda: cover(st, kind))
    print(f"   rows on disk: {len(st.list_approvals())}")

st, d = fresh()
cover(st, ApprovalKind.CRAWL)
verdict("ADVERSARIAL with account row present", lambda: cover(st, ApprovalKind.ADVERSARIAL))
from run_approval_fixture import grant_live_case_approval  # noqa: E402

(d / ".env").unlink()
h = grant_live_case_approval(st, target="https://demo.test/app")
verdict("human LIVE_CASE row, credential gone", lambda: cover(st, ApprovalKind.LIVE_CASE))
verdict("ADVERSARIAL, human live_case row only", lambda: cover(st, ApprovalKind.ADVERSARIAL))
