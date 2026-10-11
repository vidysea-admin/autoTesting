# Checkpoint A - t201a-delivery-core (cycle 0, coordinator A, blind dual check)

Policy-Version: proportional-verification/2026-10-10.9
Verdict: FAIL (C11). Attribution: checker coordinator A, qa/verdicts/t201a-delivery-core.a.md.

## Environment fingerprint
- Source: `git archive 9b6d44c1` extracted on C: (short base dir); venv on C:, Python 3.11.15; PYTHONPATH pinned to the extraction, `autotester.__file__` verified.
- Base master 6504de03; head 9b6d44c1 (code 66ba7be4). Dependency lock `uv.lock` blob 4882ef560a75. `tests/conftest.py` blob 6e574e9606ee.

## Code hashes (blobs at 9b6d44c1)
- src/autotester/delivery/email.py 478ce461da75
- src/autotester/delivery/inbox.py 276285e1678e
- src/autotester/delivery/message.py 256a848d0a11
- src/autotester/delivery/__init__.py f09c6ec73fd2
- src/autotester/delivery/templates/report_email.txt 2483e175f90e
- src/autotester/schema/delivery.py a16e66e4fac3
- tests/delivery_fakes.py 0be577a34bd6, tests/test_delivery_smtp.py ac27cc180684, tests/test_report_email.py 193d678d2044, tests/test_delivery_failure.py 7d63b38ae3f6
- .env.example 18a18c67b30c, docs/MAP.md 538d1f9d3145

## Evidence identities (all under qa/evidence/t201a-delivery-core-A/, all at code 9b6d44c1)
| Check | Command / scope | Result |
|---|---|---|
| Delivery tests | pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py, 74 collected | 74 passed |
| Floors C1-C11 | falsify.py C1..C11, `-k` per row, copy per mutant | falsify_C1-C11.out: 10 red, C6 survived |
| Floor C12 + M1-M5 | falsify.py C12 M1..M5 | falsify_C12_M1-M5.out: C12, M1, M3, M4, M5 red; M2 survived |
| Credential and TLS | cred.py | cred.out: no leak, fail-closed |
| Injection | inject.py, unicode_wire.py | inject.out: one well-formed message |
| No real mail | netguard.py over the delivery tests | netguard.log: loopback connects only, no DNS |
| Message and URL forms | msg_attack.py | `//host` accepted |
| Delivery log | log_attack.py, repro_key_collision.py | log_attack.out, repro_key_collision.out: key collision reproduced |
| Lint and doctor | ruff check src tests scripts; autotester doctor | clean |
| Full suite | not run | not owed (a criterion failed) |

Reuse notes: the C1-C10, C12 evidence stays valid while the files above are unchanged; a repair to inbox.py invalidates C6-C9 and C11 and requires the C11 repro to be re-run; a repair to schema/delivery.py invalidates C10 and C12.
