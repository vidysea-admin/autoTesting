# infra-trio (AT-820, AT-676, AT-692)

Status: checked-PASS
Fix cycle: 1
Branch: wave/infra-trio

- AT-820: no repo code does a host-wide kill (grep of src, scripts, hooks). The killer was an ad-hoc builder command. `mutation_check.kill_tree` already uses `taskkill /PID <own>`; `tests/test_infra_trio.py` pins that (fake proc) and bans `/IM`, `Stop-Process -Name`, pkill, killall in src/scripts. Hook guard denying taskkill /IM is hook-side: REPORT to Umesh, not edited.
- AT-676: already shipped (`ledger/issue_ids.py::check_issue_id_unique`, in doctor, `tests/test_issue_ids.py`). Live ledger has 12 duplicated ids, all in the grandfather list; doctor clean. Not touched.
- AT-692: no tracked script or hook pipes a verify command (only historical qa/evidence harnesses). Added `scripts/verify_gates.sh` (pipefail + PIPESTATUS, real exit code) with tests. The piping is in maker/checker prompts outside the repo.
