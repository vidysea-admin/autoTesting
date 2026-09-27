# Contract — consent gates (`RunApproval` + `require_approval`)

**Covers:** goal tasks T-124 (this gate), T-145 (the live logged-in ERP crawl it stands in front
of), T-151 (gate 1, `ApprovalKind.READ`), T-154 (gate 2 adversarial). **Owner:** /checker.
**Source of truth for intent:** plan §5A "T-124 — the two-gate consent model", authorised by
**D-018**; criteria CN1–CN7 folded verbatim from `qa/feedback-inbox.md` 2026-09-08 (maker, T-124).
**Depends on:** `core-invariants.md` (C1, C2, C3, C6) and `explore.md` (X1–X16, which the gate must
leave intact).

## Purpose

Consent used to be a habit: a `write_policy` default and a gate file a careful operator honoured.
This makes it **a file a human writes once and a runner checks every time** — what may be touched,
how much of it, until when, and who said so. The gate stands between an autonomous crawler and a
live production ERP, so it is judged adversarially: the question is never "does the code look like
it refuses", it is "can a check that ran for real get past it".

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

## Out of scope / ignore (do not raise these as findings)

- **Revocation.** Expiry only, for now. There is no `autotester revoke`; deleting the row is the
  operator's lever.
- **Gate 1 (`ApprovalKind.READ`) having no caller yet** — T-151's discovery scan is its unit.
- **Gating `ingest` / `expand` / `run_case`** — T-122's live-case gate is a separate unit.
- **A UI grant form.** CLI only; the credentials page is the right home and is not built here.
- **Org-level / multi-project / wildcard approvals**, and **any auto-granting path whatsoever** —
  the absence of one is the feature.
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
