# Contract — living project map + feature ledger

**Covers:** goal task T-005. **Owner:** /checker.
**Source of truth for intent:** grill capture `.work/grill-living-ledger.md` (2026-09-03, 9 Qs, pre-mortem)
and plan §14 — approved by Umesh 2026-09-03. **Depends on:** `core-invariants.md` (all criteria).

## Purpose

One derived snapshot Claude reads at session start for whole-project context, plus a date-wise
feature ledger carrying the *reasoning* for every live / updated / retired event — so tokens go to
the part being worked on, and a re-proposal of something retired is caught and confirmed with the
human instead of silently rebuilt. It is the product's **overview, not a logger**.

## Criteria

### L1 — Derived, never typed (rot defence)
- `docs/MAP.md` (routed, self-describing) carries three generated sections (directory map from module
  docstrings; schema summary from the Pydantic models; `scripts/` inventory from each script's docstring
  or `.ps1` header comment) delimited by markers; `autotester map` regenerates them. `docs/ARCHITECTURE.md`
  keeps a pointer to MAP.md and stays ≤ 150 lines, enforced by the doctor rule `architecture-too-long`
  (C2 cap unchanged).
- `docs/SNAPSHOT.md` is produced only by `autotester snapshot`; it has a "generated — do not edit" header.
- `autotester doctor` **fails** when `docs/MAP.md` or `docs/SNAPSHOT.md` differs from a fresh regeneration.
- **Verify:** `uv run autotester map && uv run autotester snapshot && git diff --exit-code docs/MAP.md docs/SNAPSHOT.md`; then change one module docstring → `uv run autotester doctor` exits non-zero (`stale-generated: docs/MAP.md`) until `map` is re-run; `wc -l docs/ARCHITECTURE.md` ≤ 150.

- **Committed == disk == fresh (added 2026-09-29, from the maker's 2026-09-28 request and AT-697).**
  The check above compares the working file against a fresh regeneration. It must **also** compare
  the **committed** blob against that regeneration, because a working tree can be regenerated to
  clean while the repository every clone receives is stale. Where no committed object exists (a
  pre-first-commit tree), the committed leg is reported as **skipped and named**, never as passed.
  **Verify:** commit a stale `docs/MAP.md`, regenerate it on disk without committing — `autotester
  doctor` exits non-zero naming the committed blob; the same tree with the regeneration committed
  exits 0. Sabotage: remove the committed-blob comparison — the stale-commit fixture goes red.

### L2 — Every change gets a row; the ask is gated by user value (fatigue defence)
- `docs/FEATURES.jsonl` rows validate against `schema/ledger.py::FeatureEvent`
  (`id`, `feature`, `event ∈ {planned, live, updated, retired}`, `date`, `unit`, `verdict_ref`,
  `reason`, `user_value ∈ {high, normal, low}`, `description`, `supersedes?`).
- The only write path is `autotester ledger add` (and the maker close-out that calls it). No hand edits.
- A `retired` row **refuses** an empty reason. A `live`/`updated` row for a `user_value: high`
  feature is written with a **prefilled** reason (goal task note + originating instruction) that the
  maker shows for confirm-or-edit; `normal`/`low` rows auto-stamp `reason: "update"` with no question.
- `user_value` is a default, not a fixture: `autotester ledger weight <feature> high` raises it later
  and triggers the reasoning ask once.
- **Verify:** `uv run pytest tests/test_ledger.py` covers: schema validation, refused empty retire
  reason, auto-`update` for normal, prefilled reason surfaced for high, weight raise → ask flag.

### L3 — Row on PASS
- A goal task closed on a checker PASS whose `user_value` is `high` has a matching `live` or
  `updated` row citing the verdict file. The `/checker sweep` flags a PASSed `high` unit without one.
- **Verify:** `uv run autotester ledger check` exits 0 (every closed `high` task has a row).

### L4 — Relitigation gate, confidence-gated (project principle S4)
- When the maker picks a unit, `autotester ledger relitigation "<unit title + description>"` is run.
  Deterministic match only on feature id / explicit `supersedes`; **every other case** the LLM (via
  `providers.base.Provider`, prompt file `prompts/relitigation_v1.md`) reads the *latest* row per
  retired/superseded feature (descriptions + reasons) and answers `same_behaviour: bool` with a
  one-line justification. A keyword miss is **not** treated as "no match".
- A hit is a `HUMAN_GATE` quoting feature, date, and reason, with choices rebuild-as-is / build
  differently (reason required) / cancel; the answer becomes a new ledger row + DECISIONS entry.
- **Verify:** test with the mock provider: a retired row "OTP via email link" and a new unit
  "2FA handling for login" → gate fires with the retired reason quoted; an unrelated unit → no gate.

### L5 — Lean snapshot, injected (ignored-it defence)
- `docs/SNAPSHOT.md` ≤ 60 lines: product + north star · live features (`high` with reason, `normal`
  one line, overflow rolled up with a count) · updated/retired in last 30 days with reason · next 5
  open goal tasks · last 5 decisions (computed status). No schema summary, no directory map.
- `qa/hooks/mc-sessionstart.ps1` regenerates and **prints** the snapshot and the DECISIONS index
  (all headers, computed status) — injected, not linked.
- **Verify:** `powershell -File qa/hooks/mc-sessionstart.ps1` output contains the snapshot; `wc -l docs/SNAPSHOT.md` ≤ 60.

### L6 — Every doc self-describes; CLAUDE.md is the router
- Each file in `docs/` opens with a 2-line header: **Purpose** and **Open me when**.
- `CLAUDE.md` carries a table "open X when Y" listing every `docs/` file; `autotester doctor` fails
  when a `docs/` file is missing from the router or a routed file does not exist.
- `MEMORY.md` (Claude's memory dir) gets one pointer line to the router, nothing more.
- **Verify:** `uv run autotester doctor` exits 0; remove a doc from the router → doctor fails.

### L7 — History is append-only with authorization (lab protocol)
- `docs/DECISIONS.md` exists (via `/init-lab`), append-only through `scripts/append_decision.ps1`
  (PreToolUse deny on direct Edit/Write); supersession by `Supersedes: D-NNN -- <why>` in the new entry.
- Backfilled: D-000 genesis (Lab Protocol adoption) · D-001 design-first rules · D-002 the
  2026-09-03 stack/target/auth decisions · D-003 `.env` at repo root · D-004 principle S4
  (confidence-gated rules → AI).
- **Verify:** `git log -p docs/DECISIONS.md` shows additions only; a direct Edit is denied by the hook.

### L8 - A ledger id identifies exactly one row, and a repeated one is REPORTED, never merged
- `qa/issues.jsonl` is the canonical issue ledger and is `merge=union`: two loops appending
  concurrently is normal, so a duplicated id is not an anomaly to be prevented by care - it is what
  one shared counter produces under concurrent filing, and this repo carries ten documented pairs
  to prove it.
- **The rule is detection, not prevention, and explicitly not deletion.** A duplicate id must be
  *surfaced* - `uv run autotester doctor` names each duplicated id with both line numbers.
  Pre-existing pairs are history: they are grandfathered by an allow-list that carries the reason,
  or remapped once under a manifest with the old -> new mapping recorded in each row's
  `checker_note`. **A validator is never made green by destroying the rows that made it red.**
- **No id-keyed read may silently collapse a duplicate.** `dict[id] = row` keeps one row per id,
  chosen by file order, so a `verified` row can shadow an `open` one with the same id and the open
  finding disappears from every consumer at once. A reader must return a state the caller cannot
  mistake for a single status. This is **C12(b)** on the ledger surface: absence of uniqueness
  currently reports as cleanliness. Verify by construction - build a ledger with two rows for one
  id and assert the reader does not report one clean status; a test over a unique-id fixture cannot
  catch this, because the duplicate IS the defect.
- **Allocation is separate from detection, and both are required.** A branch that files rows
  reserves an id block first rather than allocating from the shared high-water mark (`qa/QUEUE.md`,
  maker 2026-09-28: renumbering into a range another writer is still advancing cannot converge).
  That rule prevents *new* collisions while every writer reads it; it does nothing about the ones
  already on disk, and it is prose in a queue document rather than a check.
- **Precedent, same codebase:** `ledger/store.py::load_events` already rejects a repeated id in
  `docs/FEATURES.jsonl` - *"rows are history, so a repeated id is a defect, not a merge."* The
  canonical ledger is the one with no such rule. It is the outlier, not the baseline.
- **Verify:** `uv run autotester doctor` reports a violation for a ledger holding two rows with one
  id, and `uv run pytest` covers the two-rows-one-id reader case. **Links:** AT-656.

**L9 — a cited decision id must resolve to an appended entry.** Any `D-NNN` written into
`qa/gates/*.md`, `qa/contracts/*.md`, `qa/manifests/*.md`, `qa/verdicts/*.md` or `docs/*.md` names
an authorization, and a reader cannot tell a real one from an absent one by looking at the
citation. So the citation is checked, not trusted.

- **The failing shape, measured.** `qa/gates/at654-d029-dev-only-vs-production-pathlynks.md` states
  *"`qa/gates/write-policy-tier.md` is closed and `ALLOW_WRITES` stands (D-053, D-056)"* and again
  attributes Umesh's 2026-09-27 direction to *"`qa/gates/pathlynks-user-account-first.md`, D-056"*.
  **D-056 did not exist.** `grep -rhoE '^## D-[0-9]+' docs/DECISIONS.md docs/archive/ | sort -u |
  tail -5` returned D-051..D-055. The decision was taken, announced in prose, and never appended.
- **What it cost, which is the reason this is a criterion and not a lint.** The question D-056 was
  supposed to close came back to the human a third time on 2026-09-28 (*"hum usi conversation ko
  das barah baar repeat kar chuka hoon main"*). The append-only log exists precisely so a decision
  is asked once; a phantom citation defeats that while looking exactly like the thing that serves it.
- **It fails in both directions and the second is worse.** Work may proceed on consent that was
  never recorded, and work may be HELD on consent that was in fact given — which is what happened
  here for a full day, to `T-145` and to the write tier.
- **Why nothing caught it.** `scripts/append_decision.ps1` validates V3 (sequential id, never
  reused) on **write**, so the log itself cannot contain a gap. There is no check on **read**, and
  `autotester doctor` verifies router coverage and generated-section freshness, not cross-references.
  The guard is on the only surface that was never at risk.
- **A foreign id space is not this log's, and must not be resolved against it.** `docs/DECISIONS.md`
  already cites `D-088` twice — `:623` in prose and `:638` as *"**Links:** D-088 (the outage failure
  that prompted this), `D:/ai_os/umesh/decisions/log.md` 2026-09-22"*. That is a real decision in the
  AIOS personal log, a different `D-NNN` id space, and it will never resolve here. **Scope is the
  ENTRY, not the line:** within `docs/DECISIONS.md` an id qualified by a path to another decisions
  log anywhere in the same `## D-NNN` entry is out of scope wherever it appears in that entry — `:623`
  carries no path on its own line and is qualified by `:638`, so a line-scoped rule is still false.
  Out of scope means **not resolved and not reported**, never "reported and ignored".
- **A non-claiming occurrence is declared, not inferred.** Quoting a defective citation as evidence,
  or discussing a known-phantom id, is not an authorization claim — but no check can read that off
  the prose, and the attempt is what made the first draft of this criterion wrong. So such an
  occurrence is declared in an allow-list carrying **the reason**, exactly the discipline L8 applies
  to grandfathered duplicate ids. Per occurrence, with a reason. **Never per file.**
- **No whole-file exemption, and `docs/DECISIONS.md` least of all.** That file is where a phantom
  citation is most consequential, so greening this check by silencing it there is silencing with
  extra steps — the C12 shape in a different costume. This sentence exists because the maker was
  offered exactly that shortcut by its own measurements on 2026-09-28, declined it, and held the
  unit instead; the refusal belongs in the criterion rather than in one session's judgement.
- **Verify:** `uv run autotester doctor` reports a violation naming the file, line and unresolved id
  for a `D-NNN` citation with no matching `## D-NNN` header across `docs/DECISIONS.md` **and**
  `docs/archive/` (an archived entry resolves — archiving is not deletion), excluding the two classes
  above. Header-matching, never substring-matching. Three fixtures, and each is a shape that has
  already occurred in this repo rather than an invented one: (a) this criterion's own sentence
  *"D-056 did not exist"* must not fire it; (b) a cross-log citation qualified only elsewhere in its
  entry must not fire it; (c) the seven real write-policy citations across
  `qa/gates/at654-d029-dev-only-vs-production-pathlynks.md` (:8, :18, :63) and
  `qa/gates/pathlynks-user-account-first.md` (:31, :35, :38, :67) must **all** fire it **while the
  entry they name is unwritten** -- as of 2026-09-28 they name `D-057`, not `D-056` (AT-718).

- **Subject match is not part of this criterion's Verify:** the subject-match obligation is L10, split out under D-060.


**L10 — a citing line's claimed subject must match the cited entry's **What:**.** Split out of L9 under D-060 (2026-09-30) so AT-710 closes against L9's Verify clause. **Status: declarable form adopted under D-062 (2026-10-06); implementation and complete coverage remain unverified.** The text below is L9's former wrong-subject bullet, verbatim.

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
  must cover the complete occurrence set before T-196 closes. Reconcile the actual seven historical
  write-policy examples in the two L9 gate files; retain their wrong-subject fixtures and do not
  restore incorrect ids now replaced by WP-DECISION placeholders. No whole-file exemption.
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
  Independently reviewed real-tree coverage and migration are acceptance evidence in addition to
  fixtures, not inferred from L9's clean result. Named isolated falsifiers must turn each claimed
  acceptance capability red, including swapping to an existing unrelated id, moving a quote into
  Why, and removing coverage enforcement; restore the original bytes afterward. T-196 remains
  critical: active new-feature policy .3 requires tier L and two blind final coordinator checks;
  adopting this form is not implementation approval or either completion verdict.
  **Links:** AT-710; AT-718; ISS-at710-1; D-060; D-062; T-196.


## Out of scope
The UI view of the ledger (T-100); auto-inferring `user_value` from run data (suggestion source
only, later); Google-Sheet sync.

## No-fire list
- Snapshot prose wording; choice of markers; line counts under the caps.
- Absence of retired rows today (nothing has been retired yet).
- The relitigation LLM's judgement quality beyond the mock-provider test.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · routine · L7: backfill list corrected to D-000 genesis/adoption, D-001 design-first, D-002 stack, D-003 root `.env`, D-004 S4 · why: AT-013 (sweep 2aadf21) — the list was off by one against `docs/DECISIONS.md`; tightening only, applied at the T-005 cycle-1 check.
- 2026-09-03 · routine · L1: generated sections live in `docs/MAP.md` (routed sibling), not in `docs/ARCHITECTURE.md`; doctor fails when MAP.md or SNAPSHOT.md differ from regeneration; ARCHITECTURE.md ≤ 150 is doctor-enforced (`architecture-too-long`) · why: AT-019 — the generated sections pushed ARCHITECTURE.md to 200 lines against the C2 cap; relocation keeps every derived-not-typed guarantee and adds enforcement of the cap; the cap itself is untouched. Pre-declared at the T-005 cycle-1 check, folded at cycle 2.
- 2026-09-18 · routine · L1: "two generated sections" corrected to "three" — `docs/MAP.md` gained a
  `scripts` section (`render_map`'s third key) alongside `map`/`schema` · why: AT-520 (checked-PASS
  cycle 1, `qa/verdicts/at520-scripts-mapped-not-invisible.md`) — `scripts/` (including
  `mutation_check.py`, the mutation-proof instrument) was undiscoverable through any routed doc;
  `apply_map`/`check_generated_fresh`/`autotester map` needed no change, confirmed generic over
  `render_map`'s returned dict by the checker independently (zero-diff `doctor.py`, and a scratch-copy
  reproduction proving `check_generated_fresh` reddens on both a new untracked script and an edited
  existing script's docstring). Additive only, no criterion weakened.
- 2026-09-28 - routine (add) - L8 added: a ledger id identifies one row; a repeat is reported, never
  merged, and never fixed by deleting rows. Cause: the maker reserved id blocks (commit 449fd3c9,
  `qa/QUEUE.md:1333`) after finding that renumbering into a range another writer is still advancing
  cannot converge - a correct rule for ALLOCATION that says nothing about DETECTION. Checker
  measurement on master at 6f7846c9: ten duplicate ids, six of them status-divergent, and
  `ledger/checks.py:141-152` `_status_by_id` keeps the last row per id unconditionally, so three
  rows that are `open` on disk read as `verified`/`fixed` to every id-keyed consumer - including
  `check_qa_issue_rows`, the loss-detector written *because* a status silently reverted. Latent, not
  currently firing: `at540-assertion-layer` names all six as bare ids, so `_claims_a_fix` yields an
  empty set and doctor is correctly clean today; the guard is defeated the moment a manifest uses
  the documented parenthetical form. L8 is additive - no existing criterion weakened, and it
  deliberately does NOT require the ten pairs to be removed. **Changes-authorized:**
  qa/contracts/living-ledger.md L8 + Amendment log (this entry). No enforcement-path file touched.
  **Links:** AT-656; AT-645; AT-496; qa/contracts/core-invariants.md C12(b); qa/QUEUE.md.
- 2026-09-28 - routine (add) - L9 added: a `D-NNN` cited in any gate, contract, manifest, verdict
  or doc must resolve to an appended entry, checked by `autotester doctor` across DECISIONS.md and
  docs/archive/. Cause: AT-710 (high) - `qa/gates/at654-d029-dev-only-vs-production-pathlynks.md`
  cited D-056 twice as the entry authorizing Pathlynks `allow_writes`, and the highest id on disk
  was D-055 across live and archive together. Measured consequence, not hypothetical: the write-tier
  question reached Umesh for a third time on 2026-09-28 because the 2026-09-27 answer was recorded
  only in prose. `append_decision.ps1` V3 already makes a gap impossible on WRITE; nothing checked
  on READ, so the guard sat on the one surface that was never at risk. L9 is additive - no existing
  criterion weakened, and it deliberately does NOT require the phantom citation to be edited out of
  the gate file: the gate now carries the correction as history, which is the same discipline L8
  applies to duplicate rows. **Changes-authorized:** qa/contracts/living-ledger.md L9 + Amendment
  log (this entry). No enforcement-path file touched. **Links:** AT-710; AT-711;
  qa/gates/at654-d029-dev-only-vs-production-pathlynks.md; qa/gates/write-policy-tier.md.
- 2026-09-28 - routine (correct + extend) - L9 amended before it was ever enforced: a foreign id space
  is out of scope with ENTRY (not line) granularity; a non-claiming occurrence is declared in an
  allow-list with its reason rather than inferred from prose; no whole-file exemption, and
  `docs/DECISIONS.md` least of all. Cause: the maker implemented L9 against the real repo and found
  the criterion **false as written**, twice, in the authority file itself - `docs/DECISIONS.md:623`
  and `:638` cite `D-088`, a real decision in the AIOS personal log
  (`D:/ai_os/umesh/decisions/log.md`), which is a different `D-NNN` id space and will never resolve
  here. L9 said a cited id "must resolve to an appended entry" and named only DECISIONS.md and
  docs/archive/, so enforcing it verbatim would have filed permanent violations against correct
  citations. It also fired 6 times on quotation and on discussion of the phantom; the exemption the
  first draft named ("a negative statement of absence") was narrower than the shapes L9's own prose
  uses, and that gap was visible only from an implementation - the checker drafted the self-reference
  fixture and still missed 4 of the 6. **The maker was offered the cheap fix (exempt DECISIONS.md)
  by its own measurements and declined it**, holding the unit and asking for an amendment instead;
  that refusal is now written into the criterion so no later session takes the shortcut. The
  implementation also found MORE of the original defect than AT-710 recorded: `D-056` is cited 7
  times across TWO gate files, not twice in one - `at654` (:8, :18, :63) and
  `qa/gates/pathlynks-user-account-first.md` (:31, :35, :38, :67), the second file absent from
  AT-710's description, and `:35` of it rests on the phantom for the `write_policy: read_only`
  claim. Corrective, not weakening: every true violation L9 was written to catch still fires, and
  the fixture list is now three shapes that have occurred here rather than one invented.
  **Changes-authorized:** qa/contracts/living-ledger.md L9 + Amendment log (this entry). No
  enforcement-path file touched. **Links:** AT-710; AT-711; AT-662; qa/feedback-inbox.md 4a1b51f9;
  docs/DECISIONS.md:623,638.

- 2026-09-28 - CORRECTION (narrow, self-inflicted) - L9 fixture (c) amended and one bullet added,
  because this seat invalidated the fixture by its own append. Appending D-056 as the at673
  round-cap waiver (authorized by Umesh's option-B answer; `append_decision.ps1` V3 forces
  max(existing)+1, so the id was not a free choice once the append ran) turned the seven phantom
  write-policy citations from DANGLING into RESOLVING-BUT-WRONG. The avoidable error was ORDERING,
  not the id: the write-policy entry should have been written first. Fixture (c) now names D-057
  and is conditioned on the cited entry being unwritten, and L9 gains an explicit rule that
  resolution alone is not cleanliness -- a citation stating what an entry authorizes is compared
  against that entry's **What:**. Strengthening, not weakening: every violation L9 was written to
  catch still fires, and one class it would have silently stopped catching now fires too.
  **Changes-authorized:** qa/contracts/living-ledger.md L9 Verify + one L9 bullet + Amendment log
  (this entry). No enforcement-path file touched. **Links:** AT-718; AT-710; AT-711; D-056.

- 2026-09-29 - routine (tighten) - L1 gains the "committed == disk == fresh regeneration" leg and the
  pre-first-commit rule. Cause: the maker's 2026-09-28 request (`qa/feedback-inbox.md`, "L1 ... is
  declared in no contract") asked that L1 be stated somewhere a check can be judged against. It
  **was** — here, in L1 — but only in the disk-vs-fresh form, which is exactly the narrowness AT-697
  measured in `doctor.py::check_generated_fresh` (it never reads the committed blob). The maker's
  grep looked in `core-invariants.md`, not this file, so the request was half right: the criterion
  existed and was too weak. Tightening, not weakening: every violation L1 caught still fires.
  **Changes-authorized:** qa/contracts/living-ledger.md L1 + Amendment log (this entry). No
  enforcement-path file touched. **Links:** AT-697; qa/feedback-inbox.md 2026-09-28 tick 33r.

- 2026-09-29 - routine (tighten) - L9 fixture (c) must not hard-code an UNWRITTEN decision id. Cause:
  AT-740. Fixture (c) named `D-057` as the not-yet-written write-policy entry (the AT-718 fix); on
  2026-09-29 `D-057` was appended for an unrelated subject (`ade87168`), so the seven citations went
  from dangling to resolving-but-wrong a second time, and the fixture's stated precondition ("the entry
  they name is unwritten") is now false. The fixture is to be built so its precondition is asserted at
  run time (the cited id is absent, or present with a non-matching **What:**), never assumed from a
  date. With `D-057` now real and off-subject, all seven citations are the L9 wrong-subject case
  as it stands. Additive; no clause weakened. **Changes-authorized:** qa/contracts/living-ledger.md
  Amendment log (this entry). No enforcement-path file touched. **Links:** AT-740; AT-718; AT-710; D-057.
- 2026-09-30 - amend (split) - L9's wrong-subject bullet moved verbatim into new criterion L10 ("a citing line's claimed subject must match the cited entry's **What:**"), status not yet buildable (needs a declarable form for the claim; own unit); L9 keeps a one-line pointer and its Verify clause no longer has to cover the moved bullet, no other L9 sub-clause touched. Cause: at710 cycle 1 FAIL, ISS-at710-1 (verdict b385910f) - resolver yields 0 dangling citations and 9/9 capability rows reproduce; the bullet compares a citation's claim to the entry's What:, no machine-readable declared form exists, and the alternative (a `cites-for: D-NNN` keyword-overlap matcher) has an unmeasured false-positive rate. Obligation preserved in L10, weakened nowhere. **Changes-authorized:** D-060 (qa/contracts/living-ledger.md L9/L10 + Amendment log). No enforcement-path file touched. **Links:** AT-710; ISS-at710-1; b385910f; D-057; D-058; D-059; T-168.
- 2026-10-06 - routine (tighten) - L10 declarable form adopted: bounded visible What quotation and
  strict agreeing JSON marker, mandatory independently reviewed occurrence coverage and migration,
  attributable immutable-history reviews, archive full-body comparison and fail-closed negative
  oracles. Cause: independent contract review rejected optional markers beside unrestricted claims
  as vacuous narrower success; Umesh approved T-196 and D-062 authorizes this checker-owned adoption.
  L9 and all earlier invariants preserved. Implementation, real-tree coverage and dual final checks
  remain unverified; no product PASS. **Changes-authorized:** D-062 (L10 + this amendment only).
  **Links:** T-196; D-060; D-062; qa/feedback-inbox.md 2026-10-06 coverage challenge.
