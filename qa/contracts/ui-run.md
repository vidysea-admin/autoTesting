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
