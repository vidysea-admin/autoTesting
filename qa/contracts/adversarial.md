# Contract — adversarial (the bound a HELD capability must satisfy before it is built)

**Status:** DRAFT. Goes DRAFT→ACTIVE on T-154's first checker PASS. *Amended 2026-10-11: T-154 is no
longer HELD.* The separate approval the 2026-09-27 hold waited for (`docs/plan.md` "Held / blocked":
"hold the adversarial pass for a separate approval; no probe traffic without a fresh decision") was
given: D-081 item 3 (Umesh, chat 2026-10-10, "full approvaal hai"; gate
`qa/gates/d081-run-approvals.md`, `Answered: 2026-10-10 - A`) authorizes the maker to mint the signed
per-run `RunApproval` row for a bounded adversarial pass on the Pathlynks target with the
`PATHLYNKS_USER_*` test account, and says T-154 "is no longer held for a separate approval". That
authorizes the *rows*; each run still writes its own signed row naming target, scope and a probe count,
and AD1-AD3 and AD6 bind every run. The build and the first live pass are therefore unblocked; this
contract no longer sits DRAFT by design, only until T-154's first PASS.
**Covers:** goal tasks T-154 (the bounded adversarial pass — AD1–AD6) and T-155 (its report — AD7's
audit trail feeds it). **Owner:** /checker.
**Source of truth for intent:** **D-018** (`docs/DECISIONS.md`), whose `Changes-authorized` line
names this exact deliverable ("new `qa/contracts/adversarial.md` (checker-owned)"), and **D-017**
(the Track C decision that names `adversarial.py` and rejects Garak/PyRIT/DeepTeam as hard
dependencies). Criteria filed by the maker into `qa/feedback-inbox.md` 2026-09-27 (T-150, Track C
governance) as AD1–AD7; reworded and accepted by the checker on this unit's check (cycle 1) — see
Amendment log.
**Depends on:** `consent.md` (CN1, CN5, CN6, CN7 — the mechanisms this contract requires
`adversarial.py` to actually exercise, not merely resemble), `core-invariants.md` (C7 verification
independence), D-016 (the crawler's write-policy inner-guard-inside-an-outer-boundary precedent, cited
for AD6/AD7 below).

## Purpose

T-154 is, in the plan's own words, the highest-risk unit (since D-081 item 3 no longer held, but
no less bounded): it fires adversarial prompts at a real endpoint, which can cost money, trip a vendor's abuse system, or pollute a production log. D-018
already designs the single control point — a `RunApproval` naming the exact endpoint and a probe
count at or above the planned run, refused otherwise, no exceptions for production. This contract
exists so that bound is written down and checkable **before** anyone builds against it, per this
unit's brief: it narrows what a future T-154 build may do, and records that narrowing now rather
than leaving it to be improvised at build time. Nothing here authorizes sending a probe, building
T-154, or widening any existing approval; no probe was sent and no code was written to produce this
contract (T-150's manifest, cycle 1, confirms both).

## Criteria

### AD1 — Nothing outward-facing starts without a matching approval, and a refused run leaves no trace
**[D-018, mirrors `consent.md` CN1]**
- `adversarial.py` raises `ApprovalRequired` before a probe envelope, a connection to the target, or
  a `projects/<slug>/ai/adversarial/<run_id>/` directory exists.
- **The one permitted write on a refusal is AD7's row.** *(Reconciled 2026-10-11: AD1 said "exactly as
  it found it" and AD7 requires a refusal to be recorded; both cannot hold literally.)* A refused run
  creates no probe envelope, no connection, no `<run_id>/` directory and no capture or evidence file,
  and changes nothing under the project **except** appending one line to
  `projects/<slug>/ai/adversarial/refusals.jsonl` (creating that file and its parent directory if
  absent). "No trace" here means no run artifact and no outward-facing effect; the refusal log is the
  audit trail, not a trace of a run.
- **Verify (once T-154 exists):** mirrors CN1's own verify, applied to this new caller — snapshot the
  project tree, trigger a refusal through every shipped entry point, and assert the tree differs only
  by `ai/adversarial/refusals.jsonl` gaining exactly one line (and, on the first refusal, that file
  and its parent directory existing); no `<run_id>/` directory, no envelope and no connection
  attempt (a stub transport records zero calls).

### AD2 — The approval must name the exact endpoint and a probe count at or above the planned run
**[D-018 verbatim]**
- `adversarial.py` calls `require_approval` with the real target string and the real planned probe
  count — never a placeholder — so CN5 (exact target match) and CN6 (bounds checked, not just
  existence) actually bind this caller, not only the crawl they were built for.
- **Verify (once T-154 exists):** a test plans N probes against an approval granted for N-1 and
  asserts refusal naming the shortfall (`probes N > approved N-1`), reusing CN6's mechanism against
  this caller for the first time; the four CN5 exactness variants (trailing slash, host case, query
  string, and the base target) are each refused as distinct targets, same as CN5 requires elsewhere.

### AD3 — Adversarial against a named production endpoint requires a `production=True` grant
**[D-018 + CN7 verbatim]**
- `ApprovalKind.ADVERSARIAL` requested with `production=True` is refused without a matching
  `production=True` approval — this is `consent.md` CN7's own forward reference to "T-154's surface"
  discharged for real.
- **Verify (once T-154 exists):** CN7's own verify, run against `adversarial.py` rather than left as
  a documented intention; a crawl-kind run must not be silently credited with this criterion (CN7's
  own scope boundary: `production` is inert for `ApprovalKind.CRAWL`).

### AD4 — Probe sets are file-defined; Garak/PyRIT/DeepTeam are never a hard dependency
**[D-017 explicit rejection]**
- Probes live in `prompts/probes/*.md` behind a `ProbeSource` adapter, built only if the native
  probe sets prove too thin (D-017's own condition).
- **Verify (once T-154 exists):** `grep -rniE "garak|pyrit|deepteam" src/ pyproject.toml` returns
  nothing.

### AD5 — The exerciser never grades
**[D-017 "C7 is preserved" + core-invariants C7]**
- `adversarial.py` records capture only (prompt sent, response received, latency, whether the probe
  cap was hit) with no PASS/FAIL/`Verdict` construction; judgement is a separate call through
  `grade.py` — same shape as `ai-target.md` AI6, applied to this caller.
- **Verify (once T-154 exists):** same test shape as AI6, applied to `adversarial.py`.

### AD6 — An absolute probe ceiling exists in code, independent of the approval's own bound
**[maker's addition, accepted]** — not a restatement of D-018's text: D-018 names the approval as
*the* control point and does not ask for a second one. Accepted here as defense-in-depth consistent
with an existing repo precedent rather than as a D-018 derivation: D-016 already runs
`write_policy` as "an INNER guard inside Umesh's outer boundary" for the crawler (the test account's
own permissions are the outer boundary; the deny-list is a second, code-level layer inside it, not a
substitute for the account's own scope). AD6 is that same shape applied one layer further out on the
highest-risk unit in the plan: a code-level ceiling that holds even if an approval is granted more
generously than intended, exactly the failure `consent.md` CN3 already documents as *reachable*
("a row widened 12 → 9999 actions... was accepted"). It narrows what T-154 may do; it authorizes
nothing and does not require Umesh's decision to write down as a bound.
- The runner refuses to start if the planned probe count exceeds a hardcoded ceiling in code, even
  when the approval itself would permit more.
- **Verify (once T-154 exists):** an approval granting probes above the ceiling is still refused by
  the ceiling, with the ceiling's value named in the refusal.

### AD7 — A refused attempt leaves an audit trail, not silence
**[maker's addition, accepted]** — D-018's text stops at "the runner sends nothing and exits
non-zero" and says nothing about a durable record. Accepted for the same reason as AD6 (D-016
precedent, narrows rather than widens) and because T-155 (the report) needs a record of refused
attempts to be a unified report rather than a report that is silent about what was blocked.
- A refused adversarial run appends one line to a local, non-secret log (e.g.
  `projects/<slug>/ai/adversarial/refusals.jsonl`) naming target, timestamp, requested probe count,
  and denial reason. The log row must never carry probe content — it records that a request was
  refused, not what the request said (same secrets discipline as C5).
- **Verify (once T-154 exists):** trigger a refusal, assert the log row exists with those fields and
  no probe-body content.

## Explicit no-fire list (do not raise these as findings)

- Building T-154 or T-155 themselves.
- Sending any probe, including a single one, against a live target — forbidden to a *checker* and to
  every unit's own tests (mock-seeded only). The one live bounded pass is the maker's run under its own
  signed `RunApproval` row, authorized by D-081 item 3 and bound by AD1-AD3 and AD6; nothing in this
  contract is itself that authorization.
- Choosing the concrete `AiCheckKind`→probe mapping (T-152/T-153's job, `ai-target.md`).
- Revocation of an adversarial approval (expiry only, same as `consent.md`).
- A UI grant form for adversarial approvals.
- `docs/spec.md` R30 covering only T-150–T-153 and not naming T-154/T-155. This is a **known,
  disclosed gap** (see Amendment log) — AD1–AD7 rest on D-018's own explicit authorization, which is
  independent of the spec's requirements table and does not need a requirement row to be valid
  authority for this contract.

## Amendment log (append-only; git history is the version)

- 2026-09-27 · START · contract created by /checker from `qa/feedback-inbox.md` 2026-09-27 (maker,
  T-150, Track C governance) · AD1–AD5 folded verbatim in substance from the maker's filing (each
  already a direct restatement of D-018 or D-017, or a direct mirror of an existing `consent.md`
  criterion) · **AD6 and AD7 accepted as filed**, tagged `[maker's addition, accepted]` rather than
  `[D-018]`: judged as legitimate defense-in-depth under the D-016 write-policy precedent (an inner
  guard inside an outer boundary is already this repo's pattern, not a novel one), and as narrowing
  rather than widening what a HELD capability may do — accepting a criterion that only makes a
  future build stricter does not require Umesh's decision the way authorizing the build itself would;
  no gate file opened for this reason · **known gap recorded, not closed**: `docs/spec.md` R30 covers
  only T-150–T-153; T-154/T-155 have no requirement row. Not treated as blocking this contract's
  validity (D-018's own `Changes-authorized` line is independent authority), but filed as
  **ISS-t150-1** (low) recommending a requirement row be added to spec.md when T-154 is unblocked ·
  direction approved by Umesh via **D-018** and plan §5A; the checker authored the wording — the
  maker never writes a contract.

- 2026-10-11 · owner-authorized (header) + routine (AD1/AD7 reconciliation) · **Header, Purpose and one
  no-fire bullet corrected; AD1 and AD7 reconciled.** (1) The header said T-154 cannot begin without a
  separate Umesh approval. D-081 item 3 (Umesh, 2026-10-10, "full approvaal hai"), recorded in
  `qa/gates/d081-run-approvals.md` (`Answered: 2026-10-10 - A`), grants it and supersedes the
  2026-09-27 plan hold; the header now says so and keeps the status DRAFT only until T-154's first
  checker PASS. The no-fire bullet forbidding any live probe now distinguishes a checker/unit test
  (forbidden) from the maker's one run under its own signed row (authorized by D-081 item 3, bound by
  AD1-AD3 and AD6). No bound was loosened: the approval still has to name the exact endpoint and a probe
  count at or above the plan (AD2), production needs `production=True` (AD3), the ceiling holds (AD6).
  (2) AD1 ("a refused run leaves the project directory exactly as it found it") and AD7 ("a refusal is
  written to refusals.jsonl") contradicted each other. D-018's text, the only decision on the subject,
  says "the runner sends nothing and exits non-zero" and says nothing about a record, so it supports
  neither reading against the other; both criteria were accepted at creation (AD7 for T-155's unified
  report, `qa/briefs/t155-ai-report.md` P5). Reconciled in the way that keeps both: AD1 is scoped to run
  artifacts and outward-facing effects, and AD7's one row is the single allowed write. The alternative
  (no write on refusal, drop AD7 and T-155 P5) is a product choice for Umesh; it is not taken here.
  **Links:** D-017; D-018; D-081; AD1; AD7; `qa/gates/d081-run-approvals.md`.
