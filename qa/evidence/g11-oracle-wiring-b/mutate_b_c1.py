"""Checker runner: one isolated copy per mutant, green-before then red-after (batched, serial)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

S = Path('D:/autoTesting/.work/tmp/ow-b-mut')
BASE = S / "base"
PY = "D:/autoTesting/.worktrees/g11-oracle-wiring/.venv/Scripts/python.exe"

MUT = {
    "M1-W1": ("src/autotester/stages/oracle_payment.py",
              "declaration or context.declarations.payment_paths\n                   or load_declaration",
              "declaration\n                   or load_declaration",
              "tests/test_oracle_declarations.py::test_w1_the_payment_oracle_takes_its_paths_from_the_context_and_reads_no_file"),
    "M2-W2": ("src/autotester/stages/role_port_mail.py",
              "        return observation_from_read(result, assertion.target)",
              "        try:\n            return observation_from_read(result, assertion.target)\n"
              "        except Exception:\n            return Observation(matched=False, detail='')",
              "tests/test_role_port_mail.py::test_w2_an_unreadable_mailbox_is_never_read_as_absence_or_as_a_clean_run"),
    "M3a-W3": ("src/autotester/browser/role_probe.py", "if not allowed(url):", "if False:",
               "tests/test_role_port_authz.py::test_w3_a_url_off_the_platform_is_never_requested"),
    "M3b-W3": ("src/autotester/stages/authz_probe.py",
               "min(plan.request_cap, PROBE_CEILING, approval.max_probes)",
               "min(plan.request_cap, PROBE_CEILING)",
               "tests/test_oracle_privilege.py::test_mp20_the_run_stops_at_the_signed_max_probes_even_if_the_plan_asks_for_more"),
    "M3c-W3": ("src/autotester/stages/oracle_privilege.py",
               "        elif (stop := prep.budget.take(reserve=3)) is not None:  # the look, the attempt, the undo\n"
               "            unprobed.append(UnprobedItem(item=item, reason=stop))\n", "",
               "tests/test_role_port_authz.py::test_w3_every_request_the_run_made_is_counted_including_the_role_assign_page_loads"),
    "M4-W4": ("src/autotester/stages/role_port_authz.py",
              "            session.click(binding.revert_locator)", "            pass",
              "tests/test_role_port_escalation.py::test_w4_an_accepted_assign_is_a_p0_finding_and_is_reverted_in_the_same_run"),
    "M5-W5": ("src/autotester/stages/unified_report.py", "return render_html(report, found)",
              "return render_html(report)",
              "tests/test_report_findings_wiring.py::test_w5_a_recorded_p0_leak_opens_the_report_with_the_banner_and_its_repro"),
}


def run(copy: Path, node: str) -> tuple[int, str]:
    env = dict(os.environ, PYTHONPATH=str(copy / "src"), TMP="D:/autoTesting/.work/tmp",
               TEMP="D:/autoTesting/.work/tmp")
    p = subprocess.run([PY, "-m", "pytest", node, "-p", "no:cacheprovider"], cwd=copy, env=env,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def main(names: list[str]) -> None:
    for name in names:
        rel, old, new, node = MUT[name]
        copy = S / name
        if copy.exists():
            shutil.rmtree(copy)
        shutil.copytree(BASE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        rc0, out0 = run(copy, node)
        target = copy / rel
        text = target.read_text(encoding="utf-8")
        assert text.count(old) == 1, (name, text.count(old))
        target.write_text(text.replace(old, new), encoding="utf-8")
        rc1, out1 = run(copy, node)
        tail = [ln for ln in out1.splitlines() if ln.startswith(("E ", "FAILED", "ERROR")) or " failed" in ln or " passed" in ln]
        print(f"== {name} green-before rc={rc0} ({out0.strip().splitlines()[-1] if out0.strip() else ''})")
        print(f"   red-after rc={rc1}: {tail[:6]}")
        (S / f"{name}.out").write_text(out0 + "\n=====MUTATED=====\n" + out1, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:] or list(MUT))
