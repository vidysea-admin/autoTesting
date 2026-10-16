# Manifest - hosting-backup

**Status:** ready-for-check
**Fix cycle:** 0
**Unit:** AT-868 / T-203 slice: backup and restore of persistent state (go-live critical part only)
**Branch:** hosting-backup
**Base commit:** 3f081243

## What changed
- scripts/backup.sh: tar.gz of the state root (default /data) with a sidecar manifest (file count, archive sha256, per-file sha256); caches always excluded; .env, .auth, profiles excluded unless --include-secrets (prints a warning); optional gs:// upload via gsutil or gcloud.
- scripts/restore.sh: verifies archive sha256, extracts to a staging dir, verifies every file sha256, then moves in; refuses a non-empty target without --force.
- docker/DEPLOY.md: scripted backup/restore section (Cloud Run /data volume, Cloud Scheduler and cron examples, restore steps); stale "scheduled backup script" gap removed.
- tests/test_backup_restore.py: round trip equality, include-secrets, tamper refusal, non-empty target; skipped without bash.

## Follow-ups (not built here; AT-868 stays open)
- Admin page and audit trail (HO15; T-204 hand-off).
- qa/evidence/t203-linux-run.md (HO10): needs a docker daemon.
- Remaining AT-868 rows (non-root, HO19, HO21, HO34/35 rehearsal) untouched.

## Checks
pytest tests/test_backup_restore.py: 4 passed; bash -n clean on both scripts; ruff clean; autotester doctor: clean. Windows Git Bash needed path normalisation (sha256sum stdin, tar stdin and cd+pwd roots), already applied.
