# Manifest - t201a-delivery-core

**Unit:** T-201 / G4 phase A0 `t201a-delivery-core`: the pure parts of report delivery that touch no file owned by a unit in flight (message composition, outbox and SMTP adapters, delivery records, send-once procedure, retry schedule, recipient safety).
**Brief:** `qa/briefs/t201a-report-delivery.md` (untracked on master; its "base" line is stale). **Contract:** `qa/contracts/team-test-button.md` TT7-TT9 and `qa/contracts/hosting.md` HO26-HO29, plus `core-invariants.md`.
**Branch / base:** `wave/t201a-delivery-core` on master `6504de03`.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (outward-facing email; the module holds the SMTP password)
Dual check: required
dual-trigger: security src/autotester/delivery/email.py:149 (`client.login(cfg.user, password)`, the only place the SMTP password is used; the `smtplib` import is line 18, `SmtpAdapter.send` line 138, the password is read from the environment mapping at send time at line 195)
Contract: C1 C2 C3 C4 C5 C6 C7 C8 C9 C10 C11 C12 (ids below are this manifest's, mapped to contract clauses; the contract has no C-numbers for TT/HO rows)
Fix cycle: 0
Executor: claude-sonnet-subagent (maker build subagent)
Code commit (pre-check sha): 66ba7be4 (the manifest commit after it adds only this file)
Status: ready-for-check
Persona walk: not applicable to this slice (no route or page is built; the persona walk belongs to phase A1/B).

## Criteria served (quoted from the contract; the pure half only)

- **C1 (TT8, HO26)**: "a per-user checkbox "Email me run reports", stored per user, **default off** (`schema/delivery.py` `NotificationPref`, extra="forbid")" and "**only if** that user's box is ticked **and** they hold `report.view` on the project **at send time**". Served: `NotificationPref` (default off, strict) and the pure rule `delivery/email.py::may_email`. NOT served: the profile page, and a real `report.view` lookup (held).
- **C2 (TT8, HO28)**: "The message body is exactly `hosting.md` HO28's (project, run id and time, counts, coverage line, the same stored label, a link that requires sign-in; no attachment, screenshot, video, credential or page content)"; "a canary secret and canary page string planted in the run -> absent from the message"; HO28 "the text passes `Redactor.scrub`". Served: `delivery/message.py::render_message` over the strict `ReportSummary` and template file `delivery/templates/report_email.txt`. The label is READ from the summary, never computed.
- **C3 (TT8, HO27)**: "until they exist the default adapter is the **outbox adapter** (dry-run, writes the would-be message under `<data>/.work/outbox/`, sends nothing) ... **no test and no default code path contacts a real SMTP host**" and "With no SMTP configured ... nothing raises". Served: `OutboxAdapter(dir)` (directory passed in), `select_transport`, `is_configured`, and the under-pytest refusal in the default client factory. NOT served: the profile-page text "email is not configured on this server" (a route; held), the literal `<data>/.work/outbox` path (the caller passes it; held).
- **C4 (HO27)**: "TLS (STARTTLS or SSL) is used when `_TLS` is set and certificate verification is on by default"; "the password lives only in the environment ... is never displayed, logged or audited"; HO29 "No test calls a real SMTP host". Served: `SmtpAdapter`, `smtp_config_from_env`, a timeout on every connection, exercised against a recording fake client and one in-process loopback server on 127.0.0.1.
- **C5 (TT8)**: "the grep that no module outside `delivery/email.py` imports `smtplib`". Served: `tests/test_delivery_smtp.py::test_only_the_email_adapter_imports_smtplib`.
- **C6 (TT9)**: "Every send attempt writes a `DeliveryRecord` (`schema/delivery.py`, extra="forbid": run id, channel `inbox | email`, recipient user id, `status` in `sent | outboxed | failed`, a **redacted** error, attempt count, next retry time)". Served: `DeliveryRecord`, `DeliveryLog` (append-only files). Also brief section 11: the record stores the user id, never the address.
- **C7 (TT9, HO29)**: "retried a **bounded** number of times with backoff". Served: `inbox.py::retry_delay`, `next_retry_at`, `MAX_ATTEMPTS`, `RETRY_DELAYS` (pure; injected clock; nothing sleeps). The numbers are my choice, see Contract gaps.
- **C8 (TT9, HO29)**: "never changes the run's verdict or status, never delays the next queue entry, and never fails the run". Served only as far as the delivery function: `deliver_once` turns any transport exception into a `failed` record and never lets it propagate. NOT served: the queue finish hook and "the run stays `done`" (held).
- **C9 (TT9, HO28)**: "No message and no inbox row contains a password, token, cookie, API key or `.env` value ... the text passes `Redactor.scrub`". Served: stored error text is class name and code only, then scrubbed; a planted secret is absent from records, the outbox and every file under the log directory; nothing is logged with the password.
- **C10 (TT9)**: "every link in a message goes to a route that requires sign-in". Served only the static half: `ReportSummary.report_url` accepts an http(s) or site-relative path with no query, fragment or credentials, so a token-bearing link cannot be built. NOT served: "an unauthenticated GET to it is 302 to login" (a route; held).
- **C11 (brief section 3 "No criterion yet" item 3, idempotency)**: not a contract criterion; proposed behaviour, checker to rule. One (run, channel, recipient) is sent once across replays, restarts and two racing workers; a crash between "sent" and "recorded" is never resent.
- **C12 (task instruction, recipient safety; no contract text)**: header injection and address validation: CR/LF or a second address in any address, display name or subject is refused; exactly one `To`, no Cc/Bcc.

## Held for phase A1 (after t205/t204 merge) and for the checker

- TT7 in full: `GET /inbox`, the `report.view` scope table, the stored inbox entry model (brief item 2), "the label is computed once in `stages/report_delivery.py`" and the one-definition test. `ReportLabel` here is the closed vocabulary only; the function that computes it, and its thresholds (brief item 5), are not built.
- TT8 route rows: profile page `GET/POST /profile`, forged `to`/`email`/`recipient`/`cc` ignored in the Test and profile POST, "two sessions -> the recipient follows the session", send-time `report.view` through the real `authorize` (needs T-204 `Principal`; brief item 8).
- TT9 rows needing the queue or UI: the `set_finish_hook` edit of `ui/run_queue.py` (`_finish`, `recover`), the failure shown on the run page, the inbox entry present when email fails, the unauthenticated-link 302.
- TS5/TS7 "a notice with no run" entry points (brief item 1; the checker must rule).
- Declaring the mail keys as `SecretRef` (D-083 item 1; `schema/project.py` is forbidden). Interim: the names are constants in `delivery/email.py` and `.env.example` lists them, and the Redactor masks every `.env` value.
- Moving the vocabularies (`DeliveryChannel`, `DeliveryStatus`, `ReportLabel`) to `schema/team_enums.py` once it exists (TF8).
- Reconciling `DeliveryLog._create_once` with `store/team_store.py::create_marker` once T-205 lands (one concept, one place; brief item 3 proposed `create_marker`).
- `docs/ARCHITECTURE.md` rows (orchestrator, under a DECISIONS entry).
- The one live message: held for the owner. No value of any `AUTOTESTER_SMTP_*` key was read, printed or used; `.env` was not opened.

## What changed

| Path | Lines | One job |
|---|---|---|
| `src/autotester/schema/delivery.py` (new) | 201 | Strict models and closed enums: `NotificationPref`, `Recipient`, `ReportSummary`, `RenderedMessage`, `DeliveryRecord`, `SmtpConfig` (no password field). |
| `src/autotester/delivery/__init__.py` (new) | 1 | Package docstring. |
| `src/autotester/delivery/message.py` (new) | 34 | Fill the template file from a summary; scrub; no computation. |
| `src/autotester/delivery/templates/report_email.txt` (new) | 17 | The wording, as a file. |
| `src/autotester/delivery/email.py` (new) | 195 | Outbox and SMTP adapters, MIME build, env config, `may_email`, the only `smtplib` importer. |
| `src/autotester/delivery/inbox.py` (new) | 176 | `DeliveryLog` (append-only records and attempt claims), retry schedule, `deliver_once`. |
| `tests/delivery_fakes.py` (new) | 206 | Recording SMTP client, raising/ok transports, loopback SMTP server, `forbid_real_smtp`. |
| `tests/test_delivery_smtp.py` (new) | 223 | 32 tests: adapter, TLS, timeouts, credentials, injection, config, grep. |
| `tests/test_report_email.py` (new) | 133 | 31 tests: message, outbox, preference. |
| `tests/test_delivery_failure.py` (new) | 174 | 11 tests: failure record, bound, redaction, idempotency, crash, race. |
| `.env.example` (edit, appended 2 lines at the end) | 90 -> 92 | `AUTOTESTER_SMTP_FROM_NAME` (D-083 item 1; the drift test `test_env_example_documents_every_key_the_code_reads` needs it because `email.py` reads it). |
| `docs/MAP.md` | regenerated | `uv run autotester map`. |

No forbidden file was touched (`store/team_store.py`, `schema/team_enums.py`, `schema/project.py`, `ui/routes_runs.py`, `stages/run_launcher.py`, `ui/run_queue.py`, `ui/run_execution.py`, `cli.py`, `core/paths.py`, `core/safe_names.py`, `pyproject.toml`, `uv.lock`, `auth/`).

## New modules (D-082 item 1: the brief or contract names it; docstring states one job; doctor clean; checker lists it)

| Module | Docstring one job | Where named |
|---|---|---|
| `schema/delivery.py` | Strict models and closed vocabularies for delivering a finished run's report. | brief section 5 table row 1 ("plan-named"), contract TT9 |
| `delivery/__init__.py` | Report delivery package. | brief section 5 row 4 |
| `delivery/email.py` | The outbound mail adapters: dry-run outbox and SMTP sender; the only `smtplib` importer. | brief section 5 row 5, contract TT8 grep |
| `delivery/inbox.py` | Delivery records on disk and the send-once procedure around a mail transport. | brief section 5 row 4 (named for the inbox store; I put the delivery-record store here because the brief names no other file for it, see Open questions) |
| `delivery/message.py` | Compose the report e-mail from a stored summary and a template file. | brief section 5 row 7 ("not plan-named, proposed"; the "message module" the TT7/TT8 mutations name) |
| `delivery/templates/report_email.txt` | Message wording as a file (prompts are files, not inline strings). | CLAUDE.md design rule; not a module |
| `tests/delivery_fakes.py` | Fakes for the delivery tests. | brief section 5 last row |

## Pre-check (final product commit 66ba7be4, worktree clean; no full suite)

Pre-check[C1]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "defaults_off or ticked" -> 2 passed t=24s
Pre-check[C2]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "carries_exactly or planted_secret or template_is_a_file or no_slot or naive or label_is_a_closed or site_relative" -> 7 passed t=4s
Pre-check[C3]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "outbox or default_selection or default_factory_never or select_transport or config_from_env" -> 14 passed t=5s
Pre-check[C4]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "starttls_then_login or implicit_ssl or every_connection or password_is_read or authentication_failure or connect_failures or recipient_refusal or nothing_is_logged or plain_text_login or loopback_server or silent_server" -> 14 passed t=9s
Pre-check[C5]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "only_the_email_adapter" -> 1 passed t=11s
Pre-check[C6]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "attempt_limit or redacted_in_the_record or append_only" -> 3 passed t=5s
Pre-check[C7]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "backoff or attempt_limit or not_attempted_before_it_is_due" -> 3 passed t=9s
Pre-check[C8]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "unexpected_exception or attempt_limit" -> 2 passed t=7s
Pre-check[C9]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "redacted_in_the_record or planted_secret or authentication_failure or nothing_is_logged" -> 4 passed t=8s
Pre-check[C10]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "refuse_injection_paths_tokens or site_relative" -> 13 passed t=5s
Pre-check[C11]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "successful_send_is_recorded_once or crash_between or two_workers or key_cannot_escape or outbox_is_idempotent or outbox_refuses" -> 12 passed t=3s
Pre-check[C12]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "address_validation or headers_have_exactly or line_break or sender_name" -> 13 passed t=7s
Pre-check: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -> 74 passed in 13s
Pre-check[lint]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run ruff check src tests scripts -> All checks passed
Pre-check[doctor]: 66ba7be4 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run autotester doctor -> doctor: clean (after `autotester map`, which regenerated docs/MAP.md; included in the commit)

Affected existing test: `tests/test_hosting_deploy.py` (it reads `.env.example` and `src/`): 9 passed, 1 failed. The failure is `test_env_example_documents_every_key_the_code_reads` with `undocumented env keys: ['AUTOTESTER_SCHEDULE_GRACE_MINUTES', 'AUTOTESTER_TICK_INTERVAL_S']`; both are read only by `src/autotester/stages/scheduler.py` (master code, not this unit), `AUTOTESTER_SMTP_FROM_NAME` is not in the list. Pre-existing on master `6504de03`, reported not fixed (`.env.example` lines for the scheduler belong to that unit).

## Falsifications (one per criterion; green before, red after; each in a throwaway copy of `git archive HEAD src tests scripts pyproject.toml` under the C: session scratchpad, run with PYTHONPATH on the copy, deleted afterwards; the worktree was never perturbed; times are the real pytest wall times of the run)

| Criterion | Edit in the copy | Before | Red nodes after |
|---|---|---|---|
| C1 | `NotificationPref.email_run_reports` default `False` -> `True` | 2 passed (t=93s wall) | `test_notification_preference_defaults_off_and_is_a_strict_model`, `test_a_report_is_mailed_only_when_ticked_and_still_allowed_to_view_it` |
| C2 | `render_message` skips `scrub` | 2 passed | `test_message_passes_the_redactor_so_a_planted_secret_is_masked` |
| C3 | remove the under-test refusal in `_default_factory` (`if False:`) | 1 passed | `test_default_factory_never_connects_under_test_even_with_a_dummy_host` |
| C4 | STARTTLS context -> `ssl._create_unverified_context()` | 1 passed | `test_starttls_then_login_then_send_with_certificate_verification_on` |
| C5 | add `import smtplib` to `delivery/message.py` | 1 passed | `test_only_the_email_adapter_imports_smtplib` |
| C6 | append the recipient address to the stored error text | 1 passed | `test_failure_text_is_redacted_in_the_record_and_on_disk` |
| C7 | retry always scheduled 1 minute out (no bound) | 1 passed | `test_a_transport_that_always_fails_leaves_a_failed_record_bounded_by_the_attempt_limit` |
| C8 | `except Exception` -> `except TransportError` (an unexpected exception propagates) | 1 passed | `test_an_unexpected_exception_is_contained_recorded_and_scrubbed` |
| C9 | stored error not passed through `scrub` | 1 passed | `test_failure_text_is_redacted_in_the_record_and_on_disk` (assertion on the planted password and canary) |
| C10 | `report_url` pattern also allows `?`, `#`, `@`, `:` | 12 passed | `test_summary_fields_refuse_injection_paths_tokens_and_odd_links[report_url-https://x.test/r#frag]` |
| C11 | `DeliveryLog.claim` always returns True | 2 passed | `test_a_crash_between_sent_and_recorded_is_never_resent`, `test_two_workers_racing_for_one_attempt_send_exactly_once` |
| C12 | remove the address pattern check in `Recipient` | 10 passed | `test_recipient_address_validation_rejects_injection_and_malformed[a@@x.test]` and the other malformed cases |

TDD note: the three test files and `delivery_fakes.py` were written before `schema/delivery.py`, `delivery/*`; the first collection failed with ImportError (module absent), then went green; the falsifications above are the red-after-edit proof per criterion.

## Contract gaps and decisions I made (feedback for `qa/feedback-inbox.md`; the checker rules)

1. **Retry numbers (brief item 4).** I chose `RETRY_DELAYS = (1, 5, 30 minutes)` and `MAX_ATTEMPTS = len(RETRY_DELAYS) + 1 = 4` (first try plus one retry per delay). The brief says "three attempts, delays 1, 5 and 30", which is self-inconsistent (3 attempts have 2 delays). Driver is not built (no in-app loop; a caller supplies `now`).
2. **TLS mode (brief item 6).** Rule built: port 465 is implicit SSL; `AUTOTESTER_SMTP_TLS` of `0`/`none`/`false` is plain, allowed with credentials only for a loopback host; anything else (including unset, which is the case with the six D-083 keys) is STARTTLS with certificate verification. HO27 says TLS "when `_TLS` is set"; I made TLS the default instead, because D-083's six keys do not include `_TLS` and plain-text credentials to a relay would be worse.
3. **Crash between sent and recorded (brief item 3).** At-most-once: an attempt is claimed by a marker before the transport is called; a marker with no record is never resent, and after `STALE_AFTER = 10 min` it is closed as one terminal `failed` record "not resent". A real lost mail is possible in that window; a duplicate mail is not.
4. **Allow-list hook:** the contract names none, none built.
5. **Link base URL (brief item 7):** `report_url` is given by the caller, absolute http(s) or site-relative; no new env key for the public origin.
6. **Vocabulary home:** `DeliveryChannel`, `DeliveryStatus`, `ReportLabel` live in `schema/delivery.py` because `schema/team_enums.py` does not exist on master; TF8 says they belong in `team_enums.py` (held).
7. **`delivery/inbox.py` holds the delivery-record store and `deliver_once`**, not an inbox-entry store; the brief names no other file for it. The inbox entry model (brief item 2) is not built.
8. The key `AUTOTESTER_SMTP_TLS` stays documented in `.env.example` and read (optional); it is not one of D-083's six keys.

## Open owner / checker questions

- Confirm or change the retry numbers (gap 1) and the crash rule (gap 3).
- Is `delivery/inbox.py` the right home for the record store, or should phase A1 add a named module?
- Dual check: A and B should each re-run C4 and C9 and read `delivery/email.py` lines 130-160 first.
