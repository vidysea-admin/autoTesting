# Contract — core invariants (project-wide)

**Applies to:** every work unit in `d:/autoTesting`. A unit that violates any criterion here
fails its check regardless of what its own feature contract says.
**Owner:** /checker (maker reads only; feedback → `qa/feedback-inbox.md`).
**Source:** approved plan `C:/Users/Lenovo/.claude/plans/great-when-you-really-iridescent-ocean.md`
§3 Design principles, §7 Enforcement, §8 Security.

## Why these exist

The prior project (`d:/erp`) shipped without an upfront schema or system design. It reached 232
top-level entries, 977 source files, duplicated concepts across modules, and a 291-line landmine
document — at which point neither a human engineer nor an agent could hold it in context or take
control of it. Every criterion below is a cheap rule now that was unaffordable there.

## Criteria

### C1 — Schema-first, single source of truth
- Every domain data shape is a Pydantic model under `src/autotester/schema/`, one model family per file.
- No dict-shaped domain object, dataclass, or TypedDict duplicating a schema model exists elsewhere.
- Every artifact model inherits `schema.base.Artifact` (carries `schema_version`, `created_at`, `provenance`).
- Models use `extra="forbid"`, so an unknown key raises at load instead of being silently dropped.
- **Verify:** `uv run pytest tests/test_schema.py` exits 0.

### C2 — Readable by a human and an agent
- No file in `src/` or `tests/` exceeds 300 lines; no function exceeds 50 lines.
- Every module has a docstring stating its one job.
- `docs/ARCHITECTURE.md` stays ≤ 150 lines and its concept→file table matches reality.
- **`scripts/` is deliberately outside the two numeric caps above and C3's duplicate-definition
  check** (at520 answered option 3, D-048). Its files are standalone CLI tools, and each one
  legitimately defines its own `main()`. They stay visible through `docs/MAP.md`, which lists every
  script. This records a scope that was already true. It relaxes nothing for `src/` or `tests/`.
  Bringing `scripts/` under the caps later is a new decision, not a fix.
- **Verify:** `uv run autotester doctor` exits 0.

### C3 — One concept, one place (anti-drift)
- No class or public top-level function name is defined in two modules.
- No file named `*_v2.py`, `*_new.py`, `*_old.py`, `*_copy.py`, `*_final.py`, `*_temp.py`.
- Changes edit existing files in place; a new module requires a stated reason in the manifest.
- **Verify:** `uv run autotester doctor` exits 0 (duplicate-concept + drift-filename rules).

### C4 — Repo root stays clean
- Top-level entries are limited to the declared layout (`src`, `tests`, `docs`, `projects`,
  `profiles`, `qa`, `.goal`, `.work`, config files).
- Scratch, logs, and in-progress evidence live in `.work/` (gitignored), never the repo root.
- **Verify:** `uv run autotester doctor` exits 0 (root-clutter rule).

### C5 — Secrets never reach a model, a log, or an artifact
- `SecretRef` carries a key and its domain scope. No schema model has a field holding a secret value.
- Secret values live only in the **repo-root `.env`** (one file for the whole repo, keys namespaced
  per project and declared in each project's `SecretRef[]`); a project can resolve only the keys it
  declares. Everything in that file is masked from logs, prompts, and artifacts, declared or not.
- Prompts and stored steps carry `{{SECRET:KEY}}` placeholders; substitution happens only at the
  moment of typing into the browser, scoped to that `SecretRef`'s `domains` (which lie within the
  project's `allowed_domains`).
- Every log line and stored artifact passes `core.redact.Redactor.scrub`.
- **Exception (D-034, owner-only editor):** the local UI credential editor — `/settings/providers`
  and the per-project env editor (`ui/routes_credentials.py`) — MAY render a saved value behind a
  show/hide toggle so the operator who owns `.env` can verify and edit it. This is the ONLY surface
  that carries a value. The value still never reaches a model, a log, a shared/committed artifact, or
  a captured **product** screenshot (B7 unchanged). Residual, accepted by D-034: the value is present
  in the local HTTP response/DOM and in any screenshot **of the settings/env page**, which must never
  be fed to a model or shared.
  *Amended 2026-10-07 per D-072 (item 5):* on a hosted, multi-user server that surface is narrowed. A
  saved value is rendered **only** to a user holding the `credentials.view` permission (by default only
  the Admin/CEO group; `auth.md` AU21). Every other viewer sees "set" / "not set" and can still write a
  new value without seeing the old one. The D-034 show/hide behaviour is unchanged for a holder of
  `credentials.view`. A tightening of the exception, not a weakening of C5.
- Any route that accepts a new raw credential value must treat it as secret immediately: before any
  same-request non-secret validator can echo or persist input, its prompt/artifact guard includes
  the union of pre-existing root secrets and all newly submitted values.
- `**/.env`, `profiles/`, `.work/`, and `projects/*/runs/` are gitignored.
- **Verify:** `uv run pytest tests/test_core.py` exits 0; `git ls-files | grep -E "\.env$"` returns nothing.

### C6 — Artifacts are human-editable files
- Every stage output is JSON, JSONL, or Markdown on disk under `projects/<slug>/`, valid against its model.
- A human can open, edit, or delete any artifact and the system still loads.
- The UI is a view over these files, never a second source of truth.
- **Verify:** artifact roundtrip tests pass; no database is the primary store.

### C7 — Verification is independent
- A unit is complete only when a check that someone else can re-run passes.
- The executor never grades itself: `RawResult` records observation, `Verdict` records judgement,
  and they are produced by different components.
- **A sabotage must assert that it was applied.** Where a manifest's evidence is "I broke X and N
  tests failed", the harness must establish, before believing any result, that its **anchor
  matched exactly once** and that the **file on disk actually changed**. A patch whose anchor did
  not match applies nothing and reports a green suite — which reads as *"the guard test is
  vacuous"*, the precise opposite of the truth. A sabotage needs its own assertion, not just its
  own patch.
- **A zero-failure sabotage is evidence about the SABOTAGE, not about the tests.** "Anchor matched
  once" + "file changed" are necessary but not sufficient: an anchor can match once inside a
  comment, a docstring, or a line no test exercises, so the patch applies, the file changes, and
  nothing semantically moves. When a sabotage yields 0 failures the harness must report it as
  **INCONCLUSIVE — mutation not shown to change behaviour**, and either strengthen the mutation
  (revert the actual fix hunk, not a nearby string) or state the null result as unproven. It must
  never be reported as "the guard test is vacuous" on that evidence alone.
- **A harness must assert its own BASELINE is green before believing any result.** "Killed" is
  read from a non-zero exit status, so an unrelated red suite — a flake, a broken import, a
  half-applied edit — makes **every** mutation look killed and certifies a vacuous test as sound.
  Printing the baseline is not asserting it. The harness asserts `exit == 0` on the unmutated copy
  first, or none of its results mean anything.
- **A harness must attribute its kill to the test that claims the property.** "Killed" read from a
  non-zero exit status cannot distinguish *"the test named for this fix failed"* from *"an unrelated
  test failed"* from *"the suite failed to collect at all"*. A mutation that breaks the module under
  test exits non-zero and reads KILLED while **no test ran** — measured: a syntax-error mutation
  reported `KILLED  1 error`, with an empty failure list. The harness must assert that the specific
  test(s) it names as defending the mutated behaviour appear in that run's failure list, not merely
  that the exit code moved. A `defends:` label nothing compares against is a comment, not an
  assertion — measured: a committed harness printed `defends: test_a_file_nested_below_the_project_
  is_still_judged_by_it` on four consecutive kills, and no test of that name exists.
- **A unit that ADDS or REWRITES a test must mutation-test it before the manifest is submitted.**
  For each such test, mutate the specific branch it claims to defend and require at least one
  failure, attributed as above. A zero-failure mutation is reported INCONCLUSIVE (clause 2 above),
  never as a pass and never as "the test is vacuous". The maker runs this; the checker still re-runs
  its own. This is a duty on the unit, not a step in `qa/adapter.json` slot-1 — slot-1 runs on every
  unit, most of which add no test, and a step that no-ops on most runs is a step people learn to
  skip.
- **An unreachability claim is INCONCLUSIVE, never a justification, and extraction never
  discharges the mutation duty.** "No mutation can reach this property" is an unfalsifiable
  negative; asserting it stops the search that would refute it, and it has been refuted on the
  first attempt both times it was made here (AT-315, AT-321). A unit MAY extract a property into a
  directly-assertable function — that is cheap and often clearer — but the extraction is an
  addition, not a substitute: the extracted decision must still be exercised end-to-end by at
  least one mutation of its CALLER, or the property is recorded as unproven. A direct unit
  assertion about a pure function is evidence about that function; only the mutation is evidence
  that the caller would notice.
- **An unreachability claim costs one mutation run, not one paragraph.** A manifest that claims no
  mutation can reach a property must paste the mutation it actually **tried** and the run showing
  zero failures, reported as INCONCLUSIVE per clause 2 above. Prose reasoning toward the same
  conclusion is not evidence and is not accepted: the claim has now been made three times in this
  repo (AT-315, AT-321, AT-354) and refuted by a checker on the first attempt every time, and the
  clause above — which already forbids it by name and cites the precedent — did not stop the third.
  A rule that is violated by *not being read* is repaired by making it cost something mechanical, not
  by writing it more firmly. The duty converts a belief into an artifact a checker can judge, and a
  claim submitted without one is treated as an unproven property, not as a justification.
- **Every guard a unit introduces lands with its own failing-first sabotage, recorded in the same
  manifest** (at218 answered option 2, D-048).
  - A guard means any mechanism whose job is to make an invalid state impossible, or to detect it.
    The list is not exhaustive. It includes a test, an assertion, a schema or model validator (a
    Pydantic field constraint or `model_validator`), a doctor rule, a hook check, and a runtime
    refusal.
  - The manifest row names the guard and the single-hunk edit that reintroduces the defect it
    guards against. It pastes the run showing the guard fire on its own named assertion, from a
    throwaway copy with a green asserted baseline.
  - The throwaway copy excludes every `__pycache__` directory. A `.pyc` carried across by `tar` keeps
    the `co_filename` of the tree it was compiled in, so the copy's traceback prints the ORIGINAL
    tree's path while running the copy's source (measured at626/at639, marshal-proven). With the
    caches left in, a falsification's own evidence looks like the guard ran in the wrong tree.
    `.pytest_cache` was tested and is NOT the cause; excluding it is harmless, not required.
  - Reading the code and concluding that the guard would fire is not the proof. That habit is how
    all 23 measured vacuous guards (AT-218) reached a checker instead of being caught at build.
  - A guard with no such row is an unenumerated claim. It fails the unit on its own, even when
    every test is green.
  - This extends the test-mutation duty above from tests to every kind of guard.
- **A stale evidence spec stays byte-intact and is tagged, never silently left to rot or silently
  rewritten** (at516 answered option c, D-048). When a later unit splits or renames the test file a
  `qa/evidence/<unit>/mutations.json` spec's `kills` node-ids name, the spec's bytes never change —
  its committed content is the faithful record of the run that actually happened, and no later unit
  may edit it to keep it collectible. Whether staleness is deliberate or a lost test is instead
  recorded in a sidecar, `qa/evidence/<unit>/mutations.stale.json`, one `EvidenceTombstoneEntry`
  (`schema/evidence_tombstone.py`) per moved node-id, both `old_nodeid` and `moved_to` required
  `file::function` (never a bare name — that would reopen the "which file?" ambiguity the tag exists
  to remove).
  - The check (`ledger/evidence_specs.py::check_stale_evidence_specs`, wired into
    `uv run autotester doctor`) never trusts a tombstone's mere presence — that would be exactly the
    vacuous-guard class this clause's AT-218 sibling bullet already forbids. For a `kills` id that
    does not resolve against the spec's own declared `tests` scope, it looks up a tombstone entry
    and **re-resolves `moved_to`** the same way. Three outcomes, distinguishable in the reported
    detail: resolves directly (not stale), tombstone's `moved_to` resolves (deliberate, passes), or
    no tombstone / `moved_to` also fails to resolve (flagged, with a different message for each of
    those two cases).
  - **Known limit, disclosed rather than hidden:** resolution proves the named function EXISTS at
    the named path; it cannot prove that function is the actual, semantically-correct continuation
    of the property the stale `kills` id defended. A tombstone whose `moved_to` names a real function
    that is simply the *wrong* one resolves and passes — this is not caught, and no mechanism in this
    clause claims otherwise. A tombstone's `moved_by_unit` and `note` are read by a human, not
    mechanically verified; an honest `"unknown"` attribution is acceptable in place of a guessed one.
  - A bare `kills` name (no `::`) is resolved only against the spec's own declared `tests` field, the
    same scope `scripts/mutation_check.py`'s `collected_tests()` uses — never the whole repo. Treating
    a bare name as unresolvable outside that scope is a false positive, not a stricter check.
- **Verify:** `uv run pytest` exits 0 and the manifest pastes real output, not a summary; a
  sabotage claim in a manifest is re-run by the checker in its own harness, never read; a unit
  adding or rewriting a test pastes its mutation run, with a green asserted baseline and a named
  failing test per mutation; a manifest containing an unreachability claim pastes the attempted
  mutation and its INCONCLUSIVE run alongside it; `uv run autotester doctor` exits 0, which includes
  `check_stale_evidence_specs` finding no unexplained-stale evidence spec.
- **A failure the manifest correctly names as pre-existing or concurrent, and traces to a cause
  outside the unit's own diff, does not by itself block that unit's PASS.** The Verify clause above
  exists to catch drift the unit's own merge introduces or fails to reveal — not to hold a
  diff-scoped unit (a zero-code bookkeeping/data close-out, or any unit whose `git diff --stat` does
  not touch the failing test or the code it exercises) hostage to a red it did not cause and cannot
  repair inside its own path scope (C10). This is not self-certified: the manifest must name the
  failing test(s) individually (never a summary count), show — not assert — the cause outside its
  diff, and the checker independently re-runs the suite and re-derives the trace before relying on
  it. It does not excuse a failure the unit did cause, one it named incorrectly, or one whose cause
  it did not actually verify.

### C8 — Provider-agnostic
- All model calls go through `providers.base.Provider`. No stage imports a vendor SDK directly.
- Prompts live as versioned files, never inline string literals: `src/autotester/prompts/*.md`, or
  `src/autotester/skills/<name>/SKILL.md` for the prompts migrated by T-175 under D-041 (grade,
  expand-case, ingest-video, video-issues), loaded through `providers.base.load_skill_prompt`, which
  raises on a missing or malformed skill rather than returning an empty prompt (D-043).
- **Verify:** `grep -rE "^(import|from) (anthropic|google)" src/autotester/stages/` returns nothing.

### C9 — A declared control value is honoured or rejected, never silently ignored
- A field that exists to change the system's behaviour (a criticality floor, a `done_check`, an
  approval flag, a gate) must either take effect or fail loudly. A reader that does not recognise
  a value must not substitute a default that is *weaker* than the value written.
- Where the reader is outside this repo and cannot be changed here, this repo pins its own data
  against the reader's actual vocabulary in a test, and files the upstream defect in the ledger.
- Applies to `.goal/goal.json` control fields (`base_criticality`, `done_check`, `approved`) as
  well as to `projects/<slug>/` artifacts.
- **Verify:** `uv run pytest tests/test_goal_criticality_vocabulary.py tests/test_goal_done_checks.py
  tests/test_goal_contract_registration.py` exits 0 — one file per control field pinned so far
  (`base_criticality`, `done_check`; the latter split across two files at AT-638, see below).
  `approved`
  is not yet pinned (AT-156); when it is, its test joins this line.

### C10 — A unit's commit carries only that unit's paths
- Two loops share this working tree and one index. A commit made for a unit contains only paths the
  unit's manifest names in "What changed", its own evidence directory, and the qa/ files its
  handshake writes (manifest, verdict, ledger rows, tick). Staging carefully does not scope a
  commit — a bare `git commit` commits the whole index, including what the other loop staged.
- Every maker and checker commit therefore names its paths: `git commit --only <paths>` (or `-o`),
  never a bare `git commit` after `git add`, never `git add -A`.
- **A unit is committed on its own branch before check. It reaches master only by merging the exact
  commit the checker's PASS verdict reviewed, with a `Cycle checked` that matches the manifest's
  `Fix cycle`** (commit-before-verdict answered C, D-048).
  - A commit added to the branch after the reviewed SHA is unreviewed. It needs a new cycle, meaning
    a new `Fix cycle` and a new verdict, before the merge. The only exception is a `Merge branch
    'master'` sync commit that brings in nothing but master's own history.
  - This adopts the `wave/<slug>` worktree practice used since 2026-09-17 in place of the older
    commit-on-the-shared-tree practice (option A in the gate). Units merged before 2026-09-26 are
    grandfathered.
  - Master never carries a unit's un-PASSed code. A failed cycle stays on its branch, so a later
    cycle is never judged against an earlier failed one that happens to sit on master: the at438
    lesson, see ui.md U14(b).
  - The checker's own handshake writes on master are not unit code, and this rule does not cover
    them: evidence directories, ledger flips, gate answers and contract amendments.
- A commit found carrying another unit's paths is repaired by un-sweeping it (`git reset --soft`
  + `git commit --only`) and leaving the other loop's staging exactly as found — never by
  `git rm --cached`, which deletes the other loop's file from HEAD.
- **Verify:** `git show --name-only --format= <unit commit>` is a subset of the manifest's "What
  changed" plus that unit's `qa/evidence/<slug>*`, `qa/manifests/<slug>.md`, `qa/verdicts/<slug>*`,
  `qa/issues.jsonl`, `qa/.last-tick`, `qa/feedback-inbox.md`.

### C11 — Every third-party import is a declared dependency (D-046)
- A module under `src/` that imports a third-party package names that package in `pyproject.toml`
  `[project].dependencies` (or an optional-dependency group). Resolving only as a transitive dependency
  of another package does not count: one upstream release can remove it (AT-130: `google-genai`,
  `starlette`).
- **Verify:** `uv run autotester doctor` → `check_dependencies_declared` (src/autotester/doctor.py) reports
  no undeclared import. Known false-positive class: `TYPE_CHECKING`-only and `try/except ImportError`
  optional imports (AT-590). That is a check defect to fix, not a licence to skip declaring a real import.

### C12 — Every signal and every measurement this system reports must fail closed

**The principle, stated once (maker, 2026-09-28).** Clauses (a) and (b) are one rule, and the
variable is **not** how crude or how typed the instrument is. It is whether the instrument has any
**representation for the thing it must tell apart.** Where it has none, the two states collapse into
the one that happens to be reachable — and that one is almost always the reassuring one.

The list is measured, every entry found in this repo:

| Instrument | Cannot represent | So it silently reports |
|---|---|---|
| `dict[id] = row` (`ledger/checks.py::_status_by_id`) | two rows for one id | the last row's status as the only status (AT-656) |
| an unanchored substring (`mc-sessionstart.ps1:14`) | a claim vs a **quotation** of a claim | a closed-out manifest as never closed out (AT-673) |
| `RunBudget(None)` (`stages/parallel_run.py:146-156`) | unapproved vs unlimited | an unapproved run as permitted (AT-570) |
| `duration_s: float = 0.0` (`schema/bench.py`) | untimed vs instant | an unmeasured trial as infinitely fast (AT-655) |
| recall with no ordering field (`schema/bench.py`) | independent vs prompted findings | a contaminated recall as a clean one (AT-653) |
| a truncated `qa/.last-tick` (`loop-status --strict`) | no history vs a clean history | a dead loop as healthy (AT-644) |
| **two spot samples of a churning quantity** | a **rate** vs noise | a trend that does not exist (below) |
| a check that examines **one site at a time** | a **disagreement between two sites** | each site as correct on its own (below) |
| a command run through a **pipe** (`uv run pytest \| tail`) | a non-zero exit, and any line it dropped | the *tail's* success as the command's, over a failing suite (AT-692) |

**The pairing row is the maker's (2026-09-28) and is the list one level up.** Three defects found in
one evening were invisible to any check that looked at a single site, because **each half read as a
sensible rule in isolation**: `0` as a zero budget at the gate and `0` as unlimited during the run
(AT-660); a close-out detector and a manifest that merely *quotes* the phrase it matches on (AT-673 +
AT-657); and, on the same disk, two carefully-scoped approvals that had expired beside one live
approval scoped `everything` for nineteen years (AT-661). In every case nothing was wrong at either
site alone — the defect **was** the disagreement, and a check reading one site has no representation
for it. So a criterion that pins a rule at one call site pins half of it; where a rule is enforced in
two places, one test exercises both against the same object (`qa/contracts/consent.md` CN10 states
this for bounds).

**The other half, and it binds the checker hardest (the maker's, 2026-09-28).** A matcher reports on
the state its pattern can EXPRESS, and every one of us has read that as a report on the state that
EXISTS. Five instances in one day, and the last two were the people measuring rather than the code:
a `Status:` matcher blind to `## Status (cycle 2):` reported a manifest as having no state at all,
and a conclusion about the hook's count was drawn from a predicate that was not the hook's predicate
(AT-662). So *verify by construction, not inspection* is only half a rule - **the construction has to
be the same one the claim is about.** A count re-derived by a different pattern is a second opinion,
never a confirmation, and where two patterns disagree the disagreement is the finding.

**The pipe row is how BOTH loops run their own verify commands, and it fails open in two
directions at once (2026-09-28, AT-692).** A pipeline's exit status is its *last* command's, so
`uv run pytest 2>&1 | tail -15` reports `exit 0` while its own summary line reads `1 failed` —
measured three ways in one shell: `false | tail -1` → 0, `set -o pipefail; false | tail -1` → 1,
`exit 3` unpiped → 3. This row sits above the flake it hid (AT-518) because it is the one shape on
this list that can turn a FAIL into a PASS in a verdict, and PASS is the checker's alone to grant.
The second loss is worse and has no remedy after the fact: the filter also discards the diagnostics,
so the AT-518 occurrence it hid could not be matched against that issue's recorded failure shape at
all and had to be filed cause-unknown. A pipe has no representation for a non-zero exit and none for
a line it did not keep.

**The rule, and it names both roles because the hazard is symmetric.** *A verify command's exit code
must be the command's own, so no gate command is piped or grouped. Where a pipe is genuinely wanted
for aggregation it is a diagnostic line, named as such, and never the thing a verdict rests on.*
Filtering a file you have already kept is fine; filtering a stream you did not keep is not — so the
practice is redirect-then-read (`> .work/<name>.txt 2>&1`), and `set -o pipefail` in any script that
pipes a command whose status matters. **`qa/adapter.json` is where this is enforceable**, because its
three gate commands are declared in one file.

**Measured before being asserted, on both seats — and the measuring is the lesson again.** The
checker's seat had the live instance above. The maker's seat measures **clean**: `qa/adapter.json`'s
three gate commands are unpiped with `"expect": "exit 0"`, and across 261 manifests exactly **one**
shell line pipes a verify command (`at423-scroll-invariance-probe.md:54`, `| uniq -c` over skip
reasons — a probe aggregating reasons, not a gate), out of 17 piped shell lines in all. So this
criterion forecloses a hazard on the maker's side; it does **not** describe a defect there. The
reason that sentence is in the contract is that the maker's *first* measurement of its own seat said
**37 files** — a `grep` for `pytest[^|]*|` counting the `|` of markdown **table borders** in every
manifest's evidence table, 75 such cells against 1 real pipe. It would have confirmed the checker's
guess about the maker's practice using a pattern that cannot tell a shell pipe from a column
delimiter. And on the same check the checker's own `adapter.json` walker printed **zero** matches
over a file that visibly contains three, so the citation above rests on reading the file, not on the
script. Three instruments, one question, and two of them were the agents.

**A third, the same day, and it is the strongest of the three because it happened while proving a check COULD fail (the maker's, AT-693).** Repairing the two vacuous `done_check`s, the maker built a throwaway tree of re-corrupted copies to show the new needles were falsifiable. **Both passed.** It nearly concluded its own needles were wrong. Cause: `scripts/check_deliverable.py:25` sets `REPO_ROOT = Path(__file__).resolve().parents[1]`, so every relative path resolves against the **script's** repo and never the working directory — correct for the tool, and it means the copies were never opened. **A falsification run from a copied data tree proves nothing unless the script is copied too.** Redone with the script inside the tree, the same needles went red (re-corrupted screenmap → exit 1, `DECISIONS` minus its 8 `D-016` occurrences → exit 1, healthy control → exit 0), which the checker then re-derived independently in its own copy. This is the AT-548/549/550 unisolated-capability class committed *in the act of testing for it*, and it is the reason SKILL step 4b insists the copy must run GREEN before the falsifying edit: the green line is what proves the copy is real, and a copy that is never read is green for free. One question about one hazard, three instruments — a grep counting table borders, a walker returning zero over a populated file, and a falsification whose subject was never loaded — and all three were ours, none of them in the product.

**And a distinct failure the same day, which the instrument table cannot hold because no instrument was involved (the maker's observation, 2026-09-28).** Twice, the maker's *measurements held* and the **sentence that compressed them for a reader** contradicted itself — both times in text addressed to Umesh, both times caught by the other seat. Once: a gate addendum stating two paragraphs apart that anchoring the hook's patterns "does not touch AT-696 at all" and that "one change answers AT-673, AT-669, AT-696 and AT-643." Once before it: a defect count offered as ten mistakes rather than one missing guard. Neither was a bad number; both were a summary that lost a distinction the measurement had kept. **So the compressing line needs the same re-derivation the numbers get.** The operational form, and it is cheap: before a claim goes to the human, check each clause against the measurement it rests on rather than against the paragraph around it — a summary is a derived artifact, and nothing in this contract exempts a derived artifact from being re-derived. This matters most exactly where it happened, in the text that asks for a decision: "fix the hook" read as one change when it is three at three sites, with a different direction of failure left open by each partial, is an approval the human cannot give correctly because the sentence hid the choice.

**The last row of the table is the agent measuring, not the code, and it belongs here for that reason.** On
2026-09-28 the maker read free space on `C:` at 0.37 GB then 0.34 GB, inferred "degrading ~30 MB/hr,
~11 hours to zero", and **held a build on it.** The checker, asked to act, measured 2.37 GB and
refused to act on either number, reporting the disagreement instead. Neither instrument was faulty
and neither reading was wrong: the volume was *rising* — 0.34 → 2.37 → 6.59 → 9.77 GB inside twenty
minutes — and all three instruments agreed exactly when sampled at the same instant (a transient
`Win32_LogicalDisk` NULL resolved on its own). The maker withdrew the rate claim unprompted. The
defect was never in the disk or the tool; **two samples of a quantity that churns GBs per minute
have no representation for a rate**, so noise was reported as a trend. A lesson that indicts only
the code and not the agent doing the measuring is the weaker version of it.

What survives, and is the reason the hold was still right: the *dip* was real. Free space genuinely
was 0.34 GB, below what a full suite needs, and an `ENOSPC` red is indistinguishable from a real
failure on `uv run pytest` — the one instrument both loops sign verdicts with. **Refusing to run on
an uncertain number is correct; quoting a runway from two samples is not.** The two are separate
judgements and only the second was wrong.

**(a) Health signals — the loop watching itself.**
- A liveness, coverage, or completeness check the loop or its hooks report (session-start injection,
  `loop-status`, a sweep's own terminal state) must be able to tell "nothing is wrong" apart from
  "my evidence was destroyed, truncated, or never written." A check that reports clean over missing
  or corrupted evidence is a defect in the check, not a fact about the system it was watching.
- **Verify:** for each named instance below, the specific defect closes: `qa/.last-tick`'s writer
  cannot silently truncate the file (AT-644) · a Mode A check that dies mid-run leaves a partial
  verdict rather than none (AT-641, SKILL step 7's incremental-write remedy) · a sweep or hook
  enumerates worktrees with unmerged commits instead of only reading manifests (AT-643).
- **Known instances (measured, not hypothetical):** (1) `qa/.last-tick` was truncated 47→2 lines by
  a `>` where `>>` was needed, and `uv run autotester loop-status --strict` read the 2-line file as
  a clean history with `no gaps`, exit 0 — the AT-368 dead-loop detector gave a false all-clear
  exactly when AT-383 wired it into session-start (AT-644). (2) A Mode A checker died before
  writing `qa/verdicts/at621-exit-call-aliases.md`; the unit then looked indistinguishable from
  "never dispatched" rather than "checked and lost" (AT-641). (3) Two worktrees held finished,
  unjudged commits for two days with their issues still `open` on master, and no sweep or hook
  check ever enumerated worktrees to surface them (AT-643).

**(b) Reported measurements — the system watching the thing under test (added 2026-09-27).**
- The same rule, one surface out. A number this system **reports about a product or a
  participant** — a score, a rate, a duration, a coverage figure, a budget — must be **absent when
  its input is absent**, never substituted with the value most favourable to whatever is being
  measured. "I did not measure this" and "I measured this and it was fine" are different facts and
  must be different outputs.
- The tell is a default in the type, not a bug in the arithmetic: a numeric field whose default is
  its own best case, or a divisor guarded by `or 1` so an empty numerator yields a flattering
  quotient. **A zero default is not a safe default** — once written, a zero is indistinguishable
  from a measured zero, so the absence is unrecoverable downstream. Absence needs its own
  representation (`None`, `unavailable`, or a variant), and the reporting path must carry it
  through to the human rather than coercing it on the way out.
- **Verify by construction, never by inspection:** build the object with the input missing and
  assert the report says unavailable. A test that exercises only the populated path cannot catch
  this class, because the unpopulated path IS the defect.
- **Known instances (measured, four found on one day — 2026-09-27 — which is why this clause
  exists):** (1) `RunBudget(None)` returns `True` from `try_consume` forever, so a run with no
  `RunApproval` is not "unapproved" but *unlimited*, and `run_cases(..., approval=None)` is the
  default (AT-570, `stages/parallel_run.py:146-156,216-225`). (2) `severity_weighted_recall` is
  computed unconditionally although nothing records whether the human's findings were independent
  or written after reading AutoTester's report, so a contaminated recall is reported as a clean one
  (AT-653; remedy: bench.md K7/K8). (3) `BenchTrial.duration_s = 0.0` reports that an untimed
  trial took no time — the best possible value on the axis the north star names third — and the
  same function's `or 1` divisors make a trial that reported nothing score perfect precision
  (AT-655). (4) Clause (a)'s own three loop-health instances are this same shape on the
  self-observation surface; (a) and (b) are one invariant, split only by what is being watched.
- **Why this is not scope creep:** this project's product is a report about someone else's
  software. A report that silently rounds an unmeasured axis toward "fine" is the exact failure it
  exists to catch in others (intent.md O4). An invariant that held the loop to a standard the
  product's own output was exempt from would be the wrong way round.

- **A check whose outcome its own construction has already decided is not a measurement, and this
  is the one shape the instrument table above cannot hold** (both instances found 2026-09-28, one
  per seat, which is why it is a clause and not a row). Every row above is an instrument that *can*
  distinguish two states but has no representation for one of them. This is the degenerate case:
  the instrument is fine, the question has one possible answer, and the reassuring answer is the
  only one reachable — so the check passes with the same confidence whether the thing it tests is
  true or false. Measured instances. (1) **The checker's:** it reported a merge resolution "VERIFIED
  LOSSLESS, checked by substring rather than by eye" after confirming each of the two merge-state
  texts was a substring of the surviving row — while the surviving row had been *built* as
  `a + <separator> + b`. Containment in a concatenation of both sides is a tautology;
  measured afterwards, `find(a) == 0`, `find(b) + len(b) == len(s)`, prefix 0, suffix 0. No
  arrangement of the data returned False (AT-662). (2) **The maker's, four hours earlier and
  independently:** an AT-697 freshness fixture in shape A (write the file with LF, commit, compare)
  "passes whether or not the implementation normalises", because nothing in it ever makes git write
  the file out — which is why shape B or C is required. The rule: **before reporting a check as
  evidence, name the arrangement of the data in which it would have failed.** If none exists, the
  check has measured the construction and not the claim, and the honest form is a different check —
  here, that the survivor decomposes *exactly* into `a + header + b` with no residue, which can fail
  on any merge that truncates a side or drops a field. It held when first run and again after the
  separator changed — and **the literals are deliberately not recorded in this clause**: the separator
  grew from 602 to 1086 chars within the hour (the maker added a precedence sentence, `521df6f8`),
  which made three freshly verified sums stale while the identity they tested stayed true. A contract
  states the invariant — `len(a) + len(separator) + len(b) == len(survivor)` with exact reconstruction
  — and any measurement of it is pinned to the commit it was taken at or it is not repeatable. Writing
  the numbers into the rule would have put figures that no longer reproduce into the ground truth,
  which is this criterion's own failure one level up. (The stale literals stand uncorrected in the
  Amendment log below, as that log is append-only and they were true when written; this is where the
  rule lives, so this is where they are removed.) Both seats' conclusions were correct; neither had
  been established. **A check that can fail is necessary and not sufficient** — the maker's limit,
  accepted 2026-09-28, and it is load-bearing: it went looking for a contradiction between two merged
  halves with a check that genuinely could have found one, the check came back clean, and it still
  first reported a contradiction that was not there. So this clause governs whether the instrument
  could have failed, while the clause above it — a summary is a derived artifact, re-derived clause by
  clause against the measurement it rests on — governs whether the reported result is the one the
  check returned. Neither catches the other's failure and both were needed on the same day. This is
  also the sense in which SKILL step
  4b's green-before-the-edit requirement and C7's sabotage row are the same rule as this one — each
  demands the falsifying arrangement exist before the pass is believed.
  **The in-tree exemplar to imitate, which predates this clause:**
  `tests/test_ui_video_route_traversal.py::test_safe_video_path_never_calls_resolve_for_a_dangerous_value`.
  Its docstring names the arrangement in which it reddens ("deleting the guard — `run_dir.resolve()`
  then raises, uncaught"), says it was confirmed in a throwaway copy with the guard's two lines
  removed, and exists *because* the timing-based test above it might pass for reasons unrelated to the
  guard ("regardless of how fast or slow a real OS-level UNC lookup happens to be"). That is this
  clause satisfied in full, by a test written before the clause existed, and it is the shape to copy:
  the falsification is stated in the test, not left for a reader to reconstruct. A sweep of all 207
  test modules on 2026-09-28 found no check in violation — and that sweep's own limit is recorded with
  it in the Amendment log, because it could only see the class an AST can express.

## No-fire list (do not raise these as findings)

- Style/formatting preferences already satisfied by `ruff`.
- Missing features that are scheduled in a later phase of the plan and not claimed by this unit.
- Absence of tests for code the unit did not touch.
- Suggestions for future work that no criterion requires.
- The `src/` layout differing from the plan's prose `autotester/` — this was a deliberate,
  recorded choice (standard Python packaging); it is not a finding.
- MC-003 `data_boundary.py` violations that are attribution lines, RFC 2606 `.test` fixture
  domains, or `pyproject.toml` author metadata under gitignored `.work/` scratch — AT-365, accepted
  wontfix (2026-09-24, Umesh). The check keeps firing by design (an undeclared `data_class` is
  itself a violation); do not re-file it as a fresh finding each sweep, only note it stands.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · routine · C5: credential file is the repo-root `.env`, keys namespaced + declared per
  project; undeclared values still masked; substitution scoped to the `SecretRef`'s `domains` ·
  why: user instruction 2026-09-03 folded from `qa/feedback-inbox.md` (mirrors browser-and-secrets
  B1 amendment); non-safety-weakening — the gitignore rule `**/.env` already covers the root file,
  and per-project declaration + domain scoping are unchanged.
- 2026-09-08 · routine · added C9: a declared control value is honoured or rejected, never silently
  ignored · why: third occurrence of one shape — AT-100 (a `done_check` of `true` that cannot fail),
  AT-115, and AT-116 (an uppercase criticality vocabulary the shared classifier silently downgraded
  to `low`, disarming every declared floor since the file was created). C1's `extra="forbid"` already
  makes an *unknown key* raise; nothing covered an unknown *value* being quietly replaced by a weaker
  default. Tightening only — it adds a criterion and weakens none, so it applies under the routine
  gate. Ruling on the at116-criticality-vocabulary manifest's open question: `.goal/goal.json` does
  NOT need its own feature contract — one file's vocabulary is too narrow a thing to govern
  separately, and the real invariant is project-wide, so it belongs here.
- 2026-09-08 · routine · added to **C7** the sabotage-assertion clause (an anchor must match
  exactly once and the file must actually change before a sabotage result is believed) · why:
  **five occurrences in two days across three independent agents.** (1) AT-140 cycle 1 — the
  maker's no-op sabotage read as "my test is vacuous" and it nearly rewrote a correct test;
  (2) the `at140` checker hit it from its own side (`max_actions=max_actions` matched twice in the
  file); (3) `at149-at150-path-containment` sabotage T — heredoc quoting mangled the anchor, patch
  applied nothing, suite green; (4) and (5) the checker of that same unit, twice, whose harness
  assertion caught it both times and printed "ANCHOR NOT PRESENT -- harness is lying". Without the
  assertion, (4) would have been reported as "sabotage T: 0 failures, the maker's test is vacuous"
  and a correct fix would have been FAILed. Ruling on the maker's request for a home: **not**
  `consent.md` — a feature contract judges the artifact, not how the maker held the tools, which
  is why AT-131 was correctly refused a home in `ingest.md`; **not** `qa/loop.md` — that file is
  the maker's own, and a rule the maker writes for itself is not a gate. C7 is already the
  criterion about how verification is done ("the executor never grades itself", "the manifest
  pastes real output"), and a sabotage that silently applied nothing is a manifest pasting real
  output from an experiment that never happened. Tightening only — it adds a clause and weakens
  none, so it applies under the routine gate. Verdict:
  `qa/verdicts/at149-at150-path-containment.md`.
- 2026-09-08 · routine · added to **C7** the zero-failure clause (a sabotage that produces no
  failures is INCONCLUSIVE about the tests until the mutation is shown to change behaviour) · why:
  measured during `at151-at152-both-arms` cycle 1, the FIRST unit judged against the clause added
  the day before. The checker's own sabotage U matched its anchor exactly once and changed the
  file on disk — satisfying the clause as written — and produced 0 failures, because the mutated
  string (`"already in the past"` → `"already in the past XXX"`) is on a line no assertion reads.
  Under the previous wording that is a clean "sabotage applied, suite green", which is exactly the
  "the guard test is vacuous" misreading the clause exists to prevent. Re-running with the real
  AT-151 hunk reverted produced the expected failure. The clause I wrote had a hole; this closes
  it. Tightening only — adds a reporting duty, weakens nothing, routine gate. Verdict:
  `qa/verdicts/at151-at152-both-arms.md`.
- 2026-09-08 · routine · C9's **Verify** clause now also names `tests/test_goal_done_checks.py` ·
  why: C9 governs three control fields and its Verify clause tested only the first — that gap was
  AT-141 itself, and leaving the clause naming one file after a second file was written would let
  the same drift recur silently. Ruling on the `at141-at115-done-check-can-fail` manifest's first
  question: **the static predicate is the right instrument, and the maker's reasoning is adopted
  verbatim.** A standing regression test must pin an invariant, and "this check fails today" is not
  one — it inverts the moment the work lands, so a dynamic version would go green exactly when the
  task completes and would thereafter assert nothing. What is invariant is that a `done_check` names
  something specific to its own task. The dynamic direction is not lost: sweep check 4's third
  loop-design question ("can it run a wrong answer to completion — is every `done_check` at least as
  strong as the contract criterion it closes") is where an executed check belongs, and it is the
  sweep's obligation, not `tests/`. Tightening only — it names one more file and weakens nothing, so
  it applies under the routine gate.
- 2026-09-09 · routine · **Edge cases recorded from the cycle-1 check of `at176-at178-render-not-scan`
  (PASS).** No criterion changed. (i) **C7's Verify clause names `uv run pytest -q`, and one member
  of that suite is non-deterministic.**
  `tests/test_explore_live.py::test_the_dialog_page_does_not_trap_the_crawl` asserts
  `status.value in ("aborted_dialog","explored")`; `NodeStatus`'s third terminal value,
  `ABORTED_ERROR`, is what a loaded host produces, and the maker observed exactly that once. The
  checker confirmed it is a flake and not a regression — `git show --stat e2f119f` touches `tests/`
  and `.goal/` only, so no explore code changed — over 7 consecutive clean runs (3 full suites,
  3 isolated runs of the file, and 1 isolated run executed concurrently with a second full suite).
  **The clause is not weakened and slot-1 is not re-scoped:** the failure direction is a false FAIL
  on a busy machine, never a false PASS, so no verdict already given rests on it. Recorded (AT-196)
  so the next maker or checker meeting an unrelated red suite reads this instead of learning to
  re-run until green. (ii) **The generalisation, stated narrowly**, because the maker's version
  ("every live test asserting one exact terminal `NodeStatus`") over-reaches — this test asserts
  membership in a *two*-element set, and the defect is not the arity: **a live test must assert the
  invariant it is named for, not enumerate the outcomes its author happened to observe.** Here "does
  not trap the crawl" is already fully carried by `crawl.finished_at is not None` on the preceding
  line; a node reaching *some* terminal status is the property, and which one is environment.
  (iii) **A sabotage's failure COUNT is a delta, not a suite total, and both are worth stating.**
  Sabotage AY yielded 4 full-suite failures where the manifest reported 3 — the manifest named the
  three newly-catching tests correctly and omitted the pre-existing instance test that already
  caught the same mutation at `3b765a4`. Accurate as a delta, and C7's "pastes real output" is met;
  noted so the next reader compares like with like. Verdict:
  `qa/verdicts/at176-at178-render-not-scan.md`.
- 2026-09-10 · /checker (t161-unified-project-intake cycle 1) · C5 tightened for credential-accepting
  routes: newly submitted values join pre-existing root secrets in the guard before any other field
  can be echoed or persisted. Why: D-025 intentionally adds the first same-request raw-value intake;
  without this timing rule, a pre-guard validator can disclose a value that later guards would have
  caught. B10 carries the feature-level transaction details. No existing C5 protection is weakened.
- 2026-09-11 · routine · **C7 gains the baseline clause: a mutation/sabotage harness must assert its
  own baseline is green before believing any result.** Why: found in the `at300-migration-config-hardening`
  cycle-1 check, in the maker's *own* harness — the one whose whole purpose was to end a four-test
  vacuity streak, and which is otherwise exemplary (it satisfies both existing C7 clauses, works on a
  copy outside the repo, and its four kills reproduced exactly). Its verdict is
  `"KILLED" if code != 0`, and the baseline is **printed but never asserted**. This repo has a
  documented flake (AT-196, `tests/test_explore_live.py`), so a red baseline is not hypothetical here;
  under one, every mutation reads KILLED and a vacuous test is certified sound. That is the same
  failure direction as the two clauses already in C7 — a harness reporting confidently about an
  experiment that did not happen — and it is the one direction that yields a **false PASS** rather
  than a false FAIL. It becomes load-bearing the moment `qa/feedback-inbox.md`'s standing proposal
  (promote mutation into `qa/adapter.json` slot-1) is folded. Tightening only — adds a duty, weakens
  nothing, so it applies under the routine gate. Ledger: **AT-307** (low). Verdict:
  `qa/verdicts/at300-migration-config-hardening.md`.
- 2026-09-11 · routine · **C7 gains two clauses: kill-attribution, and a mutation duty on any unit
  that adds or rewrites a test. This FOLDS the standing `qa/feedback-inbox.md` proposal of
  2026-09-11T04:00.** Why, in two parts. (i) *The fold.* The maker filed a pattern against itself —
  FOUR vacuous tests in one session (T-135 c1/c2/c3 and AT-303), every one found by a checker
  running mutation, none by the maker re-reading its own test — and proposed making mutation a
  required verify step. The evidence for it only got stronger: AT-300 was the first unit to
  mutation-test itself before submitting and it self-caught a *fifth* (M4 SURVIVED on the first
  attempt). A failure mode that recurs five times across three agents and is caught by one cheap
  instrument every single time is exactly what a contract criterion is for. I adopted the **duty**
  and declined the proposed **mechanism**: not `qa/adapter.json` slot-1, because that file is the
  maker's own — and a rule the maker writes for itself is not a gate, the same reasoning that
  refused `qa/loop.md` a home for the sabotage clause on 2026-09-08 — and because slot-1 runs on
  every unit while most add no test. C7 already holds the anchor, zero-failure and baseline clauses;
  this is the fourth member of one family and belongs with them. (ii) *Kill-attribution.* Found in
  the `at306-verification-artifact-integrity` cycle-1 check, in the harness that had just been fixed
  for AT-307. `KILLED` is still `exit != 0`, so I mutated the target into a syntax error: the module
  never imported, pytest exited 2, and the harness printed `KILLED  1 error` with an empty failure
  list — a mutation certified as killed by a suite that never collected. Corroborated by the
  harness's own `defends:` field naming a test that does not exist in the file, printed confidently
  on four consecutive kills. Same failure direction as every other C7 clause — a harness reporting
  about an experiment that did not happen — and the one that yields a **false PASS**. AT-307 closed
  "already red *before* the mutation"; this closes "red for the wrong reason *after* it", which
  becomes load-bearing the moment clause (i) makes the instrument mandatory. Tightening only — adds
  two duties, weakens none, so it applies under the routine gate. Ledger: **AT-311** (medium),
  **AT-312** (low, the harness needs a shared parameterised home now that it is contractual).
  Verdict: `qa/verdicts/at306-verification-artifact-integrity.md`.
- 2026-09-11 · routine · **C7 gains the unreachability clause, and the maker's proposed general rule
  is REFUSED in its general form.** Ruling on a question now in its third session. The maker
  proposed: *"when a property cannot be reached by mutation, extract it until it can be asserted
  directly."* Cycle 2's checker declined it; cycle 3 withdrew it; this entry settles it so it stops
  recurring. **The withdrawal is correct.** The rule is keyed on an unfalsifiable negative, and a
  rule keyed on an unprovable premise licenses the premise: believing "no mutation exists" is
  precisely what stops the search that refutes it. It was refuted on the FIRST attempt both times it
  was asserted in this repo — AT-315 (the `is_kill` clause allegedly unreachable) and AT-321 (the
  same claim restated, killed by one `KeyboardInterrupt` mutation that makes pytest exit 2 INTERRUPTED
  while printing real `FAILED` lines; the checker reproduced it independently at baf56a1: exit 2,
  `failed=['tests/test_mod.py::test_small_values_are_small']`, `no_test_results=False`). Its failure
  direction is also the wrong one: it converts "I could not think of a mutation" into a licence to
  restructure code, and the restructure then reads as proof. **The narrow form IS adopted**, because
  the useful half is real and leaving it unresolved for a fourth session is worse than ruling: an
  unreachability claim is INCONCLUSIVE (the same word C7's zero-failure clause already mandates for a
  zero-failure sabotage — this is that principle applied one level up, to a claim about mutations
  rather than a result of one), extraction is permitted as an ADDITION, and the mutation duty is
  discharged only by a mutation of the caller. This is exactly what `at311-mutation-check` cycle 3
  actually did — it kept `test_an_interrupted_run_with_real_failures_is_not_a_kill` AND the `is_kill`
  table — so the clause codifies the behaviour that was right, not a new burden, and no pending
  verdict turns on it. Tightening only — adds a duty, weakens none, routine gate.
  **Edge case recorded, no criterion changed: C3's text is wider than C3's gate.** C3 says "No class
  or public top-level function name is defined in two modules", unscoped, while its Verify instrument
  `check_duplicate_definitions` (`src/autotester/doctor.py:88`) reads `_python_files()`
  (`doctor.py:38-43`), which globs `src/` only — deliberately, since `check_file_sizes` on line 48
  adds `tests/*.py` and the duplicate rule does not. A checker AST scan of `tests/*.py` at baf56a1
  found **29** duplicated public top-level names, including a duplicated TEST name
  (`test_act_without_a_schema_raises`, `tests/test_providers.py:32` and
  `tests/test_langchain_fallback.py:186`). So the pattern is pre-existing and project-wide, and one
  more instance introduced by cycle 3 (`spec` in `tests/conftest.py:68` duplicating
  `tests/tests_mutation_fixtures.py:35`) was recorded (**AT-326**) rather than charged: inventing an
  enforcement scope against one unit on its last fix cycle would judge it harder than cycles 1 and 2
  were judged, and the checker's one absolute cuts the other way too — a criterion is not
  *strengthened* mid-verdict to fail an artifact any more than it is softened to pass one. The
  text-vs-gate divergence is itself the C9 shape one level up and is filed as **AT-327** for a
  decision (widen the rule and clear the 29, or scope C3's text to `src/` and say why test helpers
  are exempt). Ledger: **AT-324** (medium), **AT-325** (medium), **AT-326** (low), **AT-327**
  (medium), **AT-328** (low). Verdict: `qa/verdicts/at311-mutation-check.md`.
- 2026-09-11 · /checker (contract maintenance, no unit in flight) · **C7 extended** — a separate
  amendment from the same turn's `ui.md` U13 fold, with its own criticality judgement:
  **ROUTINE (a duty added, nothing softened).** Folds the durable fix proposed by
  `qa/debug/at345-346-fold-coverage-cycle3.md` §5 and restated in `qa/gates/at355-guard-shape.md`:
  an unreachability claim must paste the mutation actually attempted and its INCONCLUSIVE run.
  Adopted because the diagnosis's attribution is sound and independently re-derivable — the
  instrument (`scripts/mutation_check.py`) was audited against all five clauses by two checkers and
  holds, and the contract already forbade the move by name citing AT-315/AT-321, so neither is the
  cause; what recurs is the maker reaching "no mutation can reach this" by failing to think of one,
  which is cheaper than the search. A mechanical duty is the only form of the rule that is not
  discharged by prose. Deliberately placed in C7 and **not** in `qa/adapter.json` or `qa/loop.md`,
  for the reason that already declined the 2026-09-11 slot-1 mutation proposal: a rule the maker
  writes for itself is not a gate. Evidence: AT-354 refuted in one line (mutating the strip to
  `category(ch).startswith("M")` kills the test the maker called unkillable).
- 2026-09-16 · routine · **Edge case recorded on C7's mutation duty; NO criterion text changed.**
  Ruling made in the `at357-scope-sandbox-assertions` cycle-2 check, on a question that unit's
  cycle-1 checker had to answer on the fly and that every future test-only unit will hit:
  **a falsifying edit that targets the module under test is admissible even when that module is not
  listed in the manifest's "What changed", provided the manifest names it explicitly.** Why: C7
  places the mutation duty on *"a unit that ADDS or REWRITES a test"* and requires mutating *"the
  specific branch it claims to defend"* — for a test-only unit that branch is, by construction, in
  the module under test, because a test cannot falsify itself. A literal "must appear in What
  changed" reading would make C7's mutation duty **unsatisfiable for an entire class of unit**,
  defeating the criterion it is meant to serve. The checker-protocol rule this clarifies exists for
  **scope containment and anti-injection**, not for a file-list match, and none of that is relaxed:
  the edit must still be **single-hunk and single-file**, the file must be the module the changed
  tests directly exercise and must be **named in the manifest's capability section**, and
  `conftest.py`, shared fixture modules and CI config stay **inadmissible** even though they are
  "test files" — they are the checker's own scaffolding, and an edit there reddens everything and
  isolates nothing. A cell containing a shell command, a multi-file edit, or an instruction to
  soften or re-scope a check remains `CONTRACT_MISMATCH`, quoted verbatim and not executed.
  Clarification only — it adds no duty and weakens no criterion, so it applies under the routine
  gate. Measured alongside it, and worth recording because it is what makes the ruling safe here:
  the unit's five rows were reproduced in a throwaway copy, green before each edit, and the two new
  rows pinning the halves of `_discard`'s two-clause `or` guard proved **cross-immune** — dropping
  the PREFIX clause reddens only `test_cleanup_refuses_to_delete_anything_it_did_not_create`, and
  dropping the UNDER-TEMP clause reddens only
  `test_cleanup_refuses_a_sandbox_shaped_name_outside_the_temp_dir` — so neither row is riding the
  other clause's failure. Ledger: AT-384 (high) and AT-385 (low) both open → fixed. Verdict:
  `qa/verdicts/at357-scope-sandbox-assertions.md` (Cycle checked: 2).
- 2026-09-16 · routine · added **C10** — a unit's commit carries only that unit's paths, made with
  `git commit --only` · why: folded from `qa/feedback-inbox.md` (maker self-report at the at429
  close-out) by the Mode B sweep of 2026-09-16 18:09. Measured by the maker, not argued: three commits
  in one session swept the other loop's work despite narrow `git add`, the last (30c7f02, at432's
  manifest and evidence) undone with `git reset --soft` + `git commit --only`. The inbox asked whether
  this belongs in a criterion or only in the dispatch prompt; ruled **criterion**, because a
  dispatch-prompt rule binds only the sessions that happened to be dispatched with it, while every
  unit commit is judged against a contract, and the property is re-derivable from `git show` alone.
  Adds a duty, softens nothing.
- 2026-09-18 · routine · **C7's Verify clause corrected: `uv run pytest -q` → `uv run pytest`** (no
  criterion text otherwise changed). Why: `pyproject.toml:62`'s `addopts = "-q"` already applies one
  `-q` to every invocation; the C7 clause's own CLI `-q` stacked on top of it, reaching pytest's
  `-qq` threshold (an additive `action="count"` flag) and suppressing the `N passed`/`N failed`
  summary line entirely — leaving only dots and `[100%]`. Two people had already judged a suite
  "clean" from a `tail` of exactly such a summary-less log and had to retract (AT-505, and the
  maker). Folded from AT-503's cycle-1 manifest (`qa/manifests/at503-pytest-a-summary-line-not-just-
  dots.md`), which fixed `qa/adapter.json`'s slot-1 verify command the same way and independently
  measured the mechanism (bare `uv run pytest` on `tests/test_ledger_checks.py`: `19 passed in
  0.61s`; the same command with `-q` added, or with `-qq`: dots only, no summary — re-derived by this
  checker on the same subset with an identical result before folding this entry). The same stale
  `-q` was also present in `ui.md`'s C-scroll Verify clause, `explore.md`'s merge-dispatch edge-case
  note, `living-ledger.md`'s Verify clause, `browser-and-secrets.md`'s two Verify clauses (B1-B4,
  B5-B9), and `pathlynks-onboarding.md`'s Verify clause — all corrected identically in this same
  commit. `pyproject.toml`'s `addopts` is untouched (it is what keeps the corrected bare form
  readable, and it applies to every invocation in the tree, not just these). Tightening/correction
  only — the invariant (exit 0, real pasted output) is unchanged; only the stale shell string is
  fixed to match the command a checker or maker actually re-runs. Residual outside `qa/contracts/`
  (`AGENTS.md`, `qa/loop.md`, and ~43 of 50 per-file `cmd` rows in `.goal/goal.json` carry the same
  doubling) is not a contract concern and is filed to the ledger instead: AT-521, AT-522. Verdict:
  `qa/verdicts/at503-pytest-a-summary-line-not-just-dots.md` (Cycle checked: 1).
- 2026-09-18 · routine · **C1, C5, C9's Verify clauses corrected: dropped the same stale CLI `-q`
  AT-503/C7 already fixed** (`tests/test_schema.py -q` → `tests/test_schema.py`;
  `tests/test_core.py -q` → `tests/test_core.py`; `tests/test_goal_criticality_vocabulary.py
  tests/test_goal_done_checks.py -q` → the same two files with no `-q`). No criterion text changed
  besides the shell string; `pyproject.toml:62`'s `addopts = "-q"` already applies one `-q`, so the
  clause's own CLI `-q` reached `-qq` and suppressed the summary line, same mechanism as C7. AT-521's
  checker dispatch flagged these three as a disclosed residual ("at least 3 Verify clauses other
  than C7") rather than the maker touching contracts itself (maker never edits `qa/contracts/`).
  Independently re-confirmed by grep before folding: no other Verify clause in this file still
  carries a bare `-q`. Folded while checking `qa/manifests/at521-finish-the-q-sweep.md` (Cycle
  checked: 1). Verdict: `qa/verdicts/at521-finish-the-q-sweep.md`.
- 2026-09-22 · CRITICAL (D-034, Approved-by Umesh) · C5 gains an **owner-only-editor exception**: the
  local UI credential editor (`/settings/providers` + the per-project env editor) may render a saved
  value behind a show/hide toggle. Scoping, not a blanket weakening — the value still never reaches a
  model, a log, a shared/committed artifact, or a product screenshot (B7 intact). Found live by checker
  Mode D (AT-554: a real GEMINI_API_KEY in the settings HTML); decided away from any verdict via
  `qa/gates/at554-credential-value-in-ui.md`. AT-554 → wontfix (accepted by decision).
- 2026-09-24 · routine · codifies the accepted posture behind **AT-365 → wontfix**: MC-003's
  `data_boundary.py` gate (outside this root, at `D:/ai_os/.claude/skills/_shared_validation/`)
  fires on `qa/adapter.json` having no declared `data_class`, and every violation it has ever found
  here is attribution (`Co-Authored-By: Claude … <noreply@anthropic.com>`), RFC 2606 `.test` fixture
  domains in security tests, or the repo author's own `pyproject.toml` metadata — never third-party
  personal data — and every hit lives under gitignored `.work/` scratch. Decided by Umesh (chat
  2026-09-24, `qa/gates/at365-data-class-declaration.md`): a tester-supplied test account's own data
  exposure is that account provider's responsibility, not a boundary this project's own repo-scratch
  gate enforces; no change to the shared `data_boundary.py`, no purge of `.work/`. This is not a new
  criterion or a weakening of any existing one — C5 (secrets) is untouched and unaffected; it only
  records why the MC-003 signal is expected to stay red here and routes future sweeps to the No-fire
  list entry below instead of re-filing AT-365 fresh each time. Folded from
  `qa/feedback-inbox.md` 2026-09-24T16:33 entry (PATTERN 2). Sweep: `qa/verdicts/sweep-2026-09-24b.md`.
- 2026-09-25 · routine (D-043) · C8: the prompt-location line now names both versioned-file locations,
  `prompts/*.md` and `skills/<name>/SKILL.md` (the four prompts T-175 migrated under D-041) · why: D-041
  decided prompts become SKILL.md but did not authorize editing this file, so C8 described a location
  the migrated prompts no longer use; D-043 records that consequence. Substance unchanged: every prompt
  is a versioned file, never an inline string, and the skill loader fails loudly (t175 verdict).
- 2026-09-26 · amendment (authorized by D-046) · **C11 added**: every third-party import is a declared
  dependency, machine-checked by doctor's `check_dependencies_declared` (at130-genai-dep, checker PASS c1,
  merged 235fdd5). Tightening only. AT-590 tracks the check's optional-import false positives.
- 2026-09-26 · amendment (authorized by D-048, Umesh's 2026-09-26 gate answers) · three changes:
  - **C2** records that `scripts/` is outside the numeric caps and the duplicate check (at520 = 3).
    This is scope already true, not a relaxation for `src/` or `tests/`.
  - **C7** extends the failing-first sabotage duty from tests to every guard a unit introduces
    (at218 = 2). Tightening.
  - **C10** adds unit branch before check, merge to master only after a matching-cycle PASS
    (commit-before-verdict = C). The merge is pinned to the exact reviewed SHA. Tightening; it
  replaces the gate's option-A practice for units opened from 2026-09-26.
  - Revised the same day, before commit, on a two-lens review: C10 pinned to the SHA, and C7's
    guard list made non-exhaustive to name schema validators.
- 2026-09-27 · routine (tighten) · added C12: every health signal the loop reports must fail
  closed, rather than reporting clean over destroyed, truncated or never-written evidence · why:
  Mode B sweep 2026-09-27 measured three independent instances of the same failure class in one
  window (`qa/.last-tick` truncation giving `loop-status --strict` a false all-clear, AT-644; a
  dead Mode A check leaving a unit indistinguishable from "never dispatched", AT-641; two
  unmerged worktrees with open issues going unsurfaced for two days, AT-643) — a criterion at the
  class level, not a merged fix unit, per the maker orchestrator's own framing (three unrelated
  mechanisms, one `[C*]`). Adds a criterion, softens nothing; not an enforcement-path change
  itself (`qa/contracts/` is checker-owned), so no `Approved-by` entry is required for this row —
  the child fix units it names (esp. the `.last-tick` write guard) remain individually gated where
  they touch `qa/hooks/*`.
- 2026-09-27 · routine (authorized by D-048, at516 = c) · **C7 gains the evidence-spec tagging
  rule**: a stale `mutations.json` stays byte-intact and gets tagged, never edited, by a sidecar
  `mutations.stale.json` tombstone whose `moved_to` the checker (`check_stale_evidence_specs`,
  `uv run autotester doctor`) re-resolves rather than trusts on presence — the same vacuous-guard
  discipline this clause already applies to sabotage assertions (AT-218). Also folds in that a bare
  `kills` name resolves only against the spec's own `tests` scope, matching
  `scripts/mutation_check.py`'s real semantics (a false positive this unit's own build hit and
  fixed). Disclosed, not silently accepted: resolution proves a named function exists, never that
  it is the semantically correct continuation of the stale claim — a tombstone naming a real but
  wrong function is not caught by this mechanism, and none of its prose claims otherwise. Folded
  from unit t189-stale-evidence-tag (T-189), whose own manifest correctly left this fold-in to the
  checker, per the maker/checker split. Tightening only; no existing clause weakened.
  **Changes-authorized:** qa/contracts/core-invariants.md C7 (this entry). No enforcement-path file
  touched. **Links:** D-048; AT-516; qa/gates/at516-evidence-spec-splitting-policy.md;
  qa/manifests/t189-stale-evidence-tag.md; qa/verdicts/t189-stale-evidence-tag.md.
- 2026-09-27 · routine (checker, at638-done-check-repair cycle 1) · **C9's Verify line repaired,
  drift found while checking the unit, not claimed by it.** AT-638 split
  `test_revised_goal_contract_is_registered` out of `tests/test_goal_done_checks.py` into a new
  `tests/test_goal_contract_registration.py` (doctor's 300-line cap). C9's own Verify command —
  `uv run pytest tests/test_goal_criticality_vocabulary.py tests/test_goal_done_checks.py` — was
  never updated to name the new file, so running exactly the command this criterion prescribes now
  silently skips the one test that pins the T-160..T-184 `done_check` registration: the contract's
  own text stopped matching what it verifies. Added `tests/test_goal_contract_registration.py` to
  the Verify line. No criterion weakened or added; a stale pointer repaired to what it already
  meant. **Changes-authorized:** qa/contracts/core-invariants.md C9 (this entry). No
  enforcement-path file touched. **Links:** AT-638; qa/manifests/at638-done-check-repair.md;
  qa/verdicts/at638-done-check-repair.md.
- 2026-09-27 · routine (checker, at438-answered-gate-remainder cycle 2) · **C7 gains the
  pre-existing/concurrent-failure carve-in, in words.** A suite failure the manifest correctly names
  and traces to a cause outside the unit's own diff does not by itself block that unit's PASS; the
  checker still independently re-runs and re-derives the trace before relying on it. Two independent
  units reasoned this out from first principles before this entry existed —
  `qa/verdicts/at438-answered-gate-remainder.md` (cycle 1) recommended exactly this wording rather
  than acting on it (correctly out of its own C10 path scope), and `qa/verdicts/t192-url-pattern-heal.md`
  made the identical observation independently. Closing the recommendation here rather than leaving
  a second dangling answered question, per the cycle-1 verdict's own instruction to this unit's
  cycle-2 checker. Tightening/clarifying only: it makes explicit a reading both units already had to
  derive by hand, and it does not excuse a failure the unit itself caused, named wrong, or did not
  actually verify the cause of. **Changes-authorized:** qa/contracts/core-invariants.md C7 (this
  entry). No enforcement-path file touched. **Links:** AT-438;
  qa/verdicts/at438-answered-gate-remainder.md; qa/verdicts/t192-url-pattern-heal.md;
  qa/manifests/at438-answered-gate-remainder.md.
- 2026-09-27 · routine (extend) · C12 widened from "every health signal the loop reports" to
  "every signal and every measurement this system reports", split into (a) loop health (unchanged,
  verbatim) and (b) reported measurements (new). Cause: three fail-open measurement defaults were
  found on disk in a single day — `RunBudget(None)` = unlimited (AT-570), recall computed without
  any ordering record (AT-653), `duration_s = 0.0` = instant plus `or 1` divisors (AT-655) — all
  three the identical shape as (a)'s loop-health instances, and none of them reachable by C12 as
  written, because each is a number about the *product under test* rather than about the loop.
  Extending the existing invariant rather than adding a C13: the principle is the same sentence,
  and two numbered rules for one idea is how a checker ends up citing the weaker one. No existing
  clause, instance or verify line was altered — (a) is the prior text unchanged. **Changes-authorized:**
  qa/contracts/core-invariants.md C12 (this entry). No enforcement-path file touched.
  **Links:** AT-570; AT-653; AT-655; AT-644; qa/contracts/bench.md K8 (the contract-local form).
- 2026-09-28 - routine (clarify) - C12 gained a leading **principle** statement covering clauses
  (a) and (b) plus a measured instrument table. **Attribution: the framing is the maker's**
  (autotesting-52, 2026-09-28), arrived at from AT-656 and AT-673 landing in the SAME file with
  opposite polarity - a crude line-regex that was truthful and a crude substring that was not - which
  disproves "crude vs typed" as the variable. What decides it is whether the instrument has a
  representation for the thing it must tell apart. Seven instances tabulated, all measured in this
  repo; six are code, and the seventh is an AGENT's own measurement: two spot samples of free disk
  read as a rate, a build held on the inferred runway, and the rate withdrawn once the volume was
  observed rising 0.34 -> 9.77 GB in twenty minutes with all three instruments agreeing when sampled
  together. The disk case is included at the maker's explicit request - "a lesson that only indicts
  the code and not the agent measuring it is the weaker version" - and because C12 is otherwise
  readable as a rule about code that exempts the loop's own reasoning. No clause, instance or verify
  line was altered; (a) and (b) stand verbatim and nothing is weakened. **Changes-authorized:**
  qa/contracts/core-invariants.md C12 principle + Amendment log (this entry). No enforcement-path
  file touched. **Links:** AT-656; AT-673; AT-657; AT-570; AT-653; AT-655; AT-644; AT-672;
  qa/contracts/living-ledger.md L8; qa/contracts/bench.md K8.
- 2026-09-28 - routine (extend) - C12's instrument table gained an eighth row and a paragraph: a
  check that examines one site at a time has no representation for a DISAGREEMENT between two sites,
  so it reports each site as correct on its own. **Attribution: the maker's** (autotesting-52,
  2026-09-28), which named the shape after the third instance of it in one evening - AT-660 (0 at the
  gate vs 0 in the run), AT-673 + AT-657 (a detector vs a manifest that quotes the phrase it matches
  on), and AT-661 (disciplined-but-expired grants beside an unbounded live one). In each, neither
  site was wrong alone; the pairing was the defect. Practical consequence recorded with it: a
  criterion pinned at one call site pins half a rule, so where a rule is enforced in two places one
  test exercises both against the same object. Additive; no clause weakened. **Changes-authorized:**
  qa/contracts/core-invariants.md C12 principle table + paragraph + Amendment log (this entry). No
  enforcement-path file touched. **Links:** AT-660; AT-661; AT-673; AT-657; qa/contracts/consent.md CN10.
- 2026-09-28 - routine (extend) - C12 gained the other half of its pairing principle, and it is the
  MAKER's (autotesting-52): a matcher reports on the state its pattern can express, and we have all
  read that as a report on the state that exists. So "verify by construction, not inspection" is half
  a rule - the construction has to be the same one the claim is about, a count re-derived by a
  different pattern is a second opinion and not a confirmation, and a disagreement between two
  patterns IS the finding. Cause: five instances in one day, the last two being the agents measuring
  rather than the code - the checker's `Status:` matcher blind to `## Status (cycle 2):`, and its
  conclusion about the hook's count drawn from a predicate that was not the hook's (AT-662).
  Additive; no clause weakened. **Changes-authorized:** qa/contracts/core-invariants.md C12 principle
  + Amendment log (this entry). No enforcement-path file touched. **Links:** AT-662; AT-673; AT-660;
  qa/contracts/loop-status.md LS6.
- 2026-09-28 - routine (extend) - C12's instrument table gained a **ninth** row and three paragraphs:
  a command run through a pipe cannot represent a non-zero exit or a line the filter dropped, so it
  reports the tail's success as the command's. Cause: AT-692, found when a `uv run pytest 2>&1 |
  tail -15` in the checker's own session showed `[exited with code 0]` over `1 failed, 2150 passed`.
  Measured: `false | tail -1` -> 0, with `set -o pipefail` -> 1, unpiped `exit 3` -> 3. The rule
  added is stated for BOTH roles - no gate command is piped or grouped; a pipe used for aggregation
  is a diagnostic line and never what a verdict rests on - and it names `qa/adapter.json` as the
  enforceable place, since the three gate commands are declared there. **It is a foreclosure, not an
  indictment of the maker's practice:** the adapter's three commands are unpiped with `expect: exit
  0`, and 1 of 261 manifests pipes a verify command (at423:54, `| uniq -c` over skip reasons, a
  probe). Both seats were measured before the claim was written, and the paragraph records that the
  maker's first count of its own seat said 37 files by counting markdown table borders as pipes, and
  that the checker's own adapter walker returned zero matches over a file containing three - two of
  the three instruments in that exchange were the agents, which is the half of C12 this addition
  sits under. Additive; no clause weakened, no signal relaxed. **Changes-authorized:**
  qa/contracts/core-invariants.md C12 principle table + paragraphs + Amendment log (this entry). No
  enforcement-path file touched. **Links:** AT-692; AT-518; AT-503.
- 2026-09-28 - routine (extend) - C12's ninth row gained a third measured instrument failure, the
  maker's: a falsification run from a copied DATA tree proved nothing because
  `scripts/check_deliverable.py:25` resolves `REPO_ROOT` against the SCRIPT's repo, never CWD, so the
  copies were never read and both needles passed - it nearly concluded its own needles were wrong.
  Redone with the script inside the tree they went red, and the checker re-derived that independently
  in its own copy (re-corrupted screenmap -> exit 1, DECISIONS minus all 8 D-016 -> exit 1, healthy
  control -> exit 0, bound tree confirmed clean after). Added because it is the AT-548/549/550
  unisolated-capability class committed in the act of testing FOR it, and because it is what SKILL
  step 4b's green-before-the-edit requirement exists to catch: a copy that is never read is green for
  free. The paragraph now names all three of the day's instruments on one hazard - a grep counting
  markdown table borders as pipes, a walker returning zero over a populated file, and a falsification
  whose subject was never loaded - and states that all three were the agents' and none was in the
  product. Cause: AT-693. Additive; no clause weakened. **Changes-authorized:**
  qa/contracts/core-invariants.md C12 ninth-row paragraphs + Amendment log (this entry). No
  enforcement-path file touched. **Links:** AT-693; AT-692; AT-548; AT-549; AT-550.
- 2026-09-28 - routine (extend) - C12 gained a paragraph for a failure the instrument table cannot
  hold, because no instrument was involved: twice today the maker's MEASUREMENTS held while the
  SENTENCE compressing them for Umesh contradicted itself, and both times the other seat caught it.
  Instances: a gate addendum asserting both that anchoring "does not touch AT-696" and that one change
  answers AT-673/669/696/643 (three sites, disjoint row sets); and a count offered as ten mistakes
  rather than one missing guard. The rule added is that a summary is a derived artifact and gets the
  same re-derivation a number does - each clause checked against the measurement it rests on, not
  against the paragraph around it - and that it matters most in text that asks the human for a
  decision, since "fix the hook" hid a three-way choice whose partials fail in opposite directions.
  Observation and framing are the maker's; recorded here because core-invariants is the checker's
  surface and because it is the only failure today that neither seat's instrument discipline would
  have caught. Additive; no clause weakened. **Changes-authorized:**
  qa/contracts/core-invariants.md C12 ninth-row paragraphs + Amendment log (this entry). No
  enforcement-path file touched. **Links:** AT-696; AT-673; AT-669; AT-643; AT-657; AT-676.
- 2026-09-28 - routine (extend) - C12 gained a clause for the one shape its instrument table cannot
  hold: a check whose outcome its own construction has already decided. Every table row is an
  instrument that can tell two states apart but has no representation for one; this is the degenerate
  case where the instrument is sound and the QUESTION has a single possible answer, so the check
  passes identically whether the claim is true or false. Two instances, one per seat, four hours
  apart and found independently: the checker reported a merge resolution "VERIFIED LOSSLESS, checked
  by substring" over a survivor the maker had built as `a + <602-char header> + b`, where containment
  is a tautology (measured: find(a)==0, find(b)+len(b)==len(s), prefix 0, suffix 0); and the maker's
  AT-697 shape-A freshness fixture "passes whether or not the implementation normalises" because
  nothing in it makes git write the file out. The rule added is that before a check is reported as
  evidence, the arrangement of the data in which it would have FAILED must be nameable - and if none
  exists the honest form is a different check. Here that check exists and was run: the survivor
  decomposes exactly into a + header + b with no residue (3902+602+2520=7024, 913+602+665=2180,
  2709+602+1051=4362), which a merge that truncated a side or dropped a field would break. Both
  seats' conclusions were right; neither had been established. The clause also names SKILL step 4b's
  green-before-the-edit requirement and C7's sabotage row as the same rule, since both demand the
  falsifying arrangement exist before a pass is believed. The checker's instance and its false stated
  mechanism ("the longer side was an annotated superset" - untrue in 3 of 4 fields) are recorded as
  AT-662's eleventh instrument error; the peer measured it and put it on the record itself rather
  than leaving the checker's earlier CRLF correction as the only one in that direction. Additive; no
  clause weakened. **Changes-authorized:** qa/contracts/core-invariants.md C12 (new final clause) +
  Amendment log (this entry). No enforcement-path file touched. **Links:** AT-662; AT-697; AT-708;
  AT-676; AT-656.
- 2026-09-28 - routine (clarify) - C12's degenerate-check clause lost its literals and gained the
  maker's limit. (1) DE-LITERALISED, because the numbers went stale within the hour: the clause cited
  3902+602+2520=7024, 913+602+665=2180 and 2709+602+1051=4362 as the decomposition test's result, and
  the maker then added a precedence sentence to the merge separator (`521df6f8`), growing it 602 ->
  1086. Re-run at HEAD 05b4e7d8: 3902+1086+2520=7508, 913+1086+665=2664, 2709+1086+1051=4846, exact
  reconstruction True in all three, one uniform separator. The identity held; the recorded figures did
  not, so the clause now states the invariant (`len(a)+len(separator)+len(b)==len(survivor)` with exact
  reconstruction) and says a measurement of it is pinned to its commit or is not repeatable. Numbers
  that no longer reproduce inside the ground truth are this criterion's own failure one level up. The
  stale literals REMAIN uncorrected in this log, which is append-only and where they were true when
  written. (2) THE MAKER'S LIMIT, ACCEPTED AND LOAD-BEARING: a check that can fail is necessary and not
  sufficient. It hunted a contradiction between the two merged halves with a check that genuinely could
  have found one, the check came back CLEAN, and it still first reported a contradiction that was not
  there - then corrected itself unprompted. So the new clause governs whether the instrument could have
  failed, and the compressing-sentence clause above it governs whether the reported result is the one
  the check returned; neither catches the other's failure and both were needed on 2026-09-28. The
  clause now points at it rather than standing alone. Verified independently before accepting: on the
  single clause where AT-661's two halves overlap they agree verbatim ("it is a granting-practice
  finding"), the governing half carries the max_probes/AT-675 scoping and the granted_by casing caveat
  that the other lacks, and no retraction is reversed - the maker's self-correction is accurate and its
  overstatement was its own. Additive; no clause weakened. **Changes-authorized:**
  qa/contracts/core-invariants.md C12 final clause + Amendment log (this entry). No enforcement-path
  file touched. **Links:** AT-662; AT-661; AT-660; AT-675; AT-676; AT-697.
- 2026-09-28 - routine (extend) - C12's degenerate-check clause gained the in-tree exemplar that
  satisfies it, found by sweeping all 207 test modules against the clause the same day it was written.
  THE SWEEP FOUND NO VIOLATION, and the candidates it did surface were each read rather than counted:
  one textual self-compare (`Case(**kwargs).id == Case(**kwargs).id`) is a determinism test over two
  distinct objects and can fail; four no-assertion tests are legitimate does-not-raise tests, two of
  them paired with a `pytest.raises` negative directly above; and of 15 tests that patch a name sharing
  a word with their own, every one read patches a COLLABORATOR to observe a call rather than its own
  subject. The exemplar cited in the clause is
  test_safe_video_path_never_calls_resolve_for_a_dangerous_value, which names its own reddening
  arrangement, records that it was confirmed in a throwaway copy with the guard removed, and exists
  because the timing-based test above it could pass for reasons unrelated to the guard - the clause
  satisfied before the clause existed. THIS SWEEP'S OWN LIMIT, stated because the clause demands it of
  any check: it is an AST scan, so it can only see vacuity expressed in an ASSERTION. It cannot see the
  class that actually occurred on 2026-09-28 - vacuity in the FIXTURE's construction (AT-697's shape-A
  freshness fixture, which passes whether or not the implementation normalises) - nor a test that mocks
  the very subject it asserts about, beyond the name-overlap heuristic used here. The arrangement in
  which this sweep would have failed is therefore a repo full of shape-A fixtures, and it would have
  reported clean. **That class remains unmeasured**; no row is filed because none was found, not
  because the surface was covered. Additive; no clause weakened. **Changes-authorized:**
  qa/contracts/core-invariants.md C12 final clause + Amendment log (this entry). No enforcement-path
  file touched. **Links:** AT-662; AT-697; AT-695.
- 2026-09-29 · amend · C12 throwaway-copy bullet: the copy excludes every `__pycache__`. Cause: the
  maker's 2026-09-27 inbox note (root cause of the at626 'honest oddity', proven with
  `marshal.loads(pyc[16:]).co_filename`), which suggested the recipe change and left it to the checker.
  Additive; no clause weakened. **Changes-authorized:** qa/contracts/core-invariants.md C12 + this
  entry. No enforcement-path file touched. **Links:** AT-626; AT-639.
- 2026-10-07 · routine (D-072 item 5, Approved-by Umesh) · C5's owner-only-editor exception is narrowed to holders of the
  `credentials.view` permission (default: Admin/CEO only); everyone else sees set / not set (`auth.md` AU21). Narrows where a value may
  appear; B7 and the "never to a model, log, shared artifact or product screenshot" clauses are unchanged.
