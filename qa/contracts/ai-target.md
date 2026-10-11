# Contract — ai-target (Track C: discovery, kind, check registry, behavioural capture)

**Status:** ACTIVE (2026-10-11; T-151's first checker PASS is the dual check `qa/verdicts/t151-target-discovery.md`
(coordinator A, cycle 2, `VERDICT: PASS`, commit b18e4ea6) and `qa/verdicts/t151-target-discovery.b.md` (coordinator B,
cycle 3, `VERDICT: PASS`, commit f0282ce5)). AI9-AI14 (T-155, added 2026-10-11) and any criterion with a Landing
note bind a stage that does not exist yet: ACTIVE does not mean those are built. Several criteria bind a stage
that does not exist on disk yet — see each criterion's **Landing note**; that is expected, not a
defect, and mirrors this repo's own precedent (`catalog.md` was authored DRAFT under D-039 before
`stages/catalog.py` existed).
**Covers:** goal tasks T-151 (AI1–AI3, read-only discovery + kind naming), T-152 (AI4, blocked-check
honesty — reusing, not restating, `catalog.md` CT7), T-153 (AI5–AI6, behavioural capture), and AI7
(context-folder reading, applies across T-151–T-153), and **T-155 (AI9–AI14, the unified AI test report;
added 2026-10-11)**. **Owner:** /checker.
**Source of truth for intent:** **D-017** (`docs/DECISIONS.md`), whose `Changes-authorized` line
names this exact deliverable ("new checker-authored contracts `qa/contracts/ai-target.md` and
`qa/contracts/adversarial.md`"). Criteria filed by the maker into `qa/feedback-inbox.md` 2026-09-27
(T-150, Track C governance) as AI1–AI7; reworded, split, renumbered and one criterion folded into a
cross-reference by the checker on this unit's check (cycle 1) — see Amendment log.
**Depends on:** `core-invariants.md` (C5 secrets, C7 verification independence), `catalog.md` (CT7 —
already governs "`stages/ai_catalog.py` or any later Track-C catalog code"; this contract does not
restate it), `consent.md` (pattern precedent for how a checker-owned contract is built from a maker
feedback-inbox entry).

## Purpose

Track C (D-017) gives AutoTester a second target kind: an LLM application reached through an API or
a codebase, discovered and classified without ever letting a model choose its own grading. This
contract is the bound a below-the-UI check must satisfy before the checker can call T-151/T-152/T-153
done: discovery stays deterministic and file-cited, a model may name what it found but a literal
table decides which checks run (and that table must not bend under an adversarial input), the
existing `Catalog`/`BlockedReason` vocabulary is reused rather than forked, the capturer only
observes, every capture is scrubbed before a judge sees it, and a context folder (including an
Obsidian vault) is read as plain structured markdown — no backlink graph, no Dataview, no vault-index
dependency. Like `catalog.md` before T-125 landed, several criteria here are forward-declared: they
describe what the checker will hold the eventual code to, not a property of code that exists today.

## Criteria

### AI1 — Discovery signals are deterministic and file-cited, never model-produced
**[D-017]**
- Every `Signal` emitted by `stages/discover.py` / `stages/read_context.py` is computed by grep or
  file inspection; no `Provider` call (`autotester.providers.base.Provider`, the seam every model
  call in this repo goes through) sits anywhere on the signal-emission path.
- Every `Signal` names a real `file:line` in the scanned tree — this is also T-151's own goal-task
  note, restated here as a checkable claim.
- **Landing note:** `stages/discover.py` and `stages/read_context.py` do not exist yet (measured
  2026-09-27: `ls` on both paths fails, T-151 is `pending`). Running the Verify grep today exits 2
  ("no such file") — that is a missing-file error, not a pass, and must not be read as one. This
  criterion binds T-151's own unit check, not T-150.
- **Verify (at T-151's check):** `grep -rn "Provider" src/autotester/stages/discover.py
  src/autotester/stages/read_context.py` exits with no call site found (exit 1, "no matches" — an
  exit 2 means the files don't exist and the criterion is not yet applicable); a test scans a
  fixture tree and asserts every emitted `Signal.file`/`Signal.line` resolves to a real, matching
  line on disk.

### AI2 — A literal table, not the model, chooses which checks run
**[D-017 verbatim]**
- `stages/ai_catalog.py`'s kind→checks mapping is a plain dict/match literal a reader can enumerate
  by eye — the same discipline D-016/D-015 used to keep action choice out of the crawler's model
  calls. A model may **name** the system kind from AI1's signals; it may never **choose** the check
  set.
- **Landing note:** the file does not exist yet (T-152 depends on T-151 and T-125, both pending).
  Binds T-152's own unit check.
- **Verify (at T-152's check):** the table is a literal a reader can enumerate by eye (no
  string-built branch, no prompt-conditioned dispatch); a test drives each real `AiTargetKind`
  member through the table and gets that member's exact, single entry back.

### AI3 — The check-selection table is closed against a poisoned or out-of-table "kind"
**[maker, hardening]** — not a restatement of D-017's text. D-017 says a model may never *choose*
which checks run in the ordinary case; this extends that to a case D-017's own text does not name: a
hostile context folder attempting to *steer* the kind classifier into naming a kind that was never a
real `AiTargetKind` member, hoping the mapping degrades to something the attacker's text controls.
Filed separately from AI2 (the maker's original AI2 bundled both readings; splitting keeps the
D-017-verbatim claim and this hardening claim independently attackable, as the maker itself flagged
as the right split in its feedback-inbox entry).
- A mocked classifier returning an out-of-table or adversarial-string "kind" must still resolve to
  either a real `AiTargetKind` member's exact table entry, or a named `BlockedReason`-shaped refusal
  — never a check list whose membership the string's own content could have swayed.
- **Landing note:** binds T-152's own unit check, same file as AI2.
- **Verify (at T-152's check):** a test forces a mocked classifier to return an out-of-table string
  (e.g. `"kind"` set to a value with no `AiTargetKind` member, or a string containing check names)
  and asserts the resulting check set is exactly the closed-vocabulary outcome above.

### AI4 — Track C's catalog is the one Catalog, not a second one
**[D-017 + catalog.md CT7 — cross-reference, not a new claim]**
`catalog.md` CT7 already states: *"this criterion is judged over every unit that touches
`stages/ai_catalog.py` or any later Track-C catalog code: a second `Catalog`-shaped model, or a
second `BlockedReason`-shaped enum, anywhere in `src/` is a CT7 failure."* T-152's `ai_catalog.py`
is named there explicitly. Restating it here as a new `AI`-numbered criterion would give this one
concept two ground truths in two contracts (`core-invariants.md` C3's own "one concept, one place"
principle, applied to contracts rather than code) — the checker's own duplication, of exactly the
kind AI7's context-reading criterion elsewhere polices in the product. **This contract defers to
`catalog.md` CT7 for T-152's Catalog/BlockedReason reuse and adds nothing of its own here.**
- **Verify (at T-152's check):** `catalog.md`'s own CT7 Verify — `grep -rn "class Catalog"
  src/autotester/schema/` and `grep -rn "class BlockedReason" src/` each return exactly one
  definition. (Measured 2026-09-27, before T-125 or T-152 land: both return **zero** matches —
  `schema/catalog.py` does not exist on this branch yet. That is CT7's own pre-T-125 state, not a
  new finding; CT7 already anticipates being re-verified "at any later unit that imports or extends
  catalog matching.")

### AI5 — A blocked AI check names the missing fixture, never silently drops
**[D-017, extending T-152's own goal-task note]**
- A `runnable=False` entry always carries a non-null reason naming the concrete missing thing (e.g.
  "no live endpoint configured", "no ground-truth file at `<path>`"), matching `catalog.md` CT8's
  "not merely the enum value" standard already accepted for Tracks A/B.
- **Landing note:** binds T-152's own unit check.
- **Verify (at T-152's check):** one fixture per blocking condition; the rendered/logged row text is
  distinct from the bare enum name (CT8's own test shape, applied to Track C's blocked entries).

### AI6 — The capturer never grades
**[D-017 explicit + core-invariants C7]**
- `stages/ai_capture.py` contains no `Verdict`/`Result` construction and makes no PASS/FAIL
  decision; judgement happens only in `stages/grade.py` against a `Rubric`, mirroring
  `execute.py`'s existing observation/judgement split (C7: "the executor never grades itself").
- **Landing note:** `stages/ai_capture.py` does not exist yet (T-153 depends on T-152). Binds
  T-153's own unit check.
- **Verify (at T-153's check):** `grep -n "Result\.\|Verdict(" src/autotester/stages/ai_capture.py`
  returns nothing; a test proves a capture's output is handed unmodified to `grade()` and the
  PASS/FAIL comes back from the grade call, not from capture.

### AI7 — Every capture is scrubbed before a judge sees it
**[T-153's own goal-task note, C5 lineage]**
- `ai_capture.py`'s output passes `core.redact.Redactor.scrub` and
  `core.redact.assert_no_raw_secrets` before it is ever placed in a prompt built for `grade()` — the
  same boundary C5 already requires everywhere else in the pipeline.
- **Landing note:** binds T-153's own unit check, same file as AI6.
- **Verify (at T-153's check):** plant a synthetic secret-shaped string in a mocked target response;
  assert it never reaches the built judge prompt (mirrors C5's own verify pattern, applied to this
  new caller).

### AI8 — A context folder is read as plain structured markdown only
**[D-017 explicit]**
- `read_context.py` extracts frontmatter and tags; it does not resolve `[[backlinks]]` into a graph,
  does not read a Dataview query, and depends on no Obsidian-vault-index library.
- **Landing note:** binds T-151's own unit check, same file as AI1.
- **Verify (at T-151's check):** a fixture vault containing backlink syntax and a Dataview block in
  body text is read end-to-end; the resulting `Signal`/context model carries frontmatter+tags only,
  and `grep -rniE "obsidian" pyproject.toml` returns nothing.

### AI9 — One AI test report, grouped by tier, honest about empty (T-155; D-017, goal task T-155)
*Authority: D-017 names "the report" as the last Track C unit and reuse of "the report exporter"; the goal
task is "unified AI test report grouped by tier with judge reason strings". Landing note: the stage does
not exist yet.*
- A report stage reads one project's stored Track C evidence (check entries, captures, verdicts, the
  adversarial run record) and writes **one Excel workbook** at a path the caller names. Rows are grouped
  by `Tier` in `TIER_ORDER` (`schema/catalog.py:43`: static, behavioural, adversarial). Every tier has a
  section and shows its runnable count, **including 0**: an empty tier is present and says 0, never
  omitted (the same discipline as `catalog.md` CT6).
- Absence is not health (C12(b)): a project with no stored AI results produces a workbook whose summary
  says so, not an empty file, a crash or an all-clear.
- **Verify:** `uv run pytest tests/test_ai_report.py` (the goal task's `done_check`) with a fixture in
  all three tiers asserting three sections in `TIER_ORDER` order with their counts; a fixture with one
  tier empty asserting that section present with count 0; and a no-results project asserting the "no AI
  results" statement. Falsification: drop the empty-tier section from the stage; the empty-tier test
  must go red on its own assertion.

### AI10 — A blocked check is shown as blocked, with its reason and its action (T-155; goal note)
*Authority: the goal task's note, "Blocked checks appear as blocked with a reason, never as passes";
reuses AI5 and `catalog.md` CT7/CT8.*
- An `AiCheckEntry` with `blocked_reason` set renders status `BLOCKED`, the reason text and its
  `unblock_action` (`schema/catalog.py:79-83`), not merely the enum value. It is never PASS, never blank,
  and it is counted in its tier's section, not dropped.
- **Verify:** for every `BlockedReason` value an `AiCheckEntry` can carry, a fixture row renders a status
  cell equal to `BLOCKED`, the reason's human text and the action; an assertion that no blocked row
  renders a PASS-class status. Falsification: make the status mapping fall through to PASS for a blocked
  entry; the test must go red.

### AI11 — A judged row carries the judge's own words (T-155; goal title)
*Authority: the goal title "with judge reason strings"; `report-export.md` RE6 is the precedent for a
failure that is actionable.*
- Each judged row shows, verbatim and unparaphrased, every `Failure.criterion_id`, `reason` and
  `fix_hint` when present, and `Verdict.note` when present (`schema/verdict.py`), plus `grader_provider`
  so a computed rule verdict (`"rule"`) is distinguishable from a model-judged one.
- **Verify:** a fixture FAIL with two failures and an INCONCLUSIVE with a note render each string
  exactly (cell text equality, not substring of a summary); a `grader_provider == "rule"` row is labelled
  computed. Falsification: truncate or re-word the reason in the stage; the equality test must go red.

### AI12 — The report presents and never judges (T-155; core-invariants C7, `report-export.md` RE1)
- Read-only over stored evidence: the stage constructs no `Verdict`, computes no outcome, calls no model
  provider, opens no network connection and starts no browser; it writes only the file the caller names.
  Building the report twice from the same stored evidence gives the same cell contents.
- **Verify:** a test running the stage with a provider that has no credentials and a transport stub that
  records calls asserts zero provider calls, zero network calls, no file written except the output, and
  equal cell contents across two builds; `grep -nE "Verdict\(" src/autotester/stages/ai_report*.py` (the
  stage file the maker names) returns nothing.

### AI13 — Refused adversarial attempts appear in the report (T-155; `adversarial.md` AD7)
- Each line of `projects/<slug>/ai/adversarial/refusals.jsonl` appears as a row in the report's
  adversarial section with its target, timestamp, requested probe count and reason, and **no probe
  content** (AD7 forbids the log from carrying any). A missing or empty log shows "no refused attempts
  recorded", distinguishable from "not read".
- **Verify:** a fixture log with two lines renders two rows and no probe text; a missing file and an
  empty file each render their distinct statement. Lands with T-154 (the log is its write).

### AI14 — No secret reaches the file, and column sizing is the shared helper (T-155; C3, C5, `report-export.md` RE5)
- Every cell passes `core.redact.Redactor.scrub` before it is written; a planted synthetic secret in a
  capture response and in a judge reason does not appear in any cell, and
  `scripts/check_no_secrets.py` passes on the output.
- Column widths come from `core/excel.py::autosize_columns` (`core/excel.py:13`), the helper
  `stages/crawl_report.py` and `stages/issues.py` already use; no second implementation of it exists
  (C3).
- **Verify:** the planted-secret test; `uv run python scripts/check_no_secrets.py` on the output exits 0;
  a test patching `autosize_columns` asserts it is called for the workbook's sheets.

### Open product choices for T-155 (not criteria; Umesh decides, recorded 2026-10-11)
(1) Where behavioural captures and their verdicts are stored (AI6's capturer and the judge persist
nothing today; `projects/<slug>/ai/...` is the layout T-154 begins) and which unit writes them. AI9-AI14
are written to hold wherever they are stored. (2) Report format beyond the one Excel workbook (HTML, a
CLI command, a UI page): AI9-AI14 require only the workbook, the format the goal note's `autosize_columns`
reuse implies; an additional surface is a new criterion after the answer.

## Explicit no-fire list (do not raise these as findings)

- T-151/T-152/T-153 not existing yet, or a Verify command against them exiting 2 ("file not found")
  — every criterion above is forward-declared exactly as `catalog.md`'s CT7 was under D-039 before
  T-125 landed. Raising "the code doesn't exist" against this contract itself is out of scope; it is
  what T-150 (this unit) was for.
- The concrete `AiCheckKind`→probe mapping, or anything about T-154's build — see
  `adversarial.md`. (T-155's report is AI9–AI14 below; its *build* is still not this contract's job.)
- Building `stages/discover.py`, `read_context.py`, `ai_catalog.py` or `ai_capture.py` themselves —
  that is T-151/T-152/T-153's own job, not this contract's.
- The `ProbeSource` adapter design (rejected as a hard dependency by D-017; tracked under
  `adversarial.md` AD4).

## Amendment log (append-only; git history is the version)

- 2026-09-27 · START · contract created by /checker from `qa/feedback-inbox.md` 2026-09-27 (maker,
  T-150, Track C governance) · AI1, AI5 (orig. AI4), AI6 (orig. AI5), AI7 (orig. AI6) and AI8 (orig.
  AI7) folded near-verbatim in substance from the maker's filing · AI2 split into **AI2** (D-017's
  table-mapping claim, verbatim) and **AI3** (the maker's adversarial-kind-string hardening,
  tagged `[maker]` and made independently attackable), per the split the maker itself flagged as the
  right call in its inbox entry · the maker's proposed AI3 (Catalog/BlockedReason reuse) is **not**
  refiled as a new numbered criterion — folded into **AI4** as a cross-reference to `catalog.md`
  CT7, which already explicitly extends to "any later Track-C catalog code" naming `ai_catalog.py`
  by path; giving the same claim two ground truths in two contracts would itself be a violation of
  the "one concept, one place" discipline this repo enforces on code · AI3's own grep-based Verify
  (`class Catalog`, `class BlockedReason`) was measured against this branch (2026-09-27, pre-T-125):
  both return zero matches, consistent with CT7's own pre-landing state, not a new defect · direction
  approved by Umesh via **D-017** and plan §5B; the checker authored the wording, numbering and the
  AI2/AI4 changes — the maker never writes a contract.

- 2026-10-11 · routine (adds criteria, weakens none) · **AI9-AI14 added for T-155, the unified AI test
  report.** T-155 had no acceptance criterion anywhere in `qa/contracts/`: `adversarial.md`'s header
  names it but AD1-AD7 bind the runner only (AD7 feeds the report), `report-export.md` RE1-RE6 govern
  the run reports and name no Track C, and the only acceptance text was the goal task's title and note
  (a note is not a checker-owned criterion), so the maker's readiness pass correctly refused to dispatch
  (`qa/briefs/t155-ai-report.md`). Grounded in: D-017 (T-155 is the report unit; "the report exporter"
  is reused), the goal task's title and note (tier grouping, judge reason strings, blocked-never-pass,
  `autosize_columns`), AD7's stated purpose (refusal rows), and C5/C7/C12(b) (secrets, presenter never
  judges, absence is not health). Of the maker's P1-P7: P1-P3, P5, P7 became AI9-AI11, AI13, AI14; P4
  became AI12; P6 joined AI14; the proposed "a failing static row sorts above a passing adversarial row"
  was **not** adopted (an ordering choice nothing on disk decides). Two product choices (capture/verdict
  storage; report format beyond the workbook) are left open and listed under AI14, not invented.
  **Links:** D-017; T-155; AD7; ISS-t150-1; `qa/briefs/t155-ai-report.md`.
- 2026-10-11 - routine (status change only; no criterion changed) - **DRAFT -> ACTIVE.** The status line
  set the condition "goes ACTIVE on T-151's first checker PASS". That PASS is on disk and on master:
  `qa/verdicts/t151-target-discovery.md` (coordinator A, cycle 2, commit b18e4ea6) and `qa/verdicts/t151-target-discovery.b.md` (coordinator B, cycle 3, commit f0282ce5), both `VERDICT: PASS`. Criteria with a Landing note (AI4-AI8 for T-152/T-153 and AI9-AI14 for T-155) stay judged only when their own unit is checked. Nothing was edited, added or weakened in any criterion; this records the
  transition the header already promised. **Links:** T-151; qa/verdicts/.
