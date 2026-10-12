# Manifest: release-cli

Status: ready-for-check
Fix cycle: 0
Issues: AT-900, AT-898, AT-899

- AT-900: `ProjectPaths.run_dir` now passes the id through `safe_name`; `release_cmd` refuses an unsafe `--run-id` (exit 1) before any write.
- AT-898: `stages/release.py::derive_flow_plans` builds each flow's FlowPlan from its approved cases; persisted via `save_flow_plan` once the approval gate passes.
- AT-899: pause shows build, flows, case/action counts and unplanned flows; approve/decline have their own closing lines; an already-answered release is a one-line refusal.
- Tests: tests/test_cli_release.py (new AT-900/898/899 cases), tests/test_release_gate.py unchanged and green.
