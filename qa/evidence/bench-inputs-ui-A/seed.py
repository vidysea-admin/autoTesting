import json
from datetime import UTC, datetime, timedelta
from autotester.auth import accounts, groups
from autotester.schema.crawl import Crawl, CrawlIssue
from autotester.schema.enums import CrawlStatus, IssueKind, Result
from autotester.schema.project import Project
from autotester.schema.run import Run
from autotester.schema.verdict import Failure, Verdict
from autotester.store.project_store import ProjectStore
from autotester.core.paths import repo_root
root = repo_root()
print("root", root)
PW = "correct-horse-battery"
accounts.signup("admin@team.test", PW)
for email, perms in (("editor@team.test", ["project.view@all","project.edit@all","report.view@all"]),
                     ("viewer@team.test", ["project.view@all","report.view@all"])):
    uid = accounts.signup(email, PW).id
    accounts.set_user_groups(uid, [groups.create_group("g-"+email, perms).id])
accounts.signup("nogroup@team.test", PW)
store = ProjectStore("demo", root)
store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"]))
store.save_crawl(Crawl(project="demo", id="crawl_1", status=CrawlStatus.STOPPED_BOUND, stop_reason="max_actions", screens=1, issues=2))
store.add_crawl_issue(CrawlIssue(crawl_id="crawl_1", project="demo", kind=IssueKind.NETWORK, node_id="n1", detail="https://demo.test/api/status -> 502"))
store.add_crawl_issue(CrawlIssue(crawl_id="crawl_1", project="demo", kind=IssueKind.NETWORK, node_id="n2", detail="https://demo.test/api/other -> 500 <b>x</b>"))
t0 = datetime(2026,10,21,tzinfo=UTC)
store.save_run(Run(id="run_1", project="demo", case_ids=["c1"], started_at=t0, finished_at=t0+timedelta(seconds=9)))
store.save_verdict("run_1", Verdict(run_id="run_1", case_id="c1", result=Result.FAIL, failures=[Failure(criterion_id="k", reason="boom <script>alert(1)</script>")]))
# second project the viewer/editor scope test
store2 = ProjectStore("other", root)
store2.save_project(Project(slug="other", name="Other", base_url="https://o.test", allowed_domains=["o.test"]))
print("seeded")
