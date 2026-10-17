# Contract — VIDEO LEARNING: host media prep (VL1)

**Covers:** goal task T-132 (Track A3 — probe, chunk, transcript, frames) and every later unit
that consumes `media.json`, `transcript.json`, or an extracted frame.
**Owner:** /checker. **Criticality:** HIGH — this stage decides where every reported second
lands and what a tester is recorded as having said. Both are quoted to a human downstream.
**Depends on:** `core-invariants.md` (all), `ingest.md` (I8 — narration is ground truth).

## Purpose

Turn a screen recording into the three things the analysis half needs: what the recording *is*
(duration, dimensions), pieces small enough for a vision model to read, and the narration the
tester spoke. It runs on the **host** — the container has no ffmpeg, no GPU, and the corpus is
never mounted into it — so the two halves meet on disk under `projects/<slug>/sources/<id>/`
and nowhere else. That split is what makes the degrade rules below load-bearing rather than
defensive: the host this runs on is not the host the rest of the pipeline runs on, and it is
routinely missing one of the two tools.

## Criteria

### VL1 — A missing tool produces a smaller result, never an exception
With **ffmpeg or ffprobe absent**, `stages/media_prep.prepare` returns a `MediaPrep` carrying
exactly **one chunk whose path is the original recording**, with `ffmpeg_version` unset. The
single chunk is not a convenience: a caller iterating `prep.chunks` must do something useful on
a host without ffmpeg rather than silently doing nothing, and the absent `ffmpeg_version` is the
only record of *why* there is one chunk and not twelve. Absence is judged on **both** binaries,
not either — a box with ffmpeg and no ffprobe degrades at the start, not halfway through.

With **whisper absent**, the stage persists `Transcript(engine="none")`. That value means *a
recording with no narration on record*. It may never be rendered, summarised, or reasoned about
as a claim that the video is silent (AT-134), and an unreadable sidecar is a third state
(`engine="unreadable"`), never folded into either of the other two.

*Scope note (checker, 2026-09-08):* this criterion covers a **missing** tool. A tool that is
present and **fails** is not covered here and is tracked as AT-166 until a unit closes it; the
module docstrings currently assert the stronger property ("every function degrades rather than
raising") which measurement does not support.

### VL1b — A sidecar is reused verbatim and whisper is not run
When `<video>.transcript.json` exists beside the recording it is loaded as-is and
`transcribe_subprocess` is not called. Running prep twice must not change one character of what
a tester is recorded as having said. This is not an optimisation: narration is injected into the
ingest prompt as ground truth, so a regenerated line is a **changed quote from a real person**
(ingest.md I8). Judged by comparing the persisted transcript against the sidecar segment by
segment — timings and text — not by trusting an engine label.

### VL1c — The plan covers every second, and a cut lands on the second it names
For every valid input, `plan_chunks` returns a plan that starts at 0, leaves no uncovered
interval, and reaches the full duration. A gap is a stretch of product no model ever watches and
nothing downstream reports as missing.

Separately and by **measurement, not by argument order**: a chunk's first frame, and a frame
`extract_frame` pulls at `t`, must be the second the plan/model named. The `-ss`-after-`-i`
form is the current implementation of this property; it is not itself the criterion, because on
the ffmpeg in use (8.1.1) input-side seeking was measured to be accurate too (AT-168). A future
change to the argument order is judged against the measured property, not against the comment.

### VL1d — A stage that lacks `media.json` names a command the operator can actually run
`require_prepared` refuses with a message that (i) says the work must happen on the **HOST**,
because the stage that needs it runs in a container where prep is impossible and "run it here"
is advice that cannot be followed, and (ii) names the **real** CLI command, verbatim and
runnable. A message naming a command the CLI does not expose is a dead end at exactly the moment
the pipeline stopped, and a test asserting only a substring of it does not evidence this
criterion.

### VL2 — A cached observation is never re-requested
For a given `(source, provider_label, prompt_name, chunk_index)` the provider is called **at most
once, ever**. A second `analyze` over the same recording makes **zero** provider calls and writes
the same analysis. `--force` is the only override, and it **overwrites** the cached answer in place
rather than adding a second one — the cache is a keyed file per tuple, not an append log, so a
forced re-run can never leave two answers to one question with nothing to choose between them. The
key includes the model, so adding a second model to the ensemble costs exactly the second model and
nothing else. This is the only stage that spends money; a cache that re-asks is a bill, and a cache
that duplicates is a corrupted count of agreement.

### VL2b — The cache's promise is that re-running is SAFE, not merely cheap
The stage's own rationale is that a re-run after a crash, after a code change, or just to look
again costs nothing and changes nothing. That promise is kept only if both of these hold.

- **A damaged cache entry degrades to a re-request, never to a dead source.** The crash the cache
  exists to survive is precisely what leaves a half-written observation file behind. An unreadable
  or wrong-shaped entry must be treated as *absent* — re-requested and rewritten — and must not
  propagate an exception out of `analyze`. In particular `--force`, whose whole job is to get past
  the cache, may not itself be blocked by the cache it is overriding.
- **A cached answer is reusable only while the question is unchanged.** The cache is keyed by
  prompt *name*; a prompt file in `prompts/` is code in this project (CLAUDE.md: "prompts are
  files, not inline strings"). If an edited prompt still hits the old answer, the analysis silently
  mixes answers to two different questions and nothing on disk records which. Either the key covers
  the prompt's content, or the stage refuses (or says so) when a cached entry was produced by
  different prompt text. A stale answer presented as a current one is worse than a re-spend.

### VL3 — Failure is partial, and an analysis says what it is made of
One dead provider, or one failed chunk, never loses the answers that arrived. **Total** failure
refuses (`NoObservations`) rather than persisting an empty analysis, because an empty analysis on
disk reads as *"we watched it and found nothing"* — the opposite of what happened.

That principle does not stop at zero. A `VideoAnalysis` built from 1 of 24 intended calls is the
same untruth in a quieter voice: it names both models and both prompts, and a reader has no way to
learn that twenty-three answers never arrived. So a persisted analysis must **carry its own
coverage** — how many (model, prompt, chunk) answers were intended and how many were obtained — in
a field, not in a log line that is gone by the time anyone opens the file. Downstream (T-136's
recall score, a human reading the sheet) is entitled to know whether it is reading a full reading
or a fragment, and the artifact is the only honest place for that.

### VL4 — Adjudication is a function of content alone
`adjudicate` is pure: no provider, no clock, no randomness. Given the same set of observations in
**any** order it returns identical content (`Artifact.created_at`/`provenance` excepted, and the
exception stated). "Any order" means the orders this system actually produces, which includes the
**shipped ensemble shape** — two models x two prompts x N chunks. A sort key that leaves ties is
not order-independence: Python's sort is stable, so a tie hands the decision straight back to the
caller's list order, and every first-seen-wins merge downstream (a union's order, the surviving
`url`, `purpose`, `narration`, the concatenated summary) then depends on it.

Judged by measurement on the shipped shape, not by argument: shuffle a realistic observation set —
one that includes two observations differing **only** in `prompt_name` — and compare content. A
determinism test whose every fixture carries a single `prompt_name` does not evidence this
criterion, because the tie it exists to catch cannot occur in it.

**VL4a — a single provider's own duplicate report, across its own two prompts, must merge.**
Every recording is analysed under two prompts per provider; both can independently notice the same
fault on the same screen using different enough wording that a name-keyed merge never matches them.
Two (or more) reports that share a provider label, category, and seam window are ONE finding, not
one per prompt — regardless of whether the screen names agree — because the same model saying the
same thing twice under a different question is not two findings and is not cross-model
corroboration (`models_agreeing` must not move). Judged on a fixture where a real cross-model report
is *also* present in the same window and category, from a genuinely different provider whose screen
name also fails to match: that second, independent finding must NOT be swallowed into the
same-provider merge group.

**VL4b — the text that survives a merge is chosen by an explicit, stated, and tested rule — never
whichever observation the sort key happened to place first.** A first-seen default is itself a rule,
but an unstated one: this module measured it silently downgrading a matched finding into a missed
one (a terser, incidentally-generated aside beating a dedicated, more thorough description), which
is exactly the failure VL4's own tie-discipline exists to catch, one level up — in the surviving
*content* of a merge, not just in which merge occurs. The rule governing which text survives must be
named in the module's own docs and covered by a test that would fail if the rule were silently
reverted to first-seen. **The exact-tie case (two candidates equally weighted by the stated rule) is
part of this criterion**: the module must say what happens on a tie, even if the answer is "first-seen,
deliberately" — an untested, undocumented tie-break is the same unstated-default shape VL4 already
rejects for ordering.

### VL5 — Offsets are applied in code; narration is sliced to the chunk
A chunk's timestamps are moved into whole-video time by `shift`, never by the model, and the prompt
says so in as many words. Shifting copies rather than mutates, so a cached observation read from
disk is not altered by having been adjudicated. A chunk's prompt carries **only that chunk's**
narration: handing a model three minutes of video and the whole recording's transcript invites it
to attach a real person's quote to a screen they were not talking about, and a misattributed quote
is a fabricated one (ingest.md I8). A section with no speech says so explicitly rather than leaving
the placeholder empty.

### VL6 — The exported sheet is the human sheet's shape, verified against the file
The workbook `export_issues_excel` writes matches the tester's own sheet in columns, column order,
time format (`At` as an `MM:SS` **string** — a scorer comparing a float matches nothing, silently)
and severity vocabulary (their High/Medium/Low, not our S1/S2/S3). Verified against the real
workbook on disk where the corpus is present, cell by cell — a hand-copied header is a claim about
a file, not a reading of it — with an offline shape test beside it that pins the same thing on a
host without the corpus, and a stated rule for which wins when the two disagree.

Judged **on the written workbook**, never on the helpers. The helper being right does not make the
sheet right: writing `At` as a raw number was measured to fail nothing while `at_mmss` had its own
passing parametrized test, because that test never goes through a row. Any future criterion about a
cell is judged the same way — open the file a tester would open.

*Scope note (checker, 2026-09-09):* VL6 covers the sheet this exporter writes, which is
`ERP_Issues_ALL.xlsx`'s 13-column form. The second human-workbook shape (12 columns, no `Date`,
`Clip` where ALL says `Recording`) is a **different** schema — measured on the real files when they
existed. Nothing in this unit reads or accommodates it; loading both shapes is VL9's scorer concern
and is not scored here. T-136's acceptance baseline is no longer a workbook: since 2026-09-27 it is
the comparison artifact `uv run python scripts/check_acceptance_comparison.py pathlynks` (parallel
human tester), so VL6 cites no workbook for T-136.

## Invariants

### I-VL1 — Whisper never overwrites a transcript that already exists
No path in this stage regenerates narration that is already on disk or beside the recording.

### I-VL2 — A plan never advances by more than a chunk
`plan_chunks` refuses any parameter set that would leave an uncovered second or fail to
terminate. `overlap_s >= chunk_s` is refused today; a *negative* overlap is not, and silently
produces gaps (AT-167).

### I-VL3 — The stage never asserts a fact it did not observe
Zero duration, zero chunks, `engine="none"` and `engine="unreadable"` are all *records of what
could not be determined*. None of them may be reported to an operator as a successful result
(AT-164), and none may be read downstream as a positive finding.

### I-VL4 — Anything reported as extracted evidence is a real image
A path returned by `extract_frames` is a readable image, not merely a file that happens to exist
at the expected name. A frame is quoted to a human beside an issue; an empty or truncated PNG
left by an interrupted run must not be reused as if it were the screenshot the model named
(AT-165).

### I-VL5 — A merge never softens a severity
`Severity` is declared S1, S2, S3 in **descending** severity, so `max()` over it selects the
mildest and reads as though it were right. Wherever two readings of one fault are combined, the
worse severity survives — disagreement is exactly the case in which severity matters most, and a
merge that quietly downgrades it turns the ensemble into a filter. Agreement between models raises
`confidence` and never `severity`: severity is a property of the product, not of how many models
happened to look at it.

### I-VL6 — Nothing in the analysis half asks a model to decide a merge
Seam de-duplication and cross-model joining are deliberately dumb — casefolded names, overlapping
intervals, a fixed window. A cleverer matcher would be a second model: unauditable,
non-deterministic, and fatal to VL4. Adjudication, issue derivation and export contain no provider
call of any kind.

## Explicitly UNVERIFIED (not a criterion, and not to be claimed as one)

**The whisper branch has never been executed.** `faster_whisper` is not installed in the project
venv and no `[project.optional-dependencies]` block exists to install it from (AT-169). What *is*
executed and verified on this host is the crash-isolation plumbing around it — running the module
as `python -m autotester.media.transcribe` fails at import, exits non-zero, and is caught into
`engine="none"` without taking the parent down. The *output* shape of a real whisper run is
untested. Until one has been executed against a real recording, no unit, manifest, or ledger row
may describe transcription as working; the sidecar path is what runs here, and every corpus
recording has a sidecar.

## Out of scope / ignore

- Model calls of any kind (A4: the vision ensemble, adjudication, issue derivation).
- Whisper accuracy, model choice, GPU/CPU selection.
- Chunk encoder settings (codec, preset, crf) — quality is not judged here.
- ffmpeg's own behaviour or version differences beyond the measured properties in VL1c.
- Cosmetic wording of log lines that are not refusals.

## Amendment log

- 2026-09-08 · START (initial creation) · Authored by /checker at the maker's request in the
  `t132-media-prep` manifest (cycle 1). Criteria are the checker's own, derived from evidence:
  VL1/VL1b are as requested; **VL1c was rewritten** to make the *measured* placement property the
  criterion rather than the `-ss`/`-i` argument order, because the maker's stated rationale for
  that order was falsified on ffmpeg 8.1.1 (a before-`-i` seek at t=20s on erp1.mp4 produced a
  byte-identical frame, md5 `670362ad938c57b42431d432ce4d9abb`, with keyframes 4.27s apart);
  **VL1d was tightened** from "names the host command" to "names a command the operator can
  actually run", because the shipped message names `autotester media prep`, which the CLI does
  not expose. Invariants I-VL1..I-VL4 and the UNVERIFIED section are checker additions.
- 2026-09-08 · routine · **Edge cases recorded from the cycle-3 check of `t132-media-prep`
  (PASS).** No criterion changed — these are measurements the next reader should not have to
  re-derive. (i) **I-VL4's wholeness proxy has a known hole:** a file that is exactly PNG magic
  plus the 12-byte IEND chunk (20 bytes, no image data) passes `is_complete_png`. It is not
  reachable from the failure mode the guard exists for — an interrupted write truncates the tail
  — and the guard is explicitly a wholeness proxy, not a correctness claim. Recorded, not
  tightened (AT-165 residual). (ii) **VL1d's oracle is scoped to the criterion, not to the
  project.** "No `Usage:` banner after running the whole quoted invocation" was measured to
  reject an unregistered group, an unregistered subcommand and wrong arity, and to *accept* a
  registered same-arity sibling (`ingest frames`, `ingest register`); the checker's AN4 sabotage
  confirmed this by coming back INCONCLUSIVE. VL1d is met because the *shipped message* names a
  command that was run for real; the residual is test strength (AT-174) and is deliberately not
  written into the criterion at the moment of a passing verdict. (iii) **VL1d's shape exists
  outside this criterion's scope:** the `ingest frames` refusal names `autotester ingest
  analyze`, which the CLI does not expose (AT-172, high). VL1d covers the `media.json` refusal
  only; a future amendment generalising it to every refusal that quotes a command should be
  taken on its own, away from a pending verdict. (iv) **I-VL3 boundary, measured:** the
  no-ffmpeg degrade prints a green `0s, 1 chunk(s)` and persists zeros for duration/width/height.
  This is the shape VL1 *requires*, and the bracketed `[no ffmpeg — …]` is the designated record
  of why, so it is outside I-VL3's "unqualified success claim" — filed as AT-175 (low) rather
  than scored.

- 2026-09-08 · routine · **Edge case recorded from the cycle-1 check of `at172-at173-dead-command-shape`
  (PASS).** No criterion changed. The unit generalised VL1d's shape into a class-level guard,
  `tests/test_cli_advice_resolves.py`, which resolves every backtick-quoted `autotester ...` string in
  `src/` against the live CLI. **Measured hole:** that guard cannot see advice whose command name and
  backticks live in different AST nodes -- which is exactly how `require_prepared` builds its message
  (`media_prep.py:157`, two implicitly concatenated f-strings, the name held in the `PREP_COMMAND`
  constant). Sabotaging `PREP_COMMAND` back to the dead `media prep` (anchor matched once, file
  changed, isolated worktree) yields **0 failures in the class-level guard** and exactly 1 in the full
  suite. That one is
  `tests/test_media_prep.py::test_a_stage_needing_prep_is_sent_to_a_command_that_exists`.
  **That instance test is therefore NOT made redundant by the class-level guard and may not be retired
  on that basis** -- it is currently the only thing that catches the original AT-163 regression at its
  own site. Recorded here because commit 3b765a4's argument ("stop fixing instances") would otherwise
  make deleting it look like tidying up. Residuals tracked as AT-176 (high) and AT-178 (medium);
  AT-174 stays open with a round-trip oracle design attached in the verdict. Verdict:
  `qa/verdicts/at172-at173-dead-command-shape.md`.

- 2026-09-09 · routine · **Edge cases recorded from the cycle-1 check of
  `at176-at178-render-not-scan` (PASS).** No criterion changed. AT-176, AT-178, AT-174 and AT-189
  are all closed by measurement: sabotage AY (`PREP_COMMAND` back to the dead `media prep`, anchor
  matched once, file changed, isolated worktree) now fails **3** tests in the class-level guard and
  **4** in the full suite, where at `3b765a4` it failed **0** and **1**; the collected surface is
  **9 sites / 7 distinct commands**, including `ingest prep` and the un-backticked
  `core/consent.py` advice. **VL1d now has a causal oracle** — trigger the refusal, run the command
  the *runtime message* renders, assert the refusal stops — and it discriminates the registered
  same-arity sibling that the `Usage:`-banner oracle accepts (sabotage AZ fails exactly 2, and the
  only static test among them is the collector's own). The checker verified the discrimination is
  carried by the unconditional `require_prepared` backstop and not by the sibling incidentally
  erroring: a probe sibling that exits 0 and writes no `media.json` still leaves the refusal firing.
  **Measured residuals, recorded not tightened:** (i) the collector resolves constants defined in
  the *same file* only, so the identical construction with `PREP_COMMAND` **imported** returns `[]`
  — AT-176's shape one `import` away (AT-192, medium; zero live instances); (ii) the documentation
  exclusion covers `ast.Expr(Constant)` only, so a bare **f-string or `+`-concatenated**
  documentation statement is read as advice, including this codebase's own variable-docstring
  convention (AT-193, medium; measured zero live instances under `src/autotester`); (iii) an
  unresolvable interpolation is dropped **silently** rather than surfaced, so "no advice here" and
  "advice I could not read" are indistinguishable at the API (AT-195, low); (iv) a literal lowercase
  argument is swallowed into the command by the regex (AT-194, low). None is a shipped defect — the
  criterion is met by the shipped message, which the checker ran for real — and none is written into
  VL1d at the moment of a passing verdict. Non-Python operator surfaces under `src/` were re-checked
  and are empty: no `autotester <cmd>` advice in any `.md`, `.html` or `.js`, and `ui/`'s only
  mention is a module docstring, correctly excluded. Verdict:
  `qa/verdicts/at176-at178-render-not-scan.md`.

- 2026-09-09 · **START for VL2/VL2b/VL3/VL4/VL5/VL6 and I-VL5/I-VL6** · Authored by /checker at the
  maker's request in the `t133-ensemble-and-issues` manifest (cycle 1), and deliberately **not
  transcribed** from it: each was judged against measurement before it was written. **VL2 is as
  requested**, with the overwrite-not-duplicate property added because it was measured (a forced
  re-run leaves the same 4 files under the same 4 names). **VL2b is a checker addition** — the
  maker's own rationale for the cache is "safe to re-run after a crash, after a code change";
  measurement shows a truncated cache entry raises `ValueError` out of `analyze`, that `--force`
  cannot get past it (AT-199), and that an edited prompt file silently hits the old answer
  (AT-200). The promise, not just the saving, is the criterion. **VL3 was widened** past the
  maker's "total failure refuses": a run in which 1 of 24 intended calls succeeded was measured to
  produce an analysis indistinguishable in its provenance from a complete one — same
  `provider_labels`, same `prompt_names`, no coverage field anywhere in the model (AT-198). That is
  the same claim-more-than-happened failure the zero case is already guarded against. **VL4 was
  tightened** from "in any order" to "in any order the system actually produces", because the
  shipped `PROMPT_NAMES` has two entries while the sort key
  `(offset_s, provider_label, chunk_index)` omits `prompt_name`: two observations differing only in
  prompt tie, the stable sort hands the decision to the caller, and permuting them was measured to
  change `screens`, `journey`, `issues` and `summary` (AT-197). The existing determinism test
  cannot see this — every fixture in it carries one `prompt_name`. **VL5/VL6 are as requested**;
  VL6 additionally carries the maker's own BG lesson (judge the written cell, not the helper),
  which the checker reproduced: reverting `issue_row` to write a raw number fails exactly one test,
  and it is the workbook test added after the INCONCLUSIVE — the parametrized `at_mmss` test does
  not fire. I-VL5/I-VL6 are checker additions; `worst()` was verified exhaustively over all nine
  severity pairs and no other inverted `max()` over an ordered enum exists under `src/`.
  Verdict: `qa/verdicts/t133-ensemble-and-issues.md` (FAIL, cycle 1).

- 2026-09-09 · routine · **Measurements recorded from the cycle-2 check of `t133-ensemble-and-issues`
  (PASS, 6/6).** No criterion changed; nothing was tightened at the moment of a passing verdict.
  (i) **VL4's key is now total over everything the producer can produce.** The sort key gained
  `prompt_name`; 500 shuffles of the real 2-model x 2-prompt x 3-chunk shape give 0 mismatches and
  the cycle-1 tie attack yields 1 output. One residual tie remains -- two observations sharing
  `(offset_s, provider_label, prompt_name, chunk_index)` and differing in content permute to 2
  outputs -- but it is **unreachable from the shipped system**, because `core/paths.source_observation()`
  names the cache file from exactly that tuple and `save_observation` overwrites it (measured: 12
  files before a `--force` re-run, the same 12 names after). Every other sort under `src/` was swept:
  `join_screens`/`join_issues` ties imply a merge would already have happened (three issues 8s apart
  on one screen permute to 1 output), and `stages/issues.py:133`'s `(recording_label, at_s)` can tie
  but is fed a list `adjudicate` has already ordered. (ii) **VL3 is met by the field, and the field
  is read by nobody.** `observations_used`/`observations_expected` persist correctly (a crippled run
  writes 1/12 to disk), but the only consumers in the repo are two tests -- no CLI, no sheet, no UI --
  and `is_complete` is a `@property`, so it is not serialised at all. Filed AT-207 (medium) rather
  than written into VL3, whose letter ("in a field, not in a log line") is satisfied; surfacing
  belongs with T-136. Also filed AT-208 (medium): `adjudicate(..., expected=None)` defaults expected
  to used, so any caller but `analyze` produces an artifact declaring itself complete. (iii) **VL2b's
  crash safety is carried by ONE mechanism.** `list_observations(skip_unreadable=True)` is what makes
  a truncated entry heal (sabotage fails 1); reverting the force-before-read *ordering* alone fails
  **0** tests and was reported INCONCLUSIVE, never as a vacuous guard -- with the read unable to
  raise, the two orderings are behaviourally identical. AT-209 (low) carries the one test that would
  re-separate them. Verdict: `qa/verdicts/t133-ensemble-and-issues.md` (PASS, cycle 2).

## Criteria — T-136, the scorer (authored by /checker, 2026-09-09)

These cover `stages/score.py` and `scripts/score_video_issues.py`: the first module in this
project whose output is a **number about the product**, which is a different kind of artifact from
everything above it. A wrong screen map is visibly wrong; a wrong recall is a plausible number, and
a plausible number is the one thing nobody re-derives.

### VL7 — A refusal names a command that runs

The scorer exits **non-zero** when it cannot score, and its message names a command **the CLI
actually exposes**, verbatim and runnable. This is VL1d, unchanged in substance and generalised to
this module, and it is here because the same defect has now been filed four times (AT-163, AT-172,
AT-176, AT-206) and each fix was scoped to the file it was found in. The oracle is **running the
named invocation**; a test asserting a substring of the command (`"issues derive" in stderr`)
evidences that the string is present, not that the operator has anywhere to go.

Naming a Python function that has no CLI entry point does not satisfy this. If nothing in the
shipped surface can produce the artifact the refusal demands, the refusal is a dead end whether or
not the words parse.

### VL8 — The path the shipped command reads is the repo's own project directory

Run with no `--root`, the scorer resolves `projects/<slug>/` **inside this repository**. A default
that resolves elsewhere makes every refusal unfalsifiable: the command reports "no derived issues"
for a reason that has nothing to do with whether issues exist, and no amount of pipeline work can
ever change its answer. T-136's `done_check` passes no `--root`, so this criterion is the
difference between a task that can close and one that cannot.

Judged by **running the command exactly as `done_check` names it** and reading the path it opened.
A test that supplies `--root` exercises the branch that is not shipped and cannot evidence this.

### VL9 — Both ground-truth sheet shapes load, read off the files themselves

The 12-column `Clip` form and the 13-column `Recording` form (`ERP_Issues_ALL.xlsx`) both load,
each proved by an offline shape test that needs no corpus; any real workbook of either shape is
also read where it is present on disk, and an absent workbook is reported as absent, never
substituted by a transcription. Row counts and column names are measurements, never
transcriptions (VL6's rule, same reason). VL9 judges the **scorer's loader** only: T-136's
acceptance baseline is the comparison artifact (`scripts/check_acceptance_comparison.py pathlynks`),
not a workbook, and no criterion here may depend on a workbook that is not on disk.

### VL10 — A cell that cannot be read is refused; a cell that is absent is not scored as agreement

`At` holding something that is not MM:SS is refused rather than read as second zero — second zero
matches whatever opens the recording, so a bad cell would *invent* a match.

The same standard binds the recording cell, and for the same reason. An empty, blank or missing
recording value is **unknown**, not a recording, and two unknowns are not the same recording. A key
that maps two distinct recordings onto one value, or maps absence onto a value that can match, does
not fail loudly — it moves the north star's number, in either direction, with nothing on the page
saying so.

### VL11 — A match needs the recording, the time and the text; a truth row is claimed once

Same recording **AND** within the window **AND** similarity at or above the threshold. All three:
text alone lets one loud finding claim every row, time alone matches whatever the model happened to
say at that second. Each truth row is claimed by at most one report, and every report left over is
counted as a false positive rather than passed over in silence.

### VL12 — A declared bound changes the result or is rejected

`--window` and `--threshold` are honoured, never silently ignored (core-invariants C9). Judged on a
fixture the bounds can actually bite: a fixture whose issues are byte-identical to the truth rows
makes both knobs unobservable and tests the fixture instead of the code.

### VL13 — The score is a function of content alone

Given the same truth rows and the same **set** of issues in **any order**, the scorer returns
identical content — recall, per-row claims, and false positives. This is VL4's rule applied to the
module that produces the number, and it is written down because this codebase has already been
measured losing it once: a selection with a tie is decided by the caller's list order, and
`store.list_issues()` order is a file's append order, which no one controls.

Judged by **permuting the issue list**, not by argument about how unlikely a tie is. Greedy rather
than optimal assignment is an accepted trade (it costs recall, it buys an explanation a reader can
follow) — order-dependence is not part of that trade and is not licensed by it.

### VL14 — Coverage is reported for every source that contributed an issue

The report says how complete the analyses behind the scored issues are, and names the partial ones
(VL3's purpose, finally reaching a reader). A contributing source whose analysis is **absent from
disk** is *unknown coverage*, not zero and not silence: `complete: true` may not be reachable while
any source that supplied a scored issue has no analysis to read. Skipping the unreadable and
reporting on the remainder is the same claim-more-than-happened shape VL3 exists to stop, one level
up.

### VL15 — A declared local video corpus is ingestible as a labelled human-tester bench baseline

*(Added 2026-10-17 on Umesh's decision, `qa/gates/umesh-decisions-2026-10-17.md`: the team's existing
screen recordings are the labelled human-tester **bench baseline** for the AutoTester-vs-human
scorecard, T-136/T-169. They are not a case-generation source and not a heuristic-tuning set.)*

A corpus directory declared for a project is ingestible **as a body of labelled recordings**,
distinct from single-video ingest: one invocation over the directory enumerates every recording in
it, records for each one its label (the recording's identity, as VL10 keys it) and its analysis
status, and a recording that cannot be read is listed as unreadable, not dropped and not counted.
The result feeds only the bench baseline side of the scorecard; nothing derived from the corpus is
written into case generation or a tuned heuristic.

Any eval-method output derived from the corpus **states how many recordings it rests on** (and how
many were declared, readable and analysed), as a field in the artifact, not a log line. A figure
over a partial corpus that does not say it is partial is the claim-more-than-happened shape VL3 and
VL14 exist to stop. An empty or unreadable corpus directory refuses with a command that runs (VL7)
rather than producing a baseline of zero recordings.

Judged by running the shipped corpus invocation on a corpus of at least 2 recordings where one is
unreadable, and reading the artifact: counts declared/readable/analysed, the unreadable one named.
*Status: criterion only. The build is a separate, open unit (AT-665 resolution).*

### I-VL7 — The scorer asks no model anything

`stages/score.py` and the scoring CLI contain no provider call, no network, no clock and no
randomness. The number that judges the ensemble may not be produced by a member of it (I-VL6, same
reason).

## Amendment log (continued)

- 2026-09-09 · **START for VL7–VL14 and I-VL7** · Authored by /checker at the maker's request in the
  `t136-scorer` manifest (cycle 1), and deliberately **not transcribed** from the seven bullets it
  asked for: each was judged against measurement first. **Most are as requested** — VL7's
  exit-code half, VL9, VL10's `At` half, VL11, VL12, and VL14's headline. **Four are checker
  additions or tightenings, each because measurement contradicted the manifest:**

  (i) **VL7 gained "a command that runs".** The shipped refusal names `autotester issues derive`;
  `uv run autotester issues derive --help` answers `No such command 'issues'`, and the top-level
  command list has no `issues` group. Worse, `stages/issues.py::derive_issues` has **no caller
  anywhere under `src/`** — no command produces the artifact the refusal demands. The manifest's
  bullet said "names the command that would fix it"; the criterion says *runs*, because this is the
  fifth instance of the class (AT-163/172/176/206) and the fourth guard scoped narrowly enough to
  miss the next one: `tests/test_cli_advice_resolves.py` sets `SRC = src/autotester` and collects
  only from there, so `scripts/` is invisible to it. `DERIVE_HINT`'s own docstring — "Named once so
  the advice-collector guard can see it and the CLI-resolve test can prove it is a command that
  exists" — is false in both halves; a repo-wide grep finds `DERIVE_HINT` at exactly two sites,
  both inside the script.

  (ii) **VL8 is entirely a checker addition.** `scripts/score_video_issues.py:92` resolves its
  default root as `ProjectPaths(args.project).root.parent.parent`. Measured: `repo_root()` is
  `D:\autoTesting`, so that expression is `D:\` and the shipped command reads
  `D:\projects\erp\issues.jsonl` — outside this repository. The manifest's central argument ("run
  today, it exits 2, and that is why T-136 is not closed") is therefore not evidence about the
  absence of derived issues: the command would exit 2 with the identical message against a fully
  populated project. Every CLI test passes `--root`, so the branch that ships is executed by
  nothing.

  (iii) **VL13 is a checker addition.** The manifest states the ordering "is deterministic because
  candidates sort on similarity then time". `max()` returns the **first** maximum, so a tie on both
  keys is decided by `remaining` order. Measured: two truth rows; two issues tied against the first
  row on similarity (0.8 / 0.8) and on time; `--threshold 0.7`. Issue order `[X, Y]` gives recall
  **0.5**; order `[Y, X]` gives **1.0**. At the default threshold the same construction leaves the
  *identity* of the claiming issue (and therefore `per_row.matched_title` and `similarity`)
  order-dependent. This is AT-197's defect class — which cost T-133 a fix cycle and produced VL4's
  tightening — reappearing in the module that computes the north star.

  (iv) **VL10 was widened past `At`, and VL14 gained the missing-analysis clause.** `recording_key`
  splits on the first `(`, so `clip (1).mp4` and `clip (2).mp4` both key to `clip` — the exact name
  Windows gives a duplicate file — while an empty or `None` cell keys to `""`, which is matchable:
  a sheet with a blank recording column scored against issues with a blank label was measured at
  **recall 1.0**. And `coverage()` skips a source whose analysis is absent (`if analysis is None:
  continue`), so with two contributing sources and one analysis on disk the report reads
  `complete: true` — measured. AT-207 exists because a fragment and a full reading were
  indistinguishable; that is reintroduced at source granularity inside AT-207's own fix. I-VL7 is a
  checker addition and holds today.

  **What the manifest got right, verified independently.** All ten of its sabotages (SA–SJ) were
  re-run by the checker in an isolated `git archive HEAD` extract with `PYTHONPATH` pinned, each
  anchor matching exactly once and each file re-read as changed, restored by file copy — every one
  discriminating (1–13 failures), **zero INCONCLUSIVE**. AT-208 is genuinely fixed:
  `expected=None` records 0, `is_complete` reads zero as not-complete, and the single production
  caller (`analyze_video.py:181`) still passes the real product, so nothing regressed. AT-207's
  coverage does read **real persisted** analyses off disk, not fixture objects. The decision to
  leave **T-136 `pending` is correct and is upheld** — `uv run autotester providers` really reports
  only `mock`, and `projects/erp/` really holds no `sources.jsonl`, no `analysis.json` and no
  `issues.jsonl` — and the manifest states the shortfall first rather than burying it, which is the
  behaviour this project wants. It is correct for a second reason the manifest does not give:
  even with a credential, nothing in the CLI derives or persists video issues, and VL8 would hold
  `done_check` at exit 2 regardless.

  Verdict: `qa/verdicts/t136-scorer.md` (FAIL, cycle 1).

- 2026-09-09 · routine · **VL4a/VL4b added from the cycle-1 check of
  `at231-adjudicate-duplicate-merge` (FAIL).** No existing criterion weakened. AT-231's fix
  (`_same_model_duplicate` + the length-preference block in `_apply_merge`) is real and both its
  dedicated sabotages were independently re-run and confirmed exactly as the manifest predicted —
  the code and its own tests are sound. What did **not** reproduce is the manifest's own causal
  narrative for *why* the length-preference block matters: its table names the erp1 "Rule T3"
  same-model pair (claimed similarity 0.180 -> 0.315 against the human sheet) as the finding whose
  survival the fix rescues. Independently re-adjudicating the real cached observations
  (`projects/erp/sources/*/observations/*.json`) against the real
  `ERP_Issues_Trainers.xlsx`/`Trainer module` sheet with the shipped scorer at its default
  window/threshold shows the Rule T3 pair never matches any truth row in ANY of the three states
  (pre-fix, merge-fixed-but-first-seen, fully fixed) — its title+what_is_wrong similarity to the one
  truth row it could plausibly match (E-01) tops out at 0.175, never above the 0.30 threshold. The
  finding the length-preference fix actually rescues is the **erp2 document-type pair**: with
  first-seen-wins, "Incorrect document type option" survives and scores 0.247 against truth row E-02
  (below threshold, unmatched, recall 0/7); with the length-preference fix, "Document type dropdown
  option should be 'CITS Certificate' instead of 'CIPSA Certificate'" survives and scores 0.369
  (above threshold, matched, recall 1/7 restored) — reproduced exactly. The aggregate headline
  numbers (6 issues -> 3, false positives 5 -> 2, recall preserved at 1/7) DID reproduce; only the
  per-issue mechanism and the specific 0.180/0.315 figures are wrong. VL4a/VL4b are written from
  measurement of the fix's real, confirmed behaviour (the same-provider merge bound and the
  length-preference rule), independent of the manifest's mistaken narrative. See
  `qa/verdicts/at231-adjudicate-duplicate-merge.md`.

- 2026-10-17 · routine · **Re-anchor T-136 citations (AT-752) and add VL15 (AT-665).** Sources:
  `qa/feedback-inbox.md` line 6067 (2026-10-17T14:38:00Z, Umesh "fix all of these too") and
  `qa/gates/umesh-decisions-2026-10-17.md` (AT-665: bench baseline). (1) The VL6 scope note and VL9
  named `ERP_Issues_Trainers.xlsx`, absent from disk, although T-136's ground truth changed on
  2026-09-27 to a parallel human tester (`.goal/goal.json` T-136 note): both now say the 12-column
  `Clip` shape and point T-136's acceptance baseline at the comparison artifact
  (`scripts/check_acceptance_comparison.py pathlynks`). VL9 keeps its strength: both shapes must
  still load and be proved by an offline shape test; only the dependence on an absent file is
  removed. The 2026-09-09 amendment-log entry that measured against the real
  `ERP_Issues_Trainers.xlsx` (the `at231-adjudicate-duplicate-merge` cycle-1 entry) is history of
  a measurement made when the file existed; this log is append-only, so it is left verbatim.
  (2) VL15 added: a declared local video corpus is ingestible as a labelled body of recordings and
  any output derived from it states how many recordings it rests on, framed as the human-tester
  bench baseline. This tightens the contract (new criterion) and weakens no safety or data
  invariant, so it is a routine amendment. The build of VL15 is a separate unit, still open.
