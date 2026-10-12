# Checkpoint — t204-team-login cycle 3, coordinator B (Cycle checked: 3)

Attribution: checker coordinator B, verdict `qa/verdicts/t204-team-login.r3.b.md`. Environment fingerprint: Windows 11, `git archive 37a1d211` copied to a folder on C: with its own uv venv (`uv sync`, uv.lock of 37a1d211), `autotester.__file__` inside the copy, scrubbed env, fake values. Code identity: HEAD 37a1d211, product 48a08926, cycle-3 fix dd7b49e5; `src/autotester/auth/config.py`, `docker/compose.prod.yml`, `auth/policy.py` as of that commit. Dependency lock: uv.lock of 37a1d211. Build/service: uvicorn subprocesses of the archive copy, one per matrix row. Data snapshot: template data root (fake admin) copied per row; data-root hash over a 1,220-request anonymous pass identical before/after.

| Check | Command / scope | Result |
|---|---|---|
| Startup matrix | `qa/evidence/t204-team-login-r3-B/matrix.py` (196 rows, real uvicorn, compose values from `docker compose config`) | 118 refuse (exit 3, key named), 74 start-and-serve, 4 start-then-403 (HOSTED unset, P1) |
| Compose render | `docker compose config` x 5 environments | `""`, `https://qa.example.com`, operator value, operator wins over domain, empty domain `""` |
| Anonymous surface | sub-checker `server-A/t2.py`, 74 routes x 5 methods x 4 variants (1,220 requests) | 0 non-refusals, hash unchanged |
| Permission matrix | `server-A/t3.py`, 5 user types x 12 routes x 3 states | matches policy keys, defaults, intent |
| Sessions | `server-A/t4.py` | all as AU2/AU3/AU18 |
| Upload attribution | `server-A/t5.py` | uploaded_by null (T-198 follow-up) |
| Affected tests | `pytest -p no:xdist -o addopts= tests/test_hosting_deploy.py tests/test_ui_auth_own_origin.py` in the copy (PYTHONPATH=copy/src) | 90 passed (82.9 s) |
| Lint / design | `uv --directory <copy> run ruff check src tests scripts`; `... autotester doctor` | clean; clean |
| Falsify compose default | copy with `https://${AUTOTESTER_DOMAIN:-localhost}` | 4 failed / 86 passed |
| Falsify loopback refusal | copy with `if False and` at config.py:131 | 6 failed / 84 passed; real process starts+403 on 6 rows |
| Falsify policy row | sub-checker, drive row removed from policy.py | au14 pin red, 8 passed -> 1 failed -> 8 passed |
| Not run (instruction) | full suite (`full-suite trigger: conftest edit`) | owed to the other coordinator / pre-push 6c |

Result: PASS (no FAILURES; 5 PROPOSED-ISSUE lines).
