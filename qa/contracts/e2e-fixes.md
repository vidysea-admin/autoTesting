# Contract — E2E 2026-11-01 fixes (AT-1412..AT-1421, four units)

**Covers:** the issues filed by the end-to-end check of 2026-11-01 (`.work/e2e-2026-11-01/report.md`,
`qa/issues.jsonl` rows AT-1412..AT-1421). **Owner:** /checker. **Criticality:** HIGH for E2 (the
verdict path, core-invariants C12) and E4 (the consent clock, D-112); MEDIUM for E1 and E3.
**Depends on:** `core-invariants.md` (C3 one place, C5 secrets, C9 declared value honoured, C12 fail
closed), `grade.md` (G3, G6), `langchain-fallback.md` (LC2, amended below), `run-trace.md`,
`run-video.md` (V2), `consent.md`, `parallel-run.md` (PR7), `credentials`/`pathlynks-onboarding.md`.

## Purpose

The first real end-to-end run on Pathlynks (local, master 468b3832) found that the browser side
works and that wrong or missing results came from four places: a report page that dies on one bad
trace line, a judge path that cannot reach the configured model and then holds true PASSes, a
credentials form that is a dead end, and a run that cannot say why it stopped or fail fast when its
target is unreachable. This contract makes each of those falsifiable. It is the ground truth the
checker judges against; the maker never edits it.

## Units

| Unit | Issues | Files in play (verified present 2026-11-01) |
|---|---|---|
| E1 | AT-1412 | `ui/routes_report.py`, `core/trace.py` |
| E2 | AT-1413, AT-1414 | `providers/langchain_fallback.py`, `providers/ollama_cloud.py`, `schema/verdict.py`, `skills/grade/SKILL.md`, `providers/litellm_schema.py`, `stages/grade.py`, `stages/grade_note_guard.py` (read-only here) |
| E3 | AT-1417, AT-1418 | `ui/routes_credentials.py`, `ui/routes_project_edit.py`, `ui/app.py`, `ui/project_view.py`, `ui/credential_guard.py` (rules unchanged), `ui/routes_role_accounts.py` (pairing to reuse) |
| E4 | AT-1421, AT-1415 | `stages/run_budget.py`, `stages/run_launcher.py`, `stages/execute.py`, `browser/video.py`, `stages/run_case_pipeline.py`, `schema/run.py` |
| E5 | AT-1433 | `docker/entrypoint.sh`, `core/env.py`, `ui/admin_view.py`, `store/mongo_routes.py` (read-only), `auth/store.py` (read-only) |
| E6 | AT-1419 | `ui/routes_live.py`, `ui/routes_auth.py`, `ui/app.py`, `auth/policy.py`, `core/env.py` (`on_cloud_run`) |
| E7 | AT-1416, AT-1420 | `ui/credential_guard.py`, `core/env.py`, `stages/reachability.py`, `store/migrate_creds.py` (`:60` only) |

## Out of scope (do not build, do not raise as findings against these units)

- **AT-1416** (live refuses slug `pathlynks`, `ui/credential_guard.py:38-48` vs the server's own
  `PATHLYNKS_MONGO_URI`): the fix renames or exempts a server key, which touches the D-122 store
  configuration. Needs an Umesh D-entry first. HUMAN_GATE.
- **AT-1419** (live view iframe points at `localhost:6080`, `ui/routes_live.py:40-53`): the fix is a
  new websocket proxy route in the app, a new network surface. Needs a D-entry. HUMAN_GATE.
- **AT-1420** (Cloud Run cannot reach pathlynks.vidysea.com): infrastructure (static egress IP,
  allowlist). DevOps. E4's fast-fail makes the symptom legible; it does not fix the cause.
- **Superseded 2026-11-01 for AT-1416 and AT-1419:** Umesh said the Mongo URI is already in the live
  environment and live must persist and work without DevOps, so AT-1416 is now **E7.1-E7.3** and AT-1419 is
  now **E6** (E6.9 keeps the D-entry gate on the new surface). AT-1420 stays infrastructure; only its
  diagnostic is in scope (**E7.4-E7.5**). The three bullets above are kept as the history of why they were held.
- Any change that lifts the ban on reading or printing `.env` values, or that edits
  `stages/grade_note_guard.py` so a currently-held note becomes a PASS (see E2.5).

## Criteria

### E1 — A corrupt trace line degrades the trace card, never the report page (AT-1412)

**E1.1 The run page renders.** `GET /projects/<slug>/runs/<run_id>` returns HTTP 200 when
`trace.jsonl` has a line that is not valid JSON. Today `ui/routes_report.py:207` (`run_view`) calls
`_trace_card` (`:115`), whose first statement `read_spans(...)` (`:117`) raises `TraceParseError`
(`core/trace.py:166`) and the page returns 500. The handling lives in `_trace_card` (or its single
caller), not in `read_spans`.
*Falsifier:* fixture run whose `trace.jsonl` is `{"kind": "stage"...}` (valid) then `not json`;
TestClient GET -> expect 200, body contains the run heading, the "Run bounds" card and the case
sections. Mutation: re-raise in `_trace_card` -> the test fails.
*serves:* intent#O3, intent#O13. *judges:* E1.

**E1.2 The degradation is visible and honest.** The "Trace" card still appears, states that the
trace could not be read, and carries `str(TraceParseError)` verbatim-escaped (it names the file and
line number only, never line content: AT-1304 C3, `stages/run_artifacts.py:96-97`). No spans are
shown as if the trace were empty or clean (C12: an unreadable measurement is not a clean one). A run
with NO trace file still renders no trace card at all (unchanged, `core/trace.py:155-156`).
*Falsifier:* same fixture; body contains `trace.jsonl:2` and `not valid JSON` inside the Trace card
and does NOT contain the corrupt line's text (use a line containing a canary string; assert the
canary is absent). A second fixture with no `trace.jsonl` -> no "Trace" card.
*serves:* intent#O3, intent#O7. *judges:* E1.

**E1.3 Detection is not weakened elsewhere.** `core/trace.py::read_spans` still raises
`TraceParseError` on a bad line, and `phase_summary` (`core/trace.py:184`) and
`stages/run_artifacts.py:56` keep their behaviour: the existing test
`tests/test_trace_numeric_secret.py:94` (`pytest.raises(TraceParseError, match=r"trace\.jsonl:2")`)
passes unmodified. The run-completion call `phase_summary` at `stages/run_launcher.py:172` must not
lose the saved `Run` on a corrupt trace: the run is saved with `phase_totals_s` = None (NOT
RECORDED, `schema/run.py:153-158`), never a fabricated zero. If a read of that path shows it already
cannot raise, state so in the manifest instead of adding code.
*Falsifier:* run the unchanged test; plus a launcher-level test with a corrupt trace asserting the
`Run` is saved and `phase_totals_s is None`.
*serves:* intent#O3. *judges:* E1.

### E2 — The judge path reaches the configured model and its PASS is decided structurally (AT-1413, AT-1414)

**E2.1 `langchain-fallback` honours `OLLAMA_API_KEY`.** With `OLLAMA_API_KEY` set and
`OLLAMA_BASE_URL` unset, `providers/langchain_fallback.py::_default_chain` (`:43`) includes an
`ollama` tier built against `providers/ollama_cloud.py::base_url()` (cloud URL, `:24-29`) with the
key sent as the `Authorization: Bearer` header (the construction already used at
`providers/agent_model.py:75-81`), model = `ollama_cloud.GLM` stripped of its prefix unless
`OLLAMA_MODEL` is set. With neither variable set, no ollama tier is added (LC2: an unconfigured
tier costs nothing and needs no SDK). Today the tier is gated only on `OLLAMA_BASE_URL`
(`:68`).
*Falsifier:* `monkeypatch` env to `{OLLAMA_API_KEY: "x"}` only; `dict(_default_chain())` has key
`ollama`; with `{}` it does not; with only `OLLAMA_BASE_URL` it still does (behaviour kept). The
factory is not invoked (no SDK import, no network).
*serves:* intent#O6, intent#O3. *judges:* E2.

**E2.2 Order: Ollama before Gemini, consistent with `autotester providers`.** In `_default_chain`
the `ollama` entry precedes `gemini` (the `autotester providers` command, `cli.py:64-72`, reports
GLM -> DeepSeek -> gemini, and the Pathlynks E2E proved a Gemini spend cap otherwise leaves every
verdict INCONCLUSIVE). Anthropic keeps first place when its key is present; `chatgpt` stays last.
**This amends `langchain-fallback.md` LC2** (stated order Anthropic -> Gemini -> Ollama -> ChatGPT):
the LC2 text and its test are updated by the checker in the same cycle (amendment owed, see the log;
this authoring pass was told to touch no other file). *Falsifier:* with all four credentials set,
`[k for k, _ in _default_chain()] == ["anthropic", "ollama", "gemini", "chatgpt"]`.
*serves:* intent#O6. *judges:* E2.

**E2.3 A cap on one tier is survived, and the winner is named.** With the Gemini tier raising a 429
and the Ollama tier answering, `LangChainFallbackProvider` returns the Ollama answer and
`provider.id` is `ollama` (LC3, unchanged). With the Ollama tier first and failing, Gemini answers.
*Falsifier:* fake chain entries (no SDK, no network) in both orders; assert returned value and `id`.
*serves:* intent#O6, intent#O3. *judges:* E2.

**E2.4 The judge is required to answer `defect_observed`, and a missing or null answer is not
accepted from a model-chain judge.** The schema the judge is given marks `defect_observed` as
required and non-null (a `required` entry and a boolean-only type), in the JSON Schema that
`providers/litellm_schema.py::json_mode_instruction` (`:50-54`) embeds for Ollama/json-mode
(`providers/litellm_provider.py:_strategy`) and in the schema passed to `request_options` for
schema/tool strategies. A reply that omits it or sends `null` is a parse failure that takes the
existing one repair retry (`providers/litellm_provider.py:_structured`), then a `ProviderError`
that grades INCONCLUSIVE with a named reason; it is never silently accepted. The `Judgment` field
stays tolerant to construct (`schema/verdict.py:90`, mocks and stored judgments may omit it) and
`stages/grade.py:_defect_decision` (`:256`) keeps its `None` fallback to the note guard.
`skills/grade/SKILL.md:25-29` already says "REQUIRED"; the schema now enforces what the prompt says.
*Falsifier:* (a) the schema string passed to the judge for `Judgment` contains `defect_observed` in
`required` and no `null` alternative; (b) a scripted fake model replying without the field gets one
repair prompt then `ProviderError` -> `grade()` returns INCONCLUSIVE with the reason in `note`;
(c) a reply with `defect_observed: false` parses and grades as before; (d) `Judgment(...)` without
the field still constructs. Mutation: drop the `required` marking -> (a) and (b) fail.
*serves:* intent#O6, intent#O3. *judges:* E2.

**E2.5 Fail-closed is not loosened (C12, G3, G6).** `stages/grade_note_guard.py` and
`stages/grade.py:_defect_decision` change in no way that turns a currently-held note into a PASS.
Mechanically: (a) the existing hold tests `tests/test_grade_note_guard.py`,
`tests/test_grade_defect_field.py`, `tests/test_grade_negative_path.py` pass with their parametrized
hold cases unchanged (the diff against master may only ADD cases); (b) the G6 rule (a failed
assertion is never PASS) and the `defect_observed=true` -> INCONCLUSIVE rule stand. The root cause
of the two held PASSes in `run-01M6AQYGP2AZ413Q497DQAK7W2` is NOT closed by E2.4 alone, and the
contract states why so the maker does not claim it: `_defect_decision` runs `note_guard` even when
`defect_observed` is false (`stages/grade.py:274-277`: "defect_observed=false never overrides a
defect note"), so a note containing "leaked" or "rejected, wrong, invalid" is still held unless the
expected-error cue is present (`grade_note_guard.py:_EXPECTED_CUE`, `_exemptible` `:106`). Therefore
the unit's remedy is at the prompt, not the guard: **E2.6**. Any change to the guard itself (for
example binding "no <noun> <defect-verb>") is a separate human-gated decision and is not authorized
here; if the maker believes it is needed, it files a HUMAN_GATE with the evidence.
*Falsifier:* run the three test files unmodified-plus-additions; `git diff` on the two stage files
shows no change to `_DEFECT_LEXICON`, `_NEGATED_SUCCESS`, `_negated`, `_exemptible`, `_exempt`,
`_EXPECTED_CUE`, `_CONTRARY`. Mutation: add a bypass for "no secret leaked" in `_negated` -> the
pinned hold tests of E2.7 (verbatim) fail, which is the point.
*serves:* intent#O6, core-invariants#C12. *judges:* E2.

**E2.6 The judge prompt tells the judge how to word a no-defect note.** `skills/grade/SKILL.md`
gains, next to the `defect_observed` bullet (`:25-29`), a plain instruction that (i) for a negative
case whose rejection is the expected outcome the note states it with the words "correctly rejected"
or "as expected" and without a contrary marker, and (ii) a PASS note describes what was observed in
positive terms ("credential values stayed masked") and does not use defect vocabulary even inside
a negation ("no secret leaked", "no error"). The instruction does not mention the guard's internals
and does not tell the judge to omit true defects (a note describing a real defect stays a FAIL or
INCONCLUSIVE, G3).
*Falsifier:* the loaded prompt text (`load_skill_prompt("grade")`) contains both instructions
(assert on distinctive phrases pinned in the test); the prompt still contains the `{{RUBRIC}}`,
`{{EVIDENCE}}`, `{{FORMAT}}` placeholders and the untrusted-evidence paragraph (`:30-33`).
*serves:* intent#O6, intent#O3. *judges:* E2.

**E2.7 The two E2E notes are pinned both ways.** A new test module (name chosen by the maker,
under `tests/`) holds, as module constants, the notes from the E2E run, grading each through
`grade()` with a `MockProvider`:
1. **a5ea note** (wrong password, negative case, DOM assertion `Invalid credentials` met,
   `expects_error=True`, `defect_observed=False`), verbatim from
   `.work/e2e-2026-11-01/root/projects/pathlynks/runs/run-01M6AQYGP2AZ413Q497DQAK7W2/case_a5ea57c0961a.verdict.json`
   (the quoted judge note): expected **INCONCLUSIVE today and after this unit** (guard unchanged;
   the note has no expected-rejection cue). A reworded note that follows E2.6 ("The wrong-password
   login was correctly rejected: the 'Invalid credentials' assertion was met.") -> **PASS**.
2. **cfa4 note** (valid login, `expects_error=False`, `defect_observed=False`), verbatim, containing
   "no secret leaked into the evidence": expected **INCONCLUSIVE today and after this unit**. A
   reworded note ("credential values stayed masked; the Dashboard and Logout assertions were met")
   -> **PASS**.
3. Controls that must stay held: the a5ea reworded note on a positive-path rubric
   (`expects_error=False`) -> INCONCLUSIVE; the reworded notes with `defect_observed=True` ->
   INCONCLUSIVE; a reworded note plus a genuine contrary marker ("... correctly rejected, but the
   password field leaked") -> INCONCLUSIVE.
Verbatim texts are copied from the verdict files above, with no secret value (the notes contain
none; `[secret]` is a mask token).
*Falsifier:* the module exists and passes; deleting the verbatim-held assertions or loosening the
guard (E2.5 mutation) fails it.
*serves:* intent#O6, core-invariants#C12. *judges:* E2.

### E3 — One "Test account login" block; a bad key is a plain inline message (AT-1417, AT-1418)

**E3.1 A bad credential key re-renders the form with a plain message and keeps the fields.**
Posting `/projects/<slug>/env/add` (`ui/routes_credentials.py:154`) or `/projects/<slug>/secrets`
with a key that is not UPPER_SNAKE_CASE (`schema/mailbox_ref.py:16` `^[A-Z][A-Z0-9_]*$`) returns the
page again (status 400 or 200, the maker's choice, but a normal page with the site chrome, not the
bare error page of `ui/error_pages.py:106`) with an inline message that names the rule and an
example in the project's own namespace, e.g. "Key must be UPPER_SNAKE_CASE and start with
PATHLYNKS_E2E_, for example PATHLYNKS_E2E_API_TOKEN". The submitted key, domains and description
are redisplayed; the submitted **value is never echoed** (C5). The raw pydantic text
(`String should match pattern`, `routes_project_edit.py:65-66`) never reaches the response.
*Falsifier:* TestClient POST with key `pathlynks password` and a canary value; body contains the
message, the typed key and domains, NOT the canary and NOT `String should match pattern`; the
project is unchanged on disk (no secret declared, no `.env` write).
*serves:* intent#O7, intent#O1. *judges:* E3.

**E3.2 Onboarding and the Credentials page offer one "Test account login" block.** `/onboard`
(`ui/app.py:109`, form in `ui/project_view.py:49`, row at `:23`) and `/projects/<slug>/env`
(`ui/routes_credentials.py:210`) each show one block with exactly two inputs, **Email or username**
(text) and **Password** (masked, `autocomplete="new-password"`), plus the allowed-domain scope
defaulted from the project URL host (E3.4). The existing "Add a custom credential" card
(`routes_credentials.py:106`) remains, retitled for extra keys only; `/onboard/roles` pairing
(`ui/routes_role_accounts.py`, `RoleAccount.username_key`/`password_key`, `schema/role_account.py:29-30`)
is reused, not reimplemented (C3).
*Falsifier:* GET both pages; each body has the "Test account login" heading, one email-or-username
input and one `type=password` input, and the custom-credential card still exists. Static check:
no second function that builds a username/password key pair (`grep` for the key-derivation helper
finds one definition).
*serves:* intent#O1, intent#O7. *judges:* E3.

**E3.3 Keys are generated, not typed.** Submitting the block declares two `SecretRef`s,
`<NS>_USER_EMAIL` and `<NS>_USER_PASSWORD`, where `<NS>` is `core/env.py::key_namespace(slug)`
(`:50`, e.g. `PATHLYNKS_E2E_`), with `mask_in_screenshot=True` on the password. Both pass
`refuse_foreign_key` (`ui/credential_guard.py:51`) unchanged. If either key is already declared,
the second submit updates the values (it does not 400 as `env_add_credential` does) and never
duplicates a declaration. A project with a role-accounts setup keeps its own keys untouched.
*Falsifier:* onboard a fresh slug through the block; `project.json` secrets keys are exactly the
two names; resubmitting changes values and leaves two declarations; a slug `alpha` cannot claim
keys in `ALPHA_BETA_` (existing AU21 behaviour still refuses).
*serves:* intent#O7, intent#O1. *judges:* E3.

**E3.4 Domains default to the project URL host and never widen the boundary.** The scope for both
generated keys defaults to `browser/secrets.py::host_of(base_url)` (`:71`) (the exact host, `browser/secrets.py::_host_matches`
is an exact-host match, AT-651: declaring `vidysea.com` does not admit subdomains), shown and
editable in the block, and still validated by `build_secret_ref` (`routes_project_edit.py:48-63`):
a domain outside `allowed_domains` is refused with a plain message (same inline mechanism as E3.1).
*Falsifier:* base_url `https://pathlynks.vidysea.com/signin` -> prefilled scope `pathlynks.vidysea.com`;
editing it to `evil.example` -> inline refusal, nothing saved.
*serves:* intent#O7. *judges:* E3.

**E3.5 Values are never echoed and the guard rules are unchanged.** After a successful submit and on
every later render of both pages, neither the password nor the email/username value appears in any
response body, redirect URL, log line captured by the test, or trace (C5; `show_values` stays
governed by `can_view_credentials()`, `routes_credentials.py:35`/`:219`, exactly as today for the
existing table). `ui/credential_guard.py` is not edited, and its tests pass unchanged: pasted-secret
refusal (`_refuse_unsafe_submission` calls), `refuse_server_key`, `refuse_reserved_slug`,
`refuse_foreign_key`.
*Falsifier:* canary values in a full onboard + env-page round trip; assert absence in every
response and in `caplog`; `git diff` shows no change to `ui/credential_guard.py`.
*serves:* intent#O7. *judges:* E3.

**E3.6 Layout: Save is reachable at a narrow width.** At a ~500 px viewport the credential table's
value box and Save button are reachable without horizontal page scroll (AT-1417's second half).
*Falsifier:* render the Credentials page at 500 px (browser check with a screenshot in `.work/`)
and assert the Save button's bounding box lies inside the viewport; a markup-level fallback is
`overflow-x:auto` on the table container plus a visible row-level Save. Visual claim: checker takes
the screenshot itself.
*serves:* intent#O1. *judges:* E3.

### E4 — The run says why it stopped, fails fast on an unreachable target, and every case's video is accounted for (AT-1421, AT-1415)

**Premise the checker verifies before judging a defect.** D-112 (docs/DECISIONS.md, ACTIVE) defines
the approval's `wall_clock_s` as time acting on the target; judge and housekeeping time ride a
shared exclusion clock up to `judge_allowance_s` + `housekeeping_allowance_s`
(`stages/run_budget.py:96-103`, allowances `:276-299`), and `RunBudget.remaining_ms`
(`:217-229`) already caps each browser operation at the remaining clock. The 289 s / 215 s figure of
AT-1421 therefore is NOT by itself a breach: 215 s equals 10 actions x 8 s + 3 cases x 45 s, and
excluded time is persisted in `Run.excluded_s` (`schema/run.py:164`). What is missing is that the
page does not show the arithmetic, and that nothing stops the repeated 30 s timeouts. E4.1 and E4.2
address those; they do not re-open D-112.

**E4.1 The bound is enforced and the accounting is on the page.** (a) A run whose browser-acting
time reaches `wall_clock_s` stops: remaining cases are not started, each unstarted case is recorded
as INCONCLUSIVE with the reason `wall_clock_s` (not FAIL, not silently absent: intent#O4, C12), and
the EXECUTE stage span is `failed` with `error="run budget exhausted: wall_clock_s"` (existing
mechanism, `stages/run_launcher.py:227-232`; the maker proves it with a test, it does not rebuild
it). (b) The run page's "Run bounds" card (`ui/routes_report.py:203`, `stages/report_export.py:55-62`
`bounds_text`) additionally states acting time used, judge seconds and housekeeping seconds held
off the clock (from `Run.excluded_s`), and the stop reason when there was one; a run from before
D-112 (`excluded_s` None) shows "NOT RECORDED", not zero.
*Falsifier:* (a) a fake executor that burns the clock past a tiny `wall_clock_s` over 3 cases:
case 1 runs, cases 2-3 INCONCLUSIVE with `wall_clock_s` in the verdict note, EXECUTE span failed;
(b) page text for a run with `excluded_s={"judging":40,"housekeeping":20,"total":60,...}` contains
those numbers and the bound; for `excluded_s=None` contains "NOT RECORDED".
Invariant under test: total EXECUTE wall time <= `wall_clock_s` + the two allowances + one
in-flight operation's timeout.
*serves:* intent#O4, intent#O12, intent#O13. *judges:* E4.

**E4.2 An unreachable base_url fails the run fast with one clear message.** Before the first
browser session of a run, a single bounded reachability preflight of `project.base_url` runs:
one HTTP GET (or HEAD) with no cookies, no credentials, no body, redirects followed only while the
host stays inside `allowed_domains`, total <= 10 s including one retry. Connect/DNS/TLS/timeout
failure (an HTTP response of any status counts as reachable: a 401/500 is the product's answer and
the run proceeds) ends the run before any case executes: every case is recorded INCONCLUSIVE (not
FAIL, not ERRORED-per-case with N identical 30 s goto timeouts), the run's `preflight_warnings`
(`schema/run.py:138`) and the run page carry ONE message naming the host and the failure class
("target pathlynks.vidysea.com did not answer within 10 s from this server"), and no screenshot or
video is produced for cases that never ran. The probe is itself an action on the target, so it is
read-only by construction, spends no `max_actions`, is skipped for `base_url` hosts outside the
project's allowed domains (refuse, do not probe), and never sends a credential (C5). It runs once
per run, not per case, and also guards scheduled runs (same path).
*Falsifier:* base_url pointing at a local socket that accepts and never answers (or a blackholed
test address) with `allowed_domains` set accordingly: the run ends in <= 15 s (not N x 30 s), N
INCONCLUSIVE verdicts, one message, zero browser launches (patch `BrowserSession.start` to raise if
called). A local server returning 500 -> the run proceeds to execution. A host outside
`allowed_domains` -> refused, no connection attempted (assert the socket saw no connect).
*serves:* intent#O4, intent#O13, intent#O7. *judges:* E4.

**E4.3 Each executed case keeps its `.webm` or records why not.** For every case that reached
execution, exactly one of these is true and is visible on the run page for that case: (a) a `.webm`
is kept and linked (V8: `EvidenceKind.VIDEO`); (b) the verdict is PASS and the video was pruned by
design (`qa/contracts/run-video.md` V2: a PASS keeps no video, `stages/run_case_pipeline.py:123-124`
`_finalize_video`); (c) recording was off for the session; (d) the video was lost, with the
`video-lost` session event already produced (`browser/video.py:240`); (e) the case exceeded
`MAX_VIDEO_DURATION_S` and was dropped. The silent paths are the defect: `end_case_video` returns
`None` with no event when `page.video is None` (`browser/video.py:223-224`) and when the temp file
is missing or the move did not produce the final file (`:234-238`); each must record a `video-lost`
event with the reason instead of returning a bare `None`. **Premise to check:** AT-1415's missing
video belongs to a PASS case (`case_b1cb019ebb56` was PASS in
`run-01M6AQYGP2AZ413Q497DQAK7W2`), which V2 deletes by design; the empty `_video_scratch` directory
is the expected remnant. The unit's deliverable is therefore the report line that says so, plus the
two silent-None paths made loud, not a change to V2. If the checker finds a non-PASS case with no
kept video and no recorded reason, that is a V-series defect to file separately.
*Falsifier:* (b) a PASS case's report section reads e.g. "no video kept: the case passed (run-video
V2)"; (d) fake session with `page.video = None` and with a missing temp file -> a `video-lost`
event with a reason string in the case's evidence, shown on the page; a non-PASS case with a
kept video still links it (V8 unchanged); the V2 prune test passes unmodified.
*serves:* intent#O3, intent#O4. *judges:* E4.

### E5 — Live persists without DevOps: the entrypoint selects the Mongo store when its URI is present (AT-1433)

**Premise (Umesh, 2026-11-01).** The Mongo URI is already in the live server's environment, and the
live site must keep accounts, projects and credentials across deploys without a DevOps step. Today
the store stays on `file` unless an operator sets `AUTOTESTER_STORE` / `AUTOTESTER_STORE_AREAS` by
hand (`store/mongo_routes.py:236-237`; `auth/store.py:93-100` flips auth only through its own area
entry), and `docker/entrypoint.sh` only *describes* storage (`all_state_on_mongo` `:42`,
`warn_if_ephemeral` `:63`), it never selects it. The store areas are `settings, projects, runs,
crawls, approvals, auth, credentials, blobs, queue` (`store/mongo_routes.py:25-26`; `UNROUTED` is
empty). The URI variable is `PATHLYNKS_MONGO_URI` (`core/env.py:216`, `MONGO_URI_ENV`). This unit
does not re-open D-122/D-123 (credentials stored plain, in Mongo) or the write fence.

**E5.1 The entrypoint selects Mongo for every area, only when the URI is present and the operator
chose nothing.** `docker/entrypoint.sh`, before `warn_if_ephemeral || true` (`:87`) runs, exports
`AUTOTESTER_STORE=mongo` and `AUTOTESTER_STORE_AREAS=<every area in AREAS>=mongo` (all nine,
explicitly, `auth` and `credentials` included, so the result does not depend on the global default)
exactly when (i) `PATHLYNKS_MONGO_URI` is set and non-blank (whitespace-only counts as absent,
matching the `.strip()` at `core/env.py:227`), (ii) `AUTOTESTER_STORE` is unset, and (iii)
`AUTOTESTER_STORE_AREAS` is unset. If either (ii) or (iii) is set, even to `file`, the script
exports neither (the operator's choice wins whole; no half-merge) and prints one line saying the
operator's selection was kept. After the selection, `all_state_on_mongo` (`:42`) returns 0, so the
existing "every state area is on Mongo" line replaces the ephemeral warning.
*Test seam:* extend `tests/test_container_entrypoint_behaviour.py` / `tests/test_storage_warning.py`,
which already run the real script in a bash sandbox (`_run_fn`, `sandbox`): run the selection step
as a function (name chosen by the maker) with a fake URI value and print the two variables
afterwards. Cases: URI set, nothing else -> both exported, the AREAS value contains all nine
`<area>=mongo` items (assert against `store.mongo_routes.AREAS` read from the module, so an area
added later fails this test instead of silently staying on file); URI set + `AUTOTESTER_STORE=file`
-> neither exported; URI set + only `AUTOTESTER_STORE_AREAS=blobs=mongo` -> neither exported; URI
whitespace-only -> neither.
*Mutation hint:* drop `auth=mongo` from the generated list -> the per-area assertion fails; delete
the "operator has not set" guard -> the `AUTOTESTER_STORE=file` case fails.
*serves:* intent#O1, intent#O7, intent#O13. *judges:* E5.

**E5.2 No URI, no selection, no brick.** With `PATHLYNKS_MONGO_URI` unset or blank, the entrypoint
exports neither variable and takes exactly the path it takes today (file store, the existing
ephemeral warning, function returns 0, `|| true`). This is the 503-brick guard: an area routed to
Mongo with no URI makes `store/mongo_backend.py:290` raise, and the store-outage 503
(`ui/app.py:71`) then answers every request, so the selection is never made on a guess.
*Test seam:* same sandbox, no URI -> `AUTOTESTER_STORE` and `AUTOTESTER_STORE_AREAS` still unset;
the existing warn cases in `tests/test_storage_warning.py:150-170` pass unmodified.
*Mutation hint:* make the guard test "set" instead of "non-blank" -> the blank-URI case fails.
*serves:* intent#O4, intent#O7. *judges:* E5.

**E5.3 The URI value is never printed, echoed, or placed on a command line.** The selection step
tests presence only: no echo of the value, no `set -x`, no value in the "kept operator selection"
line, no value in an `exec` argument.
*Test seam:* run the sandbox with a canary URI (`mongodb://canary-user:canary-pass@h/`) and assert
the canary is absent from stdout, stderr and the stub-recorded `exec` argv (`PY_STUB` in
`tests/test_container_entrypoint_behaviour.py` echoes its args).
*Mutation hint:* add an echo of the variable -> the canary assertion fails.
*serves:* intent#O7 (C5). *judges:* E5.

**E5.4 `storage_warning` warns on Cloud Run instead of going quiet.** `core/env.py::storage_warning`
(`:146`) returns None for every case it cannot determine: no `/proc/mounts`, no `/` entry, any
exception (`:157-165`). On Cloud Run that silence is the failure (the live site wiped itself with no
sign). New rule, with ONE helper `core/env.py::on_cloud_run()` (true when `K_SERVICE` is set and
non-blank; `K_SERVICE` appears nowhere in `src/` today; reused by E6.6, C3): when `on_cloud_run()`,
`AUTOTESTER_EPHEMERAL_OK` is not `1`, and not every store area is `mongo`
(`store.mongo_routes.store_selection()` imported lazily, as `credential_collection` does at
`core/env.py:240`, because that module imports this one), `storage_warning` returns a warning when
the root is ephemeral (the existing "not persistent" sentence) OR when persistence cannot be
verified (the unknowable branches, worded "cannot verify that ... is a persistent volume"). When every
area is `mongo` it returns None (the data root holds scratch only, as `warn_if_ephemeral` already
says). Off Cloud Run every current behaviour and test stays: unknowable -> None.
`store_selection()` raising `StoreSelectionError` must not raise out of `storage_warning` (a
diagnostic never breaks startup): it counts as "not mongo". `ui/admin_view.py::storage_banner`
(`:22`, gated on `hosted()`) shows the banner when `hosted()` OR `on_cloud_run()`.
*Test seam:* `tests/test_storage_warning.py` already drives `storage_warning(root, mounts_path)` with
a fake mounts file and monkeypatched env. Add: `K_SERVICE=x` + mounts file missing -> warning (today
None); `K_SERVICE=x` + root on a verified non-`/` volume -> None; `K_SERVICE=x` + all nine areas
`=mongo` + mounts missing -> None; `K_SERVICE=x` + `AUTOTESTER_EPHEMERAL_OK=1` -> None; `K_SERVICE`
unset + mounts missing -> None (unchanged); `K_SERVICE=x` + an invalid `AUTOTESTER_STORE_AREAS` -> a
warning, no exception. Banner: `K_SERVICE=x`, `AUTOTESTER_HOSTED` unset, ephemeral -> the banner HTML
contains the sentence.
*Mutation hint:* leave the `except Exception: return None` as it is -> the K_SERVICE-with-unreadable
-mounts case fails; ignore `store_selection()` -> the all-mongo case fails.
*serves:* intent#O3, intent#O7, intent#O13. *judges:* E5.

**E5.5 The auth flip is honest about existing accounts (A-W1).** `auth/store.py:93-96` documents why
auth never follows the global flag: pointing it at an empty Mongo collection before its users are
migrated locks everyone out. E5.1 does flip auth, so the maker states in the manifest, with a command
and its output, what happens to a container that already holds SQLite users and then starts with the
URI present (migrated; or first-admin bootstrap works on the empty Mongo; or the selection is skipped
when an existing SQLite user store is detected). A silent lockout of an existing deployment is the
defect. "Cloud Run wipes SQLite on deploy anyway" is true of the live site only, not of a compose
deployment with a volume. If the maker cannot show a safe path, it files a HUMAN_GATE with the
evidence and the checker holds E5 (not FAIL).
*Test seam:* create a SQLite auth store with one user, run the selection, then the auth-store factory
(`auth/store.py:122-126`): assert the user is reachable, or the selection did not flip `auth`.
*Mutation hint:* remove the detection/migration -> the test fails.
*serves:* intent#O7, intent#O13. *judges:* E5.

### E6 — The /live viewer works behind Cloud Run: an auth-gated same-origin proxy (AT-1419)

**Premise.** On Cloud Run only the app port is reachable, so an iframe at `http://localhost:6080`
(`ui/routes_live.py:41`, `_DEFAULT_NOVNC`) shows the viewer's own computer and, as http inside an
https page, is blocked. The Caddy front (`docker/Caddyfile`) solves this for compose by path:
`/novnc/*` -> websockify 6080 behind `/auth/check?need=control`, `/novnc-view/*` -> 6081 behind
`need=view`, look-alike VNC paths 403. Cloud Run has no Caddy. This unit reproduces that contract
inside the app. It adds a network surface (HTTP and websocket relay) and therefore needs the D-entry
of E6.9.

**E6.1 Same-origin HTTP proxy for both viewers.** The app serves `GET /novnc/{path}` and
`GET /novnc-view/{path}`, relaying to the in-container websockify HTTP side (noVNC static files) with
the prefix stripped, as Caddy does (`uri strip_prefix`). `/novnc/` relays only to `127.0.0.1:6080`,
`/novnc-view/` only to `127.0.0.1:6081`. The upstream host and port are module constants (one
test-only override, E6.8), never derived from the request: no request value reaches the host, port
or scheme of the upstream (no SSRF). `path` is normalised, and a path containing `..`, a backslash,
a NUL, a scheme, or a leading `//` is refused 400 before any connection. Hop-by-hop headers are
dropped, and `Cookie` and `Authorization` are not forwarded upstream.
*Test seam:* a stub upstream (asyncio server on an ephemeral port, or `httpx.MockTransport` if the
maker injects the client; `httpx` is a declared dependency, `pyproject.toml:14`) wired through the E6.8
mapping; `TestClient` GET `/novnc/vnc.html` as a `live.control` user -> 200 with the stub's body, the
stub saw path `/vnc.html` and no `Cookie` header; `/novnc-view/vnc.html` reaches the second stub only;
path `//evil.example/x` and `..%2f..` -> 400, stub saw nothing; a request with `Host: evil.example`
still reaches only the configured stub.
*Mutation hint:* build the upstream URL from `request.headers["host"]` or the raw path -> the SSRF
and traversal cases fail.
*serves:* intent#O4, intent#O13. *judges:* E6.

**E6.2 Same-origin websocket proxy for both viewers.** `WebSocket /novnc/websockify` and
`/novnc-view/websockify` (the path noVNC dials: `path=novnc/websockify` / `path=novnc-view/websockify`,
as rewritten by `view_only_url`, `ui/routes_live.py:56-65`) relay frames in both directions, bytes and
text unchanged, to the matching upstream, offering the `binary` subprotocol the client offered. A
close or error on either side closes the other; nothing is left open after the client disconnects
(no leaked task or socket). Frame size is bounded by a stated cap large enough for a full-screen noVNC
update; a larger frame closes the socket 1009.
*Test seam:* stub upstream websocket echo; `TestClient.websocket_connect` as an authorised user, send
bytes, receive the same bytes; close the client and assert the stub saw the close within 2 s.
*Mutation hint:* drop the close propagation -> the stub-saw-close assertion times out.
*serves:* intent#O4, intent#O13. *judges:* E6.

**E6.3 Auth uses the SAME logic as `/auth/check`, on every request, including the websocket
handshake.** The decision at `ui/routes_auth.py:148-163` (401 unauthenticated; 400 unknown need; 403
for `need=control` without `live.control`; 200 otherwise) moves into ONE function that both
`/auth/check` and the proxies call (C3: a second copy is the bug). `/novnc/*` needs `control`,
`/novnc-view/*` needs `view` (`live.view`, through the existing policy row in `auth/policy.py`). The
websocket check happens BEFORE `accept()`: an unauthenticated or unauthorised handshake is rejected
(HTTP 403 on the upgrade, or close 1008) without ever dialling the upstream; the session is read from
the handshake cookie. The HTTP login gate (T-204 AU18) is request middleware and does not see
websocket scopes, so this check is not optional. An unauthenticated HTTP request gets 401 (or the
gate's existing redirect), never the viewer HTML, and the upstream is never contacted.
*Test seam:* parametrised over {no session, session without `live.view`, `live.view` only,
`live.control`} x {`/novnc/`, `/novnc-view/`} x {HTTP, websocket}: no session -> 401/403/1008 on all
four combinations; view-only -> `/novnc-view/` allowed, `/novnc/` 403; control -> both allowed. In
every denied case the stub upstream records ZERO connections. Static check: `grep` finds one function
holding the `need not in ("view", "control")` decision. Reuse the fixtures of the existing tests of
`/auth/check`.
*Mutation hint:* move the websocket auth check after `accept()` or delete it -> the unauthenticated
websocket case connects and the zero-connection assertion fails; flip `need` for `/novnc/` to `view`
-> the view-only-on-`/novnc/` case fails.
*serves:* intent#O7, intent#O13 (HO12). *judges:* E6.

**E6.4 Cross-site websocket is refused.** The handshake `Origin`, when present, must be the app's own
origin (scheme and host as the request saw them; the D-066 Origin rule applied to this socket). A
foreign `Origin` is rejected before the upstream is dialled even with a valid session cookie. A
missing `Origin` (a non-browser client) is judged by cookie and permission alone.
*Test seam:* `websocket_connect` with `Origin: https://evil.example` and a control-user cookie ->
rejected, stub upstream sees zero connections.
*Mutation hint:* skip the origin check -> that case connects.
*serves:* intent#O7. *judges:* E6.

**E6.5 Bare and look-alike VNC paths are never the app and never the viewer.** `/novnc`, `/novnc-view`,
`/websockify*`, `/vnc.html`, `/vnc_lite.html` answer 403 (the Caddy `@vnc_other` rule), authenticated
or not, and never relay.
*Test seam:* GET each as `live.control` -> 403, stub saw nothing.
*Mutation hint:* remove the guard -> `/vnc.html` falls through to the catch-all or the relay.
*serves:* intent#O7. *judges:* E6.

**E6.6 The default viewer URL on Cloud Run is the same-origin path; localhost stays for compose.**
`ui/routes_live.py::novnc_url` (`:44`): when `AUTOTESTER_NOVNC_URL` is unset or blank AND
`core/env.py::on_cloud_run()` (E5.4's helper) is true, the default is
`/novnc/vnc.html?autoconnect=true&resize=scale&path=novnc/websockify`; `viewer_url(False)` then maps it
to `/novnc-view/...` with `path=novnc-view/websockify` and `view_only=1` through the existing
`view_only_url` (no second rewrite function). When `K_SERVICE` is unset the default is byte-for-byte
today's `http://localhost:6080/vnc.html?autoconnect=true&resize=scale`, and an explicit
`AUTOTESTER_NOVNC_URL` still wins with its existing validation (same-origin path or localhost only;
hostile characters fall back). The `/live` iframe `src` therefore never contains `localhost` on Cloud
Run.
*Test seam:* `monkeypatch` env. (`K_SERVICE=x`, no override) -> `novnc_url()` starts with `/novnc/`;
`viewer_url(True)` starts with `/novnc/`; `viewer_url(False)` starts with `/novnc-view/` and ends
`view_only=1`; GET `/live` body contains no `localhost`. (`K_SERVICE` unset) -> the exact current
string. (`K_SERVICE=x`, `AUTOTESTER_NOVNC_URL=http://localhost:6080/x`) -> that value. The existing
`/live` tests pass unmodified.
*Mutation hint:* test `hosted()` instead of `on_cloud_run()` -> the `K_SERVICE`-only case fails.
*serves:* intent#O4, intent#O13. *judges:* E6.

**E6.7 An absent upstream is legible, not a hang.** If the upstream does not accept within 3 s, HTTP
answers 502 with a plain sentence (no upstream address) and the websocket closes 1011; the app's
other routes are unaffected, and a dead viewer never blocks the event loop (upstream I/O is async or
off-thread).
*Test seam:* point the E6.8 mapping at a closed port -> 502 / close 1011 within 4 s; a concurrent GET
`/healthz` answers during the wait.
*Mutation hint:* a blocking `socket.connect` in the handler -> the concurrent healthz assertion fails.
*serves:* intent#O4. *judges:* E6.

**E6.8 The seam and the scope.** The only test-time override is ONE module-level mapping of prefix ->
(host, port) that tests patch; production values are the two loopback ports above. The relay speaks
only to loopback; no environment variable can point it elsewhere. The service table in
`docker/entrypoint.sh:94-100` is not edited by this unit: 6080/6081 stay container-internal and
`x11vnc` stays `-localhost`.
*Test seam:* assert the production mapping equals `{"/novnc": ("127.0.0.1", 6080), "/novnc-view":
("127.0.0.1", 6081)}`; `git diff` shows no change to the `exec ... supervise.py` service lines in
this unit's commits (E5 adds its own selection lines above them).
*Mutation hint:* read the host from an env var -> the mapping assertion fails.
*serves:* intent#O7. *judges:* E6.

**E6.9 The new surface has its D-entry.** `docs/DECISIONS.md` carries an ACTIVE entry (appended with
`scripts/append_decision.ps1`) authorizing the in-app VNC relay, citing AT-1419 and this contract,
before the checker PASSes E6. Absent, the verdict on E6 is HELD (not FAIL, not PASS): the code may
exist, the surface is not authorized. The maker drafts the entry for Umesh and does not write an
approval itself.
*Test seam:* `grep -n "AT-1419" docs/DECISIONS.md` finds the entry; the checker reads it.
*serves:* intent#O13. *judges:* E6.

### E7 — The credential guard stops refusing the project name over a server-owned key; reachability names the stage that failed (AT-1416, AT-1420 diagnostic)

**Premise.** `ui/credential_guard.py::refuse_reserved_slug` (`:38-48`) refuses a new project whose key
prefix covers any variable the process holds (`os.environ`, `:44`). On the live server
`PATHLYNKS_MONGO_URI` (`core/env.py:216`) is in the environment, so the slug `pathlynks` (namespace
`PATHLYNKS_`) is refused with "the key prefix PATHLYNKS_ ... is used by a setting on this server"
(callers `ui/app.py:193`, `ui/routes_role_accounts.py:175`). The name is in the environment because
the server owns it, not because a project's credential was shadowed. `is_server_key`
(`core/env.py:55-59`) knows only `PROVIDER_KEYS` and `AUTOTESTER_*`, so the Mongo URI is not
recognised as server-owned (`store/migrate_creds.py:60` special-cases it by hand).

**E7.1 A server-owned key no longer blocks the slug.** The set of server-owned names that are neither
`AUTOTESTER_*` nor provider keys (today exactly `core/env.py::MONGO_URI_ENV`) is defined ONCE in
`core/env.py`, and `refuse_reserved_slug` ignores those names when scanning `os.environ`
(case-insensitively, as `is_server_key` is). With `PATHLYNKS_MONGO_URI` set and no other
`PATHLYNKS_*` variable, onboarding slug `pathlynks` succeeds.
*Test seam:* `monkeypatch.setenv("PATHLYNKS_MONGO_URI", "x")` then `refuse_reserved_slug("pathlynks")`
does not raise (today: 400). Through the app: POST the onboarding form for `pathlynks` -> redirect,
not 400. Static: the server-owned set has one definition (`grep` finds it once; `migrate_creds.py:60`
either uses it or is behaviourally unchanged, and the maker states which).
*Mutation hint:* revert the filter -> the first assertion raises 400.
*serves:* intent#O1, intent#O7. *judges:* E7.

**E7.2 Real collisions are still refused, and the exempted key is not claimable by a project.**
(a) With `PATHLYNKS_MONGO_URI` AND `PATHLYNKS_E2E_USER_PASSWORD` in the environment, `pathlynks` is
still refused (a project-shaped key the process holds). (b) The existing AU21 cases in the guard tests
pass unchanged (provider-key prefix such as `ANTHROPIC_`, `AUTOTESTER_` prefix and its reverse, a slug
whose namespace covers any other held variable). (c) Because the exemption puts `PATHLYNKS_MONGO_URI`
inside the `pathlynks` project's own namespace, `refuse_foreign_key` (`credential_guard.py:51`) must
refuse that exact name with the same 403 as `refuse_server_key` (case-insensitive), so a
`credentials.edit` holder cannot declare the store URI as a project secret and read or overwrite it
through `/env/add`, `/secrets` or an onboarding row. (d) `mongo_uri()` (`core/env.py:220`) keeps
returning the URI after a `pathlynks` project exists, from the process variable and from the
repo-root `.env` (`load_repo_env` skips project-namespace `.env` keys when exporting, but `mongo_uri`
reads `.env` directly at `:233`).
*Test seam:* (a) two `setenv` calls; (b) the existing tests; (c) project `pathlynks` on disk, POST
`/projects/pathlynks/env/add` with key `PATHLYNKS_MONGO_URI` and `pathlynks_mongo_uri` -> 403, no
`.env` write, no declaration; (d) `mongo_uri()` with a `pathlynks` project directory present.
*Mutation hint:* filter the whole `PATHLYNKS_` prefix out of the scan instead of the one key -> (a)
fails; omit (c) -> the 403 case returns a redirect.
*serves:* intent#O7 (C5). *judges:* E7.

**E7.3 The secret-paste rules of `ui/credential_guard.py` are untouched.**
`_refuse_unsafe_submission`, `refuse_server_key`, the namespace and other-project checks of
`refuse_foreign_key`, and the pasted-secret detectors change in no way beyond E7.1-E7.2(c); E3.5's
"guard tests pass unchanged" still holds. The diff for this unit touches only `refuse_reserved_slug`,
`refuse_foreign_key` (one added check) and the `core/env.py` constant.
*Test seam:* run the guard suites unmodified; `git diff --stat` on `ui/credential_guard.py` shows
hunks only in those two functions.
*Mutation hint:* none beyond E7.1/E7.2.
*serves:* intent#O7. *judges:* E7.

**E7.4 The unreachable-target message names the failing stage (AT-1420 diagnostic).**
`stages/reachability.py::_failure_message` (`:133-146`) already distinguishes timeout, DNS, TLS,
refused and closed-connection in prose. Each message additionally carries one stable token naming the
stage that failed, from exactly this set: `dns` (`socket.gaierror`), `tcp` (`ConnectionRefusedError`
and other `ConnectionError`, network or host unreachable `OSError`), `tls` (`ssl.SSLError`,
certificate verification included), `http` (`http.client.HTTPException`: the connection closed or
spoke garbage before an HTTP answer), `timeout` (`TimeoutError`, `_NO_ANSWER`, a stuck attempt), and
`unknown` for the fallthrough (`:146`). The token is a suffix, e.g. `... from this server
[stage=dns]`, so the wording asserted by `tests/test_reachability_warning.py` and
`tests/test_run_unreachable_target.py` (including "did not answer within 10 s from this server", E4.2)
still matches as a substring and those tests pass unmodified. The message still names only the host:
never the path, query, resolved IP, proxy, or exception text. The token reaches
`Run.preflight_warnings`, each case's `not run:` error, the EXECUTE span `error` and the run page,
because `skip_run` (`stages/reachability.py` `skip_run`) already carries the one message to all of
them.
*Test seam:* call `_failure_message("h.example", exc)` for `URLError(gaierror)`,
`URLError(ConnectionRefusedError)`, `URLError(ssl.SSLCertVerificationError)`, `URLError(TimeoutError)`,
`http.client.RemoteDisconnected` and `ValueError`; assert the stage token per class, and that the
host is the only host-like string even when the exception text carries a canary IP. End to end:
base_url on a closed local port with `allowed_domains` set -> run page text contains `[stage=tcp]`;
the existing blackhole test shows `[stage=timeout]`.
*Mutation hint:* map `ssl.SSLError` to `tcp` -> the TLS case fails; put `str(exc)` in the message ->
the canary assertion fails.
*serves:* intent#O3, intent#O4, intent#O13. *judges:* E7.

**E7.5 AT-1420 stays an infrastructure issue and is not closed by E7.** E7.4 makes the live failure
diagnosable (the first live run after this lands names `dns`, `tcp`, `tls`, `http` or `timeout`); the
egress IP / allowlist remains DevOps. The maker's manifest says so and does not mark AT-1420 fixed;
the checker leaves the row `open` with a note pointing at the stage token.
*Test seam:* the `qa/issues.jsonl` row AT-1420 is not `closed` by this unit's commits.
*serves:* intent#O13. *judges:* E7.

## Verification the checker runs itself (never the maker's word)

```
uv run pytest            # no -q on the command line (AT-503)
uv run ruff check src tests scripts
uv run autotester doctor
```

plus the per-criterion tests named above, the unmodified hold suites of E2.5, and for E3.6 a
checker-taken screenshot. Evidence of a model answering (E2.1-E2.3) uses fakes only: no network, no
`.env` value is printed or read into a test.

## No-fire list

- The Gemini monthly spend cap itself (Umesh, ops: ai.studio/spend): not a code defect.
- Choosing which provider a project uses (project config), beyond making the legacy chain reach
  Ollama when a key is present.
- The wording of a model's note beyond E2.6 (the guard stays the arbiter of what is held).
- AT-1416, AT-1419, AT-1420 (above).
- Changing V2 retention (a PASS keeps no video), D-112's definition of the clock, or the
  `RunApproval` bounds model.
- Visual polish of the credentials page beyond E3.6.

## Amendment log (append-only; git history is the version)

- 2026-11-01 · init · contract authored by /checker in contract-authoring mode, from
  `qa/issues.jsonl` AT-1412..AT-1421 and `.work/e2e-2026-11-01/report.md` (master 468b3832). Every
  file:line above was read against the code at that commit. Three findings from that reading change
  the shape of the units and are recorded so they are not rediscovered: (1) E2: requiring
  `defect_observed` does not by itself release the two held PASSes, because `_defect_decision`
  runs the note guard on `defect_observed=false` too (`stages/grade.py:274-277`); the remedy is the
  prompt (E2.6) with the verbatim notes pinned as still-held (E2.7), and loosening the guard is
  outside this unit. (2) E4.1: the 289 s / 215 s overrun is consistent with D-112's exclusion
  clock; the defect is the missing arithmetic on the page and the missing fast-fail. (3) E4.3:
  AT-1415's missing video was a PASS case, which run-video V2 prunes by design.
  **Amendment owed (not made in this pass, which was scoped to this file):** `langchain-fallback.md`
  LC2 states the order Anthropic -> Gemini -> Ollama -> ChatGPT and gates Ollama on `OLLAMA_BASE_URL`
  alone; E2.1/E2.2 supersede both. The checker folds that into LC2 and its amendment log in the same
  cycle as E2's verdict. **Links:** AT-1412..AT-1421; D-112; grade.md G3/G6; run-video.md V2.

- 2026-11-01 · E2 verdict (cycle 0) · /checker. (1) **E2.7 item 1 example corrected:** the literal
  reworded a5ea note "The wrong-password login was correctly rejected: ..." is NOT a PASS under
  the unchanged guard (checker-run: INCONCLUSIVE), because `_CONTRARY` holds `wrong` and
  `_QUALIFIED_INPUT` (`stages/grade_note_guard.py:102-103`) strips only whitespace-separated
  "wrong <input>". The pinned PASS example is the spaced form "The login with a wrong password was
  correctly rejected: the 'Invalid credentials' assertion was met." The contract text was wrong,
  not the maker; E2.5 forbids the guard change that would make the hyphen form pass. (2) **E2.4(b)
  wording:** "`grade()` returns INCONCLUSIVE" is satisfied by the existing
  `run_case_pipeline.py::run_and_grade_case_resilient` (`:271-276`), which converts a
  `ProviderError` raised inside `grade()`; `grade()` itself propagates by design. (3) The
  `langchain-fallback.md` LC2 amendment owed above is made (sections LC2a/LC2b there).

- 2026-11-01 · amendment E5-E7 · /checker, contract-authoring mode, at Umesh's 2026-11-01 instruction
  (Mongo URI already in the live server env; live must persist without DevOps), relayed by the
  orchestrator. Added E5 (AT-1433: entrypoint selects the Mongo store only when the URI is present and the
  operator set neither store variable; `storage_warning` warns on Cloud Run, `K_SERVICE`, instead of
  returning None), E6 (AT-1419: auth-gated same-origin HTTP+websocket noVNC relay, default viewer URL on
  Cloud Run), E7 (AT-1416: guard stops counting the server-owned Mongo URI; AT-1420: stage token in the
  unreachable message). Every file:line read against master 3fba855f. Findings recorded so they are not
  rediscovered: (1) E5.5: the generated `auth=mongo` flip reaches an existing SQLite user store empty
  (`auth/store.py:93-100`, A-W1); the live site loses nothing it had not already lost to Cloud Run's
  ephemeral disk, but a compose deployment with a volume would lock out, so the maker must show a safe
  path or file a HUMAN_GATE. (2) E6.3: the HTTP login gate does not see websocket scopes, so the proxy
  checks auth itself before `accept()`, and the decision at `routes_auth.py:148-163` moves into one
  function, not a copy. (3) E7.2(c): exempting `PATHLYNKS_MONGO_URI` from the slug scan puts it inside
  the `pathlynks` project's own namespace, so `refuse_foreign_key` must then refuse it explicitly, or a
  `credentials.edit` holder could declare and overwrite the store URI. (4) E7.4: the existing messages
  already separate dns/tls/refused/timeout in prose; the new token only makes it machine-checkable. (5)
  `K_SERVICE` appears nowhere in `src/` today; `on_cloud_run()` is introduced once (E5.4) and reused (E6.6).
  The D-130 push hold is unchanged: it lifts only when Umesh says live storage is persistent, which E5 makes
  possible but does not itself declare. The AT-1416/AT-1419 "needs a D-entry" gate is carried by E6.9; E7 is
  not an enforcement path. **Links:** AT-1416, AT-1419, AT-1420, AT-1433; D-122/D-123; D-130; HO12;
  core-invariants C3/C5/C12.
