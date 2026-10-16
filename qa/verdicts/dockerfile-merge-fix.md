# Verdict: dockerfile-merge-fix

Verdict: PASS
Status: PASS
Cycle checked: 0
Reviewed SHA: a3280dce03da54abe2f75b02f0e14fcb7752f29e
Base: b6aa6cae0f3227a5767c1d264e9216e0b67aa064
Scope: BOOTSTRAP_REVIEW (static only). NO CONTAINER WAS BUILT; runtime behaviour in a real image is unverified.

## Checks (independently run)
- Final effective USER is 10001:10001 (last USER line, after the chmod of the wrapper). Only EXPOSE/ENTRYPOINT/CMD follow, so nothing later needs root. Base final USER was root (bug 1 confirmed, fixed).
- Wrapper heredoc is quoted `<<'EOF'`, so `$@` stays literal; last line is `exec "$@"`. Extracted from the git blob (LF; the worktree CRLF is autocrlf only, .gitattributes sets *.sh eol=lf): `bash -n` exit 0.
- Ran the actual extracted wrapper with paths rewritten to a temp sandbox and a namei shim: with CMD `sh -c 'echo CMD-RAN; exit 5'` it execs the CMD and propagates rc=5. The base wrapper ended at the banner and never ran CMD (bug 2 confirmed, fixed).
- `set -eu` in the diagnostics: a failing diagnostic aborts before exec by design (fail-fast). namei is provided by util-linux, which devops installed, so it is present in the image. On Windows bash namei is absent, which only affects local runs and not the container. Accepted.
- Writes under uid 10001: the wrapper only reads. /data and ~/.cache are chowned to 10001 and the build-time touch/rm check runs as 10001. The entrypoint writes only to /tmp (rm -f) and /data via AUTOTESTER_ROOT. The wrapper is root-owned 0755, so it is executable by 10001. Residual (pre-existing, not introduced here): `uv run` in /app is not writable by 10001, but UV_NO_SYNC=1 is set. Only a container run can confirm this.
- Devops additions preserved: `git diff dd1c7789 a3280dce -- Dockerfile` shows only the 3 intended changes (smoke import, exec, USER). util-linux/file, diagnostics, chown and the runtime-user check are intact.
- New assertions against base (.work/base_Dockerfile, from `git show b6aa6cae:Dockerfile`): non-root False, exec False, literal "import autotester" False, so the new and original assertions fail on base. On the candidate all three are True.
- `.venv/Scripts/python -m pytest tests/test_container_supervision.py tests/test_hosting_deploy.py tests/test_auth_deploy_files.py` (no -q): exit 0, 29 passed (.work/ckr_pytest.out, .work/ckr_pytest.rc).

## Not run
ruff, doctor and a container build or run. The maker claims ruff and doctor are clean, and the claim is unverified. Recommend a devops build to confirm: `docker run` shows `id` as uid 10001 and the app starts.
