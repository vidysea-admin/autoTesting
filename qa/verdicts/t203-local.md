# Verdict — t203-local

**Cycle checked:** 1
**Verdict:** PARTIAL — code criteria PASS; HO39/HO40 pending install; HO41 blocked on T-204.
Checked fresh against hosting.md HO39-HO46. Tests: `tests/test_windows_host.py` 8 passed, 1 skipped; ruff clean.

| HO | Result | Evidence |
|---|---|---|
| HO39 | pending install (needs Umesh approval) | installer uses `New-ScheduledTaskTrigger -AtStartup` and a password-bound registration (no interactive logon); `-WhatIf` test passes; `schtasks /Query` not checkable until installed |
| HO40 | pending install (needs Umesh approval) | `-RestartCount 5 -RestartInterval 1min` asserted in dry run; kill-and-recover check needs the real task |
| HO41 | BLOCKED on T-204 (not PASS) | launcher never sets AUTOTESTER_AUTH_DISABLED (tested); no login/401 layer exists in the app yet; the 401/302 test is skipped with reason |
| HO42 | PASS (config) | data root defaults to `%ProgramData%\AutoTester`, outside the repo; restart persistence follows from files under it, not exercised |
| HO43 | PASS | `/healthz` public, fixed three-key payload; `serve_windows.ps1 -Check` exits 1 on failure; smoke start answered on loopback |
| HO44 | PASS | default `--host 127.0.0.1`; `-Lan` or AUTOTESTER_BIND_HOST switches; startup log line written; socket check done via smoke start on 127.0.0.1 |
| HO45 | PASS | DEPLOY.md B.1 covers launcher, task create/remove, data root, bind, health, first admin before LAN, Ubuntu later; no secrets; Part A unchanged |
| HO46 | PASS | no Docker dependency, ruff clean; doctor shows only pre-existing violations (stale MAP/SNAPSHOT, D-9999/D-999 citations in t196 verdicts) |

Caveat: maker and checker were the same agent run; an independent /checker pass is still advisable.
