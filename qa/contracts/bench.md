# Contract — Bench (T-120)

**Covers:** goal task T-120 (final task in the P0-locked backlog). **Owner:** /checker.
**Criticality:** HIGH — T-120's own note: "North star made measurable. Scorecard computed by
`BenchTrial.score`, never by hand." This is the literal implementation of the project's stated
north star: "an expert human tester and AutoTester get the same material and the same build;
AutoTester wins on bugs found, false positives, and time."
**Depends on:** `execute.md`/`grade.md` (the pipeline a trial runs), `regression-proof.md` (the
fixture corpus reused here), `langchain-fallback.md` (the real judge).

## Purpose

Make the north star measurable: given a build with known, seeded defects (`BenchCorpus`), score
one or more participants' attempts (`BenchTrial`) on detection rate, false-positive rate, and
severity-weighted recall — via `BenchTrial.score`, never a hand-typed number. Prove this with a
real trial, not a description of one.

**Scope note — the oracle-baseline substitution is SUPERSEDED (2026-09-27).** The paragraph this
replaces read: *"a live, timed human tester was not available in this autonomous session ... The
human side is an explicitly labeled oracle baseline ... `participant_label="human-oracle-baseline"`."*
That was honest when written and is no longer the plan: Umesh, 2026-09-27, answered *"Human tester
parallel me baithega"* and *"teri reporting aur human ka compare krkee mai btuangaa"* — a real,
timed human tester sits in parallel on the Pathlynks proof run (T-169/T-136), and he owns the
verdict on the comparison. The oracle baseline is not deleted: it remains a legitimate participant
for a fixture corpus with no human in the room, and K1–K5 continue to govern it unchanged. What
changes is that it may no longer stand IN PLACE OF a human where a human actually ran — K6 makes
the two distinguishable in the artifact so no reader can mistake one for the other.

## Criteria

### K1 — `BenchCorpus` with real seeded ground truth
A corpus is built from a real, deliberately-broken fixture (the same class of regression as
T-110's `tests/fixtures/regression_site/`), with `seeded_bugs` describing a real, verifiable
defect (`location`, `detect_hint`, `severity`) — not a placeholder.

### K2 — A real AutoTester trial
`run_autotester_trial` (or the calling script) runs the unmodified `stages/execute.py::run_case` +
`stages/grade.py::grade` pipeline, through a real, non-mock judge (`LangChainFallbackProvider`),
against the corpus's broken build, and converts the resulting `Verdict`s into `Finding`s —
`matched_bug_id` set only when the failing case's mapped location is a seeded bug, `None`
(false positive) otherwise. No verdict content is invented or hand-adjusted after the run.

### K3 — Scoring goes through `BenchTrial.score`, never by hand
`stages/bench.py::scorecard(corpus, trials)` calls `trial.score(corpus)` for each trial and
returns exactly that — no parallel hand-computed detection-rate/FP-rate arithmetic anywhere in
the calling script or the manifest.

### K4 — The scorecard is comparative
The final output names both participants (`Participant.AUTOTESTER` and `Participant.HUMAN`) and
their scores side by side — this is the "expert human tester and AutoTester get the same
material" comparison the north star asks for, even though (per the Purpose's honest scope note)
one side is a documented oracle baseline rather than a live run.

### K5 — Persisted as real artifacts
The corpus and each trial save through `ProjectStore` (a new `save_bench_corpus`/
`load_bench_corpus`/`save_bench_trial`/`list_bench_trials`, following the exact pattern of every
other artifact kind in that file) — plain JSON files under `projects/<slug>/bench/`, not
throwaway in-memory objects.

### K6 — A real human trial is distinguishable from an oracle baseline, in the artifact
A `BenchTrial` whose participant is a human records **which kind of human**: a live, timed tester
or the synthetic `human-oracle-baseline`. A reader of the saved JSON alone — no manifest, no prose,
no session memory — can tell them apart. `participant_label` is a free-text string and is
therefore **not** sufficient on its own: a label is a convention, and a convention is what a later
caller silently breaks. The distinction must be a typed field the schema enforces, and the
comparison output must carry it through. A comparison that reports "human: 0.82 recall" without
saying which kind of human produced it fails this criterion even if every number in it is correct.

### K7 — Ground-truth ordering is recorded per human finding (AT-653)
A human finding authored **after** reading AutoTester's report is not independent evidence: it
anchors on what AutoTester already said. False positives survive that contamination (a claim
AutoTester made that the human rejects is still a false positive); **recall does not** (a bug the
human only noticed because AutoTester pointed at it cannot measure what a human finds unaided).
So:
- Each trial records the ordering it was produced under — whether the participant saw the other
  participant's findings before producing its own, and if so, which one ran first.
- Each human finding records whether it was **independent** or **prompted** (authored after
  reading AutoTester's report).
- `severity_weighted_recall` for the human side is computed from the **independent subset only**.
  A trial whose ordering is unknown has no independent subset, which is K8's case, not a licence
  to use all of it.
- The false-positive rate may use every reported finding, and must say that it does.

### K8 — A missing measurement reports unavailable, never a flattering default (C12 class)
Every number this contract's scorecard reports must be **absent when its input is absent**, not
substituted with the value most favourable to the participant. Concretely, and each of these is a
real defect shape found in this repo rather than a hypothetical:
- Recall with no ordering recorded reports `unavailable (ordering not recorded)`. It must not
  default to `0.0` either: a Pydantic field defaulting to zero reintroduces the same bias through
  the back door, because a zero is then indistinguishable from a measured zero.
- Wall-clock with no timing recorded reports unavailable. `duration_s: float = 0.0` states that a
  trial took **no time**, which is the best possible value on the axis the north star names third
  ("AutoTester wins on bugs found, false positives, and **time**") — so an untimed trial currently
  reads as an infinitely fast one.
- A false-positive rate over zero reported findings is not `0.0` precision; a trial that reported
  nothing has no precision to quote.
Verify by construction, not by inspection: build a trial with the input missing and assert the
scorecard says unavailable. A test that only checks the populated path cannot catch this class —
the bug IS the unpopulated path.

### K9 — The comparison artifact is complete enough to be judged by someone who was not there
`scripts/check_acceptance_comparison.py <slug>` (T-136's `done_check`) exits non-zero unless the
comparison artifact carries, for the run it names: both participants with their K6 kind; the K7
ordering and the independent/prompted split; each side's detection rate, false-positive rate,
severity-weighted recall and wall-clock, each either a number **from `BenchTrial.score`** or the
K8 unavailable marker; the seeded-or-confirmed bug list both sides were scored against; and a
per-bug row showing who found it. Umesh's verdict (he owns it — *"mai btuangaa"*) is recorded as
a decision **on** this artifact, never computed by it: the script asserts completeness, it does
not assert that AutoTester won.

### K10 — No-human-list mode is supported and honest (D-090)
T-136 is built and accepted without the independent human bug list (D-089 item 3, D-090). With no list, the comparison artifact states
recall as `unavailable until the human list arrives`, which is the K8 marker with that reason, never `0.0` and never a number. The
system must work and report in this mode as a supported mode, not an error: `scripts/check_acceptance_comparison.py` accepts the
artifact when K6, K7 and the other K9 fields are complete and recall is the unavailable marker with its reason. **False-positive rate
and wall-clock must still be present as numbers from `BenchTrial.score`** (or the K8 marker only when their own input is missing); an
artifact whose FP rate or time is missing or defaulted fails. When a human list later arrives, K7 ordering applies and recall is
computed from the independent subset only. Verify: build a trial with no human list; assert recall carries the reason string, FP rate and
time are numbers, and the check script exits 0; remove the FP rate, it exits non-zero. Mutation: default recall to 0.0, the K8 test
goes red.

### K11 — A real project's stored run converts to bench files without inventing numbers (T-136b; D-089 item 3, D-090)
`scripts/bench_from_run.py <slug> --run <id>` (stage `stages/bench_from_run.py`) turns an executed+graded stored run into the
acceptance bench files. It is a converter only: it sits on K3, K8 and K10 and adds no scoring of its own.
- **K11a** The trial (kind `autotester`, id `<slug>-acceptance-autotester`) is built only by `stages.bench.run_autotester_trial`
  (findings via `findings_from_verdicts`); no scoring or finding arithmetic anywhere in the script or stage (K3). Re-running replaces
  the trial in place, never adds a second.
- **K11b** A missing run, or a run with no verdict for any one of its `case_ids`, is refused: exit 2, a message on stderr, and nothing
  written (no corpus, no trial).
- **K11c** Corpus: a stored `<slug>-acceptance` corpus (a human list) is used untouched and never overwritten, and its `--bug-map`
  mapping applies. Absent, an empty `mode=unknown` corpus is saved, so recall reads the K10 unavailable marker and every
  AutoTester finding is unadjudicated; no bug is invented to match against.
- **K11d** Duration is measured only: the run's `finished_at - started_at`, else the sum of the stored per-case durations of the
  run, else `None` (K8 unavailable; the K9 check script then fails). Never defaulted to 0.0. A run whose per-case results are only
  partly stored must not be summed into a lower, flattering total.
Verify: fixture run, no human list: trial saved, `check_acceptance_comparison.py` exits 0, recall unavailable, FP rate a number;
ungraded run exits 2 with no files; untimed run with no results gives `duration_s is None`; human corpus present stays byte-identical.

## No-fire list

- **Scheduling, recruiting or instrumenting the human tester** — Umesh supplies the tester and
  owns the session; this contract governs what the ARTIFACT must contain, not how the human's time
  is arranged. (The older item here said a live human trial was itself out of scope; superseded
  2026-09-27, see Purpose.)
- **Judging who won.** K9's script asserts the comparison is complete; the verdict is Umesh's.
- Multi-corpus benchmarking, leaderboards, or a bench UI page — out of scope; one real corpus,
  one real comparison, is the bar for this unit.
- CI wiring to run bench automatically — future enhancement, not required here.

### K12 - AI-assisted known-bugs corpus (D-094)
A corpus of `mode: known_bugs_ai_assisted` (ground truth `provenance: ai_video_review`) is a third kind,
distinct from `human_confirmed` and `human_live`. (a) Only real bug rows (High, Medium) enter it; praise and
summary rows never do. (b) Any recall computed against it is labelled "AI-assisted video review, not
independent" in the comparison artifact (`recall_basis`) and in the printed output, and is never presented as
independent-human recall; its denominator population is `ai_video_review`. (c) FP rate stays unadjudicated
(human confirmation required). (d) The source list is internal feedback: the corpus is written only to a
gitignored path (the converter refuses a tracked one) and is read via `--corpus`; the repo holds only code,
schema, synthetic-fixture tests and decision text. K1-K11 are unchanged.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for T-120 — no contract existed before this cycle.
- 2026-09-27 · K6–K9 added; the Purpose's oracle-baseline scope note superseded; no-fire item 1
  replaced. Cause: Umesh 2026-09-27 replaced the no-human-available premise this contract was
  written under ("Human tester parallel me baithega"), and T-169/T-136 — the project's definition
  of done — had **no checkable criteria anywhere** in `qa/contracts/` (AT-281). Amending the
  contract that already governs `schema/bench.py` rather than authoring a new
  `acceptance-comparison.md`, because a new checker-authored contract file needs a
  `docs/DECISIONS.md` `Changes-authorized` line and that append path is permission-blocked
  (`ISS-at638-remainder-1`) — the criteria would have waited on a gate instead of landing.
  K8 generalises **C12** (`core-invariants.md`, "every health signal the loop reports must fail
  closed") from health signals to reported *measurements*; it is the fourth instance of one defect
  shape found in a single day — `RunBudget(None)` = unlimited (AT-570), recall-without-ordering
  = fully-credited (AT-653), `duration_s = 0.0` = instant, and the earlier loop-health signals.
  **Changes-authorized:** qa/contracts/bench.md Purpose, Criteria (K6–K9), No-fire list (this
  entry). No enforcement-path file touched. **Links:** AT-281; AT-653; AT-570;
  qa/gates/write-policy-tier.md; T-169; T-136; T-120.
- 2026-10-13 · owner-authorized (D-090, Umesh chat) · **K10** added: T-136 is built without the human list; recall is `unavailable until
  the human list arrives`; FP rate and time must still pass. K6-K9 unchanged. **Links:** D-089 item 3; D-090; T-136; T-169.
- 2026-10-13 · /checker fold-in (t136b-bench-from-run) · **K11a-d** added from the maker's proposal in `qa/feedback-inbox.md`,
  tightened (refusal writes nothing; partial per-case durations never summed). Consistent with D-089 item 3 and D-090 (no human list
  means recall unavailable, no invented numbers). K1-K10 unchanged. **Links:** D-089; D-090; T-136; T-136b.
- 2026-10-13 - /checker fold-in (t136-known-bugs) - **K12** added per D-094 (Umesh chat): Karunn's PathLynks review used as an
  AI-assisted KNOWN-BUGS oracle, labelled not independent. K1-K11 unchanged. **Links:** D-094; D-089; D-090; T-136.
