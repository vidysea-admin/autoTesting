# Build brief - t168-damage-control-report (T-168, readiness pass 2026-10-11, NOT YET DISPATCHABLE)

Written by a read-only readiness pass. Nothing here was built or run. Where the repo does not say, this brief says `unknown`.
Dispatch trigger: T-167 reaches a checker PASS merged to master (T-164 and T-165 are already done).

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- Tier: **M**. Trigger: multi-file behaviour that reads four existing evidence owners (persona/crawl, network evidence, run results, T-167's regression diff), plus a new shared report module and a public CLI/HTTP surface. No L trigger applies: no auth/tenancy change, no data write beyond the report file, no concurrency, no config/hook/CI change, and `pyproject.toml` is not touched.
- `Dual check: no`. Reason: no `security|auth|tenancy|prod-write <path:line>` trigger exists. DC4 (no secret in the report) is a security-shaped criterion, but the redaction code it relies on already exists (`src/autotester/core/redact.py`, `stages/network_capture.py:24` scrubs every URL before it becomes evidence) and the builder adds no new secret-handling path. If the builder renders any raw request URL or step text that did not pass through `Redactor.scrub`, escalate to L and require the dual check at that `path:line`.

## 2. Root and base

- Root: `D:/autoTesting`
- Base: the master commit where **T-167** (`t167-langgraph-regression`) lands with a checker PASS. T-167 is `pending` today (no `tests/test_regression_trigger.py`, no `langgraph` in `pyproject.toml`, `qa/QUEUE.md:259`). Record that SHA in the manifest. Master HEAD when this brief was written was `3a16616c`; it is NOT the base.
- Branch: `wave/t168-damage-control-report`
- Dependency note: `.goal/goal.json` T-168 `deps = [T-164, T-165, T-167]` (D-059 dropped T-155). T-164 done 2026-09-24, T-165 done 2026-10-07. T-167 deps are `[T-166, T-110]`, both done (D-055); it does NOT depend on T-179 (D-055, D-058).

## 3. Acceptance criteria (verbatim from `qa/contracts/damage-control-report.md`, status DRAFT, goes ACTIVE on T-168's first checker PASS)

### DC1 - Blocked or unvisited is NEVER rendered as pass

`coverage.md` V7(b)-(c) and `crawl-traversal.md` CR5 already require honest, reason-tagged gaps.
That honesty must **survive re-rendering here**. This is a cross-reference, not a second counting
mechanism.

**Verify:** a fixture crawl that stopped on a bound with a sub-100% V7 figure, rendered through the
unified report, shows the **same** figure and the same reason breakdown as the crawl page - never
rounded to "PASS", never omitted. A `not_visited` control or screen never appears as a passed row
anywhere in the report.

### DC2 - It READS existing evidence; it does not recompute

All four data classes come from their existing owners: the regression diff (RR3), API failures
(`network-assertions.md` NA1), workflows (`report-export.md` RE1), and change history
(`crawl-traversal.md` CR4's `PersonaRevision` counts).

The report **never computes a number none of those sources already produced.** A figure invented at
render time has no owner and no test.

**Verify:** every figure on the unified report traces to one of the four named sources. No
number-computing function bypasses all four loaders.

### DC3 - "Unified" means one artifact, not four files stapled together

One invocation produces **one** report artifact - or one coherent, clearly cross-linked pair,
following `report-export.md`'s own video-link exception shape.

This criterion exists because "unified" is half the task's own name and no decision states it. Four
unrelated, unlinked files **fails** this criterion, however complete each one is individually.

**Verify:** one invocation -> one artifact (or one cross-linked pair) containing all four data
classes.

### DC4 - No secret reaches the unified report [C5 + `report-export.md` RE5]

Inherited guarantee, restated here only because this is a new artifact and a new artifact is exactly
where an inherited guarantee gets forgotten.

**Verify:** `scripts/check_no_secrets.py` passes clean on the unified report artifact, run against a
project that touches real credentials.

**Known instrument caveat, stated so a unit does not over-trust this Verify:** AT-694 found
`check_no_secrets.py` is wired to *memory* - cited in criteria, rubrics and ~10 manifests - but is
referenced by **no** adapter entry, hook, or `done_check`. A unit satisfying DC4 must run it
explicitly and show the output; "the gate would have caught it" is not evidence here.

Other contracts the report inherits (cite, do not re-derive): `report-export.md` RE1 (read through `ProjectStore` only), RE3 (one self-contained file, video linked not embedded), RE6 (each failure shows criterion, reason, fix_hint, repro steps; AT-582 says today's export violates it), `core-invariants.md` C5, C7, C12 (a missing input is "unavailable", never a flattering default).
Spec: `docs/spec.md` R22, persona `lead` (spec.md:108-113: dashboard -> damage-control report in 2 steps; "a report whose coverage is low must not read as green").

## 4. What exists and what is missing

Exists (read these, do not re-implement):
- Coverage honesty (DC1): `src/autotester/schema/crawl.py:167` `CrawlCoverage` (`by_reason` :202, `permitted_by_reason` :205); `stages/crawl_report.py:64` `coverage_figure`, `:79` `coverage_rows`, `:104` `screens_by_reason`, `:40` `crawl_summary`; `stages/crawl_coverage.py:150` `of_run`, `:179` `compute_coverage`; storage `store/crawl_store.py:29` `save_crawl`, `:32` `load_crawl`, `:35` `list_crawl_ids`. DC1 requires importing these, not copying their string formatting.
- Change history (CR4): `schema/portal_persona.py:152` `PersonaRevision` (`counts()` :188, `missing_unjudged` is the CR5 honesty field), `PortalPersona.history` at :280; `stages/persona_changes.py:126` `classify`, `:192` `describe`; `store/project_store.py:298` `load_portal_persona`.
- API failures (NA1): `stages/network_capture.py:24` `first_party_evidence` (one `EvidenceKind.NETWORK` item per first-party response, status included, URL already scrubbed); run side `stages/execute.py:91` `_drain_network_evidence`; crawl side `stages/explore.py:212` writing through `store/crawl_store.py:79` `add_crawl_network`, `:83` `list_crawl_network`. `schema/enums.py:143` `EvidenceKind.NETWORK`.
- Workflows / run results (RE1): `store/project_store.py:165` `load_results`, `:181` `load_verdicts`; `stages/report_export.py:114` `export_excel`, `:260` `export_html`, `:162` `png_base64`, `:187` `_case_section`, `:82` `_needs_developer_detail`, `:88` `_failure_rows`; workflow rollup `stages/eval_compiler.py:26` `rollup_workflow`. Excel helper `core/excel.py` (21 lines).
- Surfaces: CLI `src/autotester/cli.py:27` `report_app`, `:257` `report excel`, `:272` `report html`, `:290` `report crawl`; HTTP `ui/routes_report.py:212` `report` (latest run, stat row + run history), `:277` `report.xlsx`, `:290` `report.html`.
- Run identity: `schema/run.py:78` `Run` carries `trigger`, `git_sha`, `case_ids`, `usage`, `bounds`.

Missing:
- **The regression diff data class (RR3).** No module, schema or store holds a "last trusted baseline" or a run-to-run diff. `grep` of `src/` for baseline/trusted_run/regression_trigger finds nothing relevant; `qa/contracts/release-regression.md` RR3 only requires T-167 to "pick one rule, name it, test it". T-168 cannot start until T-167 ships that model. What T-167 must deliver for T-168: (a) a typed, persisted diff artifact or a loader function naming the baseline run and the new/fixed/still-failing sets; (b) the baseline rule's name; (c) RR6's single issues log naming each issue's flow, with `not run` for planless flows. Without (a), DC2's "traces to a named source" fails for the first data class.
- Any unified report module, schema, CLI command, HTTP route, or `tests/test_unified_report.py` (the `done_check` file; absent).
- Headroom: `report_export.py` (300), `ui/routes_report.py` (299), `cli.py` (295), `cli_crawl.py` (300), `ui/app.py` (300), `store/project_store.py` (299) are at or within 5 lines of the 300 cap. Nothing can be added to them in place beyond a line or two. `docs/plan.md:134` unit G1 (T-205) extracts `ui/app.py`'s router list into `ui/routers.py`; if G1 has not landed, a new `include_router` line in `ui/app.py` breaks `autotester doctor`.
- Not in scope (no-fire, contract): regression-diff internals (T-167), capture internals (T-170), PDF export, scheduled export. The AI-test section is deferred to Track C release (D-059).

## 5. Files the builder will touch

Module names are `unknown` in `qa/QUEUE.md:270-279` ("files: unknown"). Proposed, to be confirmed against the new-module gate (section 8):
- N `src/autotester/schema/unified_report.py` - the one typed model for the report (CLAUDE.md: every domain shape in `schema/`, `extra="forbid"`). Line count: new.
- N `src/autotester/stages/unified_report.py` - four loaders that call the existing owners above, plus assembly. New. Keep <= 300 lines, functions <= 50.
- N `src/autotester/stages/unified_report_render.py` - HTML (+ Excel) rendering, split so neither file nears the cap. New. (A split is likely, per QUEUE.)
- N `tests/test_unified_report.py` - the `done_check` file named by `.goal/goal.json` and pinned by `tests/test_goal_contract_registration.py:51`. New.
- E `src/autotester/cli.py` (295 lines) - at most 2 lines to register a command (for example `report unified`), mirroring `cli.py:290` `report_app.command("crawl")(cli_crawl.report_crawl)`. A new `cli_unified_report.py` holds the command body (N, new).
- E `src/autotester/ui/routes_report.py` (299 lines) - at most 1 line (a link to the unified report) if kept; otherwise N `ui/routes_unified_report.py` plus an `include_router` line in `ui/app.py` (300 lines, needs G1 headroom first or an equivalent removal in the same unit).
- Read only, do not edit: `stages/crawl_report.py` (243), `stages/persona_changes.py` (205), `schema/portal_persona.py` (299), `schema/crawl.py` (269), `stages/network_capture.py` (44), `stages/report_export.py` (300), `scripts/check_no_secrets.py` (98).
- Not touched: `pyproject.toml`, `uv.lock`, any contract, `docs/ARCHITECTURE.md` prose (only after PASS and only under a DECISIONS entry).

## 6. Test scope

- Product gate: `uv run pytest tests/test_unified_report.py` (bare, no CLI `-q`; AT-503).
- Regression nodes if (and only if) a shared file is edited: `tests/test_report_export.py`, `tests/test_crawl_report.py`, `tests/test_ui_report.py` as whole files (187, 107, 298 lines; none is a directory). `tests/test_cli_surface.py` if `cli.py` changes.
- Also run explicitly and paste output: `uv run python scripts/check_no_secrets.py <the unified artifact>` (AT-694: no automated path runs it), `uv run ruff check src tests scripts`, `uv run autotester doctor`.
- The builder runs no full suite (section 11).

## 7. Reachable test cases (happy path first)

1. Happy: a project with a finished run, a complete crawl, a persona with history, and a T-167 diff -> one invocation yields one artifact with all four sections populated (DC3).
2. DC1: a fixture crawl stopped by `max_actions` (sub-100% coverage) -> the unified report's coverage line equals `crawl_report.coverage_figure(crawl)` and `coverage_rows` reason breakdown exactly; it never says 100% or "PASS"; a `not_visited` screen appears only in an "unreached" list. Falsify in a throwaway copy by dropping one reason class from the report and confirm the test goes red.
3. DC2: patch each of the four loaders to return a sentinel -> the report shows the sentinel and nothing else computed a number; grep-style check that no render function computes a count outside the loaders.
4. CR5 interaction: a persona revision with non-empty `missing_unjudged` -> the report says the diff is incomplete and does not report those screens as `missing`.
5. Honesty of absence (C12): project with no persona, or no crawl, or no baseline run -> that section says "unavailable: <reason>", not zero and not green.
6. NA1: a run with a first-party 500 response -> it appears as an API failure with method, scrubbed URL, status; a third-party request does not.
7. RE6 carry-over: a FAIL verdict shows criterion, reason, fix_hint and repro steps in the unified view.
8. DC4: a project with a real-looking `SecretRef` value in a step -> `check_no_secrets.py` exits 0 on the artifact; plant a fake raw secret in a scratch copy and confirm the scanner and test go red.
9. Negative surface: the HTTP route/CLI for a project with no runs shows the empty state, not a green report (spec `lead` negative path).
10. If the UI route exists: it uses T-204's `require_permission("report.view")` once T-204 has landed; before that, unknown whether routes are guarded (T-204 `pending`).

## 8. Gate answers

- `qa/gates/at638-four-contract-files-authorization.md` lines 3-4 (verbatim): "**Decider:** Umesh. **Status:** **ANSWERED 2026-09-27 - option A, all four** (not the three-file subset). Recorded as **D-054** with `Approved-by: Umesh`". Effect: the DC contract file is authorized; it does not authorize new source files.
- `qa/gates/new-module-authorization.md:77` (verbatim): "Answered: 2026-09-29 - A - "A: new ledger/citations.py (Recommended)", AT-710 only (standing-rule variant not chosen); Umesh via AskUserQuestion in session autotesting-23, re-confirmed to the maker session; recorded as D-057". **Does not cover T-168.** The file states "A new module is a human gate". `qa/QUEUE.md:270` carries `approved: 2026-10-10 (D-081; the owner asked for all remaining work to run)`, which approves the unit, not specific new module paths. Treat the new-file question as OPEN until the owner confirms (see `unknown` below).
- `qa/gates/d081-pathlynks-report-first.md:12` (verbatim): "Answered: 2026-10-10 - A (Pathlynks report first) - D-081". Context only: it orders T-145's live report first; it does not gate T-168.
- `qa/gates/write-policy-tier.md:4` ("Answered by: Umesh, 2026-09-27") and `d081-run-approvals.md:12`: not applicable. T-168 is read-only over stored evidence and fires no live run.
- No gate names T-168 directly. `grep` of `qa/gates/` for "T-168" returns only `at638-four-contract-files-authorization.md`.

## 9. UI surface and persona walk

- UI surface: yes (an operator-readable report page and/or file; entry from the dashboard or project report page).
- `Persona walk: required (lead - dashboard -> the damage-control report for the latest run in <= 2 steps; negative path: a low-coverage report must not read as green; docs/spec.md:108-113, docs/plan.md row 25)`.

## 10. Dependencies and conflicts

- Hard: T-167 (regression diff model). Soft: G1/T-205 headroom (`ui/app.py`).
- Shared files with other pending units, one owner each at a time: `stages/report_export.py` and `ui/routes_report.py` (touched by T-201/G4 report delivery, T-178 failure bundle, T-190 UX advisory per `docs/plan.md` rows 5, 11, 15, and by open issue AT-582 / RE6). T-168 should add NEW modules and a one-line link only, and leave those two files to their current owners.
- `tests/test_goal_contract_registration.py:51` pins T-168 deps and the `test_unified_report.py` path; do not change either.
- T-169 depends on T-168 (`qa/QUEUE.md:341`); T-168's artifact shape becomes T-169's input.
- Not related to T-179/T-180/T-181 (no shared files).

## 11. Budget and process rules

- Check budget (tier M): 10 minutes.
- The builder runs no full suite; only the files named in section 6.
- Falsification only in a throwaway copy outside the bound tree (`qa/adapter.json` read_only_allowlist note), then revert; never perturb the real worktree.
- Kill only PIDs the builder started. Headed browsers are serialized (`qa/adapter.json` `parallel.lanes.browser.max = 1`); this unit should need none (fixture data only).
- Edit in place where a file has headroom; otherwise new module only after the owner confirms. No `*_v2.py` / `*_new.py`. Scratch to `.work/`.
- The builder never edits `qa/contracts/`. Feedback (for example, a stale line number) goes verbatim into `qa/feedback-inbox.md`.
- "Ready for check" only; only `/checker` can PASS.

## Readiness findings (outside the 11 sections, for the dispatcher)

- Buildable today without T-167: the coverage section (DC1), the change-history section (CR4), the API-failures section (NA1) and the run/workflow section (RE1) all read output that already exists (T-164, T-165, T-170, report_export). A slice with the regression-diff section rendered as "unavailable: no release baseline" can be built and tested now on a branch as INPUT only. It cannot earn a checker PASS alone, because DC2/DC3 require all four classes and D-080 item 1 lands units only on a matching-cycle PASS.
- `unknown`: exact module names, whether the owner's D-081 "run all remaining work" covers new source files, and the shape of T-167's diff artifact.
