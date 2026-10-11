# Verdict B (blind dual check) - t201a-delivery-core (T-201 phase A0, report delivery core)

Date: 2026-10-11. Coordinator B. Cycle checked: 0. Resume: 0 of 2 (the session was compacted once; no checkpoint verdict was written). Policy-Version: proportional-verification/2026-10-10.9. Head 9b6d44c1 (code 66ba7be4), base master 6504de03, branch `wave/t201a-delivery-core`.
Tree judged: `git archive 9b6d44c1` extracted on C: with its own venv on C: (D: had ~900 MB free; no checkout, worktree or venv was made on D:). Every probe printed `autotester.__file__` inside that copy (`wire2.txt` line 1; `inside_copy: true` in `fals2.txt`, `fals3.txt`, `fals4.txt`). Blindness: I never opened a `.a.md` file or a `-A` directory for this unit. No value of any `AUTOTESTER_SMTP_*` key was read: `.env` was not opened, and every server below is a loopback server run inside my own process (fake addresses at `example.com`, a made-up canary password and user name).

## Plan

Tier L, dual-trigger security `src/autotester/delivery/email.py:149`. Checks: (1) the send path against 15 loopback failure modes; (2) wire bytes of a normal send and of hostile values; (3) the `may_email` x `NotificationPref` table; (4) `deliver_once` counted on the server (sequential, 8 threads, 4 OS processes, simulated crash, clock skew, key collisions); (5) the retry numbers; (6) rulings on the 8 builder gaps; (7) whole-diff scope, forbidden files, `smtplib` import, line limits, ruff, doctor; (8) the D-082 table; (9) one named falsification per criterion in a throwaway copy on C:. No full suite, no suite lock, no browser (no route or page was built).

VERDICT: FAIL
SCOREBOARD: 11/12 criteria met, 1 not met (C11); invariants C1, C2, C3, C5 hold
TIER: L (security: SMTP password used at email.py:149; outward-facing mail)

FAILURES:
- [C11 idempotency: one (run, channel, recipient) is sent once] sev: high - `DeliveryLog.records_for_key` (inbox.py, `self._load(f"{key}.*.json")`) matches a record file of ANOTHER recipient whenever one user id is a dotted prefix of another (`alice` vs `alice.smith`; `SAFE_ID` in schema/delivery.py allows `.`). Reproduced on the wire (`harness/semantics.py` section 4f, output in `out/sem1.txt`): `alice.smith` is mailed first; then `deliver_once` for `alice` finds `run-0001__email__alice.smith.01.json`, treats `alice` as already sent, sends NOTHING, and RETURNS a record whose `recipient_user_id` is `alice.smith`. alice never gets her report and the log shows no trace of her. The reverse order sends both, so the outcome depends on arrival order. The builder's tests use ids with no shared dotted prefix, so none of the 74 tests sees it. Fix direction: match the file name exactly (a regex `^{key}\.\d{2}\.json$`, or take the attempt number from a fixed-width suffix) instead of the glob.

CRITERIA (judged as the manifest quotes the contract)
- C1 (TT8/HO26 preference, default off, only when ticked AND still allowed to view): MET. `may_email` table below: true only for ticked=True with can_view=True; no stored pref, default pref, ticked=False, or can_view=False are all False. Extra fields (`to`, `cc`) rejected by `extra="forbid"`. Falsified (F-C1).
- C2 (TT8/HO28 body exactly the listed fields, label as stored, no attachment, text scrubbed): MET. Wire message is one `text/plain; charset=utf-8` part, quoted-printable, headers From/To/Subject/Auto-Submitted/Date/Message-ID/Content-Type/CTE/MIME-Version, exactly one To, no Cc/Bcc/Reply-To, no attachment; the body equals an independent `string.Template` fill (`extra.py`: `body equals independent fill: True`, `subject equal: True`). Falsified (F-C2).
- C3 (HO27 default adapter is the outbox, nothing contacts a real host, nothing raises): MET. `select_transport` with an empty env, password only, no FROM, bad port (abc, 0, 99999), host with a space, bad sender, sender name with CRLF -> `OutboxAdapter`; zero sockets opened. Under `PYTEST_CURRENT_TEST` the default client factory refuses every non-loopback host (smtp.example.com, localhost.example.com, 127.0.0.2, 0.0.0.0 all refused with "live SMTP is disabled under test", sockets opened: []). Falsified (F-C3).
- C4 (HO27 TLS with certificate verification, password only in the environment, never logged): MET. STARTTLS and implicit SSL against my loopback servers: AUTH arrives only after TLS (`auth_before_tls: [true]`); a self-signed cert and a wrong-host cert are both refused for STARTTLS and for implicit SSL with `SSLCertVerificationError`, zero AUTH attempts and zero messages; a server that does not advertise STARTTLS is refused (`SMTPNotSupportedError`, no AUTH, no message, the password is never sent in clear). Credentials over a plain connection to a non-loopback host: `smtp_config_from_env` returns None -> outbox. Disk grep over all 74 files the harness wrote: 0 hits for the password, the user name, the recipient address, base64 of user+password, base64 of the password. 0 log lines captured; stdout/stderr empty; `repr` of config and adapter leak neither password nor user. Falsified (F-C4).
- C5 (TT8 grep: no module outside `delivery/email.py` imports `smtplib`): MET. `git grep smtplib 9b6d44c1 -- src` shows only email.py. The guard test's regex (`^\s*(import smtplib|from smtplib)`) misses `import os, smtplib`, `import ssl, smtplib as s`, `__import__('smtplib')` (`extra.py`); recorded as a low (P4). Falsified (F-C5) with the plain `from smtplib import SMTP` form.
- C6 (TT9 record per attempt, redacted error, attempt count, next retry, user id not address): MET for the text. Every attempt in every failure mode wrote a `DeliveryRecord` (attempts 1..4, status, a class-name+code error, `next_retry_at` set until the bound); the disk grep found the recipient address nowhere. The returned record is wrong in the F1 case (see C11). Falsified (F-C6, scrub removed).
- C7 (HO29 bounded retry with backoff): MET. Delays 1, 5, 30 minutes; `MAX_ATTEMPTS` 4; an always-failing transport with `max_attempts=1000` made exactly 4 send calls and 0 after the bound; `retry_delay(0)` raises, `retry_delay(4+)` is None; a retry 59 s after a failure is not attempted, at +60 s it is (2 calls in the 3-probe test); inbox.py mentions no sleep, `time.time`, `datetime.now`, `utcnow`. Falsified (F-C7, delays reversed).
- C8 (HO29 failure never raises into the caller): MET. Accept/reject AUTH/reject RCPT/554 on DATA/drop mid-DATA/never answer (no banner, after EHLO, after MAIL FROM, dribble)/no STARTTLS/bad certs/connection refused/password unset: `deliver_once` returned a record every time and raised in none. Falsified (F-C8).
- C9 (error text carries neither the password nor server words): MET. A server that echoes the user, password and recipient in its 535/550/554 replies produced only `SMTPAuthenticationError 535`, `SMTPRecipientsRefused`, `SMTPDataError 554`; the disk grep found nothing. Falsified (F-C9, `str(exc)` appended).
- C10 (TT9 links need sign-in; no token, query, fragment or credentials): MET for what the criterion serves (the static half; the 302 is held). 17 of 25 hostile `report_url` values were refused at the schema (javascript:, userinfo, `?token=`, `#f`, `ftp:`, `data:`, backslashes, CRLF, non-ASCII host, `%0d%0a`, `%2e%2e`). Gaps: `//evil.example/x` and `///evil.example/x` pass (P3), `https://x.test:99999/` passes (low). Falsified (F-C10).
- C11 (idempotency across replays, restarts, racing workers; a crash between sent and recorded is never resent): NOT MET, see FAILURES. Everything else about it holds: 3 sequential calls -> 1 message; 8 threads -> 1 message, 7 None + 1 sent, no exception; 4 OS processes -> 1 message; crash after send (marker, no record): +2m None, +9m59 None, +10m01 one terminal `failed ... not resent`, +3h nothing, server messages total 1. Falsified (F-C11), and the F1 defect is outside what any builder test covers.
- C12 (recipient safety, one To, no Cc/Bcc, header injection refused): MET. CR/LF, `\x0b`, `\x00` in project name, coverage line, sender name, report_url and address were refused at the schema; comma/semicolon/space/angle-bracket/quoted/IP-literal/`localhost`/single-label/trailing-dot addresses refused; the wire message had exactly one From address, one To, no Cc/Bcc in all 50+ cases; `model_construct` bypass of `Recipient` with CRLF and `RenderedMessage` with a CRLF subject reached the server with 0 extra RCPT (a `ValueError` became a failed record). Gaps: U+2028 / U+0085 in a project name and `.a@x.test` / `a..b@x.test` pass the schema and then fail the MIME build, so the failure is recorded and retried 4 times to no purpose (P5). Falsified (F-C12).

WIRE TABLE 1 - failure modes (loopback servers in my process; `harness/wire.py`, `out/wire2.txt`)
| mode | server saw | records written | raised? |
|---|---|---|---|
| accept, plain | 1 message, AUTH before TLS: no TLS requested | 1 sent | no |
| accept, STARTTLS good cert | 1 message, AUTH after TLS | 1 sent | no |
| accept, implicit SSL good cert | 1 message, AUTH after TLS | 1 sent | no |
| reject AUTH (535 echoing user, password) | 4 AUTH attempts, 0 messages | 4 failed `SMTPAuthenticationError 535`, last has no retry time | no |
| reject RCPT (echoing address) | 0 messages | 4 failed `SMTPRecipientsRefused` | no |
| 554 on DATA (echoing) | 4 messages stored by the server | 4 failed `SMTPDataError 554` | no |
| drop mid-DATA | 0 messages | 4 failed `SMTPServerDisconnected` | no |
| drop after full DATA, before the 250 | 4 full messages (one per attempt) | 4 failed `SMTPServerDisconnected` | no |
| never answers: no banner / after EHLO / after MAIL FROM (timeout 1 s) | 0 messages | 1 failed `SMTPServerDisconnected` each (1.1 s, 1.9 s, 1.9 s) | no |
| dribbles one byte at a time (timeout 1 s) | 0 messages | 1 failed; took 20.4 s (the timeout is per socket operation, not per send: P6) | no |
| no STARTTLS advertised, tls=starttls | 0 messages, 0 AUTH | 4 failed `SMTPNotSupportedError` | no |
| STARTTLS or implicit SSL, self-signed cert | 0 messages, 0 AUTH | 1 failed `SSLCertVerificationError` | no |
| STARTTLS or implicit SSL, wrong-host cert | 0 messages, 0 AUTH | 1 failed `SSLCertVerificationError` | no |
| connection refused | - | 1 failed `ConnectionRefusedError` | no |
| password unset (live server) | 0 messages, 0 AUTH | 1 failed "the SMTP password is not set" | no |
| error text echoing credentials | credentials only in the server's reply | none of them on disk, in logs, in stdout/stderr | - |
Note on "drop after full DATA": the mail was fully delivered and the connection died before the acknowledgement, so each retry sends it again (4 copies). Plain SMTP cannot tell this apart from a lost mail; the builder's at-most-once rule (gap 3) covers a crash between sent and recorded, not a transport error after DATA. Recorded as P7 (low); the rule needs a sentence, not a code change.

WIRE TABLE 2 - hostile values (`harness/hostile.py`, `out/hostile1.txt`)
| field | refused at the schema | reached the wire, safe | reached the wire, noted |
|---|---|---|---|
| project_name (Subject and body) | `\r\n`, `\n`, `\x0b`, `\x00`, 201 chars | `Shop <evil@x.test>`, `Shop; Bcc: x`, `Subject: spoof`, `$project ${run_id} $$` (literal, not substituted) | an RFC 2047 encoded word decoding to `Shop\r\nBcc: x@evil.test` is on the wire as an encoded word (no header injection) but a mail client displays a CRLF in the Subject (P8, low); ` ` / `\x85` fail the MIME build (P5) |
| coverage_line | CRLF, `=3D =\n` | `.` and `..` dot-stuffed (`..`, `...`) so the body cannot end the DATA early; `-- ` | `\x85.` splits a line in the viewer (cosmetic) |
| sender_name | CRLF, 101 chars | `Eve <evil@example.com>`, `Eve, Mallory <m@x.test>`, encoded words: all quoted into ONE display name, one From address | ` x` reaches From |
| report_url | javascript:, userinfo, query, fragment, ftp:, data:, backslash, CRLF, non-ASCII, `%0d%0a`, `%2e%2e` | site-relative `/runs/run-0001`, `https://host:8443/runs/r1` | `//evil.example/x`, `///evil.example/x`, `:99999` pass (P3) |
| recipient address | list, CRLF, space, quoted, angle, IP literal, `localhost`, `a@x`, trailing dot, display-name form | `a+tag@x.test`, `A@X.TEST` | `.a@x.test`, `a..b@x.test` fail the MIME build (P5) |
| `model_construct` bypass (no validation) | - | CRLF address and CRLF subject: ValueError at the MIME build, 0 extra RCPT on the server | - |

WIRE TABLE 3 - `may_email` x `NotificationPref` (`harness/semantics.py` section 3)
| pref | can_view_report | may_email |
|---|---|---|
| none stored | True / False | False / False |
| default `NotificationPref(user_id)` (`email_run_reports` False) | True / False | False / False |
| ticked False | True / False | False / False |
| ticked True | True | True |
| ticked True | False | False |
Observations: `NotificationPref` coerces the strings `yes`, `on` and the int `1` to True (P9, low: strictness is pydantic's lax bool); extra fields `to` and `cc` are rejected; `may_email(pref_of_a_different_user, can_view=True)` is True because the signature has no recipient parameter (P9).

WIRE TABLE 4 - `deliver_once` idempotency, counted on the server (`out/sem1.txt` section 4)
| scenario | messages the server stored | result |
|---|---|---|
| called 3 times, same (run, channel, recipient) | 1 | sent, sent, sent (replays return the settled record); one record file |
| 8 threads at once | 1 | 7 None, 1 sent, no exception |
| 4 OS processes at once | 1 | one sent, three None, no stderr |
| crash after send (marker exists, no record) | 1 | +2m / +9m59 None; +10m01 one terminal failed "not resent"; +3h nothing; total 1 |
| crash after claim, nothing sent | 0 | closed as "not resent" after 10 min; the mail is lost (documented at-most-once, gap 3) |
| second worker with a clock ahead closes a live attempt | 1 | the first worker's own `append` then RAISES `FileExistsError` after its mail was sent; the record says failed "not resent" (P2, medium) |
| user ids `alice.smith` then `alice` | 1 (to alice.smith only) | `alice` silently not mailed, wrong record returned (F1, FAIL) |

RULINGS on the builder's 8 gaps and 4 choices
1. Retry numbers (1, 5, 30 min; `MAX_ATTEMPTS` 4): ACCEPT. The brief's "three attempts, delays 1, 5 and 30" is self-inconsistent; 4 attempts with 3 delays honours the delays and bounds the attempts. Needs one contract line (hosting.md HO29: "first try plus three retries after 1, 5 and 30 minutes").
2. TLS default to STARTTLS when `_TLS` is unset: ACCEPT, with a contract line (HO27 says TLS "when `_TLS` is set"). Plain with credentials is refused off loopback (verified). A mistyped `SENDER_NAME` or any bad key silently downgrades to the outbox (P10, low): there is no visible signal that mail is not going out.
3. At-most-once crash rule (10 min stale close): ACCEPT as a design, NEEDS A CONTRACT LINE (TT9) naming the lost-mail window; the F1 bug and P2 are defects in its implementation, not in the rule. The drop-after-DATA duplicate (P7) belongs in the same line.
4. No allow-list hook: ACCEPT, nothing in the contract asks for one.
5. `report_url` given by the caller: ACCEPT; P3 (`//host`) asks for a stricter pattern, not a new key.
6. Vocabularies in `schema/delivery.py` until `team_enums.py` exists: ACCEPT, held to TF8 (a low row, one concept one place).
7. `delivery/inbox.py` holds the delivery-record store: ACCEPT for this slice; the file is called inbox but stores delivery records (P11, naming only); phase A1 should either rename it or add the inbox module the brief names.
8. `AUTOTESTER_SMTP_TLS` documented in `.env.example` and read: ACCEPT (optional key, not one of the six).

DIFF SCOPE (step 4c): 13 files changed, 1505 insertions, 0 deletions (`git diff --stat 6504de03 9b6d44c1`): the 5 new `src/autotester/delivery/*` and `schema/delivery.py` files, 4 new test files (`delivery_fakes.py`, three `test_*`), the manifest, `.env.example` (+2 lines), `docs/MAP.md` (+14). No forbidden file touched (checked `team_store`, `team_enums`, `schema/project`, `routes_runs`, `run_launcher`, `run_queue`, `run_execution`, `cli.py`, `core/paths`, `safe_names`, `pyproject.toml`, `uv.lock`, `auth/`: no match). No existing test edited, no skip/xfail, nothing deleted. Line limits: email.py 195, inbox.py 176, message.py 34, schema/delivery.py 201, delivery_fakes.py 206, test files 223/133/174, all under 300; doctor (function <= 50 lines, docstrings) clean. `smtplib` imported only in email.py. `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: clean. The three delivery test files: 74 passed in the C: copy (19.8 s).

D-082 ITEM 1 TABLE (new modules)
| module | (a) brief/contract names it | (b) docstring one job | (c) doctor clean | (d) listed here |
|---|---|---|---|---|
| schema/delivery.py | MET (brief section 5, plan-named) | MET | MET | yes |
| delivery/__init__.py | MET (brief section 5) | MET | MET | yes |
| delivery/email.py | MET (brief section 5, TT8 grep) | MET | MET | yes |
| delivery/inbox.py | MET by name; its job here (delivery-record store) differs from the brief's "inbox store" (P11) | MET | MET | yes |
| delivery/message.py | MET (brief section 5 lists it as "not plan-named, proposed"; the brief names the file) | MET | MET | yes |
| delivery/templates/report_email.txt | not a module; a data file the brief does not name; ruled a low | n/a | n/a | yes |
| tests/delivery_fakes.py | MET (brief section 5 row) | MET | MET | yes |

FALSIFICATIONS (one named per criterion; each in a throwaway copy under the scratchpad on C:, deleted by the script afterwards; `harness/falsify.py`, `out/fals2-4.txt`; every copy printed its own `autotester.__file__`)
| criterion | edit | before | after (red) |
|---|---|---|---|
| C1 | drop `and can_view_report` in `may_email` | 1 passed | `test_a_report_is_mailed_only_when_ticked_and_still_allowed_to_view_it` failed |
| C2 | label hard-coded to "green" in `render_message` | 1 passed | `test_body_carries_exactly_the_ho28_fields` failed |
| C3 | `if config is None:` -> `if False:` in `select_transport` | 1 passed | `test_default_selection_without_credentials_is_the_outbox_and_sends_nothing` failed |
| C4 | skip the `starttls(...)` call | 1 passed | `test_starttls_then_login_then_send_with_certificate_verification_on` failed |
| C5 | add `from smtplib import SMTP` to inbox.py | 1 passed | `test_only_the_email_adapter_imports_smtplib` failed |
| C6 | store the unscrubbed text (`error = text[:ERROR_LIMIT]`) | 1 passed | `test_failure_text_is_redacted_in_the_record_and_on_disk` failed |
| C7 | reverse `RETRY_DELAYS` | 1 passed | `test_backoff_is_a_pure_increasing_bounded_schedule` failed |
| C8 | `except Exception` -> `except (TransportError, OSError)` | 1 passed | `test_an_unexpected_exception_is_contained_recorded_and_scrubbed` failed |
| C9 | append `str(exc)` to `_describe` | 1 passed | `test_authentication_failure_text_carries_neither_password_nor_server_words` failed |
| C10 | `_URL = re.compile(r".*")` | 12 passed | 5 failed (javascript:, ftp: and others) |
| C11 | `claim` always returns True | 1 passed | `test_two_workers_racing_for_one_attempt_send_exactly_once` failed |
| C12 | remove the control-character check in `single_line` | 2 passed | `test_sender_name_with_a_line_break_is_refused_at_config` failed |
Extra (beyond the floor, mutants=2): `os.link` -> `os.replace` in `_create_once` is caught by the whole delivery suite (74 passed -> 2 failed: the crash and race tests) but NOT by `test_records_are_append_only_files_never_rewritten` alone, so that test does not pin create-once by itself (low, P12); `_settled` looping over `[]` survives `test_a_successful_send_is_recorded_once_and_replays_deliver_nothing` because the claim marker blocks the resend anyway (equivalent behaviour, defence in depth).
First falsification run: `out/fals1-first-run-crashed-at-C5-base-dir-vanished.txt`: the shared scratchpad's `fals/base` directory was gone by C5 (not caused by my script; I never opened the other directories there) and the harness checked `autotester.__file__` with `python -I`, which ignores PYTHONPATH. I rebuilt the base from `git archive 9b6d44c1` into `falsB/`, dropped `-I`, and re-ran all 12 plus the two extras; those are the results above.

PROPOSED-ISSUE lines (no ledger write)
PROPOSED-ISSUE: {"severity":"high","feature":"delivery","title":"DeliveryLog.records_for_key globs `{key}.*.json`, so a recipient whose user id is a dotted prefix of another's is treated as already sent and gets the other user's record back","evidence":"inbox.py records_for_key / _load; schema/delivery.py SAFE_ID allows '.'; harness/semantics.py section 4f, out/sem1.txt","status":"open"} (P1, FAIL on C11)
PROPOSED-ISSUE: {"severity":"medium","feature":"delivery","title":"deliver_once main-path log.append is uncontained: with a clock-skewed second worker closing a live attempt, the first worker's own append raises FileExistsError after its mail was sent, and the record says 'not resent'","evidence":"out/sem1.txt 4e; inbox.py deliver_once, _close_stale","status":"open"} (P2)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"ReportSummary.report_url accepts protocol-relative `//host/x` and `///host/x`, and port 99999","evidence":"schema/delivery.py _URL; out/hostile1.txt report_url rows","status":"open"} (P3)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"The smtplib-import guard regex misses `import os, smtplib`, `import ssl, smtplib as s` and `__import__('smtplib')`","evidence":"harness/extra.py last block; tests/test_delivery_smtp.py test_only_the_email_adapter_imports_smtplib","status":"open"} (P4)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"U+2028 / U+0085 in a text field and `.a@`/`a..b@` addresses pass the schema but fail the MIME build, so the failure is retried 4 times to no purpose","evidence":"out/hostile1.txt (transport:ValueError, transport:InvalidHeaderDefect); schema/delivery.py single_line, Recipient","status":"open"} (P5)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"The SMTP timeout is per socket operation: a server that dribbles bytes held one send for 20.4 s against a 1 s timeout; there is no total deadline","evidence":"out/wire2.txt dribble(timeout1s); email.py SmtpAdapter.send","status":"open"} (P6)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"A connection that drops after the full DATA but before the 250 is retried and delivers up to 4 copies; the at-most-once rule covers only a crash between sent and recorded","evidence":"out/wire2.txt drop-after-full-data (server_messages 4)","status":"open"} (P7)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"An RFC 2047 encoded word in project_name that decodes to CRLF is shown by a mail client as a multi-line Subject","evidence":"out/hostile1.txt project_name rows","status":"open"} (P8)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"may_email takes no recipient and does not bind the preference to the user; NotificationPref coerces 'yes', 'on', 1 to True","evidence":"out/sem1.txt section 3","status":"open"} (P9)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"A mis-set optional key (for example a bad SENDER_NAME) silently downgrades select_transport to the outbox with no signal that mail is not going out","evidence":"out/sem1.txt section 6","status":"open"} (P10)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"delivery/inbox.py holds the delivery-record store, not the inbox the brief names; the template file is not named in the brief","evidence":"manifest gap 7; brief section 5","status":"open"} (P11)
PROPOSED-ISSUE: {"severity":"low","feature":"delivery","title":"test_records_are_append_only_files_never_rewritten does not pin create-once on its own (os.replace in _create_once survives it)","evidence":"out/fals4.txt C6b-os-replace","status":"open"} (P12)

CAPABILITY-COVERAGE: 12/12 criteria falsified red in C: copies; 2 extra mutants (1 caught by the suite, 1 equivalent)
LIVE-BROWSER: not-applicable (no route, page, template or static file in the diff)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The mail path is sound on the wire: TLS is verified, the password is never sent in clear or written anywhere, error text is a class name plus a code, no failure mode raises, the retry bound holds, and hostile values never produce a second recipient or a second header. The unit fails on one reproduced defect in the send-once procedure: the record lookup uses a glob, so a user whose id is a dotted prefix of another user's is silently not mailed (P1). P2 is a medium that should be fixed in the same cycle; the lows can go to the ledger.
Metrics: start=2026-10-11T14:47:59+05:30 end=2026-10-11T15:30:00+05:30 wall_min=42 agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=1 mutations=14 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2520 mutants=2 defects_unit=1 defects_6c=0
