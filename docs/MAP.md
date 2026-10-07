# AutoTester — map (generated sections; do not edit between markers)

**Purpose:** the directory map (every module's one job, from its docstring), the schema summary (every model, from its docstring), and the `scripts/` inventory (every instrument's one job, from its docstring or header comment) — derived from code by `autotester map`.
**Open me when:** you need to find which module owns a job, which model holds a shape, or which script does what (AT-520: `scripts/` used to be invisible to every routed doc). `autotester doctor` fails when this file is stale.

## Directory map

<!-- generated:map -->
| Module | One job |
|---|---|
| `browser/assertions.py` | Deterministic assertion evaluation (D-032/AT-540) — split from |
| `browser/conditions.py` | Enact a case's execution condition, or say why it cannot be (D-045/AT-581, E6). |
| `browser/db.py` | Read-only backend assertions against MongoDB. Contract: qa/contracts/db-assert.md. |
| `browser/evidence.py` | Screenshot capture and evidence-recording for `BrowserSession`. |
| `browser/launch.py` | Playwright launch options for one project's persistent browser context. |
| `browser/locator_derive.py` | Derive the most meaningful locator for an element that is on screen right now. |
| `browser/locators.py` | Semantic locators: the target grammar and the session's one place that resolves it. |
| `browser/observe.py` | Passive observation: enumerate a page's controls, capture console/network |
| `browser/secrets.py` | The credential boundary. Secret values live here and nowhere else. |
| `browser/session.py` | One owned visible browser: scoped secrets, masked evidence and bounded actions (B5-B9). |
| `browser/video.py` | Per-case video recording for `BrowserSession` (T-191/AT-587). |
| `cli.py` | Command line. Every action the UI offers is available here first. |
| `cli_crawl.py` | Crawl commands — `autotester explore` and `autotester report crawl`. |
| `cli_issues.py` | `autotester issues` — turn an analysis into the sheet a human tester reads. |
| `cli_loop.py` | `autotester loop-status` — was the maker-checker loop alive, and if not, on purpose? |
| `cli_orchestrate.py` | `autotester orchestrate` — the live caller of `stages/orchestrate.py::run_or_resume`. |
| `cli_video.py` | `autotester ingest` — register a recording and learn a FlowSpec from it. |
| `core/consent.py` | The consent gate (D-018): nothing outward-facing starts without a human's |
| `core/env.py` | Load the repo-root `.env` — one definition, used by every entry point. |
| `core/excel.py` | Workbook presentation helpers shared by every Excel exporter. |
| `core/ids.py` | Identifier generation. The ONLY place ids are minted. |
| `core/paths.py` | Filesystem layout. The ONLY place project paths are constructed. |
| `core/pricing.py` | Per-token cost estimates for LLM-call trace spans (D-041 phase 1, RT4). |
| `core/redact.py` | Secret redaction. Every log line and stored artifact passes through here. |
| `core/redact_encodings.py` | Exact encoded-spelling search: precompute how a declared secret would look |
| `core/redact_fold.py` | Credential folding: normalise a string so a case, punctuation, homoglyph, |
| `core/redact_wrap.py` | Whitespace normalisation for the exact-encoding needle search, and a |
| `core/trace.py` | The redacted per-run trace: `TraceWriter` appends one JSON line per stage |
| `core/urls.py` | URL templating: the identity input a crawled screen shares with the |
| `doctor.py` | Design enforcement. Runs the rules that keep this repo readable. |
| `ledger/checks.py` | Design rules over the project's RECORDS, as opposed to its source files. |
| `ledger/citations.py` | Does every `D-NNN` cited in a gate, contract, manifest, verdict or doc resolve to an |
| `ledger/evidence_specs.py` | AT-516 (D-048, gate answer c): does a unit's evidence spec (`mutations.json`) |
| `ledger/relitigation.py` | The cyclic-rebuild gate: is this new unit a retired feature coming back? |
| `ledger/render.py` | Derive the living docs from code and the ledger. Nothing here is hand-typed. |
| `ledger/store.py` | Read and append `docs/FEATURES.jsonl`. The only write path to the ledger. |
| `loop_status.py` | Is the maker-checker loop alive, and if it stopped, was that on purpose? |
| `media/chunks.py` | Split a recording into overlapping chunks a vision model can actually read. |
| `media/frames.py` | Pull a single still out of a recording, at a second the model named. |
| `media/probe.py` | Ask ffmpeg what a recording actually is, and whether ffmpeg is here at all. |
| `media/transcribe.py` | Get a recording's narration — reusing a sidecar first, transcribing last. |
| `providers/anthropic.py` | Anthropic provider: the `agent` and `judge` roles via the Messages API. |
| `providers/base.py` | The provider seam. Every model call in the system goes through this interface. |
| `providers/gemini.py` | Gemini provider: the `vision` role (video understanding), plus `agent`/`judge` |
| `providers/gemini_files.py` | Upload a video to the Files API and wait until the service can actually read it. |
| `providers/gemini_schema.py` | Turn a Pydantic model into a schema Gemini's `response_schema` will accept. |
| `providers/langchain_fallback.py` | LangChain-backed provider with automatic fallback across configured vendors. |
| `providers/mock.py` | Deterministic provider for tests and dry runs. Never calls a network. |
| `schema/ai_check.py` | Track C check vocabulary: which behavioural checks exist for an AI target (D-017). |
| `schema/ai_target.py` | Typed evidence and bounded read scope for deterministic AI target discovery. |
| `schema/analysis.py` | The adjudicated result of running an ensemble over one video's chunks. |
| `schema/approval.py` | Consent as an artifact, not a habit (D-018). |
| `schema/base.py` | Base model every artifact inherits. Defines the shared envelope. |
| `schema/bench.py` | The north star, made measurable: human expert tester vs AutoTester. |
| `schema/case.py` | A test case — one falsifiable claim about the product, plus how to check it. |
| `schema/catalog.py` | The test catalog: schema for `stages/catalog.py::catalog()`'s output. |
| `schema/coverage.py` | Coverage gaps and the video requests that close them. |
| `schema/crawl.py` | Crawl-safety and crawl-envelope primitives (Track B). |
| `schema/enums.py` | Every closed vocabulary in the system. Nothing else defines these strings. |
| `schema/evidence_tombstone.py` | Sidecar tag for a unit's evidence spec whose `kills` node-ids moved out from |
| `schema/failure_bundle.py` | Failure-bundle shapes (T-178, qa/contracts/failure-bundle.md FB1-FB3). |
| `schema/flowspec.py` | The FlowSpec — the system's understanding of the product under test. |
| `schema/issue.py` | A video-derived issue — its own artifact, deliberately NOT a `CaseClass`. |
| `schema/issue_kind.py` | Crawl-detected issue kind. Split out of `schema/enums.py` to keep that |
| `schema/ledger.py` | The feature ledger row and the relitigation verdict. Contract: qa/contracts/living-ledger.md. |
| `schema/media.py` | Host-side media preparation artifacts: transcripts and chunk manifests. |
| `schema/observation.py` | A vision model's raw reading of one video — INGEST's input material. |
| `schema/portal_persona.py` | The durable Portal Persona — what AutoTester knows about one product, kept |
| `schema/project.py` | Project configuration and the secret contract. One directory per project. |
| `schema/run.py` | What EXECUTE observed. Deliberately contains no judgement — see verdict.py. |
| `schema/run_state.py` | RunState: the durable per-run ledger over the filestore's stage artifacts. |
| `schema/scenario.py` | A written scenario list, and what compiling it produced (T-166, EC4/EC5). |
| `schema/screen_graph.py` | What one page-visit observed: its interactive elements and identity inputs. |
| `schema/screenmap.py` | The product map — every screen the system has learned across all a |
| `schema/trace.py` | Trace-span shapes for the redacted per-run trace.jsonl (D-041 phase 1, |
| `schema/user_persona.py` | A `UserPersona` and the opt-in `UXPolicy` -- WHO the advisory UX pass reads a run as. |
| `schema/ux_report.py` | The advisory UX artifacts: `UXFinding`, `UXCaseOutcome`, `UXReport` (PU2). |
| `schema/verdict.py` | Grading. An independent, stateless judge reads evidence against a rubric. |
| `sources/adapters.py` | Convert teaching material into the ONE content-addressed `Source` model. |
| `sources/audio.py` | Gemini-first transcription for AUDIO sources, Whisper as the no-API fallback. |
| `sources/drive.py` | Google Drive folder listing + file fetch, and the OAuth device-flow token |
| `sources/drive_register.py` | Registration for DRIVE sources: `register_drive` -> `Source` rows. |
| `sources/email.py` | Parsing for EMAIL sources: `.eml`/`.mbox` LOCAL files only. |
| `sources/email_register.py` | Registration for EMAIL sources: `register_email` -> `Source` rows. |
| `sources/extract.py` | Deterministic host-side text extraction for DOC sources. |
| `stages/adjudicate.py` | ADJUDICATE: merge every model's chunked observations into one reading. |
| `stages/agent_loop.py` | Agent fallback: when a case's steps break, ask the agent for a fix and retry. |
| `stages/ai_catalog.py` | AI CATALOG: which Track C checks apply to a classified AI target, and which can run now. |
| `stages/analyze_video.py` | ANALYZE: run the ensemble over a prepared recording, then adjudicate. |
| `stages/bench.py` | BENCH: the north star made measurable. Contract: qa/contracts/bench.md K1-K5. |
| `stages/catalog.py` | CATALOG: derive, per `CaseClass`, whether it applies, whether it can run |
| `stages/coverage.py` | COVERAGE: diff what a run actually saw against what the FlowSpec knows. |
| `stages/crawl_coverage.py` | What a crawl covered, stated by the crawl itself — and every hole, with its reason (V7). |
| `stages/crawl_report.py` | The crawl, as something a human can read: an Excel workbook and the |
| `stages/credential_files.py` | Which file names and suffixes hold credentials; they are refused without being opened. |
| `stages/discover.py` | Inspect approved bounded file trees for deterministic, cited lexical signals. |
| `stages/eval_compiler.py` | EVAL COMPILER: compile evals from the knowledge graph, the FlowSpec and a written scenario |
| `stages/execute.py` | EXECUTE: run one case's steps in a real browser, producing a RawResult. |
| `stages/expand.py` | EXPAND: FlowSpec -> Case[], covering every applicable CaseClass per flow. |
| `stages/explore.py` | EXPLORE: a bounded, safety-gated BFS crawl of a (usually logged-in) app. |
| `stages/explore_consent.py` | The crawl's consent pre-flight (D-018 gate 2) — split from `explore.py` |
| `stages/explore_incremental.py` | Incremental crawl: don't re-explore a screen the persona already knows. |
| `stages/explore_merge.py` | Fold a crawl's screen graph into the reviewed FlowSpec (Track B5). |
| `stages/explore_node.py` | One node's worth of exploring: try each safe candidate action, record what |
| `stages/explore_replay.py` | Re-performing a discovering action, INCLUDING the values that were typed. |
| `stages/explore_return.py` | Getting the browser back onto a screen the crawl has already seen. |
| `stages/explore_runtime.py` | The live state of one crawl in flight — session, store, clock, counters. |
| `stages/explore_safety.py` | The explorer's inner safety guard (Track B4, D-016). |
| `stages/explore_status.py` | How a finished crawl is judged, and how a stored one is shown (X16, X18). |
| `stages/explore_traversal.py` | Which screen the crawl visits next — the frontier's ORDER, and nothing else. |
| `stages/explore_typing.py` | The X10-b typing pre-pass (D-029): what the crawler types, and where it |
| `stages/failure_bundle.py` | Assemble and load one atomic failure bundle (T-178, qa/contracts/failure-bundle.md FB1-FB3). |
| `stages/grade.py` | GRADE: an independent, stateless judge reads a Rubric + a RawResult's evidence. |
| `stages/ingest.py` | INGEST: turn a video Source into a FlowSpec, provenance-tracked to the second. |
| `stages/issues.py` | ISSUES: turn an adjudicated analysis into rows a human tester can read. |
| `stages/knowledge_graph.py` | KNOWLEDGE GRAPH: build the typed graph from the persona + FlowSpec, and resolve a |
| `stages/manual_login.py` | Manual one-time login. Contract: qa/contracts/manual-login.md ML1-ML5. |
| `stages/media_prep.py` | MEDIA PREP: make a recording readable — probe it, cut it, transcribe it. |
| `stages/merge_flowspec.py` | Fold a freshly ingested FlowSpec into the reviewed one (Track A6, T-135). |
| `stages/network_capture.py` | First-party network capture as evidence (T-170, NA1/NA2/NA4/NA5/NA6). |
| `stages/orchestrate.py` | ORCHESTRATE: drive the stage pipeline as a resumable learn-or-explore run. |
| `stages/orchestrate_runners.py` | The concrete stage runners the orchestrator threads — thin adapters over the |
| `stages/parallel_run.py` | PARALLEL_RUN: fan N cases out across isolated browser contexts (T-173/D-041). |
| `stages/persona_changes.py` | What moved in the product since the last crawl: new / changed / missing / broken. |
| `stages/portal_persona.py` | PORTAL PERSONA: promote per-crawl knowledge into the durable, cross-run |
| `stages/portal_persona_view.py` | Render a `PortalPersona` as `knowledge.md` — a human-readable VIEW of the |
| `stages/product_map.py` | PRODUCT MAP: fold every recording analysis into one navigable screen map. |
| `stages/read_context.py` | Read approved Markdown as metadata only, never a vault graph or body corpus. |
| `stages/reconcile.py` | RECONCILE: re-map what each video taught onto the product knowledge graph (D-070 part 2). |
| `stages/report_export.py` | Tester-style run reports: an Excel summary and a screen-by-screen HTML |
| `stages/review.py` | FlowSpec review gate: nothing generates cases from an unreviewed understanding |
| `stages/run_budget.py` | RUN_BUDGET: the consent budget one case run spends against (AT-570/AT-660). |
| `stages/run_case_pipeline.py` | RUN_CASE_PIPELINE: the one function that runs a case and grades it. |
| `stages/score.py` | SCORE: compare AutoTester's issues against a human tester's own sheet. |
| `stages/screen_identity.py` | Screen identity: the rules that decide when two screens are one. |
| `stages/script_replay.py` | SCRIPT_REPLAY: record a working live run's locators as a `Script`, then replay it for free. |
| `stages/similarity_score.py` | How two bug reports are compared for `stages/score.py`'s T-136 scorer. |
| `stages/synthetic_values.py` | The synthetic value generator (X10-b, D-029): what the crawler types. |
| `stages/text_lines.py` | Number lines by  |
| `stages/ux_advisory.py` | The advisory UX pass: read a finished run's evidence as a persona, record findings (T-190). |
| `stages/video_retention.py` | T-191/AT-587 V5: keep at most the N most recent kept videos, project-wide. |
| `store/crawl_store.py` | Crawl artifact persistence — split from `project_store.py` at the |
| `store/filestore.py` | The one place any artifact is read from or written to disk. Contract: core-invariants.md C6. |
| `store/project_store.py` | Typed convenience over `filestore` for one project's directory. |
| `store/request_store.py` | Video-request persistence — split from `project_store.py` at the 300-line |
| `store/run_store.py` | Persistence for the advisory UX track: personas and one run's `UXReport` (T-190, PU1/PU2). |
| `ui/app.py` | Thin FastAPI project-list, onboarding and live-view pages over project files. |
| `ui/case_form.py` | Rendering the add-a-case form. Contract: qa/contracts/ui.md. |
| `ui/crawl_view.py` | HTML fragments for the crawl pages — split from `routes_crawls.py` to keep |
| `ui/credential_guard.py` | Credential-guard helpers: refuse a real secret typed into any UI text field. |
| `ui/env_editor.py` | The one legitimate WRITE path to the repo-root `.env` (every other module |
| `ui/error_pages.py` | App-wide `HTTPException` -> HTML page, split out of `ui/app.py` to keep that |
| `ui/helpers.py` | Shared request-validation and lookup helpers used by every UI route module. |
| `ui/project_view.py` | The project page's action card — the operator's control panel for one product. |
| `ui/routes_cases.py` | Create, list, rename and delete a project's test cases from the UI. |
| `ui/routes_catalog.py` | The test catalog page: one row per `CaseClass`, a green runnable count, and |
| `ui/routes_crawl_approval.py` | The crawl-approval card on the credentials page (D-018 consent, gate 2). |
| `ui/routes_crawl_login.py` | Which case a crawl logs in with — declared once on the project, shown before a crawl (X17). |
| `ui/routes_crawls.py` | The explorer, on screen: crawl history, one crawl's screen graph, its |
| `ui/routes_credentials.py` | The credentials editor: values shown (editable, passwords masked with a |
| `ui/routes_flow_diagram.py` | The BFS-style companion to `routes_report.py`'s DFS per-run step flow: |
| `ui/routes_issues.py` | Operator-facing video issue ledger and its human-compatible workbook. |
| `ui/routes_learn.py` | The learning loop on screen — review the FlowSpec, generate cases, see the asks. |
| `ui/routes_live.py` | Presentation-only noVNC page for watching the container's real browser, plus |
| `ui/routes_product_map.py` | Product-map cards, recorded journeys, and guarded learned-frame serving. |
| `ui/routes_project_edit.py` | Edit a project's own settings after onboarding. Contract: qa/contracts/ui.md. |
| `ui/routes_report.py` | Run history, screenshots and downloads. Contract: qa/contracts/ui-report.md UR1-UR4. |
| `ui/routes_runs.py` | Trigger a real run. Contract: qa/contracts/ui-run.md RU1-RU4. Run-history |
| `ui/routes_settings.py` | Global AI/API provider keys. Contract: qa/contracts/ui-settings.md US1-US4. |
| `ui/routes_sources.py` | The operator-facing recording registry. |
| `ui/routes_video.py` | Serves a kept run video (T-191 evidence) by its evidence-relative path -- |
| `ui/run_execution.py` | Serial and parallel case-execution helpers for a triggered run. |
| `ui/theme.py` | Shared visual system for every UI route. Contract: qa/contracts/docker.md D5. |
| `ui/theme_style.py` | The raw CSS/font-link template for every page. Split out of `theme.py` |
<!-- /generated:map -->

## Schema summary

<!-- generated:schema -->
| Model | Meaning |
|---|---|
| `AiCheckKind` (`schema/ai_check.py`) | One behavioural check an AI target can be put through. Enum order is report order. |
| `AiCheckMethod` (`schema/ai_check.py`) | Who decides a check: code from recorded facts, or the independent judge (C7). |
| `AiSignalKind` (`schema/ai_target.py`) | Observed lexical facts; never runtime claims or check selection. |
| `AiTargetKind` (`schema/ai_target.py`) | The four positive target kinds specified by the approved T-151 plan. |
| `Classification` (`schema/ai_target.py`) | Strict naming response; evidence and checks are never model-controlled. |
| `AiTarget` (`schema/ai_target.py`) | Source evidence plus classification, or an explicit non-AI outcome. |
| `Signal` (`schema/ai_target.py`) | One observed lexical fact, never a claim about runtime behavior. |
| `ScanLimits` (`schema/ai_target.py`) | Explicit finite limits on scanning and metadata parsing. |
| `ReadScope` (`schema/ai_target.py`) | Caller-supplied project identity and approvals; no ambient credential loading. |
| `ReadRefusal` (`schema/ai_target.py`) | Why an input was not read, keeping incompleteness explicit. |
| `ContextDocument` (`schema/ai_target.py`) | Markdown metadata and an unpersisted Source reference, never body text. |
| `Discovery` (`schema/ai_target.py`) | Read-only discovery receipt; classification is a separate pending operation. |
| `AnalysedScreen` (`schema/analysis.py`) | An `ObservedScreen` two or more models agreed on (or the one model that |
| `AnalysedIssue` (`schema/analysis.py`) | An `ObservedIssue` after cross-model merge — `id` is stamped by |
| `JourneyStop` (`schema/analysis.py`) | One stop in a recording's end-to-end journey — reuses `ObservedScreen`'s |
| `VideoAnalysis` (`schema/analysis.py`) | One source's adjudicated understanding — screens, flows, the ordered |
| `RunApproval` (`schema/approval.py`) | One human's authorisation for one kind of run against one target. |
| `Provenance` (`schema/base.py`) | Who or what produced this artifact, and from what. |
| `Artifact` (`schema/base.py`) | Common envelope: versioned, timestamped, attributable. |
| `SeededBug` (`schema/bench.py`) | A deliberately introduced defect with known ground truth. |
| `Finding` (`schema/bench.py`) | One reported defect from a participant, matched against ground truth. |
| `BenchCorpus` (`schema/bench.py`) | A build with known seeded defects and the material pack given to testers. |
| `BenchTrial` (`schema/bench.py`) | One participant's attempt on one corpus. |
| `Case` (`schema/case.py`) | One generated or hand-written test case. |
| `AgentFix` (`schema/case.py`) | The agent's proposed correction for one failing step. |
| `ExpandedSteps` (`schema/case.py`) | One taxonomy class's proposed steps for a flow — `stages/expand.py`'s raw |
| `ScriptStep` (`schema/case.py`) | One recorded step's locator: what replay uses in place of the case step's own target. |
| `ScriptInputs` (`schema/case.py`) | Everything that determines a script (SR2). Any difference makes it stale. |
| `Script` (`schema/case.py`) | A durable, versioned record of how one case runs, produced by a live run that worked. |
| `BlockedReason` (`schema/catalog.py`) | Why a `CatalogEntry` is not runnable. Closed by D-039 — exactly six |
| `Tier` (`schema/catalog.py`) | Cheap -> expensive ordering (D-039). `routes_runs.py`'s tiered dispatch |
| `CatalogEntry` (`schema/catalog.py`) | One `CaseClass`'s standing for one project: applicable, runnable, and |
| `StandardPack` (`schema/catalog.py`) | A named flow pattern the team's own release checklist calls out, on top |
| `PackEntry` (`schema/catalog.py`) | One `StandardPack`'s standing for one project. Reuses `BlockedReason` |
| `AiCheckEntry` (`schema/catalog.py`) | One Track C `AiCheckKind`'s standing for one AI target (T-152, ai-target.md AI4-AI5). |
| `Catalog` (`schema/catalog.py`) | One project's whole catalog: every `CaseClass`, exactly once (CT2), |
| `CoverageGap` (`schema/coverage.py`) | A screen or route observed in a run but absent from the FlowSpec. |
| `VideoRequest` (`schema/coverage.py`) | What the system asks a human to record, and why. |
| `DialogEvent` (`schema/crawl.py`) | One JS dialog (`alert`/`confirm`/`prompt`/`beforeunload`) the observer saw. |
| `CrawlBounds` (`schema/crawl.py`) | Bounds the BFS actually stops on — every field must be able to end |
| `SafetyPolicy` (`schema/crawl.py`) | What the explorer will and won't click, given a project's `write_policy`. |
| `CrawlIssue` (`schema/crawl.py`) | One problem the crawl noticed — console error, failed first-party |
| `CoverageHole` (`schema/crawl.py`) | One control the crawl discovered and did not perform, with the ONE reason why (V7b). |
| `PermittedControl` (`schema/crawl.py`) | One control the supplied account's role PERMITS (coverage.md V9). |
| `CrawlCoverage` (`schema/crawl.py`) | What a crawl covered, stated by the crawl itself (coverage.md V7). The books balance: |
| `NoiseCount` (`schema/crawl.py`) | One third-party host's dropped-request tally (never an issue, X9). |
| `Crawl` (`schema/crawl.py`) | The envelope for one bounded BFS run — `stages/explore.py`'s output. |
| `EvidenceTombstoneEntry` (`schema/evidence_tombstone.py`) | One `kills` node-id, named by file + bare function name (no parametrize |
| `EvidenceTombstone` (`schema/evidence_tombstone.py`) | `qa/evidence/<slug>/mutations.stale.json` -- absent means untagged. |
| `BundleFileKind` (`schema/failure_bundle.py`) |  |
| `BundleSource` (`schema/failure_bundle.py`) | One screenshot offered to the assembler, stamped with its originating run. |
| `BundleFile` (`schema/failure_bundle.py`) | One file inside a finished bundle. |
| `BundleManifest` (`schema/failure_bundle.py`) | `manifest.json`: written last, so its presence plus matching hashes is completeness. |
| `SourceRef` (`schema/flowspec.py`) | Where a piece of understanding came from — a video second, a doc line. |
| `FieldConstraints` (`schema/flowspec.py`) | What the UI says a field accepts. Drives boundary/edge case generation. |
| `InputField` (`schema/flowspec.py`) | One input on a screen. |
| `ExpectedState` (`schema/flowspec.py`) | What must be true for a step to have succeeded. |
| `Step` (`schema/flowspec.py`) | One browser action plus what it should produce. |
| `Screen` (`schema/flowspec.py`) | A distinguishable page/state of the product. |
| `Flow` (`schema/flowspec.py`) | An end-to-end journey through screens. |
| `Review` (`schema/flowspec.py`) | The human gate. A flowspec drives nothing until a person approves it. |
| `Conflict` (`schema/flowspec.py`) | Sources disagreed. Flagged for a human — never silently merged. |
| `FlowSpec` (`schema/flowspec.py`) | The reviewed understanding of one project's UI. |
| `ScreenJudgement` (`schema/flowspec.py`) | The judge's answer for ONE ambiguous screen pair -- the only call reconcile makes. |
| `ScreenMatch` (`schema/flowspec.py`) | One canonical video screen scored against its best candidate (RC5). |
| `StepRef` (`schema/flowspec.py`) | A step the report points a human at: which flow, which step, which second. |
| `Possibility` (`schema/flowspec.py`) | A variant flow -- another way the task was done, never an error (RC10). |
| `ReconcileReport` (`schema/flowspec.py`) | What reconcile decided, in a form a human can audit. No timestamps (RC11). |
| `Issue` (`schema/issue.py`) | One row of "what's wrong", derived from a video and (optionally) matched |
| `IssueKind` (`schema/issue_kind.py`) | What kind of problem a crawl-detected `CrawlIssue` is. |
| `FeatureEvent` (`schema/ledger.py`) | One dated event in the life of a feature: planned, live, updated, or retired. |
| `RelitigationVerdict` (`schema/ledger.py`) | The judge's answer to "is this new unit a retired feature coming back?". |
| `TranscriptSegment` (`schema/media.py`) | One spoken utterance, absolute seconds into the source video. |
| `Transcript` (`schema/media.py`) | A video's narration. `from_sidecar` loads the exact shape the existing |
| `MediaChunk` (`schema/media.py`) | One re-encoded chunk of a longer video. |
| `MediaPrep` (`schema/media.py`) | Probe + chunk manifest for one `Source`. Degrades gracefully (VL1): |
| `ObservedStep` (`schema/observation.py`) | One action a vision model saw in a video. Raw material for a `Step` — |
| `ObservedFlow` (`schema/observation.py`) | One journey a vision model saw across screens. |
| `ObservedScreen` (`schema/observation.py`) | One distinguishable screen a vision model saw. |
| `ObservedIssue` (`schema/observation.py`) | A problem the vision model itself noticed — spoken, on-screen, or both. |
| `VisionOptions` (`schema/observation.py`) | Generation config for a vision call — the settings the proven external |
| `VideoObservation` (`schema/observation.py`) | A vision provider's raw reading of one video (or chunk) — turned into a |
| `ModelObservation` (`schema/observation.py`) | One model's raw answer for one chunk — cached on disk so re-running the |
| `PersonaProfile` (`schema/portal_persona.py`) | What the product is, at a glance — the durable header of the persona. |
| `AuthField` (`schema/portal_persona.py`) | One credential input the login SHAPE has. Carries the SecretRef KEY, never |
| `AuthShape` (`schema/portal_persona.py`) | How the product authenticates, described by shape alone (PP5): which |
| `PersonaScreen` (`schema/portal_persona.py`) | One distinct screen the product has. Accumulated across runs (PP2). |
| `PersonaTransition` (`schema/portal_persona.py`) | One learned move between screens — what control takes you where. |
| `FlowRunRef` (`schema/portal_persona.py`) | A stable, runnable reference a Quick Re-Run resolves to re-exercise a |
| `TaughtFlow` (`schema/portal_persona.py`) | An end-to-end journey the product supports, carried durably with a stable |
| `Gotcha` (`schema/portal_persona.py`) | One thing that bit us — a quirk of this product worth remembering. |
| `PersonaRevision` (`schema/portal_persona.py`) | One dated entry in the persona's history: when it was updated and a |
| `GraphNode` (`schema/portal_persona.py`) | One typed node of the knowledge graph (EC1). `id` is `<kind>:<ref>`. |
| `GraphEdge` (`schema/portal_persona.py`) | One typed edge `src -> dst`; `label` tells parallel edges apart (e.g. the control). |
| `KnowledgeGraph` (`schema/portal_persona.py`) | Screen, control, flow, scenario, case, verdict, API and release nodes with typed |
| `PortalPersona` (`schema/portal_persona.py`) | The durable, cross-run model of one product under test (PP1). A single |
| `SecretRef` (`schema/project.py`) | A declared credential. Holds the KEY and its scope — never the value. |
| `ProviderConfig` (`schema/project.py`) | Which provider serves each role. Roles are swappable per project. |
| `Source` (`schema/project.py`) | An immutable input the system learned from. |
| `Project` (`schema/project.py`) | Everything the system needs to test one product. |
| `Evidence` (`schema/run.py`) | A file or value the grader may cite. Already redacted and masked. |
| `ProviderUsage` (`schema/run.py`) | Token and call accounting per provider role — the cost story per run. |
| `RawResult` (`schema/run.py`) | One case's execution record. |
| `RunBounds` (`schema/run.py`) | The `RunApproval` bounds a run ACTUALLY ran under (AT-660/CN10). |
| `Run` (`schema/run.py`) | One regression run over a set of cases. |
| `StageName` (`schema/run_state.py`) | The pipeline stages a run drives, in canonical order. |
| `StageCheckpoint` (`schema/run_state.py`) | One stage's durable record within a run. |
| `RunState` (`schema/run_state.py`) | The ledger for one run, keyed by `run_id` (`OR5`: one run_id, one lineage). |
| `Branch` (`schema/scenario.py`) | One option of a scenario (the "yes" or the "no"): the data it changes in its flow |
| `ScenarioSpec` (`schema/scenario.py`) | One declared scenario variant of a flow. Its own graph node and case set (EC4). |
| `UncoveredBranch` (`schema/scenario.py`) | A scenario branch that produced no case, with the one reason why (EC5). |
| `CompileResult` (`schema/scenario.py`) | What `stages/eval_compiler.py::compile_evals` produced. |
| `ElementRef` (`schema/screen_graph.py`) | One interactive element found by `browser/enumerate.js`. |
| `PageObservation` (`schema/screen_graph.py`) | One page-visit's raw material: its url/title and interactive elements. |
| `ScreenNode` (`schema/screen_graph.py`) | One distinct screen the crawl found. Identity is structural |
| `ScreenEdge` (`schema/screen_graph.py`) | One candidate action the crawl tried from one screen. |
| `CrawlFrontier` (`schema/screen_graph.py`) | The BFS queue state — persisted so a crash mid-crawl leaves a resumable |
| `ScreenVisit` (`schema/screenmap.py`) | One recording that showed this screen. |
| `MappedScreen` (`schema/screenmap.py`) | One screen folded across every recording that showed it. |
| `Journey` (`schema/screenmap.py`) | One recording's ordered path through screens. |
| `ScreenMap` (`schema/screenmap.py`) | The product map: every learned screen plus the journeys that visited them. |
| `StageSpan` (`schema/trace.py`) | One finished `StageCheckpoint` (RT3) — `trace_id` is always the run's |
| `LLMSpan` (`schema/trace.py`) | One call through `Provider.see_video`/`act`/`judge` (RT4), recorded at |
| `UserPersona` (`schema/user_persona.py`) | One kind of user the UX pass reads a run as. Advisory input only (PU4). |
| `UXPolicy` (`schema/user_persona.py`) | Per-project switch and cap for the UX pass. Off by default (plan decision 5). |
| `UXFinding` (`schema/ux_report.py`) | One advisory observation about one case, cited to real evidence. |
| `UXDraft` (`schema/ux_report.py`) | What the model returns for one finding -- validated against the real evidence before it |
| `UXJudgment` (`schema/ux_report.py`) | The provider's structured answer for one case (the `Provider.judge` schema). |
| `UXCaseStatus` (`schema/ux_report.py`) | How one case's UX pass ended. Only `ANALYZED` can carry findings. |
| `UXCaseOutcome` (`schema/ux_report.py`) | One case's advisory record: its status, why, and any findings. |
| `UXReport` (`schema/ux_report.py`) | One run's advisory UX pass. `complete=False` means the pass was cut short; an absent |
| `Criterion` (`schema/verdict.py`) | One checkable bar. If it can be argued about, it is not a criterion. |
| `Rubric` (`schema/verdict.py`) | The grading contract for a case. More specific than the case itself. |
| `Failure` (`schema/verdict.py`) | One unmet criterion, with the evidence that shows it. |
| `Judgment` (`schema/verdict.py`) | Raw judge output for one grading call — the stage fills in run_id, case_id, |
| `Verdict` (`schema/verdict.py`) | The judge's output for one case in one run. |
<!-- /generated:schema -->

## Scripts

<!-- generated:scripts -->
| Script | One job |
|---|---|
| `scripts/append_decision.ps1` | append_decision.ps1 -- the ONLY legitimate write path to docs/DECISIONS.md |
| `scripts/bench_trial.py` | T-120: the north star made measurable — first real human-vs-AI trial scorecard. |
| `scripts/check_crawl_approval.py` | T-145's done_check (D-018): a live crawl counts as done only if it actually |
| `scripts/check_deliverable.py` | Assert a task's deliverables exist — a `done_check` that can actually fail. |
| `scripts/check_no_secrets.py` | Scan files for any real value currently loaded in .env. Prints OK/LEAK only. |
| `scripts/explore_proof.py` | Credential-free end-to-end proof of the explorer (Track B3). |
| `scripts/flake_probe.py` | Measure a flaky test's real failure rate — and say how little N green runs prove. |
| `scripts/migrate_stamp_legacy_rubrics.py` | Stamp `Provenance` on legacy default rubrics, in stored project data. |
| `scripts/migrate_url_patterns.py` | Repair `url_pattern` values mangled by AT-287/AT-294, in stored project data. |
| `scripts/mutation_check.py` | Prove a unit's new tests are not vacuous, by killing them on purpose. |
| `scripts/onboard_pathlynks.py` | Onboard Pathlynks: real login via the credential boundary, evidence, knowledge.md. |
| `scripts/regression_proof.py` | T-110: break a feature, confirm exactly that case FAILs while an unrelated |
| `scripts/run_pathlynks_first_cases.py` | T-050: 3 hand-written Pathlynks login cases (best/worst/edge), run headed and |
| `scripts/score_video_issues.py` | Score AutoTester's issues against a human tester's sheet — T-136's acceptance. |
<!-- /generated:scripts -->
