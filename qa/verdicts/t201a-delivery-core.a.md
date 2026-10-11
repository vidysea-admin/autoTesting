# Verdict A - t201a-delivery-core (slice A0 of T-201a) - blind dual check, coordinator A

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting. Head 9b6d44c1 (code 66ba7be4), branch wave/t201a-delivery-core, base master 6504de03. Checked from a `git archive` of 9b6d44c1 extracted on C: (no checkout, worktree or venv on D:); `autotester.__file__` confirmed to resolve inside the extraction.
Date: 2026-10-11. Checkpoint: qa/checkpoints/t201a-delivery-core.a.md. Evidence: qa/evidence/t201a-delivery-core-A/.

## Check plan
Tier L, dual-trigger security src/autotester/delivery/email.py:149 (`client.login(cfg.user, password)`; confirmed by the diff read). Plan: (1) whole-diff scope audit (13 files, no deletions, no forbidden files); (2) credential and TLS attack on email.py:130-160 (cred.py); (3) header and address injection (inject.py, unicode_wire.py); (4) no-real-mail proof with a connect and DNS guard over the whole delivery test set (netguard.py); (5) message content and `report_url` forms (msg_attack.py); (6) delivery log and at-most-once, threads and processes (log_attack.py, repro_key_collision.py); (7) one falsification per criterion plus five security mutants (falsify.py); (8) rulings on the six builder gaps and the D-082 new-module table; (9) ruff and doctor. Full suite only if every criterion is met.

VERDICT: FAIL
SCOREBOARD: 11/12 criteria met (C1-C10, C12); 1 not met (C11). Test-quality findings: C6 mutant survived, implicit-SSL verification unpinned (M2), pure CR/LF address survives (C12 variant).
TIER: L (security trigger email.py:149, cited by the manifest)

FAILURES:
- [C11 correctness] sev: medium - the idempotency key is not injective, and the log reads it back with an unanchored glob. `delivery_key` (inbox.py:52-56) joins `safe_id(run_id)`, channel and `safe_id(user_id)` with `__`, and `SAFE_ID` (schema/delivery.py:22) admits `.`, `_` and `-`. `records_for_key` (inbox.py:102-103) globs `f"{key}.*.json"`, so the key `run-1__email__alice` also matches the record of `alice.smith`. Reproduced (repro_key_collision.py, run by me): after `alice.smith` is mailed for run-1, `deliver_once` for `alice` on the same run returns alice.smith's record and sends nothing; `alice` never has a record of her own, so she is silently never mailed ("alice has own record: False"). Second form: run id `x__email__y` with user `z` and run id `x` with user `y__email__z` produce the identical key (True). Third form: `records_for_run('x')` (inbox.py:105-107, glob `x__*.json`) returns the rows of run `x__email__y`, so the run page would show another run's recipients. Evidence: qa/evidence/t201a-delivery-core-A/repro_key_collision.out and log_attack.out. Why it matters: at-most-once is met, but at-least-once is not: a real recipient is suppressed and the answer returned for her is another person's record. The fix is local (anchor the glob on `.NN.json` with a regex, or encode `_`/`.` in the key).

## Per-criterion results
- C1 MET. Default off, strict model; `may_email` needs the box ticked AND report.view at send time. Floor C1 (tick-or-view) red 1 failed. Not served (profile page, held) is outside this slice.
- C2 MET. Body fields exactly project, run id, time, counts, coverage line, label, link; the label is the closed vocabulary; planted canary absent; text scrubbed. Floor C2 red 2 failed.
- C3 MET. `select_transport` picks the outbox unless the config is complete; `_default_factory` refuses a non-loopback host under pytest. The network guard (netguard.py) recorded 2 connects in the whole delivery test set, both 127.0.0.1, and zero DNS lookups. Floor C3 red.
- C4 MET. STARTTLS then login; `ssl.create_default_context()` at email.py:120 and :144; plain-text login refused for a non-loopback host (SmtpConfig validator, M3 red); the password is read only through `password_source` at email.py:149 and appears in no error text, repr, record, outbox file or log (cred.py, positive controls included; M4 and M5 red). Fail-closed on a bad certificate. Floor C4 red.
- C5 MET. Only email.py imports smtplib. Floor C5 red.
- C6 MET in behaviour, test weak. Every attempt writes a strict DeliveryRecord, the user id and never the address on disk (no `@x.test` in any file). The C6 floor (`os.link` -> `os.replace`) SURVIVED: no test pins create-once. See the key bug above for the C6 read side.
- C7 MET. Retry delays 1, 5, 30 min, `MAX_ATTEMPTS = 4`, bounded (5-call run stops at 4 sends). Floor C7 red.
- C8 MET. Any exception from the transport becomes a `failed` record; a KeyboardInterrupt propagates and leaves a marker that blocks a resend for 10 min. Floor C8 red.
- C9 MET. Error text is class name plus SMTP code, scrubbed, capped at 500; a secret in an unexpected exception is absent from the record and every file. Floor C9 red.
- C10 MET with a validator bug. `report_url` refuses query, fragment, userinfo, javascript:, data:, ftp:, CR/LF and spaces. BUG: `//evil.test/x` and `///evil.test/x` are ACCEPTED because the site-relative branch `/[A-Za-z0-9._~/-]*` matches a leading `//` (schema/delivery.py:27; msg_attack.py output). In an email a protocol-relative link resolves to another host. Severity low here because the caller supplies the link base and no route builds one yet, but it breaks the stated "goes to a route that requires sign-in" guarantee. Floor C10 red.
- C11 NOT MET (medium), see FAILURES. The claim/marker scheme is sound otherwise: 12 threads x 5 trials sent exactly once; 8 processes x 3 trials sent exactly once; a crash between send and record is never resent, closes terminal after 10 min.
- C12 MET. CR/LF, a second address, an encoded-word display name that decodes to CRLF, and a unicode display name or body all produce one well-formed 7-bit message with a single To and no Cc/Bcc (inject.py, unicode_wire.py). Floor C12 (regex allowing CR/LF) survived because the validator uses `fullmatch` and the weaker mutant is equivalent for most cases; the `if False:` form is red (10 failed). A pure CR/LF address is not in the parametrized set.

## Falsifications (one copy per mutant, green-before / red-after / restored, rc in falsify_*.out)
| ID | Mutation | Result |
|---|---|---|
| C1 | tick OR view | red (1 failed) |
| C2 | label forced "green" | red (2 failed) |
| C3 | under-test refusal off | red |
| C4 | STARTTLS branch disabled | red |
| C5 | `import smtplib` in message.py | red |
| C6 | `os.link` -> `os.replace` | SURVIVED (no test pins create-once) |
| C7 | no retry bound | red (1 failed) |
| C8 | `except TransportError` | red |
| C9 | error not scrubbed | red (1 failed) |
| C10 | allow `?#` in URL | red (1 failed) |
| C11 | claim always True | red (2 failed) |
| C12 | address check off | red (10 failed) |
| M1 | STARTTLS unverified context | red |
| M2 | implicit-SSL unverified context | SURVIVED (implicit-SSL verification is unpinned) |
| M3 | plain-text login allowed | red |
| M4 | error carries server words | red (2 failed) |
| M5 | password in adapter repr | red |
Mutants beyond the floor: 5 of 10 allowed. Equivalent mutants: none claimed.

## Builder's six gaps - rulings
1. Retry numbers (1, 5, 30 min; 4 attempts): MET as bounded backoff; the numbers are the builder's choice and acceptable.
2. TLS default: MET and fail-closed (starttls unless port 465 -> ssl or `_TLS` is 0/none/false; bad value -> None -> outbox).
3. Crash between send and record: MET (never resent; 10-minute terminal close; narrow at-least-once-never-twice stance is correct for mail).
4. No recipient allow-list: MET as designed (`may_email` gate plus address validation); no allow-list is required by the contract text.
5. Caller-supplied link base: MET, but see C10 `//host` bug which lets a caller-supplied path escape the base.
6. Enum home (`schema/delivery.py` rather than `team_enums.py`): acceptable until team_enums exists; the move is held (TF8).
Flag: the module `inbox.py` holds the delivery ledger and `deliver_once`, not an inbox store; the name differs from the brief's "inbox store". Low, naming only.

## D-082 new-module table
| Module | Named by brief/contract | One-job docstring | Doctor |
|---|---|---|---|
| delivery/email.py | yes | yes | clean |
| delivery/inbox.py | yes (name; job differs, see above) | yes | clean |
| delivery/message.py | yes | yes | clean |
| delivery/__init__.py, templates/report_email.txt | yes | n/a | clean |
| schema/delivery.py | yes | yes | clean |
All new modules listed by this checker; table acceptable.

## Other results
- Whole diff 6504de03..9b6d44c1: 13 files, no deletions, no forbidden files; `.env.example` gained `AUTOTESTER_SMTP_FROM_NAME=` with no value. No value from the repo-root `.env` was read or printed.
- Tests: the three delivery test files, 74 passed in the clean copy. ruff clean, `autotester doctor` clean on the extraction.
- Blindness kept: no `.b.md` file and no `-B` evidence directory was opened.

PROPOSED-ISSUE: [medium, correctness] delivery key not injective and `records_for_key`/`records_for_run` globs unanchored (inbox.py:52-56, :102-107; schema/delivery.py:22); a real recipient can be silently suppressed and a foreign record returned. Repro: qa/evidence/t201a-delivery-core-A/repro_key_collision.py.
PROPOSED-ISSUE: [low, security] `report_url` accepts protocol-relative `//host/...` (schema/delivery.py:27).
PROPOSED-ISSUE: [low, test-quality] no test pins create-once (`os.link`) in DeliveryLog.append (C6 mutant survived).
PROPOSED-ISSUE: [low, test-quality] implicit-SSL path (port 465) never asserts certificate verification (M2 survived).
PROPOSED-ISSUE: [low, test-quality] `test_recipient_address_validation_rejects_injection_and_malformed` has no pure CR/LF address case.
PROPOSED-ISSUE: [low, naming] `delivery/inbox.py` holds the delivery ledger, not an inbox store.

full-suite: not owed because a criterion failed
LIVE-BROWSER: not-applicable
Metrics: start=unavailable end=2026-10-11T15:31:00+05:30 wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=17 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=17 defects_unit=1 defects_6c=0
