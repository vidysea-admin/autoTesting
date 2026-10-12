# Checkpoint - t201a-delivery-core - cycle 1 - coordinator A (verdict qa/verdicts/t201a-delivery-core.r1.a.md, FAIL)

Attribution: checker coordinator A, claude-sonnet-subagent, 2026-10-11. Environment: Windows 11, CPython 3.11 (uv venv inside a `git archive 7dd225d4` copy on C:), uv.lock blob 4882ef560a75. Tree 7dd225d4 (tree 2c1c55f23b65).
Code blobs at 7dd225d4: delivery/inbox.py 7804f0ff8330, schema/delivery.py a0c742d1616a, delivery/email.py 478ce461da75 (unchanged in the repair), tests/test_delivery_failure.py b7933527c221, tests/test_delivery_smtp.py 345b847a377b, tests/test_report_email.py 88c0b26e9d1b, tests/delivery_fakes.py 0be577a34bd6, tests/test_cli_advice_resolves.py 83bb2c05c9b9, tests/advice_scan.py b12e97e176db. No config/conftest change.

| Check | Command and scope | Result |
|---|---|---|
| Affected tests | `pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts=` (97 collected) | 97 passed |
| Pre-check -k sets C1..C12 | same files with each manifest -k | counts equal the manifest (2,7,14,15,1,4,3,3,4,23,18,19) |
| Key injectivity property test | qa/evidence/t201a-delivery-core-r1-A/scripts/prop_inj.py | PASS (583,200 exhaustive + 5,896 random + adversarial; disk lookups exact) |
| Interleavings + long ids | scripts/interleave.py | 4 interleavings one send each; ValueError escapes for 64+64 capital ids |
| F1/F3/C12 direct | scripts/f_items.py | all as expected |
| Falsification x5 | scripts/fals.py, one copy each | green before, red after (2,2,1,3,3 red) |
| ruff + doctor | `ruff check src tests scripts`; `autotester doctor` | clean |
| Full suite | `shard_suite.py --repo D:/autoTesting --ref 7dd225d4 --shards 4 -- -o addopts=` | 3599 passed, 7 failed, 20 skipped; 1 new red (test_cli_advice_resolves), 3 same at 6504de03, 3 listed load-sensitive |
| cli-advice red at three refs | pytest tests/test_cli_advice_resolves.py at 7dd225d4 / 9b6d44c1 / 6504de03 | red / green / green |

Reusable on a re-submit only if the corresponding blobs above are unchanged: the property test, interleavings and falsifications depend on inbox.py and schema/delivery.py; the suite result does not carry over (any src change can reach test_cli_advice_resolves).
