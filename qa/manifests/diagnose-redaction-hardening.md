# Manifest — diagnose-redaction-hardening

Status: ready-for-check
Fix cycle: 0
Unit: diagnose-redaction-hardening (follow-up to qa/verdicts/container-ci-smoke.md advisory; plus two findings from CI run 38908337519)
Base SHA: 3f081243
Branch: worktree-agent-a949f7eafe295a450

## Changed paths
- scripts/container_diagnose.sh: `redact` rewritten (sourceable, GNU sed, case-insensitive); EXIT trap fix; new `app-perm` DIAGNOSIS signature.
- tests/test_container_ci_workflow.py: parametrized redaction shapes, negative ordinary-log test, app-perm tests, trap regression test.
- qa/manifests/diagnose-redaction-hardening.md (this file).

## Behaviour
- Redaction masks the VALUE and keeps the KEY NAME. Shapes: URL `user:pass@`; `Authorization:` (whole value, so Basic and Bearer); `Cookie:`/`Set-Cookie:` (whole value); `pwd/passwd/password/auth/credential(s)/secret/token/key/session/cookie/private` names in `k=v`, `k: v`, JSON and backslash-escaped JSON, quoted values masked to the closing quote; CLI flags `--password x`, `--token x`, `--api-key=x`; PEM blocks (single-line, JSON one-liner and multi-line); AKIA/ASIA; ghp_/gho_/ghu_/ghs_/ghr_/github_pat_; JWT eyJ..eyJ; AIza; xox[baprs]-; sk-; Bearer.
- Fail safe: over-masking is accepted (e.g. `PWD=/app` and `session: x` are masked). An unterminated PEM block masks to end of input. Unquoted multi-word values mask only the first word (documented limit).
- Needs GNU sed (the `I` flag); the CI runner and Git Bash have it. Not verified on BSD/macOS sed.
- EXIT trap now expands `$cname` when set (it was a main()-local read under `set -u`, giving "cname: unbound variable" and leaking the container). Regression test drives main() with a fake docker on PATH.
- New DIAGNOSIS signature `app-perm`: `PermissionError: [Errno 13]`, `Errno 13] Permission denied`, or `cannot create/open/write|mkdir|touch ... Permission denied`. Distinct from the python-exec `perm-denied` (126) signature.

## Expected consequence
The container-smoke CI job will now FAIL on the `/app/.work` PermissionError until the separate /app/.work fix lands. That is expected: the signature now reports a real defect that the previous DIAGNOSIS passed over.

## Consumers
`diagnose` and `redact` are used by main() in the same script and by .github/workflows/container-smoke.yml (runs the script). No other consumers.

## Checks
bash -n, ruff, pytest (tests/test_container_ci_workflow.py + tests/test_container_*.py), doctor: see the review packet. Not verifiable here: real docker run, BSD sed.
