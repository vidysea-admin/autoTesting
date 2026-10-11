# Manifest - t201a-delivery-core

**Unit:** T-201 / G4 phase A0 `t201a-delivery-core`: the pure parts of report delivery that touch no file owned by a unit in flight (message composition, outbox and SMTP adapters, delivery records, send-once procedure, retry schedule, recipient safety).
**Brief:** `qa/briefs/t201a-report-delivery.md` (untracked on master; its "base" line is stale). **Contract:** `qa/contracts/team-test-button.md` TT7-TT9 and `qa/contracts/hosting.md` HO26-HO29, plus `core-invariants.md`.
**Branch / base:** `wave/t201a-delivery-core` on master `6504de03`.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (outward-facing email; the module holds the SMTP password)
Dual check: required
dual-trigger: security src/autotester/delivery/email.py:149 (`client.login(cfg.user, password)`, the only place the SMTP password is used; the `smtplib` import is line 18, `SmtpAdapter.send` line 138, the password is read from the environment mapping at send time at line 195)
Contract: C1 C2 C3 C4 C5 C6 C7 C8 C9 C10 C11 C12 (ids below are this manifest's, mapped to contract clauses; the contract has no C-numbers for TT/HO rows)
Fix cycle: 2
Repair base: 7dd225d4
Executor: claude-sonnet-subagent (maker build subagent)
Code commit (pre-check sha): 76ba7da5 (fix cycle 2, the last; the manifest commit after it adds only this file; cycle 1 code was 477f4089, cycle 0 code 66ba7be4)
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

## Pre-check (final product commit 76ba7da5, worktree clean; no full suite; fix cycle 2)

Pre-check[C1]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "defaults_off or ticked" -> 2 passed t=25s
Pre-check[C2]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "carries_exactly or planted_secret or template_is_a_file or no_slot or naive or label_is_a_closed or site_relative" -> 7 passed t=25s
Pre-check[C3]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "outbox or default_selection or default_factory_never or select_transport or config_from_env" -> 14 passed t=27s
Pre-check[C4]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "starttls_then_login or implicit_ssl or every_connection or password_is_read or authentication_failure or connect_failures or recipient_refusal or nothing_is_logged or plain_text_login or loopback_server or silent_server" -> 15 passed t=32s
Pre-check[C5]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "only_the_email_adapter" -> 1 passed t=24s
Pre-check[C6]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "attempt_limit or redacted_in_the_record or append_only or create_once" -> 4 passed t=27s
Pre-check[C7]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "backoff or attempt_limit or not_attempted_before_it_is_due" -> 3 passed t=37s
Pre-check[C8]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "unexpected_exception or attempt_limit or clock_skewed" -> 3 passed t=34s
Pre-check[C9]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "redacted_in_the_record or planted_secret or authentication_failure or nothing_is_logged" -> 4 passed t=31s
Pre-check[C10]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "refuse_injection_paths_tokens or site_relative or plain_forms" -> 23 passed t=31s
Pre-check[C11]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "successful_send_is_recorded_once or crash_between or two_workers or key_cannot_escape or outbox_is_idempotent or outbox_refuses or injective or dotted_prefix or spell_the_separator or whole_file_names or clock_skewed or create_once" -> 18 passed t=21s
Pre-check[C12]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -k "address_validation or headers_have_exactly or line_break or sender_name" -> 19 passed t=18s
Pre-check: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_delivery_smtp.py tests/test_report_email.py tests/test_delivery_failure.py -p no:xdist -o addopts= -> 97 passed in 6s (cycle 0 had 74) t=27s
Pre-check[lint]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run ruff check src tests scripts -> All checks passed
Pre-check[doctor]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run autotester doctor -> doctor: clean

Pre-check[advice-scan]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_cli_advice_resolves.py -p no:xdist -o addopts= -> 33 passed (the cycle 1 red `test_the_collector_reports_what_it_could_not_resolve` is green) t=24s
Pre-check[affected-src-scanners]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest <each file separately> -p no:xdist -o addopts= -> test_actuator_chokepoint 2, test_adversarial 25, test_ai_catalog 28, test_approval_signing 18, test_browser 15, test_catalog 23, test_catalog_packs 13, test_cli_advice_resolves 33, test_cli_harness_safety 4, test_doctor 40, test_hosting_config 8, test_knowledge_graph 12, test_prompt_skills 16, test_regression_trigger 18, test_run_trace 10, test_schedule_marker 6, test_video_evidence 2: all passed
Pre-check[hosting-deploy]: 76ba7da5 uv --directory D:/autoTesting/.worktrees/t201a-delivery-core run pytest tests/test_hosting_deploy.py -p no:xdist -o addopts= -> 9 passed, 1 failed (`test_env_example_documents_every_key_the_code_reads`: AUTOTESTER_SCHEDULE_GRACE_MINUTES and AUTOTESTER_TICK_INTERVAL_S, read by `stages/scheduler.py`). NOT caused by this unit: identical with the cycle 2 edit stashed (7dd225d4); the keys are read by `stages/scheduler.py`, which this unit does not touch, and this branch is based on an older master than the one that documents them in `.env.example`. Expected to clear when the branch is integrated; the checker should rule.

## Falsifications, cycle 0 (code 66ba7be4; one per criterion; green before, red after; each in a throwaway copy of `git archive HEAD src tests scripts pyproject.toml` under the C: session scratchpad, run with PYTHONPATH on the copy, deleted afterwards; the worktree was never perturbed; times are the real pytest wall times of the run)

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

## Fix cycle 1 (repair base 9b6d44c1; verdicts `qa/verdicts/t201a-delivery-core.a.md` and `.b.md`, failed criterion C11)

### Mechanism chosen for the key (one mechanism: an unambiguous encoding of each component, plus exact file-name matching)

`delivery_key` (`inbox.py`) is now `<channel>__<enc(run id)>__<enc(user id)>`. `enc` keeps lower-case letters, digits, `.` and `-`; an upper-case letter becomes `_` + its lower-case letter; a raw `_` becomes `_0`. So `_` is always followed by a letter or digit, the encoded part never contains `__` (the only separator) and never ends in `_`, and the encoding is a prefix code: the key decodes to exactly one (channel, run, user). The case rule makes it injective on a case-insensitive file system too (NTFS, which this repo runs on): `Alice` and `alice` no longer map to one claim file. The channel comes first so the key still starts with a letter (`SAFE_KEY`) even when the run id starts with a capital.

Why this one, not a directory level per component: it changes one function, keeps `OutboxAdapter`'s flat `<key>.eml` and the `key=` argument of every transport unchanged, and the same key text is injective for the outbox file as well. Why encode and not only match exactly: exact matching alone cannot separate `x__email__y`+`z` from `x`+`y__email__z` (the same text).

Exact matching: `DeliveryLog._load` no longer globs. It lists the directory and keeps a file only when `re.fullmatch` accepts the whole name: `records_for_key` uses `<re.escape(key)>\.\d+\.json`, `records_for_run` uses `(?:inbox|email)__<enc(run)>__<encoded-user chars>\.\d+\.json`. The claim marker (`claim`, `claimed_at`) and the stale-close path (`_close_stale` -> `claimed_at`, `append`, `latest`) never globbed: they build the exact path `<key>.<NN>.json` from the injective key, so they are exact by construction, and `latest` goes through `records_for_key`. A name such as `<key>.01.02.json` is the file of the user `<id>.01` attempt 2, not a second record of `<id>`; a test pins that.

### Repaired items

| Item | Test (all in `tests/test_delivery_failure.py` unless noted) |
|---|---|
| Key injective, including the separator spelled inside ids and upper/lower case (18 ids x 18 ids x 2 channels) | `test_the_delivery_key_is_injective_even_on_a_case_insensitive_file_system` |
| `alice.smith` mailed first no longer suppresses `alice` (both sent, own records) | `test_a_dotted_prefix_user_does_not_suppress_the_shorter_one` |
| Run `x__email__y`+`z` vs run `x`+`y__email__z`; `records_for_run('x')` returns only run x | `test_run_and_user_ids_that_spell_the_separator_do_not_collide` |
| Whole-file-name matching; stray names ignored | `test_lookups_match_whole_file_names_and_ignore_stray_files` |
| P2: the main-path `append` in `deliver_once` is contained (`except FileExistsError` returns the record on disk); the stale-close text now says `outcome unknown ... may or may not have been sent; not resent`. The race is driven by the first worker's own transport calling the second worker with `now = NOW + STALE_AFTER` (no sleep) | `test_a_clock_skewed_worker_closing_a_live_attempt_does_not_break_the_first_worker` |
| Create-once pinned on its own for records and claims | `test_create_once_is_pinned_for_records_and_claims_on_their_own` |
| Implicit SSL (port 465) verifies the certificate (`tests/test_delivery_smtp.py`) | `test_implicit_ssl_default_factory_verifies_the_certificate` |
| Pure CR and pure LF recipient addresses, as suffix, prefix and embedded (`tests/test_delivery_smtp.py`) | `test_recipient_address_validation_rejects_injection_and_malformed[...]` (6 new ids) |
| `report_url` refuses `//host`, `///host`, `https://x//host`, port 0, 65536, 99999 and keeps port 1, 65535, `/`, `/a//b` (`tests/test_report_email.py`; `schema/delivery.py` `_URL` and `_url`) | `test_summary_fields_refuse_injection_paths_tokens_and_odd_links[report_url-...]` (6 new ids), `test_report_url_accepts_the_plain_forms_next_to_the_refused_ones` |

How P2 is made truthful: records are append-only and one file per attempt number, so worker 1 cannot overwrite worker 2's record, and a second record for the same attempt would either break the attempt count or reopen the duplicate-send race. The closing record therefore states what is knowable: the outcome is unknown, the message may or may not have been sent, and it is not resent. Worker 1 returns the record on disk instead of raising. Residual, stated: in this race the run page shows `failed (outcome unknown)` for a mail that did go out; it is never a false "not sent".

Files changed in cycle 1 (line counts after): `src/autotester/delivery/inbox.py` 205, `src/autotester/schema/delivery.py` 204, `tests/test_delivery_failure.py` 272, `tests/test_delivery_smtp.py` 242, `tests/test_report_email.py` 143. No new file, no file over 300 lines, `email.py` untouched (so the `dual-trigger` line 149 is unchanged). Retry numbers, TLS default, crash rule, module names and the phase A1 list are unchanged.

### Falsifications, cycle 1 (one copy per mutant under `%TEMP%\t201a_fix1_fals` on C:; `autotester.__file__` printed and asserted inside the copy; copy deleted afterwards; all three delivery test files)

| Item | Edit in the copy | Before | After (red nodes) |
|---|---|---|---|
| key injectivity | `_encode_part` returns the id unchanged | 97 passed | 2 failed: `test_the_delivery_key_is_injective_even_on_a_case_insensitive_file_system`, `test_run_and_user_ids_that_spell_the_separator_do_not_collide` |
| exact matching | `records_for_key` pattern `\..*\.json` (prefix match) | 97 passed | 2 failed: `test_a_dotted_prefix_user_does_not_suppress_the_shorter_one`, `test_lookups_match_whole_file_names_and_ignore_stray_files` |
| append race | `except FileExistsError` in `deliver_once` -> `except ZeroDivisionError` | 97 passed | 1 failed: `test_a_clock_skewed_worker_closing_a_live_attempt_does_not_break_the_first_worker` |
| `//host` | `(?!/)` removed from `_URL` | 97 passed | 3 failed: `report_url-//evil...`, `report_url-///evil...`, `report_url-https://x.test//...` |
| port range | range check disabled | 97 passed | 3 failed: the three port cases |
| create-once | `os.link` -> `os.replace` in `_create_once` | 97 passed | 3 failed: `test_create_once_is_pinned_for_records_and_claims_on_their_own`, `test_a_crash_between_sent_and_recorded_is_never_resent`, `test_a_clock_skewed_worker_closing_a_live_attempt_does_not_break_the_first_worker` (the older `test_records_are_append_only_files_never_rewritten` still does not catch it alone; the new test does) |
| implicit SSL | `_default_factory` uses `ssl._create_unverified_context()` | 97 passed | 1 failed: `test_implicit_ssl_default_factory_verifies_the_certificate` |
| pure LF address | `Recipient` check uses `re.match(pattern + '$')` | 97 passed | 1 failed: `...rejects_injection_and_malformed[a@x.test\n]` |

### Not repaired (checker B items P4..P12 other than those named, plus one of mine)

P4 smtplib-import guard regex misses `import os, smtplib` and `__import__('smtplib')`; P5 U+2028/U+0085 and `.a@`/`a..b@` pass the schema and fail the MIME build (retried 4 times); P6 no total deadline against a dribbling server; P7 a drop after full DATA can deliver up to 4 copies (needs a sentence in the contract); P8 an RFC 2047 encoded word shows as a multi-line Subject; P9 `may_email` takes no recipient, lax bool coercion; P10 a bad optional key silently selects the outbox; P11 the `inbox.py` naming (A's naming flag). P12 is repaired by the create-once test. New, mine: an id of 64 characters made mostly of capitals or underscores encodes to more than 100 characters, and two such ids can exceed `SAFE_KEY` (200); `delivery_key` then raises `ValueError`, as it already did for over-long keys. Ids that long are not expected; not changed.

## Fix cycle 2 (repair base 7dd225d4; the last allowed cycle; one failed point)

**Failed point:** `tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve` was red at 7dd225d4 (green at 9b6d44c1). Cause, reproduced first (`unresolved_in_source(SRC)` returned `(delivery/inbox.py, 130)`): cycle 1's `DeliveryLog.records_for_run` (`src/autotester/delivery/inbox.py`) interpolated `_CHANNELS`, which is bound at module level to a `"|".join(...)` call, into an f-string. `tests/advice_scan.py` flags any f-string that interpolates an upper-case name it cannot resolve to a literal. The cycle 1 affected set missed this test because it does not import `autotester.delivery`; it walks all of `src/`.

**Change (one file, `src/autotester/delivery/inbox.py`, `records_for_run`):** the same regex built by concatenation, `"(?:" + _CHANNELS + ")__" + re.escape(_encode_part(run_id)) + "__" + _PART + r"\.\d+\.json"`; no f-string over an upper-case name. The docstring said "oldest first" but the sort is by file name (`sorted(self.records_dir.iterdir())`); it now says "in file-name order (channel, then user, then attempt)". The sort is not changed. The pattern string is character-for-character the same as before. Every other f-string in `src/autotester/delivery/` was checked (email.py lines 90, 106, 109, 136; inbox.py lines 61, 71, 84, 102, 107, 111): none interpolates an upper-case name. `tests/advice_scan.py`, `tests/test_cli_advice_resolves.py`, `EXPECTED_SITE_COUNT` and every guard are untouched.

**Behaviour unchanged:** `tests/test_delivery_failure.py` (17, holding every exact-match `records_for_run` / `records_for_key` assertion: `records_for_run('x')` vs `'x__email__y'`, `records_for_key(key[:-1]) == []`, `records_for_run('run') == []`, attempt-limit counts) is green, 17 passed, before and after.

**Widened affected-test list for future cycles (every file that walks `src/` with `rglob`/`ast`, plus the delivery files):** `tests/test_cli_advice_resolves.py` (and its helper `tests/advice_scan.py`), `tests/test_actuator_chokepoint.py`, `tests/test_adversarial.py`, `tests/test_ai_catalog.py`, `tests/test_approval_signing.py`, `tests/test_browser.py`, `tests/test_catalog.py`, `tests/test_catalog_packs.py`, `tests/test_cli_harness_safety.py`, `tests/test_doctor.py`, `tests/test_hosting_config.py`, `tests/test_hosting_deploy.py`, `tests/test_knowledge_graph.py`, `tests/test_prompt_skills.py`, `tests/test_regression_trigger.py`, `tests/test_run_trace.py`, `tests/test_schedule_marker.py`, `tests/test_video_evidence.py`, plus `tests/test_delivery_smtp.py`, `tests/test_report_email.py`, `tests/test_delivery_failure.py`. Run each with `-o addopts=`.

### Falsification, cycle 2 (copy of `git archive HEAD` of 76ba7da5 under the C: session scratchpad, random-suffix folder; PYTHONPATH on the copy; `autotester.__file__` printed and confirmed inside the copy; the worktree never perturbed)

| Item | Edit in the copy | Before | After |
|---|---|---|---|
| advice scanner sees an upper-case f-string interpolation | `records_for_run` pattern first part back to `f"(?:{_CHANNELS})__"` | `tests/test_cli_advice_resolves.py` 33 passed | 1 failed: `test_the_collector_reports_what_it_could_not_resolve` (32 passed) |
| restore | the worktree's `inbox.py` copied back | | 33 passed |

### Open items (recorded, deliberately not changed in cycle 2)

- An over-long run id plus user id makes `delivery_key` raise `ValueError("delivery key too long")` out of `deliver_once`.
- A worker that loses the close race records "outcome unknown" with no retry.
- The retry numbers (gap 1 below).
- `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads` fails on this branch for two `stages/scheduler.py` keys (see Pre-check[hosting-deploy]); not from this unit.
- Items P4..P11 under "Not repaired" in fix cycle 1 stand.

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
