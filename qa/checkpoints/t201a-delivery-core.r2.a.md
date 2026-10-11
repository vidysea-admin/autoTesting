# Checkpoint - t201a-delivery-core, cycle 2, coordinator A

Policy-Version: proportional-verification/2026-10-10.9
Attribution: claude-sonnet-subagent, coordinator A, verdict `qa/verdicts/t201a-delivery-core.r2.a.md`.
Environment: Windows 11, Python 3.11.15 (uv venv built from the copy's `uv.lock`, blob 4882ef56), copy of `git archive 701a50e6`; other trees: `7dd225d4`, `6504de03`, master `f6003e87` and `09fc65a8`.
Code hashes (blobs): `delivery/inbox.py` 94630ca7 at 701a50e6 (7804f0ff at 7dd225d4); `tests/advice_scan.py` b12e97e1; `tests/test_cli_advice_resolves.py` 83bb2c05. Config/fixtures/conftest: unchanged by the repair (repair diff = `inbox.py` + manifest only).

| Check | Command and scope | Result |
|---|---|---|
| Repair diff and scope | `git diff 7dd225d4 701a50e6`; `git diff --stat 6504de03 701a50e6` | `inbox.py` only; 13 files, none outside the manifest list |
| Pattern equality | `regex_equal.py`: 28 run ids, then a 502-record store | equal strings and flags; identical lists |
| Advice test | `pytest tests/test_cli_advice_resolves.py -p no:xdist -o addopts=` (33 collected) | 33 passed |
| Scanner | `scanner.py` (delivery dir f-strings, old file, synthetic bad/good) | clean at head; old file and bad sample flagged |
| C6 C7 C8 C9 C11 | manifest `-k` commands, 3 delivery files | 4 / 3 / 3 / 4 / 18 passed |
| Own inputs | `crit_inputs.py` | all asserts passed |
| Delivery files | 3 files (97 collected) | 97 passed |
| Scanner files | 16 files `-o addopts=` | 240 passed |
| ruff, doctor | `ruff check src tests scripts`; `autotester doctor` | clean, clean |
| Falsifications | 3 copies | red after, green restored |
| Hosting-deploy | at 6504de03, 7dd225d4, 701a50e6 | same 2-key red; green after merge |
| env_creation | head, mbase alone; master and merge alone and combined | red 5 of 5 on old base; intermittent on master |
| Trial merge | clone on C:, master `09fc65a8` + `701a50e6` | 1 conflict (`.env.example`), advice 33 (24 sites), hosting 10, delivery 97, ruff, doctor clean |

Reuse note: C1-C5, C10 and C12 inputs (`email.py`, `message.py`, `schema/delivery.py`, template) are byte-identical to the previously checked state; their recorded results stand. Evidence: `qa/evidence/t201a-delivery-core-r2-A/`.
