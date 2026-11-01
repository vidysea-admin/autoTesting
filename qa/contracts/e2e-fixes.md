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

## Out of scope (do not build, do not raise as findings against these units)

- **AT-1416** (live refuses slug `pathlynks`, `ui/credential_guard.py:38-48` vs the server's own
  `PATHLYNKS_MONGO_URI`): the fix renames or exempts a server key, which touches the D-122 store
  configuration. Needs an Umesh D-entry first. HUMAN_GATE.
- **AT-1419** (live view iframe points at `localhost:6080`, `ui/routes_live.py:40-53`): the fix is a
  new websocket proxy route in the app, a new network surface. Needs a D-entry. HUMAN_GATE.
- **AT-1420** (Cloud Run cannot reach pathlynks.vidysea.com): infrastructure (static egress IP,
  allowlist). DevOps. E4's fast-fail makes the symptom legible; it does not fix the cause.
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
