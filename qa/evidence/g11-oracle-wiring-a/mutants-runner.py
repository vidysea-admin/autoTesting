import shutil, subprocess, sys, os, json
S = os.path.dirname(os.path.abspath(__file__))
PY = "D:/autoTesting/.worktrees/g11-oracle-wiring/.venv/Scripts/python.exe"
M = [
 ("W1", "src/autotester/schema/oracle_context.py", "default_factory=OracleDeclarations, exclude=True, repr=False", "default_factory=OracleDeclarations, repr=False",
  "tests/test_oracle_declarations.py::test_w1_declarations_are_never_serialised_with_the_context"),
 ("W2", "src/autotester/stages/role_port_mail.py", "self._mail_recipients.get(role_id) or credentials.get(ref.user_key, \"\")", "credentials.get(ref.user_key, \"\")",
  "tests/test_role_port_mail.py::test_w2_a_mail_that_arrived_is_observed_through_the_read_only_reader"),
 ("W3", "src/autotester/stages/role_port_authz.py", "lambda target: host_in_platform(platform, host_of(target))", "lambda target: True",
  "tests/test_role_port_authz.py::test_w3_a_url_off_the_platform_is_never_requested"),
 ("W4", "src/autotester/stages/oracle_privilege.py", "        reverted = _revert(esc, probe.lower_role_id, control)", "        reverted = False",
  "tests/test_role_port_escalation.py::test_w4_a_press_whose_outcome_is_not_shown_is_still_undone_and_recorded"),
 ("W5", "src/autotester/stages/cross_role_runner.py", "for finding in findings if record else ():", "for finding in findings:",
  "tests/test_report_findings_wiring.py::test_w5_run_scenario_does_not_write_unless_asked_to_record"),
]
env = dict(os.environ, TMP="D:/autoTesting/.work/tmp", TEMP="D:/autoTesting/.work/tmp")
def run(tree, node):
    e = dict(env, PYTHONPATH=f"{S}/{tree}/src")
    r = subprocess.run([PY, "-m", "pytest", node, "-p", "no:cacheprovider"], cwd=f"{S}/{tree}", env=e, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.strip()][-6:]
    return r.returncode, "\n".join(tail)
which = sys.argv[1:] or [m[0] for m in M]
for cid, f, old, new, node in M:
    if cid not in which: continue
    shutil.rmtree(f"{S}/mut-{cid}", ignore_errors=True)
    shutil.copytree(f"{S}/base", f"{S}/mut-{cid}")
    p = f"{S}/mut-{cid}/{f}"
    s = open(p, encoding="utf-8", newline="").read()
    assert old in s, (cid, "pattern missing")
    open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
    g = run("base", node); r = run(f"mut-{cid}", node)
    print(json.dumps({"id": cid, "node": node, "green_before_rc": g[0], "mutant_rc": r[0]}))
    print("  GREEN:", g[1].splitlines()[-1] if g[1] else "")
    print("  MUT  :", r[1])
