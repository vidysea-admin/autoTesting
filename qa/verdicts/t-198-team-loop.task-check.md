# Task-level verdict - T-198 developer video intake (independent close-out check, 2026-10-13)

Contract `qa/contracts/team-intake.md` TI1-TI11 (G3). t198a merged at 7a01127a with dual PASS r2 (dba80100). Re-checked on master after the T-204 merge.

VERDICT: FAIL (task not closed; the file at the done_check path is deliberately not written)

Gaps:
1. TI10 (CRITICAL) route/job gating by `video.upload`: T-204's route policy refuses unauthenticated and unprivileged requests at the middleware, but the intake gate seam `ui/intake_gate.py` is still `OpenGate`; nothing calls `set_gate(...)` in src. The `fetch-drive` background job therefore re-asks nothing at `recheck`.
2. TI11 `uploaded_by` from the session: the web routes cannot fill it because the gate is not installed (only the CLI `--uploaded-by` flag fills it).
3. The fix exists as branch `wave/t198c` (00f3373a, "real intake gate, TI10/TI11") but has no manifest status beyond its own, no checker verdict, and is not merged. `qa/manifests/t198b-developer-portal.md` (TP1-TP6) is likewise unchecked and unmerged; the contract file covers both units.

Next: dual-check and merge t198c (Tier L, auth), then re-run this check.
