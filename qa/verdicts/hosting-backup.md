# Verdict - hosting-backup

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** 5512c7b54573829abfc6be2c18004efbce537c42 (base 3f081243; candidate tree clean, verified before write)

## Scope
AT-868 / T-203 slice: scripts/backup.sh, scripts/restore.sh, docker/DEPLOY.md backup section, tests/test_backup_restore.py. Contract: qa/contracts/hosting.md HO36 (slice only; admin page, linux evidence and encryption are declared follow-ups, AT-868 stays open) and HO37 (design rules).

## Independent checks (evidence under .work/chk/ev/*.rc and *.log, worktree-local scratch)
- bash -n backup.sh and restore.sh: rc 0 / rc 0.
- pytest tests/test_backup_restore.py (no -q, venv python, PYTHONPATH=worktree src): 4 passed, rc 0 (72 s).
- ruff check src tests scripts: rc 0.
- autotester doctor: rc 0, "doctor: clean". A first run flagged root-clutter b.log, which was my own stray probe output (removed); not a candidate defect.
- Adversarial probes run in scratch dirs (chk, chk3, chk4): see findings. Data-root convention matches container-writable-workdir (`AUTOTESTER_DATA_DIR`, default `/data`; env default verified). Spaces in root/out/archive paths work. Missing root and missing `--root` value exit 1. GCS path exercised (gsutil present: reaches upload and returns its error rc).

## Findings

### Proven defects (blocking)
1. **restore.sh fails for any relative archive path.** `(cd "$STAGE" && grep ... "$MANIFEST")` resolves a relative `$MANIFEST` after the cd. Repro: `restore.sh out/autotester-backup-*.tar.gz --root rr` and `cd out && restore.sh x.tar.gz` both end "REFUSED, per-file sha256 check failed" on a valid archive; the absolute path works. It fails closed, but the tests only use absolute paths so it was missed. It also leaves an empty target dir created (`mkdir -p "$ROOT"` runs before verification). Fix: absolutize ARCHIVE/MANIFEST after the argument loop, and add a relative-path test.
2. **Restore integrity checks have gaps.** (a) A file present in the archive but absent from the manifest is restored unverified (probe d, h: rc 0). (b) A manifest line for a name containing a backslash or newline starts with `\` and is silently dropped by the `^[0-9a-f]{64} ` filter, so that file is not verified (probe g: a wrong hash restored with rc 0). (c) No check that archive members are regular files: a symlink or hardlink member is accepted. A "symlink then file through it" member sequence was crafted, but GNU tar on this Windows host cannot create symlinks, so the Linux behaviour is NOT verified here; on Linux as root a link to an absolute path followed by a file under it is the classic exploit. Fix: list the archive (`tar -tvzf`), reject non-regular, absolute and `..` members, and require the member list to equal the manifest file list (also compare against the `files` count).
3. **Secret exclusion is top-level only.** Without `--include-secrets` the archive still held `projects/x/.env`, `.env.local`, `projects/x/.auth/db`, `credentials.json`, `id_rsa`, `key.pem`, `token.json` and `misc/Cookies`; only `./.env`, `./.auth` and `./profiles` are skipped. DEPLOY.md says credentials never live in a project folder, so this matches the documented layout, but the repo already knows these credential names (`stages/credential_files.py`) and an unencrypted archive that leaks them is the failure this flag exists to prevent. Fix: exclude by basename and suffix at any depth using that list, plus `.auth` and Cookies/profile directories at any depth, or state in the script header, manifest and DEPLOY.md that only the top-level three paths are excluded. The maker must pick one and test it.

### Non-blocking observations (record, fix when convenient)
- Manifest is unsigned: the archive hash is anchored only to a file sitting beside it, so someone who can write both can forge a consistent pair. This cannot be fixed without a key or the HO36 passphrase; say so in DEPLOY.md.
- The final `tar | tar` copy is not atomic. `--force` merges over the target and a mid-copy failure (disk full) leaves a half-restored tree; nothing outside the target is ever deleted (verified: the failed per-file check left the existing target untouched, "KEEP" file intact). The staging dir sits under the target, so an interrupted restore can leave `.restore-stage.*`, which the next backup would include.
- `find -type f` does not match symlinks, so links are skipped rather than followed (by code reading; native symlinks could not be created on this host to run it). A symlink in the data root is silently omitted from the backup.
- `--out` inside the root makes later archives include earlier ones (default `./backups` is cwd-relative).
- No snapshot consistency for live files (the auth SQLite file is copied raw). A partial archive is left behind if tar fails midway (no manifest, so restore refuses it).
- HO36 asks for an encrypted snapshot; this slice documents "store encrypted" instead. Accepted as the declared slice, not a pass on HO36.
- `restore.sh ../` traversal member: GNU tar refused it (rc 2, nothing written outside). Absolute-path member: leading `/` stripped. Stage cleaned on exit.

## Remaining gates
Fix cycle 1 for findings 1-3 with tests (relative path; extra and backslash-named member; non-regular member; nested secret name). Linux/docker re-run of the symlink probe (HO10 evidence) is still owed by AT-868.

## Accounting
Maker usage unknown (BOOTSTRAP_REVIEW scope with standing escalation, <=300 s target; the actual check ran over that because pytest took 72 s under saturated CPU and a gcloud call stalled once). Ratios unverified; tokens and cost not measured by the host (null).
