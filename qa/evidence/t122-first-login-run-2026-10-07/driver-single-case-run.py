"""Scratch driver: the UI trigger_run path, restricted to the one BEST login case (T-122)."""
import json, sys
from autotester.core.env import load_repo_env
load_repo_env()
from autotester.browser.secrets import SecretStore
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.run import Run, RunBounds
from autotester.ui import routes_runs as rr
from autotester.ui.helpers import _load_project_or_404

slug = "pathlynks"
store, project = _load_project_or_404(slug)
cases = [c for c in store.list_cases() if c.id == project.login_case_id]
assert len(cases) == 1, "login case missing"
judge = LangChainFallbackProvider()
print("judge available:", judge.available())
paths = ProjectPaths(slug)
print("root:", paths.root)
secrets = SecretStore.load(project, paths.env_file, strict=False)
keys = rr._require_declared_values(project, secrets, slug, cases)
print("account keys used (names only):", sorted(keys))
approval = rr._require_live_case_approval(project, store, cases, secrets, keys)
print("approval:", approval.id, approval.run_kind.value, approval.granted_by, approval.max_actions, approval.wall_clock_s)
run_id = f"run-{ulid()}"
run_dir = paths.run_dir(run_id)
flags = [rr._is_entry_case(c, project) for c in cases]
plan = rr._execute_with_trace(store, run_id, secrets, project, cases, flags, run_dir, paths, slug, judge, approval)
store.save_run(Run(id=run_id, project=slug, case_ids=[c.id for c in cases], parallel_n=plan.n,
    parallel_bound_by=plan.bound_by, bounds=RunBounds(approval_id=approval.id,
    max_actions=approval.max_actions, max_probes=approval.max_probes, wall_clock_s=approval.wall_clock_s)))
print("RUN_ID", run_id)
for r in store.load_results(run_id):
    print("RESULT", r.case_id, r.outcome.value, (r.error or "")[:300])
    for e in r.evidence: print("  EV", e.kind.value, getattr(e, "path", None), str(getattr(e,"note",""))[:160])
for v in store.load_verdicts(run_id):
    print("VERDICT", v.case_id, v.result.value, v.grader_provider, v.scoreboard[:200])
