# Verdict - hosting-backup

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 1
**Reviewed SHA:** 887ac17ac4a5c42f0d5ed0ac04d39d7e0b353a81 (base 3f081243; prior FAIL 0171092d, cycle 0; candidate tree clean, verified before write)

## Scope
AT-868 / T-203 slice: scripts/backup.sh, scripts/restore.sh, docker/DEPLOY.md backup section, tests/test_backup_restore.py. Contract: qa/contracts/hosting.md HO36 (slice only; admin page, linux evidence and encryption remain declared follow-ups, AT-868 stays open) and HO37.

## Independent checks (evidence in worktree .work/chk1/ev/*.rc, *.log)
- bash -n backup.sh, restore.sh: rc 0 / 0.
- pytest tests/test_backup_restore.py (no -q, venv python, PYTHONPATH=worktree src): 10 passed, 1 skipped (backslash name, POSIX only), rc 0, 82 s.
- ruff check src tests scripts: rc 0. autotester doctor: rc 0, clean.
- Cycle-0 probes re-run in scratch (.work/chk1/s), all prior blockers closed:
  1. Relative archive path: `cd out && restore.sh x.tar.gz --root ../r1` restores 3 files, rc 0.
  2. Extra member (archive+manifest+sidecar all re-forged consistently but with an extra file): REFUSED, staged tree differs from manifest. Link members (symlink then file through it, and hardlink; crafted with python tarfile since this host cannot create symlinks): both REFUSED from the listing before extraction, target not left behind. Absolute/`..` member: REFUSED. Missing sidecar: REFUSED. Tampered manifest (sidecar kept): REFUSED.
  3. Nested secrets: with 14 secret-named files seeded at root and nested (.env, .env.local, key.pem, id_rsa*, credentials*.json, token*.json, *service-account*.json, Cookies*, Login Data, .auth/db), the default archive held only keep.txt, flow.json and sub/env.txt. `--include-secrets` archives all 19 and warns.
  Failed restores remove the target they created.

## Answers to the brief
- Forged sidecar: a fully self-consistent forged archive + manifest + sidecar (attacker controls both) is accepted (probe: modified keep.txt restored, rc 0). Expected: the sidecar guards corruption and a one-sided tamper, not an attacker who controls both. Acceptable for this slice because DEPLOY.md states "real signing is a follow-up"; it must stay on the AT-868 list (HO36 signing/encryption).
- `--force` window: restore stages and verifies fully first, then per top-level entry does rm -rf then mv. A crash between the two loses that one existing entry; existing entries not in the archive are kept (merge, not replace; verified). This is NOT stated in DEPLOY.md or `--help` (DEPLOY says "overwrite" and "renaming it into the target", which reads as more atomic than it is). Acceptable for a manual restore with the stack stopped, but add one line to DEPLOY.md. Non-blocking residual. The default path (new or empty target, no --force) is safe: verification and staging complete before any write to the target, and nothing pre-existing is touched.
- Backslash names: the test is skipped on this host and the script behaviour for them is unverified here. By code reading the staged-tree sha256sum compare uses the same escaped-name output on both sides, so it should hold. Recommend adding tests/test_backup_restore.py to the Linux container-smoke workflow; non-blocking residual that AT-868 must close with Linux evidence (HO10).

## Residuals (non-blocking, recorded)
Undocumented `--force` non-atomic window and merge semantics; unsigned manifest; Linux backslash/symlink-on-disk evidence owed; encryption (HO36) and admin page; `--out` inside root; no live-SQLite snapshot consistency; `.env*` also skips `.env.example` (safe direction).

## Accounting
Maker usage unknown, BOOTSTRAP_REVIEW with standing escalation (<=300 s). Active time exceeded 300 s because pytest took 82 s under saturated CPU, plus scripted probes; overrun recorded, not waived. Tokens and cost not host-measured (null); ratios unverified.
