# Build brief — t196-citation-subject-check (T-196, criticality critical)

Prepared 2026-10-10 by a read-only readiness pass. Nothing was built, run or committed. Facts marked `unknown` are not in the repo; do not guess them. Re-read `git -C D:/autoTesting rev-parse master` at dispatch.

**Dispatchable: YES, for the CODE slice only.** Criterion L10 exists (`qa/contracts/living-ledger.md` on branch `wave/t196-citation-subjects`, text below; master's copy lacks the 2026-10-07 sealed-record amendment). The unit can NOT reach `ready-for-check` or PASS from a builder alone: a checker-owned track must run in parallel (section 10). No owner decision is open on disk (section 8).

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- **Tier: L.** Triggers: config/CI (`src/autotester/doctor.py::run` is the adapter's slot-3 verification gate, `qa/adapter.json` `verify.commands` `uv run autotester doctor`, and this unit wires a new check and a blocking/non-blocking split into it); data migration (current mutable authorization claims in contracts, gates and docs are rewritten to the canonical form). The goal criticality is `critical`.
- Tooling path touched: `src/autotester/ledger/citations.py` and `src/autotester/doctor.py` READ `docs/DECISIONS.md`, `docs/archive/*.md` and the five citation globs. They never write them. `docs/DECISIONS.md` stays append-only through `scripts/append_decision.ps1` (not touched). No enforcement-path file (`.claude/hooks/*`, `scripts/append_decision.ps1`, `.claude/settings.json`, `qa/hooks/*`) is touched, so no `Approved-by` entry is needed for the code slice.
- **Dual check: no** (policy .9 requires a real `security|auth|tenancy|prod-write <path:line>` trigger and this unit has none: no auth, no credentials, no production write). **Flag for the orchestrator:** the L10 text (last paragraph of its Verify, below) was written under policy .3 and still says "tier L and two blind final coordinator checks". That is a checker-owned contract line; the checker decides at close-out whether .9 supersedes it.

## 2. Root and base

- Root `D:/autoTesting`. Base = `master` @ `4f8f5da100931ebda1b26836304bfbd38460764b` (at preparation time).
- **Branch: CONTINUE the existing `wave/t196-citation-subjects`** (tip `6367f1c2`), not a fresh branch. Reason: it is 5 commits ahead of master and 43 behind. It carries `a6f9a3dd` (the scanner, strict models and tests, doctor wiring held back) and the checker's `2749e38d` (the L10 sealed-record amendment authorized by D-066), neither of which is on master. `git merge-tree --write-tree master wave/t196-citation-subjects` returns a tree with no conflict lines, so merging master in is clean; merge master in first.
- **Its worktree `D:/autoTesting/.worktrees/t196-citation-subjects` is dirty** with the real remaining build, uncommitted (files last modified 2026-10-07 21:10-21:25, no owner process found): modified `src/autotester/cli.py`, `doctor.py`, `ledger/citations.py`, `schema/ledger.py`, `docs/MAP.md`, `docs/SNAPSHOT.md`; untracked `src/autotester/ledger/review_block.py` (87 lines), `ledger/seals.py` (155), `tests/seal_fixtures.py` (63), `tests/test_citation_known_disputed.py` (108), `tests/test_citation_seals.py` (178). `qa/QUEUE.md` calls the worktrees INPUT only. Procedure: the orchestrator confirms nobody is writing in that worktree; if so the builder continues there, re-runs the tests below, and commits in reviewable slices. If not confirmed, the builder makes a new worktree off the branch tip and copies the diff and the five untracked files in as INPUT, re-proving each. Never stash, reset or checkout over the uncommitted files.

## 3. Acceptance criteria (verbatim: `qa/contracts/living-ledger.md` L10, as on `wave/t196-citation-subjects`)

Contract-level facts: criterion id L10 (split out of L9 by D-060; L9 must be preserved and not weakened). The goal `done_check` is `uv run pytest tests/test_citations.py` (exit 0). Core invariants C2 (file and function caps), C7 and C12 apply (the manifest cites them). K1 and K2 below are named in the L10 text.

**L10 — a citing line's claimed subject must match the cited entry's **What:**.** Split out of L9 under D-060 (2026-09-30) so AT-710 closes against L9's Verify clause. **Status: declarable form adopted under D-062 (2026-10-06); sealed-record disposition added 2026-10-07 under the answered gate `qa/gates/t196-l10-coverage.md` (B); implementation and complete coverage remain unverified.** The text below is L9's former wrong-subject bullet, verbatim.

> **Resolution is necessary and not sufficient -- the SUBJECT must match too (added 2026-09-28,
>   AT-718).** Fixture (c) was written naming `D-056`, and on 2026-09-28 this seat appended a real
>   `D-056` on an unrelated subject (the at673 round-cap waiver). Every one of those seven citations
>   instantly began to RESOLVE while still being wrong, and a check that only asks "does `## D-NNN`
>   exist" would have gone green on all seven in the same stroke -- reporting the defect as fixed at
>   the exact moment it got harder to see. So the check may not treat a resolving id as clean on its
>   own: where a citation states what the entry authorizes, that claim is compared against the entry's
>   own **What:** field, and a mismatch is a violation in its own right. This is the C12 shape once
>   more -- a green that the construction, not the code, produced. **Links:** AT-710; AT-711; AT-718.

- **Canonical visible claim, not an optional annotation.** A mutable authorization claim uses
  `Decision claim D-001: "Exact quotation from What" <!-- decision-claim: {"id":"D-001","what":"Exact quotation from What"} -->`.
  The complete claim occupies one line, with optional surrounding whitespace only. The visible
  quotation is a JSON string literal (including escapes for embedded quotation marks); the marker
  contains exactly one strict JSON object with exactly the string fields `id` and `what`. Decode
  both strings and require agreement after whitespace normalization. The visible id and marker id
  must agree and match L9's citation syntax. Empty/whitespace-only quotations, duplicate JSON keys,
  extra fields, duplicate/conflicting markers, detached markers, malformed declarations and extra
  authorization prose on a canonical line are declaration violations. A marker cannot manufacture
  its own prose citation: exclude its contents from occurrence enumeration, retaining the visible id.
  A marker in a quoted example is not a live claim only when its occurrence has an independently
  reviewed nonclaiming classification; examples never provide a whole-file exemption.
- **Comparison boundary.** Collapse whitespace runs to one space and trim, with no other
  normalization. The decoded claim must be a nonempty case-sensitive contiguous quotation from
  that id's full entry's `**What:**` field. A What field ends at the next standalone top-level
  `**Field:**` line or decision-entry boundary; nested/list formatting remains content. Inline
  content after `**What:**` is included. A quote in Why, Result, another entry or an index summary
  is not evidence. Missing/duplicate What fields or multiple full bodies for one id are unavailable
  or ambiguous subjects and must report a violation, never select a convenient body. A partial
  quotation proves textual attribution only, not that an operational action is authorized; coverage
  review must reject a quotation selected to conceal a conflicting surrounding claim. No fuzzy
  keyword, paraphrase, semantic model or hash-only comparison may replace this check.
- **Archives and exemptions.** Full entries in `docs/DECISIONS.md` and `docs/archive/*.md` supply
  What. An archive INDEX row can resolve L9 existence but cannot supply L10's subject; index-only
  attribution reports subject unavailable. Preserve both L9 exemptions before local resolution or
  comparison: entry-scoped foreign ids stay out of scope even if the numeric id exists locally;
  reasoned nonclaiming exemptions stay per occurrence. L9 still checks ordinary local references.
- **Coverage is mandatory, independently reviewed, and current.** Enumerate every visible citation
  occurrence across L9's five globs, including structural headers and repeated occurrences. Bind
  the reviewed inventory to relative path, exact line text, cited id, ordinal among that line's
  same-id occurrences, and multiplicity of identical lines. An inventory row declares a kind
  (structural header, ordinary reference, authorization claim, foreign entry, or nonclaiming), a
  nonempty reason, reviewer attribution and a durable review reference. No automated prose inference
  classifies claims. Missing, stale, ambiguous or duplicate/conflicting inventory rows report coverage
  violations; changed text or added multiplicity invalidates review. An empty inventory cannot pass
  a tree containing citations. Classifications are review evidence, not an arbitrary allow-list:
  the checker independently challenges ordinary-reference/nonclaiming reasons against the actual
  claim, and a maker's classification alone does not establish complete coverage.
- **Migration and immutable history.** Every mutable current authorization claim must migrate to
  the canonical visible form; unrestricted surrounding authorization prose remains an uncovered
  claim even beside a valid marker. Immutable decision history is not rewritten: an attributable
  occurrence-specific historical review records the claimed quotation and checks it against What;
  unknown/disputed attribution remains reported. A historical review cannot silently reclassify a
  wrong authorization as nonclaiming. Inventory plus canonical declarations and historical reviews
  must cover the complete occurrence set before T-196 closes; a valid sealed record (next bullet)
  counts as a historical review for exactly the occurrences it covers. Reconcile the actual seven
  historical write-policy examples in the two L9 gate files; retain their wrong-subject fixtures and
  do not restore incorrect ids now replaced by WP-DECISION placeholders. No whole-file exemption
  except a sealed record as defined next, which is a reviewed, hash-bound, self-invalidating row and
  not an exemption.
- **Sealed-record disposition (immutable history; added 2026-10-07, gate
  `qa/gates/t196-l10-coverage.md` Answered B, Umesh).** Rationale he gave: logic and the product
  evolve; keep the good part of what was done and update it later. It lets one reviewed row cover
  the citation occurrences of a closed historical record instead of one row per occurrence. It
  lowers review volume only; it never lowers what counts as a violation.
  - **Sealed historical unit, precisely.** Only these can be sealed: (a) a whole file under
    `qa/manifests/` or `qa/verdicts/` whose manifest `Status:` is terminal (`checked-PASS`,
    `merged-no-check (docs-lane)`, `merged-no-check (test-lane)` or `STALLED`; a verdict is closed
    when its same-slug manifest is), or (b) one full decision entry (the `## D-NNN` header line up
    to, not including, the next `## D-` header line) in `docs/DECISIONS.md` or `docs/archive/*.md`.
    Contracts, gates, `qa/feedback-inbox.md`, SNAPSHOT/MAP and every other file are living or
    appended-to records and can never be sealed.
  - **Sealed row.** One inventory row of kind `sealed-record` with: `path`; `scope` (`file` or
    `entry:D-NNN`); `sha256` of the unit's bytes with CRLF normalized to LF; `baseline` (a commit
    sha); a nonempty `reason` stating why the unit is closed history; `reviewer` attribution (the
    /checker or Umesh; a build or maker agent's own seal does not count, same independence as the
    coverage bullet); and a durable `review_ref`. `reason` and `reviewer` are never generated or
    defaulted by the code that enforces this criterion.
  - **Doctor re-derives, never trusts the row.** It recomputes the hash from the working tree and
    requires `baseline` to be an ancestor of HEAD, `git show <baseline>:<path>` (or the entry slice
    of it) to hash to the recorded value, and the unit to be eligible above. A seal covers the L10
    coverage obligation for every citation occurrence inside the unit, each still enumerated and
    counted in a separate `sealed` total in the doctor output. A per-occurrence inventory row for an
    occurrence in a sealed unit stays valid and keeps its own classification; the seal fills only
    occurrences with no row and never reclassifies one.
  - **Any change invalidates the seal.** A hash mismatch (any byte, including an appended line), a
    deleted or renamed unit, an ineligible path, a missing baseline or a missing or duplicate or
    conflicting sealed row for the same unit reports a coverage violation, and every occurrence in
    the unit is unreviewed until an independent re-review records a new row. New occurrences, changed
    occurrences and occurrences in any unsealed file fail exactly as before.
  - **No inference, no subject pass.** Doctor never chooses what to seal, never infers a subject
    and never reads a seal as evidence that any claim is true or authorized. A sealed occurrence is
    covered, not classified clean: nothing may cite sealed text as authority.
  - **Known-disputed historical claims: open item pending Umesh's ruling; the seal does NOT resolve
    them.** Two early claims in `docs/DECISIONS.md` cannot truthfully satisfy the What-only
    boundary while unchanged. The gate answer B did not rule on them. (K1) The D-006 body at
    `docs/DECISIONS.md:80` says the UTF-8 change to `scripts/append_decision.ps1` was "authorized
    by D-000 `Changes-authorized`"; D-000's What adopts the Lab Protocol generally and does not
    name the appender or UTF-8 scope, so the claim leans on D-000's Changes-authorized field, not
    its What. (K2) The D-014 body at `docs/DECISIONS.md:209`, first `D-005` occurrence (ordinal 1;
    the second same-line occurrence is a separate, honestly quoted row), says it discharges D-005
    items with `Action` += BACK, HOVER, PRESS_KEY, SCROLL; D-005's What lists HOVER, PRESS_KEY and
    SCROLL but not BACK, so BACK is attributed to a decision that did not name it. Until Umesh
    rules, doctor lists K1 and K2 by path, id, ordinal and exact line text as
    `decision-citation-known-disputed`, counted, **non-blocking** (they alone do not make doctor
    exit nonzero); a seal can never cover them; and a qa/issues.jsonl row (feature living-ledger,
    severity low) tracks them open until the ruling is recorded here as an amendment. Any change
    to either line's text, or any third disputed occurrence, is blocking, and T-196 cannot receive a
    final PASS while this item is open.
- **Verify:** `uv run pytest tests/test_citations.py` and `uv run autotester doctor` must evidence
  the following with file/line/id diagnostics: absent id gives L9 dangling (also with an empty log);
  present unrelated What gives subject mismatch; exact matching canonical claim is clean; matching
  archived full entry is clean; index-only subject is unavailable; quote only outside What fails;
  whitespace variation is clean but changed case/punctuation/content fails; missing/duplicate What
  or duplicate full bodies fails closed; malformed/detached/conflicting markers or visible/JSON
  disagreement fails; existing foreign-entry and per-occurrence nonclaiming exemptions remain clean
  while neighboring unexempted claims fail. Coverage fixtures must fail on an added unclassified
  resolving authorization claim, changed reviewed text, increased identical-line multiplicity,
  conflicting classifications and a valid irrelevant quote beside a wrong unrestricted claim.
  Sealed-record fixtures must show: an unchanged eligible sealed unit is clean and counted under
  `sealed`; a one-byte edit, an appended line, a rename and a deletion each fail; a wrong hash, a
  baseline that is not an ancestor or whose content hashes differently, a missing reason or
  reviewer, a maker-attributed seal, a duplicate or conflicting seal, and a seal on a contract,
  gate, inbox or SNAPSHOT path each fail; a new citation in an unsealed file fails; a seal beside a
  per-occurrence row does not reclassify it; K1 and K2 are listed `known-disputed` and
  non-blocking, a seal naming them is rejected, and editing either line or adding a third disputed
  occurrence turns doctor red. Independently reviewed real-tree coverage and migration are acceptance evidence in addition to
  fixtures, not inferred from L9's clean result. Named isolated falsifiers must turn each claimed
  acceptance capability red, including swapping to an existing unrelated id, moving a quote into
  Why, removing coverage enforcement, and removing the seal hash comparison; restore the original bytes afterward. T-196 remains
  critical: active new-feature policy .3 requires tier L and two blind final coordinator checks;
  adopting this form is not implementation approval or either completion verdict.
  **Links:** AT-710; AT-718; ISS-at710-1; D-060; D-062; T-196.


Note on the K1/K2 paragraph above: it says the two disputed claims are an open item pending Umesh's ruling. The ruling has since been given and recorded (section 8: gate `Answered (disputed claims K1/K2)`, D-068, D-069), but the contract paragraph has not been amended to record it. That amendment is checker-owned. Until it lands, build to the paragraph as written (list K1 and K2 as `decision-citation-known-disputed`, non-blocking, never sealable, any change or a third disputed occurrence blocking).

## 4. What exists and what is missing

Committed on the branch tip (from `git show`, nothing re-run by this pass): `src/autotester/ledger/citations.py` (295 lines at tip) holds the scanner `check_citation_subjects`; `src/autotester/schema/ledger.py` (125 at tip, 61 on master) the strict claim and review models; `tests/test_citations.py` (300 at tip, 111 on master). The manifest (branch copy, 2026-10-07) records: ruff clean; `tests/test_citations.py` `2 failed, 59 passed in 10.18s` where the two failures are expected on the branch (a dangling-D-entry test needing decision entries that were uncommitted at the time, and the doctor-wiring test); `tests/test_schema.py tests/test_ledger.py tests/test_ledger_checks.py tests/test_doctor.py` `104 passed`. Doctor wiring is deliberately held back: wired, it exits 1 with 1599 violations (1213 `decision-citation-coverage`, 385 `decision-citation-declaration`; per `qa/gates/t196-l10-coverage.md`), because only 877 occurrences have an independently reviewed inventory row (CURRENT block in `qa/feedback-inbox.md`) out of about 2,100.

In the dirty worktree (uncommitted, unverified): `ledger/seals.py` (the sealed-record check: re-derive the hash, ancestor baseline, eligibility, any change invalidates), `ledger/review_block.py`, `citations.py` slimmed to 271 lines, 35 more lines in `schema/ledger.py`, `doctor.py` gaining `NON_BLOCKING = frozenset({"decision-citation-sealed", "decision-citation-known-disputed"})` and `blocking()` plus the wiring of `check_citation_subjects` into `run()`, `cli.py` `doctor` command exiting on `blocking()` only, and three new test files for seals and the known-disputed pair.

Gap to L10 (code slice, the builder's):
- Prove the committed scanner against every item in L10's Verify list with the files in section 6, on the merged-with-master tree.
- Sealed-record disposition: `seals.py` must hit every Verify fixture (unchanged unit clean and counted under `sealed`; one-byte edit, appended line, rename, deletion fail; wrong hash, non-ancestor or mis-hashing baseline, missing reason or reviewer, maker-attributed seal, duplicate or conflicting seal, seal on a contract/gate/inbox/SNAPSHOT path fail; new citation in an unsealed file fails; a seal never reclassifies a per-occurrence row).
- K1 and K2 listed `known-disputed`, non-blocking, never sealable; editing either line or adding a third turns doctor red.
- Named isolated falsifiers (swap to an unrelated id, quote moved into Why, coverage enforcement removed, seal hash comparison removed), each green, red-for-the-named-reason, restored.
- `tests/test_citations.py` is at 300/300 and `citations.py` at 295/300 at the tip: keep splitting into the existing new modules rather than growing them.

Gap that is NOT the builder's (checker/independent track, section 10): the real-tree inventory and seal rows (rows need reviewer `/checker` or Umesh, a build agent's own seal does not count), canonical migration of current mutable authorization claims in `qa/contracts/*.md` (checker-owned) and gates/docs, recording the K1/K2 ruling in the contract, and the real-tree `autotester doctor` going green.

## 5. Files the builder will touch

Existing, edit in place (line counts at the branch tip; master where noted):
- `src/autotester/ledger/citations.py` (295 tip; 271 in the dirty tree)
- `src/autotester/schema/ledger.py` (125 tip)
- `src/autotester/doctor.py` (280; the dirty tree adds `NON_BLOCKING` and `blocking()` and the wiring)
- `src/autotester/cli.py` (295; doctor command exit logic; stays under 300 only if the dirty change is net +2 or less)
- `tests/test_citations.py` (300 tip: at the cap)

New (uncommitted, already in the dirty tree; each is justified by the 300-line cap under C3; `qa/manifests/t196-citation-subject-check.md` said "no new product/test module", so the orchestrator should confirm or have the checker accept them):
- `src/autotester/ledger/seals.py` (155)
- `src/autotester/ledger/review_block.py` (87)
- `tests/seal_fixtures.py` (63)
- `tests/test_citation_seals.py` (178)
- `tests/test_citation_known_disputed.py` (108)

Regenerated, not hand-edited: `docs/MAP.md`, `docs/SNAPSHOT.md` (`uv run autotester map`).
Not the builder's: `qa/contracts/*` (checker only), `docs/DECISIONS.md` and `docs/archive/*` (immutable, append through the script only), `qa/gates/*`, `qa/issues.jsonl` (checker), `.goal/goal.json`, `qa/QUEUE.md`, `docs/ARCHITECTURE.md`. `src/autotester/schema/enums.py:26` docstring (D-069: BACK attributed to D-014) rides "the next unit touching that file"; not this unit.
Count: 5 existing product/test + 5 new = 10 (plus 2 generated).

## 6. Test scope

Bare `uv run --offline pytest --noconftest -p no:cacheprovider <file>` with the manifest's synthetic env (`PYTEST_CURRENT_TEST=governance-tests`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `AUTOTESTER_APPROVAL_KEY=synthetic-governance-key`), no CLI `-q`:
- `tests/test_citations.py` (done_check)
- `tests/test_citation_seals.py`
- `tests/test_citation_known_disputed.py`
- affected consumers: `tests/test_doctor.py`, `tests/test_ledger_checks.py`, `tests/test_ledger.py`, `tests/test_schema.py`, `tests/test_product_map.py`
- end gates: `uv run ruff check src tests scripts`, then `uv run autotester doctor` run on a CONTROLLED fixture tree by the tests; on the real tree the doctor result is expected to stay red until the checker track lands, and that is not the builder's failure.
The full suite is not the builder's job. Whole-repo RAM headroom is `unknown` (the manifest measured about 2.14 GiB and says the 4 GiB acceptance headroom is not met; do not run heavy parallel jobs).

## 7. Reachable test cases

Happy path first, then the failures L10 lists:
- an exact canonical claim `Decision claim D-001: "<exact What quote>" <!-- decision-claim: {...} -->` is clean; whitespace variation is clean; an archived full entry is clean;
- a present unrelated What gives a subject mismatch; a quote that appears only in Why fails; changed case, punctuation or content fails; an index-only archive row reports subject unavailable;
- missing or duplicate What, or duplicate full bodies for one id, fails closed; malformed, detached, conflicting markers and visible/JSON disagreement fail; foreign-entry and reasoned nonclaiming exemptions stay clean beside neighbouring unexempted claims that fail;
- coverage: an added unclassified resolving authorization claim fails; changed reviewed text fails; increased identical-line multiplicity fails; conflicting classifications fail; a valid irrelevant quote beside a wrong unrestricted claim fails; an empty inventory over a tree with citations fails;
- sealed records and K1/K2: every fixture in section 4;
- doctor caller: removing the `check_citation_subjects` wiring turns the controlled-tree test red.

## 8. Gate answers

Owner choices: **none open on disk.** The three that were open are answered.

- `qa/gates/t196-l10-coverage.md`, `Answered: 2026-10-07T01:34:13Z — B — chat (Umesh): "logic badalte rehte hai, product evolve hota hai, purane ka acha part rakh kar later update kar sakte hai". Ruling on the 2 disputed historical claims still to be shown to Umesh.` (option B: a sealed-record disposition for immutable history.) Recorded as D-066.
- same file, `Answered (disputed claims K1/K2): 2026-10-07T03:17:22Z — i, after a second independent confirmation — chat (Umesh): "2nd confirmation le loo aur sabhi update krr doo … remove/delete if needed krr skte hai". Recorded as D-068.` D-069 then records the correction: both K1 and K2 changes stand as authorized, the attribution is corrected by a correcting entry, old entries untouched.
- `docs/DECISIONS.md` D-062 (declarable form), D-066 (authorizes the L10 sealed-record amendment as committed in `2749e38d`), D-068 point 2, D-069 (K1/K2 disposition; "T-196 may treat ISS-t196-citation-subjects-k1k2 as resolvable once /checker records the disposition"). All `Approved-by: Umesh`.
- Open items that look owner-held but are not: the goal note ("Owner reconciliation choice requested once") and the master copy of the manifest are stale (written 2026-10-06, before the answers). Two critical notifications are still unacknowledged in `.goal/goal.json`: T-195 (2026-09-27T07:47:03, "T-195 is CRITICAL — human required", T-195 is itself `done`) and T-196 (2026-09-30T18:34:35, same text). Acknowledging them is a human act.

## 9. UI surface and persona walk

`Persona walk: skip (CLI-only developer/operator tool, `autotester doctor` output; no screen, route or component; docs/plan.md:59 lists it as "skip (governance)")`.

## 10. Dependencies and conflicts

- Must land first: none by dependency (`deps: []`).
- **Checker-owned track that must run in parallel and finish before `ready-for-check`:** (1) record the K1/K2 ruling in L10 as an amendment (the contract paragraph still calls it pending); (2) reconcile L10's ".3 two blind checkers" line with policy .9; (3) independent review and seal rows for the roughly 1,200 unreviewed occurrences in closed manifests, verdicts and full decision entries (reviewer must be `/checker` or Umesh), and independent classification of the rest; (4) canonical migration of mutable authorization claims in contracts (checker-owned) and in gates/docs, each migration plan-approved independently as the earlier at052/t191 ones were; (5) resolve `ISS-t196-citation-subjects-k1k2` in `qa/issues.jsonl`. Any of the 18 unresolved historical claims from the manifest's checkpoint I that the checker finds disputed would need a new Umesh ruling (`unknown` whether there are any).
- Shared files (one owner each):
  - `src/autotester/doctor.py`: this unit (`qa/QUEUE.md`: "doctor.py: this row"). No other pending unit is known to edit it.
  - `src/autotester/cli.py` (295/300): this unit for the `doctor` command only; other units touching `cli.py` are `unknown` (T-174 CLI contract may); one writer at a time.
  - `qa/feedback-inbox.md` (the CURRENT review block, append-only): reviewers append; the builder only appends a fold-in note.
  - `docs/MAP.md`, `docs/SNAPSHOT.md`: generated; last merger regenerates.
  - `qa/contracts/living-ledger.md`: checker only. Master and the branch differ here (the branch has the sealed-record text).
- Disjoint from T-167 and T-179: no shared source file; they share only the generated MAP/SNAPSHOT. T-196 can be built in parallel with T-167 now.

## 11. Budget and process rules

- Check budget (tier L): 45 min. The builder runs no full suite, only the files in section 6.
- Falsification only in a throwaway copy outside the bound tree, then a byte-identical restore. Earlier helper proofs on older hashes (manifest) are intermediate and do not count; redo them on the final identity.
- Kill only PIDs you started. Scratch and evidence go to `.work/`. Edit in place. Do not edit immutable history, contracts or verdicts. Offline only: no model, provider, browser, account or network traffic.
- Manifest `qa/manifests/t196-citation-subject-check.md` stays `BUILDING` until the checker track lands; the builder updates it with exact commands, exit codes and hashes only. Only `/checker` can PASS.
