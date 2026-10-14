# Manifest - approval-revoke

**Status:** ready-for-check
**Fix cycle:** 1
**Unit:** signed revocation of a RunApproval (user asked to revoke pathlynks appr_d89c9e3c61fd)
**Branch:** wave/approval-revoke

## Changes
- schema/approval_revocation.py: `ApprovalRevocation{approval_id, revoked_by, revoked_at, reason, signature}` (extra=forbid, HMAC via AUTOTESTER_APPROVAL_KEY); `is_valid` is False when unsigned, forged, edited or the key is missing; `drop_revoked`, `revoked_ids`.
- Stored in sibling `approval_revocations.jsonl` (core/paths.py), so `approvals.jsonl` and its loaders are unchanged. store/approval_revocations.py; `ProjectStore.list_approvals` drops validly revoked rows.
- core/consent.py: `require_approval` / `require_project_approval` take `revocations=`; a validly revoked row is refused ("revoked"); unsigned or forged revocations are ignored.
- cli_revoke.py, registered in cli_subapps.py: `autotester revoke <slug> <approval_id> --by --reason`; exits 1 on missing key or unknown id.
- tests/test_approval_revoke.py (6 tests).

## Verify
PYTHONPATH=<worktree>\src python -m pytest tests/test_approval_revoke.py tests/test_consent.py tests/test_approve_cli.py tests/test_approval_signing.py tests/test_approval_prod_gate.py ; ruff check src tests scripts ; autotester doctor
Result: 83 passed, ruff clean. Doctor: only the pre-existing stale-generated docs/MAP.md (needs `autotester map`).

## Command for the human (after merge, NOT yet run)
uv run autotester revoke pathlynks appr_d89c9e3c61fd --by "Umesh" --reason "wall_clock 600000000s unsigned grant; revoked on request"
