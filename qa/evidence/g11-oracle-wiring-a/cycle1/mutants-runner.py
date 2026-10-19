import shutil, subprocess, sys, os, pathlib
S = pathlib.Path(r"D:/autoTesting/.work/tmp/check-g11-ow-a-c1")
PY = r"D:/autoTesting/.worktrees/g11-oracle-wiring/.venv/Scripts/python.exe"
base = S / "base"
P = "tests/test_oracle_privilege.py"; A = "tests/test_role_port_authz.py"; E = "tests/test_role_port_escalation.py"; D = "tests/test_oracle_declarations.py"
MUT = {
 "M1_W3_drop_look_budget": ("src/autotester/stages/oracle_privilege.py",
   "        elif (stop := prep.budget.take(reserve=3)) is not None:  # the look, the attempt, the undo\n            unprobed.append(UnprobedItem(item=item, reason=stop))\n", "",
   [A+"::test_w3_nothing_is_sent_once_the_request_cap_is_spent", A+"::test_w3_a_cap_too_small_for_a_press_and_its_undo_sends_not_even_the_look", P+"::test_mp20_the_cap_reserves_room_for_the_revert_so_it_is_never_exceeded"]),
 "M2_W3_drop_signed_bound": ("src/autotester/stages/authz_probe.py",
   "min(plan.request_cap, PROBE_CEILING, approval.max_probes)", "min(plan.request_cap, PROBE_CEILING)",
   [P+"::test_mp20_the_run_stops_at_the_signed_max_probes_even_if_the_plan_asks_for_more"]),
 "M3_W3_price_two": ("src/autotester/stages/authz_probe.py",
   "len(probe.read_urls) + 3 * len(probe.controls)", "len(probe.read_urls) + 2 * len(probe.controls)",
   [P+"::test_the_approval_gate_covers_reads_and_both_attempt_and_revert", A+"::test_w3_a_plan_whose_every_control_is_reachable_stays_inside_the_signed_approval"]),
 "M4_W1_echo_input": ("src/autotester/schema/oracle_context.py",
   "extra=\"forbid\", arbitrary_types_allowed=True, hide_input_in_errors=True)", "extra=\"forbid\", arbitrary_types_allowed=True)",
   [D+"::test_w1_a_bad_declaration_dict_on_the_context_does_not_echo_the_input"]),
 "M5_W4_no_undo_on_raise": ("src/autotester/stages/oracle_privilege.py",
   "    except Exception:  # state unknown: undo if anything took, say whether the undo held\n        reverted = _revert(esc, probe.lower_role_id, control)\n",
   "    except Exception:  # state unknown: undo if anything took, say whether the undo held\n        reverted = False\n",
   [E+"::test_w4_an_assign_that_raises_mid_flight_after_the_click_took_is_still_undone"]),
}
def run(root, nodes):
    env = dict(os.environ, PYTHONPATH=str(root / "src"), TMP="D:/autoTesting/.work/tmp", TEMP="D:/autoTesting/.work/tmp")
    r = subprocess.run([PY, "-m", "pytest", *nodes], cwd=root, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout[-1500:]
which = sys.argv[1:] or list(MUT)
allnodes = sorted({n for k in which for n in MUT[k][3]})
rc, out = run(base, allnodes)
print("GREEN-BEFORE (unmodified copy):", rc, out.strip().splitlines()[-1])
for k in which:
    f, old, new, nodes = MUT[k]
    root = S / ("mut-" + k)
    if root.exists(): shutil.rmtree(root)
    shutil.copytree(base, root)
    p = root / f; t = p.read_text(encoding="utf-8")
    assert t.count(old) == 1, (k, t.count(old))
    p.write_text(t.replace(old, new), encoding="utf-8")
    rc, out = run(root, nodes)
    fails = [l for l in out.splitlines() if l.startswith("FAILED")]
    print(k, "rc=", rc, "|", out.strip().splitlines()[-1]); [print("   ", l[:170]) for l in fails]
