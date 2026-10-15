# AutoTester — map (generated sections; do not edit between markers)

**Purpose:** the directory map (every module's one job, from its docstring), the schema summary (every model, from its docstring), and the `scripts/` inventory (every instrument's one job, from its docstring or header comment) — derived from code by `autotester map`.
**Open me when:** you need to find which module owns a job, which model holds a shape, or which script does what (AT-520: `scripts/` used to be invisible to every routed doc). `autotester doctor` fails when this file is stale.

## Directory map

<!-- generated:map -->
| Module | One job |
|---|---|
| `agents/budget.py` | The per-run token/cost meter of the lead tester (T-179, AL11). |
| `agents/comparison.py` | Agent-vs-pipeline on one seeded corpus (T-179, AL12/AL13). |
| `agents/context.py` | The trusted context of a lead-tester run: everything a model may NOT choose. |
| `agents/evidence_tools.py` | The read-only evidence tools (T-180, AL8): `read_result`, `read_rubric`, `read_verdict`. |
| `agents/gain.py` | The measured-gain harness (T-181, AL12/AL13): one corpus, two paths, one report. |
| `agents/guards.py` | The checks that stop an acting tool, in code (AL3). One job: decide, before any browser |
| `agents/lead.py` | The lead tester's loop (T-179c, AL4/AL5/AL7): a model returns one step per turn, the loop runs |
| `agents/lead_agent.py` | The lead tester built on Deep Agents (T-179, AL1/AL4/AL5/AL6/AL7/AL11). |
| `agents/report_tools.py` | The two remaining read tools of the lead tester (T-179, AL2): `report` and `capture_network`. |
| `agents/subagents.py` | The five subagents of the lead tester and the one place their tool allowlists live (T-180, |
| `agents/tools.py` | The lead tester's stage tools and their one dispatcher (T-179, AL2/AL3/AL6). |
| `auth/access.py` | The one authorization function (AU12) and the project relation data it reads. |
| `auth/accounts.py` | Accounts: open signup, first-account admin, password check, admin account actions. |
| `auth/audit.py` | The audit trail (AU22): one JSON line per state-changing request in |
| `auth/config.py` | Auth startup configuration (AU3 cookie Secure rule, AU17 gate switch, AU20 hosted |
| `auth/context.py` | The current request's principal, set by the auth middleware for the request's |
| `auth/db.py` | The auth store's SQLite file: connection, tables, one-time seeding, last-admin guard. |
| `auth/defaults.py` | The four seeded groups and their default ticks (auth.md "Default groups", AU11). |
| `auth/groups.py` | IAM-style groups: create, rename, tick permissions, set members, delete (AU10). |
| `auth/loopback.py` | The AU17 loopback switch, kept import-free: whether login is OFF (single-user loopback only). |
| `auth/passwords.py` | Password hashing: argon2id via argon2-cffi, behind one hash/verify pair (AU1). |
| `auth/policy.py` | The central route policy (AU14, AU16, TF4): the rule table, its matcher, the unit merge. |
| `auth/ratelimit.py` | Login rate limit (AU5): 5 failures per account or 20 per client address inside a |
| `auth/sessions.py` | Server-side sessions (AU3): a 256-bit random id in the cookie, only its SHA-256 in the |
| `browser/assertions.py` | Deterministic assertion evaluation (D-032/AT-540) — split from |
| `browser/click_recovery.py` | Click readiness: scroll into view, wait out overlays, expand a collapsed parent menu. |
| `browser/conditions.py` | Enact a case's execution condition, or say why it cannot be (D-045/AT-581, E6). |
| `browser/db.py` | Read-only backend assertions against MongoDB. Contract: qa/contracts/db-assert.md. |
| `browser/destroy_guard.py` | One job: refuse a click or submit on an account-destroying control, at every write policy. |
| `browser/evidence.py` | Screenshot capture and evidence-recording for `BrowserSession`. |
| `browser/launch.py` | Playwright launch options for one project's persistent browser context. |
| `browser/locator_derive.py` | Derive the most meaningful locator for an element that is on screen right now. |
| `browser/locators.py` | Semantic locators: the target grammar and the session's one place that resolves it. |
| `browser/observe.py` | Passive observation: enumerate a page's controls, capture console/network |
| `browser/secrets.py` | The credential boundary. Secret values live here and nowhere else. |
| `browser/session.py` | One owned visible browser: scoped secrets, masked evidence and bounded actions (B5-B9). |
| `browser/video.py` | Per-case video recording for `BrowserSession` (T-191/AT-587). |
| `cli.py` | Command line. Every action the UI offers is available here first. |
| `cli_auth.py` | `autotester auth` -- break-glass account administration from the server shell (T-204). |
| `cli_crawl.py` | Crawl commands — `autotester explore` and `autotester report crawl`. |
| `cli_intake.py` | `autotester ingest zip` and `ingest fetch-drive`: hand over recordings without the browser. |
| `cli_issues.py` | `autotester issues` — turn an analysis into the sheet a human tester reads. |
| `cli_loop.py` | `autotester loop-status` — was the maker-checker loop alive, and if not, on purpose? |
| `cli_orchestrate.py` | `autotester orchestrate` — the live caller of `stages/orchestrate.py::run_or_resume`. |
| `cli_release.py` | `autotester release` / `release-log` — the release manager's way to run the whole suite (T-167). |
| `cli_revoke.py` | `autotester revoke`: withdraw a previously granted approval with a signed row. |
| `cli_run.py` | `autotester run`, `run-report`, `catalog`, `mcp-serve`: the machine-facing commands (T-174). |
| `cli_schedule.py` | `autotester schedule tick`: the stateless pass that makes scheduled tests run (T-200, TS7). |
| `cli_subapps.py` | The list of CLI sub-apps `autotester` registers (T-205/TF5, design rule). |
| `cli_video.py` | `autotester ingest` — register a recording and learn a FlowSpec from it. |
| `cli_video_review.py` | `autotester ingest review`: a pointer-guided review of one recording (T-197, CLI half). |
| `core/consent.py` | The consent gate (D-018): nothing outward-facing starts without a human's |
| `core/env.py` | Load the repo-root `.env` — one definition, used by every entry point. |
| `core/excel.py` | Workbook presentation helpers shared by every Excel exporter. |
| `core/exit_codes.py` | The one exit-code table for machine-facing commands (T-174, CM1). |
| `core/file_lock.py` | One job: a cross-process advisory file lock (`msvcrt.locking` on Windows, `flock` elsewhere). |
| `core/ids.py` | Identifier generation. The ONLY place ids are minted. |
| `core/localtime.py` | Fixed-offset time zones and local-to-UTC conversion for the scheduler. |
| `core/path_pii.py` | One job: make a URL path template safe to store -- no email, phone, token, UUID or JWT. |
| `core/paths.py` | Filesystem layout. The ONLY place project paths are constructed. |
| `core/pricing.py` | Per-token cost estimates for LLM-call trace spans (D-041 phase 1, RT4). |
| `core/redact.py` | Secret redaction. Every log line and stored artifact passes through here. |
| `core/redact_encodings.py` | Exact encoded-spelling search: precompute how a declared secret would look |
| `core/redact_escaped.py` | Escaped-spelling redaction: percent/entity/plus-encoded secrets, encoded PII, URL creds. |
| `core/redact_fold.py` | Credential folding: normalise a string so a case, punctuation, homoglyph, |
| `core/redact_wrap.py` | Whitespace normalisation for the exact-encoding needle search, and a |
| `core/repo_docs.py` | Repo-level documents: the living map, the ledger, the history, the router. |
| `core/safe_names.py` | Refuse any name that could leave its directory or break on Windows (R65, TF7). |
| `core/trace.py` | The redacted per-run trace: `TraceWriter` appends one JSON line per stage |
| `core/upload_limit.py` | The ONE accessor for the admin upload limit (`max_upload_bytes`), read at request time. |
| `core/urls.py` | URL templating: the identity input a crawled screen shares with the |
| `delivery/email.py` | The outbound mail adapters: the dry-run outbox and the SMTP sender (hosting.md HO27, HO29). |
| `delivery/inbox.py` | Delivery records on disk and the send-once procedure around a mail transport (TT9, HO29). |
| `delivery/message.py` | Compose the report e-mail from a stored `ReportSummary` and a template file (hosting.md HO28). |
| `doctor.py` | Design enforcement. Runs the rules that keep this repo readable. |
| `ledger/advisory.py` | Which doctor findings are advisory warnings and which block (L10, D-087). |
| `ledger/checks.py` | Design rules over the project's RECORDS, as opposed to its source files. |
| `ledger/citations.py` | Does every `D-NNN` cited in a gate, contract, manifest, verdict or doc resolve to an |
| `ledger/evidence_specs.py` | AT-516 (D-048, gate answer c): does a unit's evidence spec (`mutations.json`) |
| `ledger/issue_ids.py` | Id uniqueness for `qa/issues.jsonl` (AT-676, AT-645). |
| `ledger/relitigation.py` | The cyclic-rebuild gate: is this new unit a retired feature coming back? |
| `ledger/render.py` | Derive the living docs from code and the ledger. Nothing here is hand-typed. |
| `ledger/review_block.py` | Reads the one current citation-review block in `qa/feedback-inbox.md` (L10). |
| `ledger/seals.py` | L10 immutable-history dispositions: sealed records and the known-disputed claims. |
| `ledger/store.py` | Read and append `docs/FEATURES.jsonl`. The only write path to the ledger. |
| `loop_status.py` | Is the maker-checker loop alive, and if it stopped, was that on purpose? |
| `mcp_server.py` | The AutoTester MCP server: three tools, a thin adapter over `stages/run_service.py` (T-174 CM4). |
| `media/chunks.py` | Split a recording into overlapping chunks a vision model can actually read. |
| `media/frames.py` | Pull a single still out of a recording, at a second the model named. |
| `media/probe.py` | Ask ffmpeg what a recording actually is, and whether ffmpeg is here at all. |
| `media/redacted.py` | The redacted derivative of a recording, and the frames cut from it (TV7). |
| `media/transcribe.py` | Get a recording's narration — reusing a sidecar first, transcribing last. |
| `providers/agent_model.py` | The production chat-model constructor for the agent layer (T-181, AL12). |
| `providers/anthropic.py` | Anthropic provider: the `agent` and `judge` roles via the Messages API. |
| `providers/base.py` | The provider seam. Every model call in the system goes through this interface. |
| `providers/gemini.py` | Gemini provider: the `vision` role (video understanding), plus `agent`/`judge` |
| `providers/gemini_files.py` | Upload a video to the Files API and wait until the service can actually read it. |
| `providers/gemini_schema.py` | Turn a Pydantic model into a schema Gemini's `response_schema` will accept. |
| `providers/images.py` | One job: turn a prompt plus screenshot files into OpenAI-style message content. |
| `providers/isolated.py` | ISOLATED_PROVIDER: run a `Provider` call in a killable child process (D-089 item 2, T-177 AF4). |
| `providers/langchain_fallback.py` | LangChain-backed provider with automatic fallback across configured vendors. |
| `providers/litellm_provider.py` | LiteLLM provider: the `act` and `judge` roles for any model LiteLLM can reach. |
| `providers/litellm_schema.py` | One job: the schema and answer-parsing half of the LiteLLM provider. |
| `providers/mock.py` | Deterministic provider for tests and dry runs. Never calls a network. |
| `providers/model_chain.py` | Ordered model chain over LiteLLM: Ollama GLM -> Ollama DeepSeek -> Gemini. |
| `providers/ollama_cloud.py` | Ollama cloud endpoint settings for LiteLLM: the one place that knows them. |
| `schema/acceptance.py` | The T-136 acceptance-comparison artifact: AutoTester vs a human tester, as data. |
| `schema/agent_comparison.py` | The agent-vs-pipeline comparison report (T-179 AL12/AL13): the four north-star axes for each |
| `schema/agent_fallback.py` | Typed shapes for the browser-use fallback actuator (T-177, qa/contracts/agent-fallback.md). |
| `schema/agent_guardrails.py` | The declared limits of an agent run and the rule that says whether it beat the pipeline |
| `schema/agent_layer.py` | The shapes the lead tester's tool surface speaks (T-179, D-042): which tools exist, |
| `schema/ai_check.py` | Track C check vocabulary: which behavioural checks exist for an AI target (D-017). |
| `schema/ai_probe.py` | Track C adversarial shapes: a file-defined probe set, the record of one pass, a refusal row. |
| `schema/ai_target.py` | Typed evidence and bounded read scope for deterministic AI target discovery. |
| `schema/analysis.py` | The adjudicated result of running an ensemble over one video's chunks. |
| `schema/approval.py` | Consent as an artifact, not a habit (D-018). |
| `schema/approval_revocation.py` | A signed withdrawal of one `RunApproval` (D-018 follow-up, AT-110 key). |
| `schema/auth.py` | Team login shapes (T-204, D-072; contract qa/contracts/auth.md): the closed permission |
| `schema/base.py` | Base model every artifact inherits. Defines the shared envelope. |
| `schema/bench.py` | The north star, made measurable: human expert tester vs AutoTester. |
| `schema/bug_run.py` | What reading the bug store and processing one run reports: the shapes of T-199b (TB3, TB4, TB6). |
| `schema/case.py` | A test case — one falsifiable claim about the product, plus how to check it. |
| `schema/catalog.py` | The test catalog: schema for `stages/catalog.py::catalog()`'s output. |
| `schema/cli_output.py` | The machine-readable result of a run (T-174, CM2/CM4). |
| `schema/coverage.py` | Coverage gaps and the video requests that close them. |
| `schema/crawl.py` | Crawl-safety and crawl-envelope primitives (Track B). |
| `schema/crawl_summary.py` | CrawlSummary: the small, redacted, TRACKED record of one finished crawl. |
| `schema/delivery.py` | Report-delivery shapes: preference, recipient, summary, rendered message, record, SMTP settings. |
| `schema/enums.py` | Every closed vocabulary in the system. Nothing else defines these strings. |
| `schema/evidence_tombstone.py` | Sidecar tag for a unit's evidence spec whose `kills` node-ids moved out from |
| `schema/failure_bundle.py` | Failure-bundle shapes (T-178, qa/contracts/failure-bundle.md FB1-FB3). |
| `schema/flowspec.py` | The FlowSpec — the system's understanding of the product under test. |
| `schema/intake.py` | Shapes for video intake: zip limits, the per-member report, and where a source came from. |
| `schema/issue.py` | A video-derived issue — its own artifact, deliberately NOT a `CaseClass`. |
| `schema/issue_kind.py` | Crawl-detected issue kind. Split out of `schema/enums.py` to keep that |
| `schema/lead_loop.py` | The steps a lead-tester model may return, and what a finished loop reports (T-179 AL5/AL7). |
| `schema/ledger.py` | Ledger records, relitigation and reviewed decision citations (living-ledger contract). |
| `schema/media.py` | Host-side media preparation artifacts: transcripts and chunk manifests. |
| `schema/observation.py` | A vision model's raw reading of one video — INGEST's input material. |
| `schema/portal_persona.py` | The durable Portal Persona — what AutoTester knows about one product, kept |
| `schema/project.py` | Project configuration and the secret contract. One directory per project. |
| `schema/release.py` | Release regression shapes: a flow's persisted plan, a run's scope, its record and diff. |
| `schema/review_recall.py` | The TA16 evidence record: a video review measured against an oracle, in numbers (T-206). |
| `schema/run.py` | What EXECUTE observed. Deliberately contains no judgement — see verdict.py. |
| `schema/run_queue.py` | One Test press waiting for, holding, or having had a browser slot (T-203, hosting.md HO16). |
| `schema/run_state.py` | RunState: the durable per-run ledger over the filestore's stage artifacts. |
| `schema/scenario.py` | A written scenario list, and what compiling it produced (T-166, EC4/EC5). |
| `schema/schedule.py` | The per-project schedule (G5, R51): a typed, bounded setting plus the slot-record vocabulary. |
| `schema/screen_graph.py` | What one page-visit observed: its interactive elements and identity inputs. |
| `schema/screenmap.py` | The product map — every screen the system has learned across all a |
| `schema/server_settings.py` | Admin-set server limits (D-072 G6 and item 10): run concurrency and the upload size ceiling. |
| `schema/sheet_plan.py` | The shapes of a tracker-sheet sync PLAN (T-199b dry run; contract TB9, TB10, TB11, TB13 in part). |
| `schema/subagent.py` | The shape of one subagent of the lead tester (T-180, D-042, AL8-AL10): its name, the skill |
| `schema/team_enums.py` | The Group 10 (team features) vocabulary file: every closed value set the team units add. |
| `schema/trace.py` | Trace-span shapes for the redacted per-run trace.jsonl (D-041 phase 1, |
| `schema/tracked_bug.py` | A tracked bug and the events that move it: the data shapes of T-199a (team-bug-loop TB1-TB6). |
| `schema/tracker_binding.py` | The shapes of a project's tracker binding and the state of its sheet sync (T-199d; TB12, TB14). |
| `schema/unified_report.py` | The damage-control report's typed shape: one run's four evidence classes plus crawl coverage. |
| `schema/user_persona.py` | A `UserPersona` and the opt-in `UXPolicy` -- WHO the advisory UX pass reads a run as. |
| `schema/ux_report.py` | The advisory UX artifacts: `UXFinding`, `UXCaseOutcome`, `UXReport` (PU2). |
| `schema/verdict.py` | Grading. An independent, stateless judge reads evidence against a rubric. |
| `schema/video_pointer.py` | The shape of a human's pointer file once parsed (T-197 / TV1). |
| `schema/video_review.py` | The typed review of one recording: summary, confirm-list, what was and was not looked at (T-197). |
| `schema/video_share.py` | The shapes of the video portal (T-198b / G9, team-intake.md TP1-TP6). |
| `sources/adapters.py` | Convert teaching material into the ONE content-addressed `Source` model. |
| `sources/audio.py` | Gemini-first transcription for AUDIO sources, Whisper as the no-API fallback. |
| `sources/bounded_write.py` | One bounded, hashing copy for every intake path (zip member, Drive fetch). |
| `sources/drive.py` | Google Drive folder listing + file fetch, and the OAuth device-flow token |
| `sources/drive_errors.py` | The ways a Drive fetch fails, each with its own fixed, human message (TI8, HO33). |
| `sources/drive_intake.py` | Drive intake: one pasted link or id becomes registered sources, or an honest typed failure. |
| `sources/drive_jobs.py` | Persist one Drive fetch job so the page can poll it and a restart cannot lose its result. |
| `sources/drive_link.py` | Parse a pasted Google Drive link (or a bare id) into a `DriveRef`: only an id survives. |
| `sources/drive_register.py` | Registration for DRIVE sources: `register_drive` -> `Source` rows. |
| `sources/drive_verify.py` | Drive fetch verification: bound the download, check size and md5, stage it, or remove it. |
| `sources/email.py` | Parsing for EMAIL sources: `.eml`/`.mbox` LOCAL files only. |
| `sources/email_register.py` | Registration for EMAIL sources: `register_email` -> `Source` rows. |
| `sources/extract.py` | Deterministic host-side text extraction for DOC sources. |
| `sources/gws_drive.py` | The real Drive seam: the existing `gws` CLI login behind `DriveFetcher` (metadata, list, fetch). |
| `sources/gws_runner.py` | Run the `gws` CLI as a subprocess: an argument list, a timeout, a size watch, no shell. |
| `sources/intake_commit.py` | Atomic video registration, the per-project intake lock, staging and orphan sweep. |
| `sources/zip_intake.py` | Safe zip expansion: one video source per video member, everything else accounted for. |
| `sources/zip_names.py` | Zip member-name vetting that behaves identically under Windows and Ubuntu path rules. |
| `stages/acceptance_comparison.py` | Build and check the T-136 acceptance comparison from stored bench artifacts. |
| `stages/account_destroy.py` | One job: decide whether a control would destroy the account (Umesh 2026-10-15, D-098). |
| `stages/adjudicate.py` | ADJUDICATE: merge every model's chunked observations into one reading. |
| `stages/adversarial.py` | ADVERSARIAL: a bounded pass of file-defined probes at one AI endpoint. It records, never judges. |
| `stages/agent_actuator.py` | AGENT_ACTUATOR: the guards, bounds and typed boundary around an agent that drives a page. |
| `stages/agent_loop.py` | Agent fallback: when a case's steps break, ask the agent for a fix and retry. |
| `stages/ai_capture.py` | AI CAPTURE: exercise one AI endpoint and record what happened. It observes and never decides. |
| `stages/ai_catalog.py` | AI CATALOG: which Track C checks apply to a classified AI target, and which can run now. |
| `stages/ai_judge.py` | AI JUDGE: map captured observations into the existing grade stage's evidence and rubric. |
| `stages/ai_report.py` | AI REPORT: one Excel workbook of a project's stored Track C evidence, grouped by tier (T-155). |
| `stages/analysis_flows.py` | Turn a finished `VideoAnalysis` into DRAFT flows in the FlowSpec (TV9, R37). |
| `stages/analyze_video.py` | ANALYZE: run the ensemble over a prepared recording, then adjudicate. |
| `stages/bench.py` | BENCH: the north star made measurable. Contract: qa/contracts/bench.md K1-K5. |
| `stages/bench_from_run.py` | Turn a real project's executed+graded run into the T-136 bench files. Contract: bench.md K10. |
| `stages/browser_recovery.py` | Bounded recovery from a closed browser between serial cases (AT-888). |
| `stages/browser_use_backend.py` | BROWSER_USE_BACKEND: browser-use (MIT) as the `ActuatorBackend` for unknown screens (T-177). |
| `stages/bug_loop.py` | BUG LOOP: a tracked bug's lifecycle as one table and a fold over events (T-199a, TB1-TB4, TB6). |
| `stages/bug_run.py` | BUG RUN: turn one finished run's verdicts into bug events, and notice cases that moved (T-199b). |
| `stages/bug_wiring.py` | BUG WIRING: the one door from a finished run to the project's tracked bugs (T-199d). |
| `stages/case_expectation.py` | Does a case's own expected outcome say an error is the correct result? (grader-expected-error) |
| `stages/catalog.py` | CATALOG: derive, per `CaseClass`, whether it applies, whether it can run |
| `stages/coverage.py` | COVERAGE: diff what a run actually saw against what the FlowSpec knows. |
| `stages/crawl_coverage.py` | What a crawl covered, stated by the crawl itself — and every hole, with its reason (V7). |
| `stages/crawl_report.py` | The crawl, as something a human can read: an Excel workbook and the |
| `stages/credential_files.py` | Which file names and suffixes hold credentials; they are refused without being opened. |
| `stages/discover.py` | Inspect approved bounded file trees for deterministic, cited lexical signals. |
| `stages/entry_precondition.py` | Whether a case needs a logged-out visitor (so it must not share the signed-in profile). |
| `stages/eval_compiler.py` | EVAL COMPILER: compile evals from the knowledge graph, the FlowSpec and a written scenario |
| `stages/execute.py` | EXECUTE: run one case's steps in a real browser, producing a RawResult. |
| `stages/expand.py` | EXPAND: FlowSpec -> Case[], covering every applicable CaseClass per flow. |
| `stages/explore.py` | EXPLORE: a bounded, safety-gated BFS crawl of a (usually logged-in) app. |
| `stages/explore_consent.py` | The crawl's consent pre-flight (D-018 gate 2) — split from `explore.py` |
| `stages/explore_flows.py` | One job: derive reviewable `Flow` PROPOSALS from a crawl's discovery tree (AT-887, D-084). |
| `stages/explore_incremental.py` | Incremental crawl: don't re-explore a screen the persona already knows. |
| `stages/explore_merge.py` | Fold a crawl's screen graph into the reviewed FlowSpec (Track B5). |
| `stages/explore_node.py` | One node's worth of exploring: try each safe candidate action, record what |
| `stages/explore_replay.py` | Re-performing a discovering action, INCLUDING the values that were typed. |
| `stages/explore_return.py` | Getting the browser back onto a screen the crawl has already seen. |
| `stages/explore_runtime.py` | The live state of one crawl in flight — session, store, clock, counters. |
| `stages/explore_safety.py` | The explorer's inner safety guard (Track B4, D-016). |
| `stages/explore_status.py` | How a finished crawl is judged, and how a stored one is shown (X16, X18). |
| `stages/explore_summary.py` | Crawl persistence hygiene: redact what is written, and write the tracked summary. |
| `stages/explore_traversal.py` | Which screen the crawl visits next — the frontier's ORDER, and nothing else. |
| `stages/explore_typing.py` | The X10-b typing pre-pass (D-029): what the crawler types, and where it |
| `stages/failure_bundle.py` | Assemble and load one atomic failure bundle (T-178, qa/contracts/failure-bundle.md FB1-FB3). |
| `stages/generic_acceptance.py` | GENERIC ACCEPTANCE: one harness that drives a product through BOTH entry modes (T-169). |
| `stages/grade.py` | GRADE: an independent, stateless judge reads a Rubric + a RawResult's evidence. |
| `stages/grade_note_guard.py` | The notes-vs-verdict cross-check: a judge PASS whose own note describes a defect is not a PASS. |
| `stages/ingest.py` | INGEST: turn a video Source into a FlowSpec, provenance-tracked to the second. |
| `stages/issues.py` | ISSUES: turn an adjudicated analysis into rows a human tester can read. |
| `stages/knowledge_graph.py` | KNOWLEDGE GRAPH: build the typed graph from the persona + FlowSpec, and resolve a |
| `stages/known_bugs.py` | Map an AI-assisted video-review findings list to a `BenchCorpus` (bench.md K12). |
| `stages/manual_login.py` | Manual one-time login. Contract: qa/contracts/manual-login.md ML1-ML5. |
| `stages/media_prep.py` | MEDIA PREP: make a recording readable — probe it, cut it, transcribe it. |
| `stages/merge_flowspec.py` | Fold a freshly ingested FlowSpec into the reviewed one (Track A6, T-135). |
| `stages/network_capture.py` | First-party network capture as evidence (T-170, NA1/NA2/NA4/NA5/NA6). |
| `stages/orchestrate.py` | ORCHESTRATE: drive the stage pipeline as a resumable LangGraph run (D-041, T-167). |
| `stages/orchestrate_checkpoint.py` | Persist one run's LangGraph checkpoint without arbitrary Python deserialization. |
| `stages/orchestrate_gate.py` | The checks and ledger views around the orchestration graph (RR2, T-167). |
| `stages/orchestrate_runners.py` | The concrete stage runners the orchestrator threads — thin adapters over the |
| `stages/parallel_run.py` | PARALLEL_RUN: fan N cases out across isolated browser contexts (T-173/D-041). |
| `stages/persona_changes.py` | What moved in the product since the last crawl: new / changed / missing / broken. |
| `stages/portal_persona.py` | PORTAL PERSONA: promote per-crawl knowledge into the durable, cross-run |
| `stages/portal_persona_view.py` | Render a `PortalPersona` as `knowledge.md` — a human-readable VIEW of the |
| `stages/product_map.py` | PRODUCT MAP: fold every recording analysis into one navigable screen map. |
| `stages/reachability.py` | One job: warn, before a run, about cases aimed at screens the latest crawl never reached. |
| `stages/read_context.py` | Read approved Markdown as metadata only, never a vault graph or body corpus. |
| `stages/real_acceptance.py` | REAL-TARGET ACCEPTANCE DRIVER (T-169 GR1-GR4): approvals, evidence files, human checklist. |
| `stages/reconcile.py` | RECONCILE: re-map what each video taught onto the product knowledge graph (D-070 part 2). |
| `stages/release.py` | The release trigger: stitch every flow's persisted plan into ONE gated release run (T-167). |
| `stages/release_compare.py` | Release record assembly, the trusted-baseline rule and the regression diff (T-167, RR3/RR6). |
| `stages/report_delivery.py` | The report label (computed once) and the website inbox listing (TT7, R58, R22). |
| `stages/report_export.py` | Tester-style run reports: an Excel summary and a screen-by-screen HTML |
| `stages/review.py` | FlowSpec review gate: nothing generates cases from an unreviewed understanding |
| `stages/review_recall.py` | Score stored video reviews against an oracle corpus into a `ReviewRecall` (TA16). |
| `stages/run_budget.py` | RUN_BUDGET: the consent budget one case run spends against (AT-570/AT-660). |
| `stages/run_case_pipeline.py` | RUN_CASE_PIPELINE: the one function that runs a case and grades it. |
| `stages/run_launcher.py` | The one run launcher: gates, execution and the saved `Run` (T-205, team-foundation TF1/TF2). |
| `stages/run_record.py` | T-136c: persist a finished run with its measured wall clock and name it for bench tooling. |
| `stages/run_service.py` | Run / report / catalog as plain functions for the CLI and the MCP server (T-174, CM1-CM4). |
| `stages/schedule_gate.py` | The TS5 gate: a scheduled run may start only under the credential-derived approval (D-068). |
| `stages/schedule_owner.py` | HO24: a schedule has no more rights than its owner, checked at fire time. |
| `stages/schedule_store.py` | The files the scheduler writes: slot claim markers, slot records and the tick heartbeat. |
| `stages/schedule_sweep.py` | TS7: a scheduled run killed after its enqueue must not stay `enqueued` forever. |
| `stages/schedule_tick.py` | One stateless pass over every scheduled project, plus the heartbeat and `--dry-run` (TS7). |
| `stages/schedule_time.py` | Slot arithmetic: which UTC instants does a schedule mean to fire at, inside a window? |
| `stages/schedule_wiring.py` | Wires the scheduler core to the real world: the projects on disk, the run queue, the TS5 gate. |
| `stages/scheduler.py` | The scheduler core (G5): which slots are due, who may claim them, and what a tick records. |
| `stages/score.py` | SCORE: compare AutoTester's issues against a human tester's own sheet. |
| `stages/screen_identity.py` | Screen identity: the rules that decide when two screens are one. |
| `stages/script_replay.py` | SCRIPT_REPLAY: record a working live run's locators as a `Script`, then replay it for free. |
| `stages/sheet_plan.py` | SHEET PLAN: from the open bugs and one read of the sheet, the exact cells a sync would write. |
| `stages/sheet_sync.py` | SHEET SYNC: try to sync a project's bugs to its sheet, and turn any failure into a status (TB12). |
| `stages/sheet_write.py` | SHEET WRITE: the sheet client interface, the dry run, and the guarded write of a confirmed plan. |
| `stages/similarity_score.py` | How two bug reports are compared for `stages/score.py`'s T-136 scorer. |
| `stages/synthetic_values.py` | The synthetic value generator (X10-b, D-029): what the crawler types. |
| `stages/text_lines.py` | Number lines by  |
| `stages/tracker_binding.py` | TRACKER BINDING: propose a project's column mapping from a header row, and keep it per project. |
| `stages/tracker_export.py` | TRACKER EXPORT: BugStore bugs as CSV / xlsx bytes in the Tracker sheet's layout (TB15). |
| `stages/unified_report.py` | The damage-control report's loaders and assembly (T-168, `damage-control-report.md` DC1-DC4). |
| `stages/unified_report_render.py` | Draws a `UnifiedReport` as ONE self-contained HTML file (T-168, DC1-DC3). |
| `stages/ux_advisory.py` | The advisory UX pass: read a finished run's evidence as a persona, record findings (T-190). |
| `stages/video_access.py` | Who may open a video, and how: the video resource, shares and share links (TP1, TP3). |
| `stages/video_comments.py` | Timestamped comments on a video, and promoting one to a pointer (TP2, TP6). |
| `stages/video_pointers.py` | Parse a reviewer's pointer file into typed lines and a whole error list (TV1). |
| `stages/video_requests.py` | The request-access flow (TP5): ask, route to the people who may approve, decide once. |
| `stages/video_retention.py` | T-191/AT-587 V5: keep at most the N most recent kept videos, project-wide. |
| `stages/video_review.py` | Review one recording with human pointers: the typed, redacted, capped, idempotent run (T-197). |
| `stages/video_review_items.py` | Turn a model reply into validated confirm-list items (TV3, TV4, TV5, TV6). |
| `stages/video_review_plan.py` | Which seconds of a recording get looked at, and which do not (TV2, TV7 preview). |
| `stages/video_review_prompt.py` | Build the model prompt for one batch of frames, and say what narration there is (TV5, TV6). |
| `stages/video_review_render.py` | Render a stored review as Markdown or HTML with the identical item set (TV10, TV4, TV6). |
| `stages/video_review_store.py` | Find the stored reviews of one recording (T-197 TV10): newest first, read-only. |
| `store/approval_revocations.py` | Read and append the sibling `approval_revocations.jsonl` of a project. |
| `store/bug_store.py` | BUG STORE: the set of bug events, one file each, under a caller-given directory (T-199a/b, TB6). |
| `store/crawl_store.py` | Crawl artifact persistence — split from `project_store.py` at the |
| `store/filestore.py` | The one place any artifact is read from or written to disk. Contract: core-invariants.md C6. |
| `store/project_store.py` | Typed convenience over `filestore` for one project's directory (C1/C3). |
| `store/request_store.py` | Video-request persistence — split from `project_store.py` at the 300-line |
| `store/run_store.py` | Persistence for the advisory UX track: personas and one run's `UXReport` (T-190, PU1/PU2). |
| `store/server_settings.py` | Read and write the admin's server settings; resolve what is in force right now. |
| `store/team_store.py` | The sibling store for team data: markers, records, preferences, outboxes (T-205/TF7, R65). |
| `ui/admin_view.py` | Markup for the admin pages: accounts, groups and the permission checkboxes (AU8, AU10). |
| `ui/app.py` | Thin FastAPI project-list, onboarding and live-view pages over project files. |
| `ui/auth_middleware.py` | The login gate (T-204, auth.md AU6/AU13/AU14/AU16/AU22): one ASGI middleware that |
| `ui/auth_view.py` | Markup for the sign-in, sign-up and "waiting for an admin" pages (T-204). |
| `ui/case_form.py` | Rendering the add-a-case form. Contract: qa/contracts/ui.md. |
| `ui/crawl_view.py` | HTML fragments for the crawl pages — split from `routes_crawls.py` to keep |
| `ui/credential_guard.py` | Credential-guard helpers: refuse a real secret typed into any UI text field. |
| `ui/env_editor.py` | The one legitimate WRITE path to the repo-root `.env` (every other module |
| `ui/error_pages.py` | App-wide `HTTPException` -> HTML page, split out of `ui/app.py` to keep that |
| `ui/helpers.py` | Shared request-validation and lookup helpers used by every UI route module. |
| `ui/inbox_view.py` | Markup for "My reports" (TT7). Presentation only: it renders the `InboxEntry` rows the |
| `ui/intake_gate.py` | The one seam where sign-in and project permission plug into video intake. |
| `ui/intake_gate_auth.py` | The real intake gate: sign-in and `video.upload` on that project (team-intake.md TI10, TI11). |
| `ui/intake_upload.py` | The Add-videos upload door: one form field takes a recording or a zip of them. |
| `ui/preflight_view.py` | One job: render a run's preflight warnings as a card for the run report page. |
| `ui/project_view.py` | The project page's action card — the operator's control panel for one product. |
| `ui/routers.py` | The one ordered list of routers the UI app serves (T-204/T-205, TF3). |
| `ui/routes_access_requests.py` | Share-link opening, request-access, and the approvers' list (T-198b / G9, TP3, TP5). |
| `ui/routes_admin.py` | Admin routes: accounts (users.manage, AU8) and groups (groups.manage, AU10). |
| `ui/routes_auth.py` | Sign in, sign up, sign out and the waiting page (T-204, auth.md AU2-AU7). |
| `ui/routes_cases.py` | Create, list, rename and delete a project's test cases from the UI. |
| `ui/routes_catalog.py` | The test catalog page: one row per `CaseClass`, a green runnable count, and |
| `ui/routes_crawl_approval.py` | The crawl-approval card on the credentials page (D-018 consent, gate 2). |
| `ui/routes_crawl_login.py` | Which case a crawl logs in with — declared once on the project, shown before a crawl (X17). |
| `ui/routes_crawls.py` | The explorer, on screen: crawl history, one crawl's screen graph, its |
| `ui/routes_credentials.py` | The credentials editor: values shown (editable, passwords masked with a |
| `ui/routes_flow_diagram.py` | The BFS-style companion to `routes_report.py`'s DFS per-run step flow: |
| `ui/routes_inbox.py` | The website inbox, `GET /inbox` ("My reports", T-201 TT7; the owner-visible half of T-200 |
| `ui/routes_intake.py` | The Google Drive door of Add-videos: paste a link, get a background job and its result page. |
| `ui/routes_issues.py` | Operator-facing video issue ledger and its human-compatible workbook. |
| `ui/routes_learn.py` | The learning loop on screen — review the FlowSpec, generate cases, see the asks. |
| `ui/routes_live.py` | Presentation-only noVNC page for watching the container's real browser, plus |
| `ui/routes_product_map.py` | Product-map cards, recorded journeys, and guarded learned-frame serving. |
| `ui/routes_project_access.py` | Who can reach one project: owner, assignees (project.assign) and shared-with |
| `ui/routes_project_edit.py` | Edit a project's own settings after onboarding. Contract: qa/contracts/ui.md. |
| `ui/routes_proposals.py` | Review a project's proposed test cases from the UI: list, approve, prune, single or bulk. |
| `ui/routes_report.py` | Run history, screenshots and downloads. Contract: qa/contracts/ui-report.md UR1-UR4. |
| `ui/routes_runs.py` | Trigger a real run. Contract: qa/contracts/ui-run.md RU1-RU4. Run-history |
| `ui/routes_schedule.py` | The schedule routes (TS1): view the card, save, pause, resume and delete one project's schedule. |
| `ui/routes_server_settings.py` | The admin page for server limits (hosting.md HO15): run concurrency and the upload ceiling. |
| `ui/routes_settings.py` | Global AI/API provider keys. Contract: qa/contracts/ui-settings.md US1-US4. |
| `ui/routes_sources.py` | The operator-facing recording registry. |
| `ui/routes_team_run.py` | The team Test button (T-201b, qa/contracts/team-test-button.md TT1-TT6): a teammate with |
| `ui/routes_tracker.py` | The internal bug tracker page and its Tracker-layout export (T-199, TB7 in part, TB15). |
| `ui/routes_unified_report.py` | The damage-control report as a page (T-168): the lead's two-step route from the project page. |
| `ui/routes_video.py` | Serves a kept run video (T-191 evidence) by its evidence-relative path -- |
| `ui/routes_video_comments.py` | Comment routes of the video portal (T-198b / G9, TP2, TP6). |
| `ui/routes_video_portal.py` | The video page, its byte route and the sharing controls (T-198b / G9, TP1, TP3). |
| `ui/routes_video_review.py` | POST /projects/{slug}/videos/{video_id}/review: the "Run review" button (TA5, TV7). |
| `ui/run_execution.py` | Serial and parallel case-execution helpers for a triggered run. |
| `ui/run_queue.py` | The server-wide run queue (T-203, D-072 G6, hosting.md HO15-HO20): pressing Test returns at once. |
| `ui/run_queue_view.py` | The queue status card shown on a project's runs page (T-203): what is queued, running, done. |
| `ui/schedule_view.py` | The project schedule card (TS1): what the schedule is, when it fires next, what it did last. |
| `ui/team_run_view.py` | Markup for the team Test button (T-201b): the button, the request status page, the "started |
| `ui/theme.py` | Shared visual system for every UI route. Contract: qa/contracts/docker.md D5. |
| `ui/theme_style.py` | The raw CSS/font-link template for every page. Split out of `theme.py` |
| `ui/upload_stream.py` | Read one multipart upload from the wire into a staged file, stopping at the admin limit. |
| `ui/video_portal_view.py` | The HTML of the video portal: player page, request-access page, shared list, requests list. |
| `ui/video_review_view.py` | The Review card on the video page: a Run review form (if allowed) and the latest review. |
<!-- /generated:map -->

## Schema summary

<!-- generated:schema -->
| Model | Meaning |
|---|---|
| `Measure` (`schema/acceptance.py`) | One reported measurement: exactly one of a value or an unavailable reason. |
| `ParticipantColumn` (`schema/acceptance.py`) | One side of the comparison, with its K6 kind and K7 ordering split. |
| `BugRow` (`schema/acceptance.py`) | One ground-truth bug and which participants found it. |
| `AcceptanceComparison` (`schema/acceptance.py`) | The comparison a reader who was not there can judge (bench.md K9). |
| `PathMeasure` (`schema/agent_comparison.py`) | What one path produced on the SAME corpus. All four numbers are measured, not estimated; |
| `Comparison` (`schema/agent_comparison.py`) |  |
| `FallbackActionKind` (`schema/agent_fallback.py`) |  |
| `FallbackAction` (`schema/agent_fallback.py`) | One action the agent chose, as the guards see it (AF3). |
| `ActuatorResult` (`schema/agent_fallback.py`) | What a backend returns after driving the page: the actions taken, what it observed and |
| `FallbackStatus` (`schema/agent_fallback.py`) | How an invocation ended. Deliberately no PASS: only `grade.py` writes a verdict. |
| `FallbackOutcome` (`schema/agent_fallback.py`) | The adapter's whole answer for one invocation. `reason` names the bound, the refusal or |
| `WinRule` (`schema/agent_guardrails.py`) | When the agent counts as a gain over the pipeline. Default (awaiting Umesh): the agent |
| `AgentGuardrails` (`schema/agent_guardrails.py`) | Per-run ceilings: the token/cost budget (D-042) and the step cap. Domains and the write |
| `AgentToolName` (`schema/agent_layer.py`) | The stage tools of the lead tester. |
| `ToolEffect` (`schema/agent_layer.py`) | What a tool can do to the outside world. T-180 allowlists subagents by this. |
| `RefusalClass` (`schema/agent_layer.py`) | Why a tool call produced no action. A refusal is a result, never an exception the |
| `ToolSpec` (`schema/agent_layer.py`) | One tool: its name, effect, and the existing function it wraps (C3). |
| `CrawlArgs` (`schema/agent_layer.py`) | Bounds the model REQUESTS; the approval decides whether they are granted. |
| `RunCaseArgs` (`schema/agent_layer.py`) |  |
| `GradeCaseArgs` (`schema/agent_layer.py`) |  |
| `ReadCaseArgs` (`schema/agent_layer.py`) | Evidence reads (T-180): which case's stored artifact to read; the run is trusted context. |
| `EmptyArgs` (`schema/agent_layer.py`) | Tools that take nothing (`get_persona`, `get_catalog`): everything is trusted context. |
| `ToolOutcome` (`schema/agent_layer.py`) | What a tool call returns to the model. `summary` is scrubbed before it is built, and the |
| `AiCheckKind` (`schema/ai_check.py`) | One behavioural check an AI target can be put through. Enum order is report order. |
| `AiCheckMethod` (`schema/ai_check.py`) | Who decides a check: code from recorded facts, or the independent judge (C7). |
| `AiReply` (`schema/ai_check.py`) | What an AI endpoint answered, as the transport seam hands it to the capturer. |
| `AiExchange` (`schema/ai_check.py`) | One prompt and what was observed of its answer. Facts only: no verdict lives here (C7). |
| `AiCapture` (`schema/ai_check.py`) | A captured run of one check against one endpoint: observation, never judgement. |
| `ProbeSet` (`schema/ai_probe.py`) | One probe file under `prompts/probes/`: a category name and its probe texts (AD4). |
| `ProbeRecord` (`schema/ai_probe.py`) | One probe sent and what was observed of the answer, tagged with the set it came from. |
| `ProbeRun` (`schema/ai_probe.py`) | A completed bounded pass against one endpoint: observation, never judgement (AD5). |
| `ProbeRefusal` (`schema/ai_probe.py`) | One line of `refusals.jsonl` (AD7). Carries no probe content, by construction. |
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
| `ApprovalRevocation` (`schema/approval_revocation.py`) | One human's withdrawal of consent previously granted by `approval_id`. |
| `PermissionKey` (`schema/auth.py`) | The closed catalogue (auth.md "Permission catalogue"). |
| `Scope` (`schema/auth.py`) |  |
| `User` (`schema/auth.py`) | One account. The password hash never leaves the auth store's own modules. |
| `Group` (`schema/auth.py`) | An IAM-style group: a name, its ticked permissions, and its members' ids. |
| `ProjectRelation` (`schema/auth.py`) |  |
| `ResourceRef` (`schema/auth.py`) | What `authorize` judges a scoped key against (auth.md Vocabulary). |
| `Principal` (`schema/auth.py`) | Who makes the current request, resolved from a live server-side session. |
| `RouteRule` (`schema/auth.py`) | One row of the central route policy table (AU14). |
| `Provenance` (`schema/base.py`) | Who or what produced this artifact, and from what. |
| `Artifact` (`schema/base.py`) | Common envelope: versioned, timestamped, attributable. |
| `SeededBug` (`schema/bench.py`) | A deliberately introduced defect with known ground truth. |
| `Finding` (`schema/bench.py`) | One reported defect from a participant, matched against ground truth. |
| `BenchCorpus` (`schema/bench.py`) | A build with known seeded defects and the material pack given to testers. |
| `BenchTrial` (`schema/bench.py`) | One participant's attempt on one corpus. |
| `BadEventFile` (`schema/bug_run.py`) | An event file the store could not use. It is reported by name and never deleted (P4). |
| `BugSnapshot` (`schema/bug_run.py`) | One read of the log: the valid events (in replay order), the bugs they fold to, and the |
| `RunOutcome` (`schema/bug_run.py`) |  |
| `RunReport` (`schema/bug_run.py`) | What `process_run` did with one run. Counts are of events, not verdicts. |
| `BugLoopConfig` (`schema/bug_run.py`) | The per-project stored configuration of the bug loop: N, the consecutive evidenced PASS |
| `Case` (`schema/case.py`) | One generated or hand-written test case. |
| `CaseProposal` (`schema/case.py`) | A step-less candidate, bound to an exact FlowSpec snapshot and human review. |
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
| `CaseReport` (`schema/cli_output.py`) |  |
| `RegressionReport` (`schema/cli_output.py`) |  |
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
| `CrawlSummary` (`schema/crawl_summary.py`) |  |
| `DeliveryChannel` (`schema/delivery.py`) |  |
| `DeliveryStatus` (`schema/delivery.py`) |  |
| `ReportLabel` (`schema/delivery.py`) | The stored report label. Computed once elsewhere (TT7); every reader takes it as given. |
| `NotificationPref` (`schema/delivery.py`) | Per-user opt-in (HO26). Default OFF: no mail until the user ticks the box. |
| `Recipient` (`schema/delivery.py`) | Who a message goes to. Built from the authenticated identity, never from a request body. |
| `RunCounts` (`schema/delivery.py`) |  |
| `ReportSummary` (`schema/delivery.py`) | Exactly what HO28 lets a message carry: names, counts, one coverage line, a link. |
| `RenderedMessage` (`schema/delivery.py`) |  |
| `DeliveryRecord` (`schema/delivery.py`) | One attempt's outcome (TT9). Stores the user id, a redacted error, never the address. |
| `InboxEntry` (`schema/delivery.py`) | One row of the website inbox (TT7): a request the viewer may read the report of. |
| `SmtpConfig` (`schema/delivery.py`) | Transport settings from the environment. No password: that is read at send time (C5). |
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
| `IntakeOutcome` (`schema/intake.py`) | Exactly one of these per zip member that is listed (TI3). |
| `IntakeStatus` (`schema/intake.py`) | Overall result. `partial` is never reported as `ok` (TI5). |
| `ZipLimits` (`schema/intake.py`) | The archive-level caps beside the per-file one (which is the admin upload limit). |
| `UploadOrigin` (`schema/intake.py`) | A file picked in the browser; `file_name` is the name the client sent. |
| `ZipOrigin` (`schema/intake.py`) | A member of a zip: the archive's name and the member's path inside it. |
| `DriveOrigin` (`schema/intake.py`) | A Google Drive file, by its id (never its name or a link carrying a token). |
| `MemberResult` (`schema/intake.py`) | One row of the per-member table the CLI prints and the Add-videos page shows. |
| `IntakeReport` (`schema/intake.py`) | What one zip intake did. `exit_code` is 0 only when nothing failed. |
| `DriveRef` (`schema/intake.py`) | A pasted Drive link or bare id, parsed to the only thing that is ever used: the id. |
| `DriveItem` (`schema/intake.py`) | One Drive file's metadata as Drive reports it. `name` is untrusted text: it may become |
| `IntakeActor` (`schema/intake.py`) | Who the sign-in gate says is adding videos (TI10, TI11). `email` is None until T-204's |
| `DriveJob` (`schema/intake.py`) | One pasted Drive link being fetched in the background (HO33). Holds the Drive id and the |
| `Issue` (`schema/issue.py`) | One row of "what's wrong", derived from a video and (optionally) matched |
| `IssueKind` (`schema/issue_kind.py`) | What kind of problem a crawl-detected `CrawlIssue` is. |
| `ToolCallStep` (`schema/lead_loop.py`) |  |
| `DelegateStep` (`schema/lead_loop.py`) |  |
| `FinishStep` (`schema/lead_loop.py`) |  |
| `LeadRun` (`schema/lead_loop.py`) | What one lead loop did. `delegations` counts subagent calls actually made (AL7). |
| `TokenBudget` (`schema/lead_loop.py`) | A run's declared ceiling (AL11): tokens and/or cost. Either left unset is not enforced. |
| `AgentRun` (`schema/lead_loop.py`) | How one framework-driven lead run ended. `stopped` names the reason, so a budget halt is |
| `FeatureEvent` (`schema/ledger.py`) | One dated event in the life of a feature: planned, live, updated, or retired. |
| `RelitigationVerdict` (`schema/ledger.py`) | The judge's answer to "is this new unit a retired feature coming back?". |
| `DecisionClaim` (`schema/ledger.py`) | The strict inline declaration of a quotation attributed to a decision's What. |
| `CitationReview` (`schema/ledger.py`) | An inline inventory declaration, bound to exact visible occurrence content. |
| `SealedRecord` (`schema/ledger.py`) | One reviewed, hash-bound row covering the citations of a closed historical unit. |
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
| `TrackerConfig` (`schema/project.py`) | Where a project's confirmed bugs go (Group 10, T-205/TF6 placeholder). |
| `Project` (`schema/project.py`) | Everything the system needs to test one product. |
| `FlowPlan` (`schema/release.py`) | One flow's validation plan: the cases that decide whether the flow still works. |
| `ReleaseScope` (`schema/release.py`) | What one release executes, frozen when the run is first accepted (RR2/RR6). |
| `ReleaseDecision` (`schema/release.py`) | The human's answer to the `interrupt()` pause. It is NOT an approval (RR2). |
| `FlowOutcome` (`schema/release.py`) | One flow's line in the release log. `not_run` is never folded into `passed` (RR6). |
| `ReleaseIssue` (`schema/release.py`) | One entry of the release's single issues log, always naming its flow (RR6). |
| `RegressionDiff` (`schema/release.py`) | This release against its trusted baseline (RR3). `baseline_run_id` None = no baseline. |
| `ReleaseRecord` (`schema/release.py`) | One release's durable outcome: per-flow results, ONE issues log and the diff. |
| `OracleRef` (`schema/review_recall.py`) | Where the denominator came from. Never a claim of independence. |
| `ReviewRecall` (`schema/review_recall.py`) | `recall.json`. `k` and `unconfirmed_count` must be re-derivable from the id lists. |
| `Evidence` (`schema/run.py`) | A file or value the grader may cite. Already redacted and masked. |
| `ProviderUsage` (`schema/run.py`) | Token and call accounting per provider role — the cost story per run. |
| `RawResult` (`schema/run.py`) | One case's execution record. |
| `RunBounds` (`schema/run.py`) | The `RunApproval` bounds a run ACTUALLY ran under (AT-660/CN10). |
| `Run` (`schema/run.py`) | One regression run over a set of cases. |
| `QueueStatus` (`schema/run_queue.py`) |  |
| `QueueEntry` (`schema/run_queue.py`) |  |
| `RunQueueFile` (`schema/run_queue.py`) | The on-disk form (`<data root>/.work/run_queue.json`). |
| `StageName` (`schema/run_state.py`) | The pipeline stages a run drives, in canonical order. |
| `StageCheckpoint` (`schema/run_state.py`) | One stage's durable record within a run. |
| `RunState` (`schema/run_state.py`) | The ledger for one run, keyed by `run_id` (`OR5`: one run_id, one lineage). |
| `Branch` (`schema/scenario.py`) | One option of a scenario (the "yes" or the "no"): the data it changes in its flow |
| `ScenarioSpec` (`schema/scenario.py`) | One declared scenario variant of a flow. Its own graph node and case set (EC4). |
| `UncoveredBranch` (`schema/scenario.py`) | A scenario branch that produced no case, with the one reason why (EC5). |
| `CompileResult` (`schema/scenario.py`) | What `stages/eval_compiler.py::compile_evals` produced. |
| `ScheduleInvalid` (`schema/schedule.py`) | A value was refused at save. `field` names it; the caller stores nothing. |
| `WeeklyRule` (`schema/schedule.py`) |  |
| `ScheduleConfig` (`schema/schedule.py`) |  |
| `SlotRecord` (`schema/schedule.py`) | One append-only line per slot decision. Holds no secret: ids, instants and a short cause. |
| `SlotClaim` (`schema/schedule.py`) | The content of a claim marker: what the winning tick decided, so a crash can be re-driven. |
| `TickReport` (`schema/schedule.py`) | What one `autotester schedule tick` did: the JSON document of `--output json`. |
| `ElementRef` (`schema/screen_graph.py`) | One interactive element found by `browser/enumerate.js`. |
| `PageObservation` (`schema/screen_graph.py`) | One page-visit's raw material: its url/title and interactive elements. |
| `ScreenNode` (`schema/screen_graph.py`) | One distinct screen the crawl found. Identity is structural |
| `ScreenEdge` (`schema/screen_graph.py`) | One candidate action the crawl tried from one screen. |
| `CrawlFrontier` (`schema/screen_graph.py`) | The BFS queue state — persisted so a crash mid-crawl leaves a resumable |
| `ScreenVisit` (`schema/screenmap.py`) | One recording that showed this screen. |
| `MappedScreen` (`schema/screenmap.py`) | One screen folded across every recording that showed it. |
| `Journey` (`schema/screenmap.py`) | One recording's ordered path through screens. |
| `ScreenMap` (`schema/screenmap.py`) | The product map: every learned screen plus the journeys that visited them. |
| `ServerSettings` (`schema/server_settings.py`) | What the admin chose; absent fields keep the documented defaults. |
| `SheetColumns` (`schema/sheet_plan.py`) | Which sheet column holds which bug field. The mapping is an input here; proposing and |
| `SheetState` (`schema/sheet_plan.py`) | One read of the sheet's tab: the header row and the data rows under it (row 2 onward). |
| `CellChange` (`schema/sheet_plan.py`) |  |
| `CellConflict` (`schema/sheet_plan.py`) | A cell a human changed since we wrote it. It is reported and never overwritten (TB10). |
| `PlanRow` (`schema/sheet_plan.py`) |  |
| `SheetPlan` (`schema/sheet_plan.py`) | What a sync would write. `plan_hash` is derived from the content and checked on load. |
| `SyncMemory` (`schema/sheet_plan.py`) | What we last wrote, per bug and column, so a later human edit is told from our own value. |
| `PlanConfirmation` (`schema/sheet_plan.py`) | A named person saw the plan with this hash. Whether that person holds `project.edit` is |
| `SubagentName` (`schema/subagent.py`) |  |
| `SubagentSpec` (`schema/subagent.py`) | One subagent. Frozen: the allowlist cannot be widened after construction. |
| `SubagentInvocation` (`schema/subagent.py`) | What ONE subagent is handed (AL9): its own prompt, the task text, the files the lead |
| `ScheduleMode` (`schema/team_enums.py`) |  |
| `ScheduleZone` (`schema/team_enums.py`) | The only two zones a schedule may use (Umesh, 2026-10-07). IST is +05:30, no DST. |
| `SlotOutcome` (`schema/team_enums.py`) | What a tick decided for one slot. A record carries exactly one of these. |
| `SchedulerHealth` (`schema/team_enums.py`) |  |
| `CredentialState` (`schema/team_enums.py`) | Why the TS5 gate admits or refuses a run; the value leads the slot record's detail. |
| `RunVia` (`schema/team_enums.py`) | Which surface asked for a run (`Run.via`); `None` means the original UI Run button. |
| `SourceOriginKind` (`schema/team_enums.py`) | Where a `Source` came from (`Source.origin`); `None` means it predates provenance. |
| `AccessRequestStatus` (`schema/team_enums.py`) | Where an access request to a video stands (`AccessRequest.status`, TP5). |
| `StageSpan` (`schema/trace.py`) | One finished `StageCheckpoint` (RT3) — `trace_id` is always the run's |
| `LLMSpan` (`schema/trace.py`) | One call through `Provider.see_video`/`act`/`judge` (RT4), recorded at |
| `ToolSpan` (`schema/trace.py`) | One agent-layer step (T-179 AL5): a lead planning step, a tool call, or a delegation to a |
| `BugStatus` (`schema/tracked_bug.py`) |  |
| `EventKind` (`schema/tracked_bug.py`) | What happened, in the loop's vocabulary. The first seven are verdict-derived; `case_changed` |
| `BugSeed` (`schema/tracked_bug.py`) | What a bug is made of when its first FAIL opens it. |
| `BugEvent` (`schema/tracked_bug.py`) | One fact. `ref` is the idempotency token: a verdict ref (`run/case`), an issue ref |
| `TrackedBug` (`schema/tracked_bug.py`) | One bug, as folded from its events. Never written to disk. |
| `TrackerBinding` (`schema/tracker_binding.py`) |  |
| `SyncStatus` (`schema/tracker_binding.py`) |  |
| `RegressionSection` (`schema/unified_report.py`) | RR3/RR6: the release's single issues log and its diff against the trusted baseline. |
| `ApiFailure` (`schema/unified_report.py`) | One first-party response the product answered badly (NA1). `status` None = unreadable. |
| `ApiSection` (`schema/unified_report.py`) |  |
| `FailureLine` (`schema/unified_report.py`) | RE6: one unmet criterion, verbatim off the stored verdict. |
| `CaseLine` (`schema/unified_report.py`) | One case of the run. `result` is the grader's word, or `not run` / `no verdict`. |
| `WorkflowSection` (`schema/unified_report.py`) |  |
| `RevisionLine` (`schema/unified_report.py`) | One dated persona revision with the CR4 counts its owner produced. |
| `HistorySection` (`schema/unified_report.py`) |  |
| `CoverageSection` (`schema/unified_report.py`) | DC1: the crawl's own figure and reason breakdown, the same rows the crawl page shows. |
| `UnifiedReport` (`schema/unified_report.py`) | One invocation's report: all four data classes, one artifact (DC3). |
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
| `PointerLine` (`schema/video_pointer.py`) | One accepted line. `kind` is `time` (one second), `window` (a range) or `free` |
| `PointerError` (`schema/video_pointer.py`) | One refused line. The raw text is deliberately not kept: it may carry a secret. |
| `PointerParse` (`schema/video_pointer.py`) | Everything a pointer file said. Count identity (TV1): |
| `RedactionWindow` (`schema/video_review.py`) | `[start_s, end_s]` of one source a human blanked out (frames) and muted (audio). |
| `FramePlan` (`schema/video_review.py`) | Which seconds will be looked at, and which stretches the reviewer pointed at. |
| `Spans` (`schema/video_review.py`) | `analysed` and `not_reviewed` tile `[0, duration_s]` exactly: no gap, no overlap. |
| `ReviewPlan` (`schema/video_review.py`) | The `--dry-run` preview: what a run WOULD do. Producing it makes zero provider calls. |
| `ReplyItem` (`schema/video_review.py`) | One item as a model returned it: every field optional, nothing trusted yet. |
| `ReviewReply` (`schema/video_review.py`) | The shape asked of the model. A reply that does not validate is a `failed` review. |
| `ConfirmItem` (`schema/video_review.py`) | One line of the confirm-list. `status` is a human's; a model can never set it. |
| `RejectedItem` (`schema/video_review.py`) | An item that failed validation. Kept with its reason, never rendered, never blank. |
| `VideoReview` (`schema/video_review.py`) | The stored review. `id` is derived from content (TV10), never from a clock. |
| `Share` (`schema/video_share.py`) | One person who may open one video (the video's `shared_with` entry). |
| `ShareLink` (`schema/video_share.py`) | A video's share link. Opening it grants nothing by itself (TP3); the token is not here. |
| `AccessRequest` (`schema/video_share.py`) | A signed-in person without access asking for it (TP5). One pending per person+video. |
| `VideoComment` (`schema/video_share.py`) | A comment at a second of the recording (TP2). `pointer_line` is set by TP6 promotion. |
<!-- /generated:schema -->

## Scripts

<!-- generated:scripts -->
| Script | One job |
|---|---|
| `scripts/adversarial_proof.py` | Credential-free, network-free proof that the adversarial pass refuses to exceed its scope. |
| `scripts/agent_live_comparison.py` | T-181 AL12: the LIVE agent-vs-pipeline comparison on the seeded local fixture product. |
| `scripts/append_decision.ps1` | append_decision.ps1 -- the ONLY legitimate write path to docs/DECISIONS.md |
| `scripts/bench_from_run.py` | T-136b: convert a real executed+graded run into the acceptance bench files. |
| `scripts/bench_trial.py` | T-120: the north star made measurable — first real human-vs-AI trial scorecard. |
| `scripts/check_acceptance_comparison.py` | T-136 done_check: is the Pathlynks acceptance comparison complete? (bench.md K9) |
| `scripts/check_crawl_approval.py` | T-145's done_check (D-018): a live crawl counts as done only if it actually |
| `scripts/check_deliverable.py` | Assert a task's deliverables exist — a `done_check` that can actually fail. |
| `scripts/check_no_secrets.py` | Scan files for any real value currently loaded in .env. Prints OK/LEAK only. |
| `scripts/explore_proof.py` | Credential-free end-to-end proof of the explorer (Track B3). |
| `scripts/flake_probe.py` | Measure a flaky test's real failure rate — and say how little N green runs prove. |
| `scripts/hosting_state_listing.py` | Print the durable state under a data root as JSON, for a before/after-restart diff (HO4). |
| `scripts/install_windows_task.ps1` | (no description) |
| `scripts/known_bugs_corpus.py` | Convert an AI-assisted review findings list to a known-bugs bench corpus (bench.md K12). |
| `scripts/migrate_stamp_legacy_rubrics.py` | Stamp `Provenance` on legacy default rubrics, in stored project data. |
| `scripts/migrate_url_patterns.py` | Repair `url_pattern` values mangled by AT-287/AT-294, in stored project data. |
| `scripts/mutation_check.py` | Prove a unit's new tests are not vacuous, by killing them on purpose. |
| `scripts/onboard_pathlynks.py` | Onboard Pathlynks: real login via the credential boundary, evidence, knowledge.md. |
| `scripts/regression_proof.py` | T-110: break a feature, confirm exactly that case FAILs while an unrelated |
| `scripts/renumber_duplicate_issue_ids.py` | Give fresh ids to the LATER row of every duplicated id in qa/issues.jsonl. |
| `scripts/review_recall.py` | Write `recall.json` (TA16): stored video reviews scored against an oracle corpus. |
| `scripts/run_pathlynks_first_cases.py` | T-050: 3 hand-written Pathlynks login cases (best/worst/edge), run headed and |
| `scripts/run_real_acceptance.py` | T-169 GR1-GR4: drive one acceptance mode against a REAL, already-onboarded project. |
| `scripts/score_video_issues.py` | Score AutoTester's issues against a human tester's sheet — T-136's acceptance. |
| `scripts/serve_windows.ps1` | (no description) |
<!-- /generated:scripts -->
