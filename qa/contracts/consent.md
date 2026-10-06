# Contract — consent gates (`RunApproval` + `require_approval`)

**Covers:** goal tasks T-124 (this gate), T-145 (the live logged-in ERP crawl it stands in front
of), T-151 (gate 1, `ApprovalKind.READ`), T-154 (gate 2 adversarial). **Owner:** /checker.
**Source of truth for intent:** plan §5A "T-124 — the two-gate consent model", authorised by
**D-018**; criteria CN1–CN7 folded verbatim from `qa/feedback-inbox.md` 2026-09-08 (maker, T-124).
**Depends on:** `core-invariants.md` (C1, C2, C3, C6) and `explore.md` (X1–X16, which the gate must
leave intact).

## Purpose

Consent used to be a habit: a `write_policy` default and a gate file a careful operator honoured.
This makes it **a signed approval a runner checks every time** — the exact project, kind, target,
scope, expiry and operational bounds. Human-granted approvals remain supported. **D-063** adopts
Umesh's AT-674 Answer for the Pathlynks USER run: provisioned declared credentials, the exact target
and allowed domains authorize a newly derived `LIVE_CASE` grant under CN11. The human does not type
counts or a signing key; positive finite bounds are system-selected operational brakes. This narrow
derivation never bypasses the gate or repairs a loaded row. The gate is judged adversarially: the
question is never "does the code look like it refuses", it is "can a check that ran for real get
past it". CN1-CN10 retain their fail-closed obligations.

## Criteria

### CN1 — Nothing outward-facing starts without an approval, and a refused run leaves no trace
- `run_crawl` raises `ApprovalRequired` **before** a crawl envelope, a browser navigation, a click,
  a screenshot or a screenshot directory exists.
- **The property is judged at every shipped entry point, not only at the seam.** `autotester
  explore`, the UI `POST /projects/{slug}/explore`, and a direct `run_crawl` call must all leave
  the project directory exactly as they found it when the run is refused. A criterion proven only
  on a path no operator uses is the maker's own "guard tested nowhere", inverted onto the proof.
- **Verify:** `scripts/explore_proof.py`'s first invariant (real ungated crawl, assert no crawl
  directory was created) **and** a refused CLI/UI run leaving no `projects/<slug>/crawl/<id>/`.

### CN2 — The gate lives at the seam, not in each caller
- The CLI and the UI both reach `run_crawl`; neither may *replace* the seam check with its own.
- A caller-side pre-check that runs **in addition to** the seam check is permitted and is the
  expected way to satisfy CN1's second clause — the seam remains the guarantee, the pre-check is
  only there so nothing is created before the refusal.
- **Verify:** removing `_require_consent` from `run_crawl` must fail the suite and the proof
  (checker sabotage test — re-run it, do not read it).

### CN3 — An approval cannot widen itself by a careless edit
- `RunApproval.id` is content-addressed over **every** bound field (`project`, `run_kind`, `target`,
  `scope`, `max_actions`, `max_probes`, `wall_clock_s`, `production`, `granted_by`, `granted_at`,
  `expires_at`); `require_approval` refuses a row whose id no longer matches its contents.
- `note` is deliberately **outside** the payload, so a human may annotate an approval without
  re-granting it.
- **Stated limitation, not a defect to be quietly discovered later.** `content_id` is an *unkeyed*
  hash, so the id is recomputable by anyone who can write `approvals.jsonl` — including the agent
  the gate exists to bound. CN3 therefore claims exactly what it delivers: **detection of an edit
  that did not recompute the id**, i.e. accident and carelessness. It is **not** resistance to a
  forger. Any prose (docstring, CLI `--help`, commit message) that says an approval "cannot be
  edited on disk to widen itself" overclaims and must be corrected. Closing the forger case needs a
  secret outside the writable surface — an Umesh decision, tracked as **AT-110**, not assumed here.
- **Verify:** edit `max_actions` on a real `approvals.jsonl` row → refused with "edited after it was
  granted"; the recomputed-id variant is a **known, documented** acceptance until AT-110 is decided.

### CN4 — Consent is never open-ended
- `expires_at` is required. An unparseable expiry is treated as **expired**, never as eternal.
- **A date given at the grant means through the END of that day, for grants minted from
  2026-09-26 on** (at147 answered C, D-048).
  - `approve --expires <date>` stores an explicit, **offset-aware** end-of-day timestamp in the
    operator's local timezone, e.g. `2026-09-26T23:59:59+05:30`. Consent lapses after the last
    local second of the named day, and `--expires <today>` is therefore grantable.
  - The timestamp must never be stored naive. `RunApproval.is_expired` (schema/approval.py) reads a
    naive stamp as UTC, so a naive `T23:59:59` would run about 5.5 h past local midnight on an IST
    host.
  - **A bare date already on disk keeps its old meaning.** `fromisoformat` reads
    `expires_at: "2026-09-09"` as midnight, so that row lapses at the START of its day. No stored
    approval is widened: option B, retroactive end-of-day, was declined.
  - Making a stored bare date inclusive, or changing the time stamped on new grants, is a CRITICAL
    amendment, not a fix.
- **The grant and the runtime must agree: every expiry `approve` ACCEPTS must be one
  `require_consent` will HONOUR.** Two comparisons implementing one rule is where AT-145 and
  AT-147 both came from — a whole day in which `approve` printed a green "granted" line for a
  consent the very next `explore` refused as expired. A refusal at the grant must also name what
  the operator should type instead; a gate that only says "no" trains the operator to stop reading
  it (the CN6 principle, applied one level up at the grant).
- **Verify:** `tests/test_consent.py`; and the property test driving the real CLI grant into the
  real `require_consent` (`tests/test_approve_cli.py::test_the_grant_and_the_runtime_agree_on_every_expiry_they_accept`).
  For the end-of-day rule, a test must show all three of these:
  - a NEW grant for day D is honoured at D 23:59:59 local time and refused one second later, with
    the boundary pinned as an exact aware instant;
  - a pre-existing bare-date row for D still lapses at D 00:00;
  - `--expires <today>` is granted AND honoured.
  Each is red with the fix reverted (C7).

### CN5 — Approval does not transfer
- Matching on (`project`, `run_kind`, `target`) is **EXACT** string matching. A prefix match would
  let an approval for one endpoint authorise another under the same host; consent to read is not
  consent to fire probes.
- **Trailing slash, host case and query string are deliberately different targets.** `https://h/a`
  does not authorise `https://h/a/`, `https://H/a` or `https://h/a?x=1`. This is brittle on purpose:
  the alternative is URL normalisation, and every normaliser is a place where an approval silently
  grows. The operator pastes the target out of the refusal message, which always prints the exact
  string the runner will compare, so brittleness costs a copy-paste and buys unambiguity.
- **Verify:** exactness probes over those four variants, all refused.

### CN6 — Bounds are checked, not just existence
- A run wider than its approval is refused with the shortfall named (`actions 150 > approved 20`).
- **Every** rejection reason is reported, not only the first — one bad row must not hide a good one,
  and a refusal that only says "no" teaches the operator nothing.
- **The refusal's suggested grant command must actually work.** It carries the bounds of the run it
  is refusing; an operator who pastes it verbatim (filling only the `<...>` placeholders) and re-runs
  the same command must proceed. A suggestion that does not work is worse than none, because it
  spends the reader's trust on the way to the same dead end.
- **Verify:** run the refusal's own command verbatim, then re-run the crawl; it must proceed.

### CN7 — Adversarial against production must say production
- `ApprovalKind.ADVERSARIAL` requested with `production=True` requires `production=True` granted.
- **Scope boundary (recorded so it is not mistaken for coverage):** nothing in the system computes
  *whether a target is production*, and the crawl gate never requests `production=True`. So the
  `production` field is **inert for `ApprovalKind.CRAWL`** — the live ERP crawl of T-145 is
  authorised by an ordinary crawl approval. That is the current, intended shape; making the ERP
  target require an explicit production grant is tracked as **AT-112**, not assumed to exist.
- **Verify:** `tests/test_consent.py`; a crawl-kind run must not be silently credited with CN7.

### CN8 — The done_check can fail *and* can pass
- `scripts/check_crawl_approval.py <slug>` is T-145's `done_check`. It exits 0 **only** when the
  project has a finished crawl on disk whose bounds an intact, unexpired `RunApproval` authorised;
  exit 1 otherwise; exit 2 on usage.
- A `done_check` that can only fail is no better than one that can only pass (`{"cmd": "true"}`,
  AT-100). **Both directions must be demonstrated**, on constructed state, by the checker.
- **Verify:** exit 1 today for `erp`; exit 0 against a scratch root holding a real approved crawl;
  exit 1 again when that approval is removed or tampered.

### CN9 — The gate applies to every crawl, including local fixtures
- **The maker's trade is upheld.** The gate is unconditional; it is *not* switched on by "is the
  target remote / not localhost". Tests grant a real `RunApproval` rather than bypassing the gate.
- Reasons, recorded so this is never quietly reversed: a "is this localhost?" predicate fails
  **open** on a misconfiguration (an unresolved hostname, a proxy, a tunnelled port, a stale
  `base_url`), and it is precisely the misconfigured case that most needs the refusal; and a guard
  only production callers pass through is a guard exercised by no test in the suite. The cost —
  four test entry points and the proof script granting an approval — is paid once and buys the
  gate's happy path being exercised by every crawl test that exists.
- Reversing this is a **CRITICAL** amendment (it weakens a safety invariant): human decision only.

### CN10 — A bound means one thing on both sides, and a bound that constrains nothing is not a bound
- **One meaning, stated once.** `max_actions`, `max_probes` and `wall_clock_s` each mean the same
  thing at the gate (`core/consent.py::_shortfalls`) and during the run
  (`stages/parallel_run.py::RunBudget.try_consume`). Today they do not: the gate compares bare
  (`if actions > approval.max_actions`) so `0` is a **zero budget**, while the run guards on
  truthiness (`if approval.max_actions and ...`) so `0` is **unlimited** — and the permissive
  reading is the one that governs once a run starts. All three fields carry the identical inversion
  (`parallel_run.py:158`, `:162`, `:164`).
- The chosen meaning is written in the field's own docstring in `schema/approval.py`, so the next
  reader does not re-derive it from two call sites that disagree.
- **Asserted from both sides in ONE test.** Two tests each checking one side is exactly how this
  survived: each passes, and the disagreement between them is what nothing asserts. The test
  constructs one approval and exercises the gate and the budget against it.
- **A fixture with `0` bounds is an unexercised refusal path, not a fixture.** It passes the gate
  *and* enforces nothing, so "an approved run proceeds" passes for the wrong reason, and "an
  over-budget run is refused" cannot be written at all — `0 > 0` is false, so there is no
  over-budget to construct. Every fixture approval carries **non-zero** bounds, and an over-budget
  refusal test exists.
- **The over-budget test names the bound it exceeds and by how much.** A fixture whose bounds came
  from the printed grant command is non-zero and *looks* correct, so a refusal test can pass against
  a bound large enough that exceeding it was arranged rather than tested. The test states the bound
  and the margin (e.g. `max_actions=3`, attempt 4) so the refusal is demonstrably the bound firing
  and not a number chosen to make the assertion true. **The maker's addition, 2026-09-28.**
- **The remediation covers all three bound fields, not the one visible on disk.**
  `cli_crawl.py::approve_cmd` defaults `--max-actions`, `--max-probes` and `--wall-clock` to `0`
  with no `min=` anywhere in the file, so a CLI grant with no bound flags reaches every one of
  `parallel_run.py:158`, `:162`, `:164`. That the three rows on disk happen to be zero only on
  `max_probes` is a fact about the UI form's `min='1'`, not about the defect's reach. A fix scoped to
  the observed field closes a third of the invariant and reads as closed.
- **Plausibility, which fixing `0` does not give you.** A bound may be present, non-zero, signed and
  pass every check while constraining nothing: `projects/pathlynks/approvals.jsonl`'s live row
  carries `wall_clock_s = 600000000.0`, which is **19 years**. No falsy guard fires on it and no
  criterion above rejects it. This is the worse of the two failures because it survives a reviewer
  reading the row. **CORRECTED 2026-09-28, this clause overreached:** it first said a grant path or
  validator "must reject a bound that exceeds any defensible run". Rejecting requires a policy
  ceiling, and **what counts as a defensible maximum is a gate decision, not a build's** — the maker
  was right to push back. What the unit owes is **visibility, not enforcement**: the run's own record
  states the bounds it ran under, so `19 years` appears where a human reads it. A build must NOT
  invent a ceiling or hard-code a maximum, and if it judges plausibility uncheckable without a policy
  number it says so in Disclosures rather than guessing one. The ceiling itself is Umesh's to set;
  until he does, this axis (`wall_clock_s` — the only bound that limits a run which is *misbehaving*
  rather than merely long) is reported and not enforced, and that is stated rather than hidden.
- **The visibility clause is satisfied by the run's own record on disk. RULED 2026-09-28 (checker,
  at570 cycle 1), so it is not re-litigated per unit.** `schema/run.py::RunBounds` written onto
  `Run.bounds` and saved into `run.json` MEETS this clause. The clause's own words are "the run's own
  record states the bounds it ran under", and in this repo an artifact on disk *is* a human-readable
  surface (core-invariants C6: a human can edit any artifact). A **rendered** surface is a stronger
  obligation than the text carries, and the clause was narrowed once already because the checker had
  imposed more than it had standing to; adding the stronger reading inside the very check that judges
  against it would be the retroactive contract movement the Lab Protocol exists to catch.
  - Absence must have its own representation: `bounds: RunBounds | None = None` where `None` means
    NOT RECORDED, never zeros and never "unbounded" (C12(b)).
  - **Rendering it remains open as AT-682, and it is a real thinness, not a formality** — a bound no
    surface shows is visible only to someone who already went looking. The next unit that touches
    `ui/routes_report.py` (at 300/300 lines, which is why this one could not) carries it. A future
    tightening of this clause to require a rendered surface is a routine amendment made BEFORE the
    unit that will be judged by it, never during its check.
- **Never rescued.** Existing rows are not special-cased, grandfathered, migrated or back-filled to
  survive a semantics change. Under a fail-closed reading they authorize nothing, and re-granting is
  already required (AT-674).
- **Ratification is disclosed, not assumed.** If the build chooses what `0` means rather than a
  human ratifying it, the **verdict must say so in those terms** — that the semantics were chosen by
  the build and await ratification. A PASS is not blocked by the absence of ratification (the code
  must mean something, and fail-closed is the reversible direction), but a PASS that is silent about
  it launders a build's design decision into a settled one, which is the decision drift the Lab
  Protocol exists to catch. This binds the checker, not the maker.
- **Verify:** `uv run pytest` covers one approval asserted from both the gate and the budget side,
  and an over-budget refusal; `grep` shows no truthiness guard on a bound in `RunBudget`.
  **Links:** AT-660; AT-570; AT-674; core-invariants C12.

### CN11 — Account-derived LIVE_CASE grants preserve verification and bound the whole run
- **Authority and identity (D-063; AT-674 Answer).** A newly minted grant derives only from validated
  current provisioned account credentials declared by the project, the exact requested target and
  allowed domains. Its `project`, `run_kind=LIVE_CASE`, `target` and `scope` match the requested run
  exactly; scope records the validated account/domain scope without wildcards or widening. CN5's
  slash/case/query distinctions still apply. No transfer across projects, kinds, targets or scopes.
  No automatic `READ`, `CRAWL` or `ADVERSARIAL` grant follows from this criterion.
- **Selected credentials only.** Preconditions inspect the keys actually referenced by the requested
  case set. Missing, undeclared, unavailable or out-of-scope referenced credentials refuse before
  browser actions. Unused COUNSELLOR keys never gate the USER run or provide a fallback identity.
  Resolution remains per-`SecretRef` host-scoped at the existing browser substitution boundary; a
  credential value never enters a grant, model, log or artifact (C5).
- **Explicit first-use preparation.** Only the authorized grant path may call key provisioning;
  imports, file loads and signature verification never create a key. Generate a random key only
  when neither an effective process override nor a stored key exists. Preserve existing stored
  keys, process overrides and unrelated env entries. Use the existing owner-only atomic env writer
  with serialized create-if-absent: concurrent first uses converge on one persisted key and no
  caller overwrites the winner. If signed historical state has lost its verification key, refuse
  instead of generating a replacement and making that history unverifiable.
- **New rows only; verification remains unconditional.** Never sign, re-sign, migrate, backfill or
  rescue loaded approval rows. Mint a new signed, content-addressed row with an explicit unexpired
  expiry obeying CN4 and validated identity/scope. Verify signature, content integrity, identity,
  expiry, production requirements and bounds before any browser action at every execution entry
  and at the existing seam. Missing or invalid inputs fail closed; no dev/fixture/localhost bypass.
- **Operational brakes.** System-selected `max_actions`, `max_probes` and `wall_clock_s` are positive
  and finite; CLI grant defaults are positive real bounds with invalid/nonpositive inputs rejected.
  Bounds retain CN10's single meaning: zero never becomes unlimited. Record the actual limits;
  do not invent a human consent ceiling or describe a default as measured product coverage.
- **One aggregate budget.** Serial, entry/login and parallel case execution share one `RunBudget`
  for the entire requested run, including executor actions, probes and elapsed wall time. No path,
  worker, retry or case resets or bypasses its consumed totals. Stop on a brake, identify the brake
  and record stopped/truncated truth; partial execution never reports completed E2E (C12).
- **Redacted accountability.** Record performed actions, field changes and their prior values,
  button presses, actual bounds and stop reasons in the existing report/trace surfaces after
  redaction. Secret prior values are never copied into accountability records or screenshots.
- **Remaining gates.** Human FlowSpec review, explicit adversarial authorization, production
  promotion, project write policy and model-spend gates remain applicable. CN11 grants no blanket
  live-account write, paid-model-run, production-write or release authority.
- **Verify:** independently exercise the authorized grant through real preflight/seam checks with
  synthetic credentials and a scratch env; refuse each identity/scope variant and invalid credential,
  signature, expiry or bound. Prove unused role keys are irrelevant, loaded rows stay byte-intact,
  concurrent first use preserves the winning key/other entries/overrides, and lost-key signed history
  refuses without writes. Exercise serial/entry/parallel against the same budget, exceed each named
  brake by a stated margin, and assert redacted stopped/truncated reports and trace records. Each
  claimed guard has an isolated green-before/red-after/restored falsification under C7; acceptance
  requires its own evidence, not this contract adoption.

## Out of scope / ignore (do not raise these as findings)

- **Revocation.** Expiry only, for now. There is no `autotester revoke`; deleting the row is the
  operator's lever.
- **Gate 1 (`ApprovalKind.READ`) having no caller yet** — T-151's discovery scan is its unit.
- **Gating `ingest` / `expand` / `run_case`** — T-122's live-case gate is a separate unit.
- **A UI grant form.** CLI only; the credentials page is the right home and is not built here.
- **Org-level / multi-project / wildcard approvals**, and **auto-granting outside CN11's
  account-derived LIVE_CASE path** — D-063 authorizes only that narrow exception. Automatic READ,
  CRAWL and ADVERSARIAL grants remain excluded.
- The `production` field being unused by the crawl gate (recorded in CN7 as a boundary, tracked as
  AT-112 — not a fresh finding each check).
- `approvals.jsonl` being deliberately hostile to hand-editing. It is a **stated exception** to
  core-invariant C6's "a human can edit any artifact": the file still loads and still deletes
  cleanly, it simply refuses an edited row instead of honouring it. C6 holds.

## Amendment log (append-only; git history is the version)

- 2026-09-08 · START · contract created by /checker from `qa/feedback-inbox.md` 2026-09-08 (maker,
  T-124), CN1–CN7 verbatim in substance · direction approved by Umesh via **D-018** and plan §5A;
  the checker authored the wording, the maker never writes a contract.
- 2026-09-08 · tighten · **CN1** extended from "`run_crawl` raises before anything exists" to "the
  property holds at every shipped entry point" · why: measured — a refused `autotester explore` and
  a refused `POST /projects/{slug}/explore` both create `projects/<slug>/crawl/<id>/shots/` and
  launch Chromium before the seam refuses, because `BrowserSession.start()` runs inside the `with`
  that wraps `run_crawl`. The narrower wording was satisfied by a path no operator uses. Tightening,
  not weakening — auto-applied. Tracked as AT-111.
- 2026-09-08 · record edge case · **CN3** limitation stated explicitly (unkeyed content-address =
  accident detection, not forgery resistance) · why: measured — a row widened 12 → 9999 actions with
  `production` flipped true and its id recomputed was accepted, and a 500-action crawl ran on a
  human grant of 12. Recording the true property rather than letting a later reader trust the
  overclaim. AT-110 carries the design decision.
- 2026-09-08 · record edge case · **CN5** trailing-slash / case / query-string variants named as
  deliberately distinct targets, with the reason · why: measured all four as refused; brittleness
  is the intended trade against a normaliser that silently widens consent.
- 2026-09-08 · tighten · **CN4** extended with (a) the measured meaning of a bare `expires_at`
  (START of the named day) and (b) the grant↔runtime agreement property · why: measured — AT-145
  and AT-147 were one defect twice, a `<` at the grant against a midnight `>` at the runtime, so
  `approve --expires <today>` was granted and then refused. Recording the property once, as a
  criterion, is what stops it arriving a third time. Tightening, not weakening — auto-applied.
  The *end-of-day alternative* is deliberately NOT adopted here: it widens every approval on disk
  by up to 24h, which is CRITICAL → `qa/gates/at147-expiry-end-of-day.md`.
- 2026-09-08 · add criterion · **CN8** (a `done_check` must be demonstrated in both directions) and
  **CN9** (the gate is unconditional; the maker's trade upheld, reversal is CRITICAL) · why: the
  maker asked for a ruling on the trade and it should not stay implicit; AT-100's lesson is that an
  unfalsifiable check is the failure mode, and "can only fail" is the mirror of it.
- 2026-09-26 · amendment (authorized by D-048; Umesh answered qa/gates/at147-expiry-end-of-day.md = C)
  · **CN4**: new grants store an offset-aware local `<date>T23:59:59±hh:mm`, so a named day is
  inclusive. The timezone rule was added on the same-day pre-commit review (is_expired reads naive
  stamps as UTC). Bare-date rows
  already on disk keep start-of-day. This widens consent only for grants made after this date,
  and only by the operator's own explicit choice of day. Nothing already granted changes. The
  maker builds it against this text, and AT-150/AT-151 are re-judged against it.
- 2026-09-28 - routine (add) - CN10 added: a bound means one thing on both sides, and a bound that
  constrains nothing is not a bound. Cause: AT-660, found while verifying the maker's narrowing of
  AT-659. `0` is a zero budget at the gate (`_shortfalls`, bare comparison) and unlimited during the
  run (`RunBudget.try_consume`, truthiness guard), on all three bound fields, and
  `require_approval`'s own defaults are `0` - so a caller that omits them is accepted by a vacuous
  check and then bounded by nothing. AT-570's briefed fix (making `approval` non-optional) is
  necessary and NOT sufficient: the fail-open survives inside a signed, unexpired, correctly-scoped
  approval, which is worse than the original defect because everything a reviewer inspects says the
  run was authorized. CN10 also carries two things the `0` question does not reach: a fixture with
  `0` bounds cannot express an over-budget refusal, so it is an unexercised refusal path (the maker
  ranked this the most likely escape and it is the AT-218 vacuous-guard class); and a bound can be
  non-zero, valid and still decorative - the live pathlynks row's `wall_clock_s` is 19 years. The
  ratification clause binds the CHECKER's verdict wording, answering the maker's direct question:
  absent ratification does not block a PASS, silence about it does. Additive; no criterion weakened.
  **Changes-authorized:** qa/contracts/consent.md CN10 + Amendment log (this entry). No
  enforcement-path file touched. **Links:** AT-660; AT-659; AT-570; AT-674; AT-218;
  qa/contracts/core-invariants.md C12.
- 2026-09-28 - routine (correct) - CN10's plausibility clause narrowed from "must reject a bound that
  exceeds any defensible run" to visibility plus an explicit Disclosures route. Cause: the maker
  pushed back that rejecting needs a policy ceiling and a ceiling is a gate decision, not a build's,
  and it is right - the clause as written would have had a build agent invent a policy number to
  satisfy a contract. Weakens no other criterion and removes an obligation the checker had no
  standing to impose. **Changes-authorized:** qa/contracts/consent.md CN10 (this entry).
  **Links:** AT-660; AT-661.
- 2026-09-28 - routine (extend) - CN10 gained two clauses, both the MAKER's (autotesting-52), both
  verified against cli_crawl.py before folding. (i) The over-budget refusal test must name the bound
  and the margin: a fixture seeded from the printed grant command is non-zero and looks correct, so
  the test can otherwise pass against a bound so large that exceeding it was arranged. (ii) The
  remediation scope is all three bound fields. This one corrects MY narrowing: I had inferred from
  the UI form's min='1' that only max_probes was reachable. approve_cmd defaults all three bounds to
  0 (:241-243) with no min= in the file, so a CLI grant reaches all three guards. The UI's min='1'
  bounds what the UI can write, not what the system can hold. Additive; no criterion weakened.
  **Changes-authorized:** qa/contracts/consent.md CN10 + Amendment log (this entry). No
  enforcement-path file touched. **Links:** AT-660; AT-570; AT-675.
- 2026-09-28 - routine (record a ruling) - CN10 gained an explicit ruling that the visibility clause
  is MET by `Run.bounds` in `run.json`, with the rendered-surface reading named as a stronger
  obligation the text does not carry and left open as AT-682. Cause: the at570 build agent asked the
  question directly in its manifest (D3) rather than assuming an answer, and said it was not claiming
  the clause met. The checker's answer must live in the contract, not only in one verdict, or the next
  build re-derives it. Ruling in full: an artifact on disk is a human-readable surface in this repo
  (C6); the clause says "the run's own record"; and this clause was already narrowed once for
  checker overreach, so tightening it inside the check it governs would be retroactive. Weakens no
  criterion and adds no obligation. **Changes-authorized:** qa/contracts/consent.md CN10 + Amendment
  log (this entry). No enforcement-path file touched. **Links:** AT-682; AT-660; AT-570;
  qa/contracts/core-invariants.md C6, C12(b).

- 2026-10-06 · CRITICAL, authorized by **D-063** (Approved-by: Umesh; AT-674 direct Answer)
  · checker-owned adoption by `/root/adopt_account_grant_contract`: Purpose and auto-grant exclusion
  reconciled; **CN11** added for account-derived LIVE_CASE only. Records exact identity/scope,
  selected credential preconditions, explicit serialized first-use key preparation with lost-key
  refusal, unchanged loaded rows, positive finite brakes, one aggregate budget and redacted truthful
  accountability. CN1-CN10 unchanged; other authorization, production and model-spend gates retained.
  **Changes-authorized:** qa/contracts/consent.md Purpose, auto-grant exclusion, CN11 and this log.
  Contract maintenance only: no product acceptance/PASS, runtime, credential write, commit or release.
  **Links:** D-063; AT-674; T-122; qa/gates/pathlynks-user-account-first.md; core-invariants C5/C12.
