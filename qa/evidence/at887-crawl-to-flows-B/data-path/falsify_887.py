"""B coordinator falsifications for AT-887: each in its own copy on C:, green before, red after."""
import os, shutil, subprocess, sys
from pathlib import Path
S = Path(sys.argv[1]); SRC = S/"b-copy"; PY = S/"venv-b2/Scripts/python.exe"; WORK = S/"b-fal"
shutil.rmtree(WORK, ignore_errors=True); WORK.mkdir()
M = "src/autotester/stages/explore_merge.py"; F = "src/autotester/stages/explore_flows.py"
T = "tests/test_explore_flows.py"
CASES = [
 ("F1 review DRAFT reset removed", M, '"review": Review(\n            status=ReviewStatus.DRAFT,\n            note=f"{added} screen(s), {len(new)} flow(s)', '"review": merged.review if True else Review(\n            status=ReviewStatus.DRAFT,\n            note=f"{added} screen(s), {len(new)} flow(s)', T+"::test_merge_adds_flows_as_draft_and_never_approves"),
 ("F2 skip-existing filter dropped", M, "new = [f for f in proposed if merged.flow(f.id) is None]", "new = list(proposed)", T+"::test_merge_never_overwrites_a_reviewed_flow_and_re_arms_the_gate"),
 ("F3 typed edges replayable", F, "_CLICKED = {Action.CLICK, Action.NAVIGATE}", "_CLICKED = set(Action)", T+"::test_a_screen_reached_only_through_typed_input_gets_no_flow"),
 ("F4 input sort removed", F, "by_node = {n.id: n for n in sorted(nodes, key=lambda n: n.id)}", "by_node = {n.id: n for n in nodes}", T+"::test_same_crawl_same_proposals_whatever_the_storage_order"),
 ("F5 flow id depends on crawl id", F, 'identity = {"nodes": [n.id for n in path], "targets": [e.target for e in chain]}', 'identity = {"nodes": [n.id for n in path], "targets": [e.target for e in chain], "c": crawl_id}', T+"::test_ids_are_the_path_not_the_crawl_so_a_re_crawl_adds_nothing"),
 ("F6 version bumped twice", M, '"version": merged.version if bumped else merged.version + 1,', '"version": merged.version + 1,', T+"::test_flows_for_screens_the_spec_already_knows_still_bump_the_version_once"),
 ("F7 unnavigated edges replayable", F, "or edge.outcome is not EdgeOutcome.NAVIGATED or edge.action not in _CLICKED", "or edge.action not in _CLICKED", T+"::test_orphans_cycles_and_unnavigated_discoveries_are_skipped_not_guessed"),
 ("F8 door: CLI merges screens only", "src/autotester/cli_crawl.py", "spec = merge_stored_crawl(store_, before, project, crawl_id)", "spec = __import__('autotester.stages.explore_merge', fromlist=['x']).merge_screens(before, store_.list_nodes(crawl_id), project, crawl_id=crawl_id)", "tests/test_explore_flows_doors.py::test_the_cli_door_proposes_flows_and_says_so"),
 ("F9 door: UI merges screens only", "src/autotester/ui/routes_crawls.py", "spec = merge_stored_crawl(store, store.load_flowspec(), slug, crawl_id)", "spec = __import__('autotester.stages.explore_merge', fromlist=['x']).merge_screens(store.load_flowspec(), store.list_nodes(crawl_id), slug, crawl_id=crawl_id)", "tests/test_explore_flows_doors.py::test_the_ui_button_proposes_flows_and_never_approves"),
 ("F10 door: DISCOVER merges screens only", "src/autotester/stages/orchestrate_runners.py", "spec = merge_screens_and_flows(None, nodes, ctx.store.list_edges(crawl.id), project.slug,\n                           crawl_id=crawl.id, login_case_id=crawl.login_case_id)", "from autotester.stages.explore_merge import merge_screens\n        spec = merge_screens(None, nodes, project.slug, crawl_id=crawl.id)", "tests/test_explore_flows_doors.py::test_orchestrated_discover_parks_flow_proposals_in_its_draft"),
]
def run(d, node):
    env = dict(os.environ, PYTHONPATH=str(d/"src"), AUTOTESTER_ALLOWED_HOSTS="testserver")
    chk = subprocess.run([str(PY), "-c", "import autotester;print(autotester.__file__)"], env=env, cwd=d, capture_output=True, text=True).stdout.strip()
    r = subprocess.run([str(PY), "-m", "pytest", "-p", "no:xdist", "-o", "addopts=", "-p", "no:cacheprovider", node, "--tb=line", "-q"], env=env, cwd=d, capture_output=True, text=True, timeout=600)
    tail = [l for l in r.stdout.splitlines() if l.strip()][-4:]
    return chk, r.returncode, tail
for name, rel, old, new, node in CASES[5:]:
    d = WORK/name.split()[0]
    shutil.copytree(SRC, d, ignore=shutil.ignore_patterns("qa", ".goal", "docs", ".git", "__pycache__", "projects", "uv.lock", ".venv"))
    chk, rc0, t0 = run(d, node)
    p = d/rel; txt = p.read_text(encoding="utf-8")
    assert txt.count(old) == 1, (name, txt.count(old))
    p.write_text(txt.replace(old, new), encoding="utf-8")
    _, rc1, t1 = run(d, node)
    print(f"{name}: import={'copy' if str(d) in chk else 'WRONG:'+chk} green-before rc={rc0} | after rc={rc1} :: {' / '.join(t1)[:300]}", flush=True)
    shutil.rmtree(d, ignore_errors=True)
shutil.rmtree(WORK, ignore_errors=True)
