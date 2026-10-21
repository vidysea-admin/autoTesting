import os, shutil, subprocess, sys, json
SRC = r"D:\autoTesting\.worktrees\bench-inputs-ui"
WORK = r"D:\autoTesting\.work\tmp\bi-chkB\mut"
PY = os.path.join(SRC, ".venv", "Scripts", "python.exe")
OUT = r"D:\autoTesting\.worktrees\bench-inputs-ui\qa\evidence\bench-inputs-ui-B\mutants.json"
T = "tests/test_ui_bench_inputs.py"
M = "tests/test_bench_marks.py"
MUTANTS = [
    # id, criterion, file, old, new, test node
    ("F-C1", "C1", "src/autotester/stages/bench_marks.py", "if mark is None or finding.matched_bug_id is not None:", "if True:", M + "::test_one_real_one_false_one_unmarked_gives_fp_rate_over_the_two_adjudicated"),
    ("F-C2", "C2", "src/autotester/stages/bench_inputs.py", "digest = hashlib.sha256(raw).hexdigest()", "digest = hashlib.sha256(raw[:-1]).hexdigest()", T + "::test_c2_an_editor_uploads_the_list_it_is_stored_privately_and_its_hash_is_pinned"),
    ("F-C3", "C3", "src/autotester/ui/bench_inputs_view.py", "<label for='atomic-list-file'>Atomic answer list (JSON file)</label><br>", "", T + "::test_c3_every_new_control_has_a_visible_label_and_no_page_loads_anything_external"),
    ("S-auth", "C1/C2 auth", "src/autotester/ui/bench_inputs_view.py", "return who is not None and authorize(who, PermissionKey.PROJECT_EDIT, resource_for(slug))", "return who is not None", T + "::test_c1_a_view_only_account_sees_the_ruling_without_controls_and_cannot_mark"),
    ("S-key", "C1 inj", "src/autotester/ui/routes_bench_inputs.py", "if not _KEY.fullmatch(finding) or verdict not in _VERDICTS:", "if verdict not in _VERDICTS:", T + "::test_c1_a_malformed_mark_is_a_400_and_writes_nothing"),
    ("S-next", "C3 redirect", "src/autotester/ui/routes_bench_inputs.py", 'target if target.startswith(f"/projects/{slug}/") else f"/projects/{slug}/bench",', "target,", T + "::test_c1_an_off_site_next_is_ignored"),
    ("S-cap", "C2 size", "src/autotester/stages/bench_inputs.py", "if len(raw) > MAX_BYTES:", "if False:", T + "::test_c2_a_bad_list_is_refused_without_echoing_its_content_and_nothing_is_stored"),
    ("S-echo", "C2 echo", "src/autotester/stages/bench_inputs.py", "exc.errors(include_input=False, include_url=False)", "exc.errors(include_input=True, include_url=False)", T + "::test_c2_a_bad_list_is_refused_without_echoing_its_content_and_nothing_is_stored"),
]
ignore = shutil.ignore_patterns(".git", ".venv", ".work", "qa", "__pycache__", "projects", "node_modules", ".worktrees", ".pytest_cache", ".ruff_cache", ".playwright-mcp")
env0 = dict(os.environ, TMP=r"D:\autoTesting\.work\tmp", TEMP=r"D:\autoTesting\.work\tmp")

def run(root, node):
    env = dict(env0, PYTHONPATH=os.path.join(root, "src"))
    chk = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"], cwd=root, env=env, capture_output=True, text=True).stdout.strip()
    assert root.lower() in chk.lower(), chk
    r = subprocess.run([PY, "-m", "pytest", node, "-p", "no:cacheprovider"], cwd=root, env=env, capture_output=True, text=True)
    last = [l for l in r.stdout.strip().splitlines() if l.strip()][-1]
    return r.returncode, last

res = []
os.makedirs(WORK, exist_ok=True)
base = os.path.join(WORK, "base")
if os.path.exists(base):
    shutil.rmtree(base)
shutil.copytree(SRC, base, ignore=ignore)
# the repo conftest/pyproject need to be present; qa excluded -> check pyproject only
for mid, crit, f, old, new, node in MUTANTS:
    d = os.path.join(WORK, mid)
    if os.path.exists(d):
        shutil.rmtree(d)
    shutil.copytree(base, d)
    green = run(d, node)
    p = os.path.join(d, f)
    s = open(p, encoding="utf-8", newline="").read()
    assert s.count(old) == 1, (mid, s.count(old))
    open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new))
    red = run(d, node)
    res.append({"id": mid, "criterion": crit, "file": f, "node": node, "green_before": green, "red_after": red})
    print(mid, "green:", green, "| mutated:", red, flush=True)
    shutil.rmtree(d, ignore_errors=True)
json.dump(res, open(OUT, "w"), indent=1)
