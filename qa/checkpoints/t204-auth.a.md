# Checkpoint (coordinator A, blind) — t204-auth, cycle 0

Policy-Version: proportional-verification/2026-10-06.6
Written: 2026-10-07T19:40+05:30
Bound to: branch wave/t204-auth, worktree D:/autoTesting/.worktrees/t204-auth, HEAD f7380803fbb042017ccd0043a1f688f0c1027145 (code d87b2181, base 7782df41)
Verdict file: qa/verdicts/t204-auth.a.md (FAIL, F1 F2 F3)

## Evidence identity

| Item | Value |
|---|---|
| src/autotester/ui/auth_middleware.py | 513019395ec844ec9fea3337c3681cd81bf030db |
| src/autotester/ui/routes_credentials.py | dc7a2c57af5fa024352f6c4679026ea0275b554d |
| src/autotester/ui/routes_admin.py | 35138caff0a17b9e1538775c1ef806f8b7c50d5e |
| tests/conftest.py (protected) | 39708fc028937c27d2556f7687d2b2275f7c126c |
| uv.lock | 438507c39ed4d9ff94aa07168850fa4c973197a2 |
| Environment | Windows 11, .venv from the repo, PYTHONDONTWRITEBYTECODE=1, bound tree clean (git status clean before and after) |

## Commands and scope

| Evidence | Command / scope | Result | Attribution |
|---|---|---|---|
| lint | `ruff check --no-cache src tests scripts` | clean | A (own) |
| doctor | `.venv/Scripts/autotester.exe doctor` | `doctor: clean` | A (own) |
| F3 PoC | scratchpad/own/poc_title_xss.py against worktree source, temp root | raw `<script>` in `<title>` | A (own) |
| route variants | scratchpad/own/poc_paths.py, poc_esc.py | no bypass; escaping elsewhere holds | A (own) |
| auth core review | sub-checker s1 (scratchpad/s1) | AU1-AU9 held except F2; P8-P10, P16 | sub-checker, read by A |
| HTTP surface | sub-checker s2 (scratchpad/s2) | F1 reproduced (poc6.out); AU13/AU14/AU16 held | sub-checker, read by A |
| test infra / conftest | sub-checker s3 (scratchpad/s3) | merge hazard P6, audit-file leak P7 | sub-checker, read by A |
| browser walk AU26 | sub-checker s5, Playwright MCP, 127.0.0.1:8765, temp root | passes, low findings | sub-checker; evidence scratchpad/s5/evidence (29 PNG + report.json) |
| falsification | sub-checker s4, copies scratchpad/s4/m01..m22, x1..x4; node = the manifest's named test per row | 22/22 green-before red-after | sub-checker; logs run1.log run2.log |
| full suite | NOT RUN | n/a | lock D:/autoTesting/.work/suite.lock held by another unit until 19:29 and re-taken; verdict FAIL stands without it; repair checker runs it on the fixed tree |

Extra mutants: x1 raw-token session lookup SURVIVED; x2 limiter keyed on X-Forwarded-For SURVIVED; x3 RED; x4 RED.

## Scope notes

- Coordinator B's files (qa/verdicts/t204-auth.b.md, qa/checkpoints/t204-auth.b.md) were not opened. A `git diff --stat` once listed sibling-unit file names; nothing from B entered the analysis.
- No lock taken, none left. No issues.jsonl edit, no merge, no push, no goal change.
- AU1 judged blocked on a human gate (argon2-cffi==25.1.0 D-entry pending Umesh). Deferral rulings R1-R4 are in the verdict.
- Resume: after the maker fixes F1-F3, the repair checker re-runs ruff, doctor, the three PoCs, the affected falsification rows (m03, m21 plus new tests) and the one full suite with tests/test_crawl_inventory_live.py deselected.
