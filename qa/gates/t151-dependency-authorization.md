# HUMAN_GATE — T-151 dependency, prompt and mock authorization

**Opened:** 2026-10-06T19:50Z by /maker (from qa/verdicts/t151-plan-approval.md in .worktrees/t151-target-discovery, required change 3)
**Blocks:** T-151 (deterministic discovery/context) reaching ready-for-check; T-152/T-153 behind it.

**Question:** T-151's built code adds three things that no DECISIONS entry authorizes. D-017 names
only the three modules (schema/ai_target.py, stages/discover.py, read_context.py). Do you approve them?
1. A new runtime dependency, `pyyaml==6.0.3`, in pyproject.
2. A new prompt file for target discovery.
3. An `act` hunk in `src/autotester/providers/mock.py`.

**Options:**
- A: Approve all three. The maker appends a DECISIONS entry via `scripts/append_decision.ps1`
  with `Approved-by: Umesh`.
- B: Approve them without pyyaml. The maker replaces YAML parsing with the stdlib (json/tomllib).
- C: Hold T-151.

**Answer format:** reply "T-151: A", "T-151: B" or "T-151: C".

Answered: 2026-10-07T01:34:13Z — A — chat (Umesh): approve all three (pyyaml==6.0.3, the target-discovery prompt file, the mock.py act hunk). DECISIONS entry to follow.
