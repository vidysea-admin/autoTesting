# Verdict — diagnose-redaction-hardening

Verdict: FAIL
Status: FAIL
Cycle checked: 0
Reviewed SHA: 4bdb3437878f9c0f4ec9694ba105e29c28cbac83
Base SHA: 3f081243030be35f856a57286ffa0efc5602d6d7
Checker: independent, fresh context (Opus 5.5), 2026-10-16
Final hashes (sha256): scripts/container_diagnose.sh 93149e6633428f4d5254aa8433cf0e9de195cec00b16b99b41fc6c2c20b93b63; tests/test_container_ci_workflow.py 0a7c11cd9585f2c48a08248f4585578d20fd715c9e2d3aa187315b69dd58ad85

## Why FAIL (proven, reproducible with GNU sed 4.9 by sourcing the script)
The script header promises "No secret values are ever written". The manifest claims quoted JSON values are masked to the closing quote. The log is shared outside the team, so leaks here are blocking. Probe: `.work/checker-diagnose-redaction-hardening/leak_probe.sh`, output `leak_probe.out`: 15 of 72 shapes leak.
1. **Repo-native key names leak.** `PATHLYNKS_PW=x`, `DB_PASS=x`, `pass=x` and `pw=x` pass through unchanged. The name list has `passw(or)?d|pwd` but not `pass` or `pw`. This repo really uses `PATHLYNKS_PW`, `PROD_PW`, `DEMO_PW`, `APP_PASS` and `ST_PASS` (tests/qa evidence), so a container log that echoes such an env value would leak it.
2. **An escaped quote inside a JSON value leaks the tail.** `{"password":"a\"S3CR3T"}` becomes `{"password":"<redacted>"S3CR3T"}`. This contradicts the manifest's "quoted values masked to the closing quote".
3. **Other leaks:**
   - `password => "x"` becomes `password =<redacted> "x"`
   - `<password>x</password>`
   - URL-encoded `password%3Dx` and `password%22%3A%22x`
   - OAuth `?code=x&state=1`
   - space-separated `token x`, `the token is x` and `GEMINI_API_KEY x`
   - short flag `-p x`
4. **BSD/macOS sed:** there is no detection and no fail-safe. The script does not check `sed --version` and does not warn. BSD ERE has no `\b`, so the AKIA/ASIA rule probably stops matching there, and the `I` flag behaviour is version-dependent. This was not verifiable here, so it is unproven but unguarded: a silent leak cannot be excluded.

Masked correctly (sample):
- mixed case `PassWord=` and `X-Api-Key:`
- spaces around `=` and `:`
- single- and double-quoted values with spaces
- embedded `=` and `&`
- `?token=` and `access_token=`
- `Authorization:Bearer` with no space, Basic and Proxy-Authorization
- `client_secret` and `private_key_id`
- base64 after `secret:`
- `export FOO_SECRET=`
- postgres/redis/mysql userinfo
- `.env` lines with `#`
- end-of-line tokens
- ghp, AKIA, JWT, sk- (including sk-proj), AIza, xoxb
- PEM: RSA, EC, OPENSSH, ENCRYPTED and PGP. Single-line, JSON `\n` and multi-line all work, and an unterminated block masks to end of stream.

## Over-redaction and ordering
- Order: `redact` runs on every section before it is written to LOG, and DIAGNOSIS reads that redacted LOG. That order is correct for confidentiality.
- Over-redaction probe (`over_input.txt` to `over_output.txt`):
  - These lines are unchanged: Permission denied, uid=10001, exec format error, PREFLIGHT FAIL, Address already in use, OOMKilled, python paths including `session.py` and `keyboard.py`, and `session started`.
  - These are cosmetically mangled: `author: bob`, `keyboard: layout`, `keys=3 sessions=1`.
- `diagnose` gives identical output on the raw and redacted copies: 9 FAIL plus env-absent.
- Risk: a stray, unterminated `-----BEGIN X-----` line deletes the rest of that section's stream. That can hide later signature lines in the same section. This is advisory.
- Performance: roughly linear, but slow on this contended CPU. A 40 KB line containing a key took 8.7 s, and a 300 KB line took 215 s (`scaling2.result`, `long.result`). This is advisory.

## Trap and app-perm
- The trap is now `trap "docker rm -f '$cname' ..."`, expanded at install time. That is safe under `set -u`, and `cname=autotester-smoke-$$` cannot contain quotes. The regression test passes. Accepted.
- `app-perm` fires on `PermissionError: [Errno 13] ... '/app/.work'` and on `mkdir: cannot create directory`. It does not fire on benign "denied" text or on the python exec Permission denied line (tests pass). Accepted.

## Commands (independently run, exit codes in evidence files)
- `bash -n scripts/container_diagnose.sh`: rc=0 (`bashn.out`)
- `review_budget.py preflight`: PREFLIGHT_OK, import from the worktree src, py 3.11.16 (`preflight.out`)
- `PYTHONPATH=<wt>/src .venv/Scripts/python -m pytest tests/test_container_ci_workflow.py`: 61 passed, rc=0, 444.66 s (`pytest.out`)
- `ruff check src tests scripts`: rc=0 (`ruff.out`)
- doctor: "doctor: clean", rc=0 (`doctor.out`)

Evidence directory: `.work/checker-diagnose-redaction-hardening/`. All of it was independently produced; no maker evidence was reused.

## Fix requests (cycle 1)
1. Add `pass` and `pw` to the name set, at least as `_pass`, `_pw` and bare `pass=`/`pw=`. Add a test for `PATHLYNKS_PW=`.
2. Handle backslash-escaped quotes inside quoted values, using `"([^"\\]|\\.)*"`.
3. Cover `=>`, XML tags, URL-encoded `%3D`/`%22`, and the OAuth `code=` param.
4. Make the script refuse to run, or mask whole lines, when sed is not GNU. Detect this with `sed --version` or a self-test.

## Not verified
- Real docker run
- BSD/macOS sed

## Budget (BOOTSTRAP_REVIEW plus standing escalation; ratio unverified)
- Maker usage: unknown (null).
- Checker active time: about 1177 s by the bash wall clock, including 445 s of pytest and about 215 s of the long-line probe.
- Checker tokens: unknown (null), with debits of 70k for startup and 60k for review.
- Escalation limit: 480 s. **Exceeded on active_s: `NEEDS_EXTRA_REVIEW` (`phase2-final-result.json`, rc=2). The breach is recorded, not waived.**
- The 150k token limit is above the CLAUDE.md 1.0x maker cap, which cannot be evaluated because maker tokens are unknown.
- Clock note: the helper's `observed_at` and the bash `date` disagree by about 8 min.
- No PASS was issued.
