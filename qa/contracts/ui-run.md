# Contract — ui-run (triggering a real run from the web UI)

**Status:** ACTIVE. Amends `qa/contracts/ui.md`'s no-fire list, which previously deferred
run-triggering as "a future enhancement" (plan §3b,
`C:/Users/Lenovo/.claude/plans/great-when-you-really-iridescent-ocean.md`).

## Why this exists

Umesh: a non-technical user must be able to click a button and get a real, graded run — no
terminal. Before this, `ui/app.py` could only view state the CLI had already produced.

## Criteria

- **RU1 — a queued run, one real execution path, no second copy.** *(amended D-074, 2026-10-07; issue AT-789 as cited in the dispatch)*
  `POST /projects/{slug}/run` does **not** run in the web request: per `hosting.md` HO16 (D-072)
  the Test button returns a 303 at once and the run waits in the server queue (`queued`, then
  `running`, then `done`/`failed`/`refused`/`interrupted`). When the run starts, the queue worker
  calls the exact same `run_and_grade_case` (`stages/run_case_pipeline.py`) any CLI script would,
  via a real `BrowserSession` — never a mock, never a second copy of run/grade logic. The former
  "v1 is synchronous (the request waits for the browser to finish)" boundary is retired; queue
  semantics (FIFO, caps, restart survival) are judged under HO16-HO18, not here.
- **RU2 — honest failure before wasting a browser.** A project with zero cases → `400` before
  any browser starts. No AI provider configured (`LangChainFallbackProvider().available()` is
  `False`) → `400` before any browser starts. Both checked in that order.
- **RU3 — every case is run and persisted.** Every case in `store.list_cases()` gets a real
  result + verdict saved via the same `ProjectStore` methods the CLI scripts use, and a `Run`
  record is saved. The response redirects (303) to `/projects/{slug}/report` on success.
- **RU4 — global provider keys are actually visible to the running process.** A plain
  `uvicorn`/Docker process does not source `.env` on its own; `ui/app.py` must load it itself
  (matching the convention every real-run script already follows) so a key set via `.env` (or
  the future `/settings/providers` page) is genuinely usable from the web UI, not just from a
  script that happens to call `load_dotenv` itself.
- **RU5 — an entry-screen case never runs on a profile that was not removed (added 2026-10-11; issue
  AT-733; `core-invariants.md` C12(b)).** An entry-screen case (`_is_entry_case`) is meant to start
  from a genuinely logged-out state, which is why it gets a dedicated profile, `ProjectPaths(f"{slug}-entry-test").profile_dir`
  (`profiles/<slug>-entry-test`), wiped before its run (amendment log, 2026-09-04). The wipe is the
  only thing that makes that start state true, so it is a measurement and fails closed.
  - Before the case's browser starts, the profile directory is removed and then **positively
    established absent**. These are all failures: the removal raises (`OSError`, `PermissionError`),
    the directory is still present afterwards, or the presence check itself raises, so that absence
    cannot be determined. A directory that was already absent before the wipe is success. A
    presence test that reports "absent" when it errors (for example `os.path.lexists`) is the fail-open
    shape C12 forbids and does not satisfy this criterion.
  - On any such failure the case's `RawResult` is `ERRORED`, its error names the profile path and the
    cause (scrubbed like any other case error), and its verdict comes from `grade_errored_result`
    (the existing errored-result path, so never PASS and never FAIL). No `BrowserSession` is started
    for that case and the case is never executed. Every sibling case still runs and the Run record is
    still saved (RU3); the failure is one case's ERRORED, not a 500 and not an aborted run.
  - One behaviour on every path that runs an entry case: the serial path and the entry leg of a
    parallel run (both call `ui/run_execution.py::_run_entry_case`).
  - **Verify (by construction, C12(b)):** a test builds the unpopulated state and asserts the report
    says it. With the removal stubbed to leave the directory in place, and separately stubbed to
    raise `PermissionError`, a run containing one entry case and one sibling, once with a serial
    plan and once with a width-2 plan, ends with: the entry case `ERRORED`, its error containing the
    profile path, its verdict not PASS, the fake case runner never given the entry case id, no
    `BrowserSession` constructed for `<slug>-entry-test`, the sibling `COMPLETED` and the Run saved.
    The control: a healthy wipe of a directory holding a stale file leaves it absent and the entry
    case executes. Falsification (checker, throwaway copy, anchor matching once, copy green first):
    restore `shutil.rmtree(..., ignore_errors=True)` with no absence check; the stub-leaves-directory
    test must go red on its own named assertion. On Windows the checker may also hold a file open
    inside the profile (no share-delete) and expect `ERRORED`, not PASS; that probe is the checker's
    and is optional on POSIX, where deleting an open file succeeds.
  - **Does not require:** the reason a removal fails to be fixed, a retry, or a changed profile path.
    The criterion is that a case which cannot get its logged-out start refuses to run, not that the
    wipe always succeeds.

## No-fire list (out of scope for this contract)

- The queue itself, its caps, ordering and restart survival (`hosting.md` HO16-HO18); this
  contract only requires that the queued run reaches the one real pipeline *(amended D-074,
  2026-10-07: the former "background job queue is a fast-follow" line is superseded by D-072/HO16)*.
- Report enrichment (run history, inline screenshots, download buttons) — plan §3c, a separate
  unit/contract.
- The `/settings/providers` page itself — plan §3d, a separate unit/contract (RU4 only requires
  that *if* a key is set in `.env`, the running UI process can see it).

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for the real run-trigger route unit (plan §3b, RU1-RU4),
  checker-PASSed cycle 1 (`qa/verdicts/ui-run-trigger.md`, ledger F-024).
- 2026-09-04 · routine · recorded the `at044-entry-case-profile-isolation` fix (ledger F-030):
  `trigger_run` now gives an entry-screen case (`_is_entry_case`) a dedicated, wiped-before-
  every-run profile instead of the shared persistent session, fixing a real regression where
  the Run button reproduced the original guaranteed-INCONCLUSIVE bug. RU1-RU4 meaning unchanged
  (still the same one real pipeline, no second execution path) — this tightens *how* a session
  is chosen per case, not what the criteria require. Checker-PASSed cycle 1
  (`qa/verdicts/at044-entry-case-profile-isolation.md`). Found by sweep: shipped with zero
  contract-side trace until now (AT-048).
- 2026-10-07 · routine (correct; D-072 and `hosting.md` HO16 already decide it, D-074 date) · **RU1
  reworded**: the run is queued, not synchronous. The Test button returns 303 immediately and the run
  waits in the server queue (HO16); the synchronous v1 text pre-dated D-072 and now contradicted
  HO16. RU2-RU4 unchanged (RU3's 303 redirect now describes the enqueue response; the saved results
  and `Run` record are written by the worker). The one-real-pipeline requirement is unchanged. The
  ledger row the dispatch calls AT-789 is a different open row today (T-178 TDD order); the stale-RU1
  finding needs its own row from the sweep. **Links:** D-072; HO16; D-074.
- 2026-10-11 · routine (adds a criterion, weakens none) · **RU5 added: an entry-screen case never runs
  on a profile that was not removed.** The 2026-09-04 entry above recorded the wiped profile as an
  implementation fact and said "RU1-RU4 meaning unchanged", so no criterion ever required the wipe to
  succeed; the code at `ui/run_execution.py` `_run_entry_case` calls `shutil.rmtree(..., ignore_errors=True)`
  and starts the browser regardless, so a locked profile (a lingering Chromium on Windows) lets a
  logged-out entry case run logged in and PASS. The queue row and the old manifest cited "RU1/RU3
  (entry-profile amendment)"; no such text existed. · why: issue AT-733 (open, high), `core-invariants.md`
  C12(b) (a start state that was not measured must not read as the favourable one), D-080 item 6 (the
  defect is not accepted as risk; re-planned as one bounded unit with a 2-cycle cap). The proposed
  wording in `qa/briefs/at733-bounded.md` section 3 was adopted with these changes: the check no longer
  asserts a 303 (RU1 now queues the run), "verdict INCONCLUSIVE" became "not PASS, from
  `grade_errored_result`" (the contract states the property, not the grader's current label), "presence
  cannot be determined" is named a failure explicitly, and the optional Windows locked-file probe is
  assigned to the checker. **Links:** AT-733; C12(b); D-080; D-081; `qa/briefs/at733-bounded.md`.
