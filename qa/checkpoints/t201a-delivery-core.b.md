# Checkpoint B - t201a-delivery-core (cycle 0, coordinator B, blind dual check)

Verdict: FAIL (C11, finding P1). Verdict file: `qa/verdicts/t201a-delivery-core.b.md`. Policy-Version: proportional-verification/2026-10-10.9. Resume 0 of 2. Written 2026-10-11T15:30+05:30.

## Evidence identity (per completed check)

Common to every row: tree `82f4f2a0e295e4784ddfa020b647c85212efe4fa` (head 9b6d44c1, code commit 66ba7be4, base 6504de03), extracted with `git archive 9b6d44c1` on C: (scratchpad `src/`, own venv on C:, Python 3.11), `uv.lock` blob `4882ef560a7547c4d4b3cab65089769691545e44`, no `.env` read, no network beyond loopback. Original checker attribution: claude-sonnet-subagent (checker coordinator B), files under `qa/evidence/t201a-delivery-core-B/`.
Code blobs: `delivery/email.py` 478ce461da756d2ec194ba5a08ea7c3f5c2629b5, `delivery/inbox.py` 276285e1678e57df6ddf09de959d77aa7f46236b, `schema/delivery.py` a16e66e4fac315fb0a18bfc20d1985dcd881dff8, `delivery/message.py` 256a848d0a11b9f43a8a7eda96cf14f283cd6205.

| check | command and scope | result | file |
|---|---|---|---|
| delivery tests | `uv --directory <copy> run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py` (74 collected) | 74 passed | out/pytest3.txt |
| ruff | `uv run ruff check src tests scripts` | All checks passed | out/ruff.txt |
| doctor | `uv run autotester doctor` | clean | out/doctor.txt |
| wire failure modes | `python harness/wire.py` (15 loopback modes, disk grep, log capture) | see verdict table 1 | out/wire2.txt (wire1 superseded: password-unset hit a dead port) |
| hostile values and body bytes | `harness/hostile.py`, `harness/extra.py` | see verdict table 2 | out/hostile1.txt |
| may_email, idempotency, retry, outbox, config | `harness/semantics.py` | tables 3 and 4; F1 reproduced in section 4f | out/sem1.txt |
| falsification, 12 criteria + 2 extra | `harness/falsify.py C1..C12 C6b-os-replace` in copies under `falsB/` | all 12 red-after; os.replace caught by the whole delivery suite | out/fals2.txt, fals3.txt, fals4.txt |

Not run by design: full suite, suite lock, browser. Reusable on an unchanged evidence identity: everything above for files whose blobs are listed.

## To re-check after a fix (repair checker)

Re-run `harness/semantics.py` section 4f (user ids `alice.smith` then `alice`: expect two messages, each record carrying its own user id); the 8-thread / 4-process / crash cases of section 4; falsification C11 (claim always true) and one for the new exact-match rule; read the repair diff of `delivery/inbox.py`; decide P2 (uncontained FileExistsError) together with F1.
