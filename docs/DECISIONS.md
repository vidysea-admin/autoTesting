# DECISIONS — d:/autoTesting (append-only history)

**Purpose:** the reasoned history of every design decision, experiment, and rejected approach in
AutoTester, so a later session cannot relitigate old ground without seeing why it was settled.
**Open me when:** you are about to change an approach, revive something, or need to know *why* the
system is shaped as it is. Never edit — append only via `scripts/append_decision.ps1`.
Schema: `D:/ai_os/templates/lab-protocol/DECISIONS.schema.md` (Lab Protocol v1.1: write-time status
∈ {ACTIVE, REJECTED}; SUPERSEDED is computed from later entries' `Supersedes:` fields).

## D-000 | 2026-09-03 | type: decision | status: ACTIVE
**What:** Adopted the Lab Protocol for this repo (append-only DECISIONS, computed-status injection,
authorized state edits) on top of the maker-checker pair installed the same day.
**Why:** Umesh's explicit requirement (goal.md, 2026-09-03): the previous product (`d:/erp`) lost
human control because schema, structure, and reasoning were never written down and drifted; this
project must stay readable to a human engineer and cheap for an agent to hold in context.
**Result:** `docs/DECISIONS.md` (this file) + `docs/archive/INDEX.md` + repo-committed hooks
(`.claude/hooks/lab-*.ps1`, `decisions-append-guard.ps1`) + `scripts/append_decision.ps1` +
`.claude/settings.json` hooks merged with the maker-checker hooks. `ARCHITECTURE.md` lives at
`docs/ARCHITECTURE.md` (plan §6 layout); the repo copy of the session-start hook falls back to it.
`qa/contracts/` + `autotester doctor` + `uv run pytest` are the validators — no separate
`contracts/verify_contracts.py` (spec'd project, not research-first data pipeline).
**Changes-authorized:** `.claude/settings.json` (hooks merge); `.claude/hooks/*` (lab + mc hooks);
`scripts/append_decision.ps1`; `qa/hooks/mc-*.ps1`; `CLAUDE.md` lab + maker-checker blocks —
enforcement wiring that lets the protocol and the pair travel with the repo.
**Approved-by:** Umesh — plan v2 (§7 Enforcement, §14 Living ledger) approved via `ExitPlanMode`
2026-09-03; maker-checker init authorized by "proceed ahead with /maker /checker" (2026-09-03).
**Links:** goal T-000, T-005; commits a5ffcec, 458304a; plan
`C:/Users/Lenovo/.claude/plans/great-when-you-really-iridescent-ocean.md`

## D-001 | 2026-09-03 | type: decision | status: ACTIVE
**What:** Design-first build: every domain shape is a Pydantic model in `src/autotester/schema/`
(`extra="forbid"`), one concept in one place, file ≤ 300 lines / function ≤ 50, clean repo root,
all model calls through `providers.base.Provider`, prompts as files. Enforced by `autotester doctor`.
**Why:** `d:/erp` reached 232 root entries, 977 source files, duplicated concepts, and a 291-line
landmine CLAUDE.md — unreadable to humans and expensive for agents. Cheap rules now, unaffordable later.
**Result:** `qa/contracts/core-invariants.md` C1–C8; doctor + ruff + pytest green at P0 (26 tests).
**Links:** goal T-000; commit a5ffcec; contract `qa/contracts/core-invariants.md`

## D-002 | 2026-09-03 | type: decision | status: ACTIVE
**What:** Stack and scope: Python; Gemini (key in hand) for vision/video + Anthropic SDK behind a
pluggable provider layer; first target Pathlynks; auth via `.env` credentials + persistent browser
profile with OTP as a human pause; file-based storage (JSON/JSONL per project, SQLite index later,
no Mongo for AutoTester's own state); Playwright headed by default; no LangGraph in v1.
**Why:** Umesh's answers 2026-09-03 (AskUserQuestion): Gemini key exists, Anthropic SDK preferred,
both wanted; Pathlynks is the real regression target; human-editable artifacts are the point.
File checkpoints give resumability with zero framework context cost; stage interface stays
LangGraph-node-shaped for a mechanical migration if headless-days autonomy is ever needed.
**Result:** plan v2 §1, §4, §6; provider seam + mock provider built at P0.
**Links:** goal T-000; plan §1 Decisions

## D-003 | 2026-09-03 | type: decision | status: ACTIVE
**What:** One credential file for the whole repo at the repo root (`d:/autoTesting/.env`), keys
namespaced per project (`PATHLYNKS_*`) and declared per project via `SecretRef[]` with domain
scope; undeclared values are masked but never resolvable. Replaces the per-project
`projects/<slug>/.env` in the first draft.
**Why:** Umesh, mid-cycle 2026-09-03: "place .env too in the root directory". Security is unchanged
(scoping comes from per-project `SecretRef.domains`; gitignore `**/.env` already covers root), and one
file is simpler to hand to a human.
**Result:** `core/paths.py::env_file` → root; contracts B1 + C5 amended by /checker (cycle 2); `.env.example` at root.
**Links:** goal T-011; verdict `qa/verdicts/t011-secret-store.md`; commit 06c614d

## D-004 | 2026-09-03 | type: decision | status: ACTIVE
**What:** Project-wide principle: **rules answer only where they are confident; everywhere else,
spend tokens on AI judgement.** A deterministic check may decide a case only when it can be certain
(exact id, explicit link); an absent keyword hit is never treated as confidence of "no match".
First application: the feature-ledger relitigation gate reads descriptions via the LLM.
**Why:** Umesh, grill 2026-09-03 Q6: "simplistic rule-based systems fail on edge cases and give a
confident wrong answer… it is better to lose the tokens instead of betting in the wrong direction."
**Result:** encoded in `qa/contracts/living-ledger.md` L4; to be cited by later contracts
(grader, coverage diff, case expander) wherever a threshold or match is decided.
**Links:** goal T-005; grill capture `.work/grill-living-ledger.md`

## D-005 | 2026-09-03 | type: decision | status: ACTIVE
**What:** CONFIRM the five-artifact model (FlowSpec / Case / RawResult / Verdict + Rubric) and the observation-vs-judgement split after the T-004 schema survey; AMEND before P2 ingest locks FlowSpec, additively only: `Action` += HOVER, PRESS_KEY, SCROLL Â· `ExpectedState` += answer{exact,must_include,fuzzy}, url_match, checks[] Â· `Case` += tags[] and a `DIMENSION_BY_CLASS` lookup (WebTestBench's four dimensions over our 15 classes) Â· `Flow` += setup_flow_id Â· `FlowSpec` += app_overview Â· `RawResult` += started_at, finished_at, attempt, browser, viewport Â· `Evidence` += content_type Â· `Verdict` += known_issue_ref, case_hash. No renames, no removals; `CaseClass` stays closed; `extra="forbid"` stays.
**Why:** Umesh asked whether the schema was web-researched; it had been brain- and market-scout-derived only. Surveyed Playwright Test Agents, Gherkin, WebTestBench, Mind2Web/Online-Mind2Web, WebArena evaluators, CTRF/Allure, Momentic/Midscene (docs/research/schema-2026-09.md). None separates executor observation from grader judgement or carries per-step source provenance â€” both are ours to keep. Every gap found is at the edges (action vocabulary, answer-style assertions, timing/attempt fields, tags) and is a field each now versus a migration plus re-review of every FlowSpec later.
**Result:** amendments scheduled as part of T-060 (ingest) and T-040 (execute); interop adapters Case->Gherkin, Verdict->CTRF, WebArena task->Case+Rubric, Run->Online-Mind2Web result.json proposed for a later unit. Rejected: (a) Scenario Outline in-model (expand to concrete Cases, fold back on export); (b) collapsing Outcome+Result into one CTRF-style status (loses the independent-grader guarantee); (c) opening CaseClass (the completeness guarantee is the product).
**Links:** goal T-004 (closed), T-060, T-040; docs/research/schema-2026-09.md; commit 5f83bdb

## D-006 | 2026-09-03 | type: session | status: ACTIVE
**What:** T-005 (living map + feature ledger) built and sent to /checker; D-005 appended. Found that `scripts/append_decision.ps1` read the UTF-8 entry file with the Windows-PowerShell default encoding, so the `·` and `—` characters in D-005 are stored as `Â·` / `â€”` — read them as a middle dot and an em dash. This file is append-only, so D-005 stays as written; the script now reads and writes UTF-8 (authorized by D-000 `Changes-authorized`: `scripts/append_decision.ps1`). The upstream template copy is outside this repo and is left to the checker/inbox.
**Why:** a history file that garbles punctuation on every non-ASCII entry would rot exactly the way the ERP notes did; fixing the write path once is cheaper than a lifetime of corrections.
**Result:** this entry is the first written through the UTF-8 path — the em dash here (—) and middle dot (·) should read correctly.
**Links:** goal T-005; qa/manifests/t005-living-ledger.md; qa/feedback-inbox.md (2026-09-03 tooling-defect entry)

## D-007 | 2026-09-03 | type: decision | status: ACTIVE
**What:** After every checker PASS commit, the checker pushes `origin master` itself — no confirmation asked. This replaces the prior default (push is a human decision, confirmed each time) for THIS repo only.
**Why:** Umesh, direct instruction 2026-09-03 ("but next time se tho tu khud push krr lega naa as a /checker" -> "yes wire that"): repeated per-push confirmation was friction once the repo was public and the pair's commits were already narrowly scoped and checker-verified. The confirm-first default remains the house rule everywhere else; this is a standing, explicit, repo-scoped exception.
**Result:** `CLAUDE.md` maker-checker block gets a "Push on PASS" line; the checker dispatch instructions (`maker/SKILL.md`'s prompt template is global, so this repo's own contract carries the addition instead) push after commit. Known residual: the harness-level safety classifier may still block a `git push`/`gh` call independent of this authorization — that gate is not lifted by this decision and the checker must fall back to reporting the block, exactly as today.
**Changes-authorized:** `CLAUDE.md` (maker-checker discipline block) — add the auto-push rule.
**Approved-by:** Umesh — direct instruction, this session, 2026-09-03.
**Links:** commit 04f5e3d (the manual push this rule replaces going forward)

## D-008 | 2026-09-03 | type: fix | status: ACTIVE
**What:** Fix `.claude/hooks/lab-session-start.ps1`'s ARCHITECTURE.md excerpt filter (AT-015): it
looked for numbered headings (`## 1.`/`## 2.`/`## 3.`/`## 6.`) from the generic Lab Protocol
template, but this project's `docs/ARCHITECTURE.md` uses named headings (`## What it does`,
`## Pipeline`, etc.) and always has — every prior unit's manifest confirms this project's own
house style is named, not numbered, sections. The filter therefore matched zero lines every
session, silently injecting an empty ARCHITECTURE block. Fix: keep every section except
`## Directory map and schema summary` (mechanical, generated into `docs/MAP.md` separately, not
needed as session-start "ground truth"), instead of an inclusion allowlist keyed to numbers that
never existed in this repo. The existing 100-line cap and `[... capped ...]` message are unchanged.
**Why:** Umesh approved this batch (2026-09-03, this session, via AskUserQuestion: "AT-015/AT-028
... Yes, approve both") after the checker's sweep-found issue AT-015 confirmed via direct grep
that zero ARCHITECTURE.md headings in this repo have ever matched the hook's numbered-section
regex, so every session start has silently injected an empty ground-truth block instead of the
intended architecture excerpt.
**Result:** `.claude/hooks/lab-session-start.ps1` lines ~111-124 changed from an inclusion
allowlist (`^## (1|2|3|6)[\.\s]`) to an exclusion of the one generated/mechanical section; the
injected label text updated to describe what's actually kept, not a numbered-section claim that
was never true.
**Changes-authorized:** `.claude/hooks/lab-session-start.ps1` (ARCHITECTURE excerpt filter only;
no other hook logic touched).
**Approved-by:** Umesh — direct approval, this session, 2026-09-03 (AskUserQuestion batch:
"AT-015/AT-028 ... Yes, approve both").
**Links:** issue AT-015 (`qa/issues.jsonl`); qa/manifests/at015-hook-fix.md

## D-009 | 2026-09-03 | type: fix | status: ACTIVE
**What:** Add `scripts` to `qa/adapter.json`'s slot-1 ruff command (AT-028): was `uv run ruff
check src tests`, becomes `uv run ruff check src tests scripts`. `scripts/` was empty when the
adapter's commands were allowlisted at the START gate (2026-09-03), but now holds real production
code (`scripts/onboard_pathlynks.py`, `scripts/check_no_secrets.py`, both shipped in T-030) that
every unit's manifest has actually been linting all along — the adapter's written command was the
stale artifact, not the practice.
**Why:** Umesh approved this batch (2026-09-03, this session, via AskUserQuestion: "AT-015/AT-028
... Yes, approve both") after the checker's t080-agent-loop and at011-loop-md checks both
independently confirmed the divergence between the allowlisted command and actual practice.
**Result:** `qa/adapter.json` line 10's `cmd` updated; `CLAUDE.md`'s Commands section already
reads `uv run ruff check src tests` too and gets the same `scripts` addition for consistency.
**Changes-authorized:** `qa/adapter.json` (slot-1 verify command only) and `CLAUDE.md` (Commands
section, to match).
**Approved-by:** Umesh — direct approval, this session, 2026-09-03 (AskUserQuestion batch:
"AT-015/AT-028 ... Yes, approve both").
**Links:** issue AT-028 (`qa/issues.jsonl`); qa/manifests/at028-adapter-fix.md

## D-010 | 2026-09-03 | type: fix | status: ACTIVE
**What:** Raise `.claude/hooks/lab-session-start.ps1`'s ARCHITECTURE.md excerpt cap from 100 to
150 lines (AT-029) — a correction found while fixing AT-015 under D-008. D-008's own committed
text said the cap was "unchanged," which became inaccurate the moment AT-015's broadened filter
(keep every named section except the generated directory map) needed more than 100 lines to
avoid truncating mid-file. D-008 is append-only and cannot be edited to reflect this; this entry
is the correct, explicit authorization the checker's cycle-2 verdict required
(`qa/verdicts/at015-at028-hook-adapter-fix.md`, AT-030).
**Why:** Umesh's original batch approval for AT-015 (2026-09-03, AskUserQuestion: "AT-015 (a
session-start hook injects an empty ARCHITECTURE block every session)... Approve both as one
routine batch?" → "Yes, approve both") authorized fixing AT-015 completely — a hook that still
truncates before reaching real content (Design rules/Commands/Status) has not actually fixed the
empty-injection bug, only partially. The cap value itself is not arbitrary: 150 matches
`docs/ARCHITECTURE.md`'s own C2 line-budget ceiling, so the excerpt (after excluding the one
generated section) can never exceed the source file's own maximum — a true ceiling, not an
active truncator under normal conditions.
**Result:** `.claude/hooks/lab-session-start.ps1` line ~126: `$keep.Count -ge 100` → `-ge 150`,
label text updated to say "capped at 150 lines". Independently re-verified by extracting the
literal code block from the file on disk and executing it against the real
`docs/ARCHITECTURE.md`: 139 lines kept, no truncation, all 10 headings present through `## Status`.
**Changes-authorized:** `.claude/hooks/lab-session-start.ps1` (the cap value on the ARCHITECTURE
excerpt filter only — same file D-008 already authorized, this entry names the specific
additional line D-008's text did not cover).
**Approved-by:** Umesh — the original AT-015 batch approval, this session, 2026-09-03
(AskUserQuestion: "AT-015/AT-028 ... Yes, approve both"), explicitly extended here to cover this
necessary correction to deliver that same approved fix, per the checker's requirement
(AT-030) that the authorization be named explicitly rather than assumed from D-008.
**Links:** issue AT-029, AT-030 (`qa/issues.jsonl`); qa/verdicts/at015-at028-hook-adapter-fix.md
(Cycle checked: 2, FAIL); qa/manifests/at015-at028-hook-adapter-fix.md

## D-011 | 2026-09-03 | type: fix | status: ACTIVE
**What:** Correct the authorization record for the ARCHITECTURE-cap raise (100→150 lines) in
`.claude/hooks/lab-session-start.ps1` — D-010's `Approved-by` line recycled the old AT-015/AT-028
batch-approval quote with an "explicitly extended here" assertion instead of quoting the actual
fresh, cap-specific approval exchange that happened this session. D-010's code/text is otherwise
accurate and is NOT re-litigated; this entry supplies the missing verbatim authorization only,
per the Lab Protocol's append-only rule (D-010 itself is never edited).
**Why:** Checker cycle-3 verdict (`qa/verdicts/at015-at028-hook-adapter-fix.md`) filed AT-031:
D-010's stated authorization did not match what the maker's own dispatch narrated as having
happened. The `/agent-debugger` diagnosis (`qa/debug/at015-at028-hook-adapter-fix-cycle3.md`)
confirmed this is an execution gap, not a process ambiguity — D-008/D-009 already modelled the
correct verbatim-quote pattern two entries earlier in the same file — and named "append a new
D-011 that directly quotes the real fresh approval exchange" as the routine, low-risk recovery.
**Result:** The real exchange, verbatim, from this session (AskUserQuestion, 2026-09-03):
Question: "Separately: the hook fix for AT-015 needed a follow-on correction (raising an
injection cap from 100 to 150 lines) that the checker says needs its own explicit sign-off, not
just an extension of your original 'approve both' batch answer. Approve this specific cap
change?" — Answer selected: "Yes, approve the cap change." This IS the specific, fresh, cap-only
approval AT-031 required; D-010's underlying code fix (the cap value, 150, matching
`docs/ARCHITECTURE.md`'s own C2 budget) stands unchanged and correct.
**Changes-authorized:** none (this entry corrects the authorization record only; no file besides
`docs/DECISIONS.md` itself changes as a result of D-011).
**Approved-by:** Umesh — direct answer, this session, 2026-09-03, quoted verbatim above.
**Links:** issues AT-030, AT-031 (`qa/issues.jsonl`); qa/verdicts/at015-at028-hook-adapter-fix.md
(Cycle checked: 3, FAIL); qa/debug/at015-at028-hook-adapter-fix-cycle3.md

## D-012 | 2026-09-05 | type: decision | status: ACTIVE
**What:** Rewrite every hook command in .claude/settings.json from `powershell -Command "$i=[Console]::In.ReadToEnd(); & \"$env:CLAUDE_PROJECT_DIR\...\" -InputJson $i"` to `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/<script>.ps1` for: decisions-append-guard.ps1, lab-session-end.ps1, lab-session-start.ps1. No hook script changes; the scripts already read stdin when -InputJson is empty.
**Why:** Claude Code executes hook commands through bash -c on this machine, which expands `$i` and `$env:...` to empty strings before PowerShell parses the command. Every hook in this repo has therefore failed with a parse error on every invocation since it was installed (evidence: `hook_non_blocking_error` records in the session transcripts; AIOS decisions/log.md 2026-09-05). The append-only DECISIONS guard, the session-start protocol snapshot and the /landplane reminder have never actually run here. Run with -File, the repo copies work (verified in D:/KnowledgeBase on 2026-09-05: lab-session-start injects the snapshot with a RECOVERY warning; decisions-append-guard denies a direct edit).
**Result:** Enforcement becomes live from the next session. The /init-lab template in the AIOS carries the same fix (templates/lab-protocol/project-settings.template.json, commit d2d93a4) so new repos are correct.
**Changes-authorized:** .claude/settings.json (hook command strings only; matchers, timeouts and entries unchanged)
**Approved-by:** Umesh
**Links:** AIOS decisions/log.md 2026-09-05 (two entries: machine-wide hook fix; Lab-repo finding); memory reference_hook_commands_run_under_bash

## D-013 | 2026-09-05 | type: decision | status: ACTIVE
**What:** Sync the committed hook scripts decisions-append-guard.ps1, lab-session-start.ps1 to the AIOS Lab-Protocol template (D:/ai_os/templates/lab-protocol/hooks, commit of 2026-09-05): JSON output is now ASCII-escaped before it is written. Behaviour otherwise unchanged.
**Why:** Under the harness PowerShell writes stdout in the OEM codepage; non-ASCII characters copied from ARCHITECTURE.md / DECISIONS.md into the session-start snapshot became 0x1a bytes inside the JSON string and Claude Code rejected the payload (raw-text fallback + a hook_non_blocking_error per session). Observed in this repo's live session on 2026-09-05 right after the hook commands were rewired (see AIOS decisions/log.md).
**Result:** The session-start snapshot and the append-guard reply are accepted as JSON; no more error records.
**Changes-authorized:** .claude/hooks/decisions-append-guard.ps1 , .claude/hooks/lab-session-start.ps1 (byte-identical to the AIOS template)
**Approved-by:** Umesh
**Links:** AIOS decisions/log.md 2026-09-05 (ASCII-escape addendum); hook-fixtures.ps1 'lab-session-start under chcp 437'

## D-014 | 2026-09-07 | type: decision | status: ACTIVE
**What:** Additive schema amendments for Track A (learn from recordings), per the approved plan (plan.md section 4) and the answered AT-052 gate. (1) Discharge D-005 items: `Action` += BACK, HOVER, PRESS_KEY, SCROLL (execute.py gains a `.get()` guard so an unhandled action is ERRORED, never a KeyError); `FlowSpec` += app_overview. (2) Move ObservedStep/ObservedFlow/ObservedScreen/VideoObservation from schema/flowspec.py to new schema/observation.py and extend them (t_end, url, purpose, fields, ui_elements, screenshot_ts; on_screen_text, narration; exit_screen; issues[], summary, open_questions) plus VisionOptions and ModelObservation. (3) New artifact kinds, each a schema model + ProjectPaths property + ProjectStore method, plain JSON/JSONL under projects/<slug>/ (C6): Transcript + MediaPrep (schema/media.py), VideoAnalysis (schema/analysis.py), Issue (schema/issue.py), ScreenMap (schema/screenmap.py). (4) Screen += source_ref; Source += recorded_on. (5) New closed vocabularies: IssueCategory (12 prior-art categories + feature_gap, wrong_model, data_error), IssueOrigin, IssueStatus, Confidence. `CaseClass` stays closed -- Issue is a separate artifact (D-005's rejection stands). Media prep is host-side ffmpeg/faster-whisper via subprocess; every model call stays behind providers.base.Provider; prompts stay files.
**Why:** Umesh 2026-09-07: "product map, Test cases, issues excel and product flow end to end. like all maximum learning we can take." VideoObservation cannot carry issues, urls, fields or screenshot moments, and nothing persists what a video taught the system. Ground truth is dominated by spoken change requests (10/33 "Feature gap" rows) which the prior taxonomy has no home for. Additive now vs a re-review of every FlowSpec later (D-005's own reasoning). Corrected fact: erp1/2/3.mp4 are scored against ERP_Issues_Trainers.xlsx (7 rows); the 33 rows of ERP_Issues_ALL.xlsx belong to other recordings.
**Result:** units T-130..T-136 build on these; A1 (T-130) is schema-only. Plan of record copied into the repo as plan.md (allow-listed in doctor's root rule) so the backlog never again lives only outside the repo.
**Changes-authorized:** docs/ARCHITECTURE.md (Pipeline, Concept-to-file table, Storage, Commands, Status -- unit A6); qa/contracts/ingest.md (I6-I9); new qa/contracts/video-learning.md (VL1-VL8); qa/contracts/coverage.md no-fire amendment; qa/contracts/report-export.md scope note; .gitignore (chunks/, frames/ under projects/*/sources/*/); src/autotester/doctor.py ALLOWED_ROOT_ENTRIES += plan.md.
**Approved-by:** Umesh -- plan approved 2026-09-07 (plan.md), gate qa/gates/at052-bfs-video-corpus-grill.md.
**Links:** T-121, T-130..T-136; D-005; plan.md; C:/Users/Lenovo/Videos/Screen Recordings/ERP_Issues_Trainers.xlsx

## D-015 | 2026-09-07 | type: decision | status: ACTIVE
**What:** Build the autonomous explorer as a NEW stage stages/explore.py (+ explore_node.py, explore_safety.py, explore_merge.py, screen_identity.py) under its own contract qa/contracts/explore.md; execute.md E5 stays intact -- run_case never invents an action, the explorer is the one place that does. New model families schema/screen_graph.py (ElementRef, PageObservation, ScreenNode, ScreenEdge, CrawlFrontier, ScreenNaming) and schema/crawl.py (CrawlBounds, SafetyPolicy, DialogEvent, CrawlIssue, Crawl); enums NodeStatus, EdgeOutcome, IssueKind, CrawlStatus. New browser modules browser/observe.py (+ enumerate.js) and browser/launch.py (launch_options moved verbatim out of session.py, which is at its C2 cap). Screen identity = content_id over (templated URL path + structural signature of non-row interactive elements), never URL alone and never an LLM description. Artifacts under projects/<slug>/crawl/<crawl_id>/ as JSONL; shots/ gitignored. Rejected: extending Provider.act with images for vision-guided crawling -- the crawl is DOM-driven and deterministic; a model is optional and only names screens.
**Why:** Umesh 2026-09-07: "mere bhaai ye sab tho honaa mandatory"; blast radius "jo jo uss account mai access hoga vo krr lengee" (gate at052 answered). The prior attempt failed on URL-only identity (SPAs invisible), an LLM-text stop condition that never fired, beforeunload dialog traps, GA noise reported as issues, and coverage from "did the script run" -- each is designed against in explore.md X1-X12.
**Result:** units T-140..T-145 (B1, B2, B4, B3, B5 in that order, then the live ERP demo). B4 (safety) lands before B3 (crawl) so a crawler never exists in this repo without brakes.
**Changes-authorized:** docs/ARCHITECTURE.md concept-to-file row for the explorer (offset by folding the Pathlynks onboarding row into the scripts row; file stays at 150 lines) and Storage line; .gitignore projects/*/crawl/*/shots/; qa/contracts/explore.md (new, checker-owned); execute.md E2 and browser-and-secrets.md routine amendments after B1; coverage.md V1 after B5.
**Approved-by:** Umesh -- plan approved 2026-09-07 (plan.md section 5).
**Links:** T-140..T-145; qa/gates/at052-bfs-video-corpus-grill.md; D-005; D-014; D-016; plan.md

## D-016 | 2026-09-07 | type: decision | status: ACTIVE
**What:** Project.write_policy is enforced at runtime for the first time, by the explorer only (stages/explore_safety.py), as an INNER guard inside Umesh's outer boundary (the test account's own permissions). For crawler-invented actions: READ_ONLY -- destructive-name deny-list ON, form-submit controls never clicked, nothing typed. TEST_ACCOUNT -- deny-list ON, submits allowed, nothing typed. ALLOW_WRITES -- deny-list OFF, submits allowed, nothing typed. At every policy: logout/sign-out never clicked; unnamed non-link controls skipped and counted (D-004: a rule decides only where certain); the human-authored login case run via run_case is the only pre-crawl form submit; beforeunload is accepted, every other dialog dismissed, more than dialog_repeat_limit dialogs on one node aborts the node; host re-check after every action (off-domain -> go_back, else goto base_url); failed requests are issues only when first-party, third_party_ignore hosts dropped, other third parties counted as noise. No allowed_domains wildcard. Test accounts carry no 2FA (Umesh 2026-09-07); real user accounts (which do) are never used.
**Why:** write_policy has been declared and defaulted since T-000 and read by zero code. The target is production (no staging named), so the default is the tightest policy; ALLOW_WRITES is Umesh's switch. The TEST_ACCOUNT row is the maker's interpretation, shown once in the B4 manifest for confirm-or-edit.
**Result:** SafetyPolicy defaults in schema/crawl.py; tests/test_explore_safety.py; explore.md X5-X9.
**Links:** T-142; D-014; D-015; D-004; plan.md

## D-017 | 2026-09-08 | type: decision | status: ACTIVE
**What:** AutoTester gains a second TARGET KIND. Today a target is a web product reached through a browser and judged on its screens; Track C adds a target reached through an API endpoint or a codebase -- an LLM application -- judged on its outputs. New models schema/ai_target.py (AiTarget, Signal) and schema/ai_check.py (AiCheckKind, AiCheck); new stages discover.py, read_context.py, ai_catalog.py, ai_capture.py, adversarial.py; new checker-authored contracts qa/contracts/ai-target.md and qa/contracts/adversarial.md. Discovery signals are DETERMINISTIC (grep and file inspection): SDK imports, prompt-template files, agent-framework usage, tool/MCP registrations, retrieval use, presence of ground truth, presence of a live endpoint. A model may NAME the system kind from those signals; it may never CHOOSE which checks run -- that mapping is a table in code, the same discipline D-015 used to keep action choice out of the model's hands for the crawl. C7 is preserved: ai_capture.py and adversarial.py exercise the target and never grade it; judgement goes through stages/grade.py with a Rubric. A context folder (including an Obsidian vault) is read as ordinary structured markdown -- frontmatter and tags only; backlinks, Dataview and live-vault features are out of scope. Rejected for now: vendoring Garak/PyRIT/DeepTeam as hard dependencies -- their value here is their probe corpus, so probe sets live in prompts/probes/*.md and a ProbeSource adapter behind the provider seam is designed for and built ONLY if the native sets prove too thin.
**Why:** Umesh 2026-09-08, choosing "adopt the cheap parts + a Track C for AI-system testing" over adopting the reference material's cheap patterns alone, after being shown that the reference describes testing AI systems' outputs rather than web screens. Vidysea's own products carry LLM features a browser cannot grade, so the north star -- a human tester and AutoTester get the same material, AutoTester wins on bugs found, false positives and time -- applies unchanged to them. Building this as a second target kind rather than a separate tool reuses the provider seam, the grade stage, the redaction boundary, the Catalog and the report exporter.
**Result:** units T-150..T-155 (governance, discovery+classification, check registry+matching, behavioural checks, bounded adversarial pass, report). Track A keeps tick priority; Track C advances on ticks where Track A waits on a checker. If Track A slips again, Track C is the track to pause -- it is the only one with no human ground-truth sheet waiting on it.
**Changes-authorized:** docs/ARCHITECTURE.md (Pipeline, Concept-to-file table, Storage); new qa/contracts/ai-target.md and qa/contracts/adversarial.md (checker-owned); .gitignore for capture artifacts under projects/*/ai/.
**Approved-by:** Umesh -- plan revision approved 2026-09-08 (plan.md section 5B), scope chosen via an explicit two-option question.
**Links:** T-150..T-155; D-015; D-016; D-018; plan.md section 5B

## D-018 | 2026-09-08 | type: decision | status: ACTIVE
**What:** (1) Consent becomes an ARTIFACT, not a habit. New schema/approval.py::RunApproval (target, scope, bounds, granted_by, granted_at, expires_at, run_kind) and core/consent.py::require_approval, content-addressed so an approval cannot be widened after the fact. Gate 1 covers read scope (a discovery scan outside the project); gate 2 covers every outward-facing run -- the live crawl and, above all, the adversarial pass, whose approval must name the exact endpoint and a probe count at or above the planned run. An adversarial run against a production endpoint requires the approval to say production explicitly. Without a matching unexpired approval the runner sends nothing and exits non-zero. (2) T-145's done_check, currently {"cmd": "true"} -- a check that cannot fail, on a HIGH-criticality high-user-value live-crawl task (filed by the 2026-09-08 sweep as AT-100) -- is replaced by a command asserting both the crawl's exit code and a matching approval row. (3) qa/adapter.json's verify allowlist is widened to the commands checkers already legitimately run: the proof scripts (scripts/*_proof.py), docker inspect, git show, md5sum, and checker-authored probe scripts under .work/.
**Why:** the reference material's two consent gates are a better articulation of what write_policy and the HUMAN_GATE files reach for informally, and the explorer is about to be pointed at a live production ERP (T-145) with a done_check that cannot fail. Firing adversarial prompts at an endpoint is outward-facing and can cost money, trip a vendor's abuse detection, or pollute a production log; it is the one capability in the plan that must be impossible to start by accident. The allowlist is widened rather than enforced-as-written because it is currently narrower than honest practice -- every recent verdict ran commands outside it, so as written it makes each real check a silent CONTRACT_MISMATCH.
**Result:** units T-124 (consent gates + the T-145 done_check replacement) and T-126 (adapter allowlist, governance debt); the refusal criteria in qa/contracts/adversarial.md; a pre-crawl approval check in stages/explore.py.
**Changes-authorized:** qa/adapter.json verify.commands; .goal/goal.json T-145 done_check; qa/contracts/explore.md amendment for the pre-crawl approval (checker-owned); new qa/contracts/adversarial.md (checker-owned).
**Approved-by:** Umesh -- plan revision approved 2026-09-08 (plan.md section 5A).
**Links:** T-124, T-126, T-145, T-154; AT-100; D-016; D-017; plan.md section 5A

## D-019 | 2026-09-08 | type: fix | status: ACTIVE
**What:** Restore the two locally-authorized changes to `.claude/hooks/lab-session-start.ps1` that commit 051303e (D-013) reverted as an unintended side effect, and add the regression test whose absence let this happen twice. (1) The ARCHITECTURE.md excerpt filter goes back to D-008's rule -- keep every `## ` section EXCEPT `## Directory map and schema summary` (generated into docs/MAP.md separately) -- instead of the generic Lab Protocol template's numbered-heading allowlist `^## (1|2|3|6)[\.\s]`, which matches nothing in this repo because this project's ARCHITECTURE.md has always used named headings. (2) The excerpt cap goes back to D-010's 150 lines, with the label text saying 150. (3) NEW `tests/test_session_start_hook.py` reads the real .ps1 and asserts the authorized constants are present and that the filter, applied to the real docs/ARCHITECTURE.md, keeps every named section. (4) This file is now DELIBERATELY NOT byte-identical to the AIOS template: any future template sync must re-apply these two local deltas, and this entry is the record that says so.
**Why:** AT-097 (high, found by the 2026-09-08 checker sweep). D-008 and D-010 are both ACTIVE and both carry Approved-by: Umesh; D-010's Result names the exact line and value. The disk disagreed with both. Bisected: 5f83bdb cap=100 numbered-filter -> f9e3456 cap=150 named-filter (the authorized fix) -> 051303e cap=100 numbered-filter (the revert). 051303e is D-013, whose own Changes-authorized says "byte-identical to the AIOS template" and whose What says "Behaviour otherwise unchanged" -- so the revert was neither intended nor recorded, and D-013 carries no Supersedes line. Measured on disk 2026-09-08 by executing the on-disk filter against the real docs/ARCHITECTURE.md (150 lines, 11 named headings): it keeps exactly ONE line, the H1 title. Every session started since 2026-09-05 has been injected an empty ground-truth block -- AT-015 fully regressed, inside the very hook whose job is to make the protocol survive forgetting. Deliberately NOT expressed as **Supersedes:** D-013: D-013's actual purpose (ASCII-escaping hook JSON output, which fixed a real harness rejection) is correct, still in force and must stay ACTIVE; marking it SUPERSEDED would tell every future reader to discard a fix that is load-bearing. What is replaced is only its "byte-identical to the template" treatment of this one file, which is stated above rather than encoded as a supersession that would misreport the rest.
**Result:** the session-start hook injects real ground truth again; a pytest fails if either constant is reverted, so a third silent regression is not possible. AT-097 and AT-029 close together -- AT-029 (the cap firing before Design rules/Commands/Status) is the same defect's other half.
**Changes-authorized:** .claude/hooks/lab-session-start.ps1 (ARCHITECTURE excerpt filter + cap only; the ASCII-escaping from D-013 is untouched); new tests/test_session_start_hook.py.
**Approved-by:** Umesh -- STANDING authorization D-008 and D-010, both ACTIVE and both Approved-by Umesh, which authorize precisely these two values. This entry restores their effect and creates NO new authority; it does not approve anything Umesh has not already approved. Flagged to him in the tick report as a change made to an enforcement path without a fresh approval, so he can reverse it in one commit if he disagrees.
**Links:** AT-097; AT-029; AT-015; D-008; D-010; D-011; D-013; commits 5f83bdb, f9e3456, 051303e

## D-020 | 2026-09-08 | type: fix | status: ACTIVE
**What:** Correct `.claude/hooks/lab-session-start.ps1` line 118 from `Join-Path $root "ARCHITECTURE.md"` to `Join-Path $root "docs\ARCHITECTURE.md"`, so the session-start hook reads the architecture file this project actually has. Remove the strict xfail in tests/test_session_start_hook.py that pinned the defect, leaving the path assertion live. This closes AT-097 and AT-029 (the excerpt filter and the 150-line cap restored under D-019 were correct but were repairing code that never executed) and AT-106.
**Why:** AT-106, found by the checker on the D-019 unit. The hook has looked for ARCHITECTURE.md at the REPO ROOT since the genesis commit; this project has always kept it at docs/ARCHITECTURE.md and `git log --all --diff-filter=A -- ARCHITECTURE.md` is empty, so a root copy has never existed. Executing the real hook emits "[WARN] ARCHITECTURE.md missing at repo root" and injects ZERO architecture headings. The sibling line 50 already reads "docs\DECISIONS.md", so the missing docs\ prefix on line 118 is a plain oversight inconsistent with its own file. This is an enforcement-path VALUE that no prior entry authorizes -- D-008 and D-010/D-011 name the filter and the cap and say nothing about the path -- and this repo has FAILED two checks (AT-030, AT-031) for treating a batch approval as covering a specific value by extension, so it was gated rather than extended onto D-019.
**Result:** the session-start hook injects real ground truth for the first time in this repo's history: 0 headings -> all 10 named sections. AT-097, AT-029 and AT-106 close together. The strict xfail is removed in the same commit; it existed precisely so this fix could not land while a stale xfail hid it.
**Changes-authorized:** .claude/hooks/lab-session-start.ps1 (the $archPath value only; the D-013 ASCII-escaping and the D-008/D-010 filter and cap are untouched); tests/test_session_start_hook.py.
**Approved-by:** Umesh -- asked directly 2026-09-08 via an AskUserQuestion presenting three options (fix the path / move ARCHITECTURE.md to the root / close as won't-fix) with the diff and the blast radius of each; he chose the path fix. Gate record: qa/gates/at106-hook-architecture-path.md, Answered line written before this entry.
**Links:** AT-106; AT-097; AT-029; AT-107; D-008; D-010; D-011; D-019; qa/gates/at106-hook-architecture-path.md

## D-021 | 2026-09-09 | type: fix | status: ACTIVE
**What:** Replace this repo's permission posture so routine maker-checker work stops raising approval prompts. (1) Add a `permissions` block to `.claude/settings.json`: `allow` = the three tool-level grants `Bash`, `Edit`, `Read`; `deny` = 13 destructive rules (sudo, ssh, chmod 777, rm -rf on root/home, git push --force, gh repo/release delete). The hooks block is untouched. (2) Machine-wide, OUTSIDE this repo and recorded here only because it is what actually unblocked this project: `D:/ai_os/.claude/hooks/edit-in-place-guard.ps1` no longer treats a stem ending in a digit as drift, and its allow-list gains `.work`, `scratchpad`, `temp\claude`, `.playwright-mcp`, `.goal`, `qa`, `brainstorms`. It still asks on `_v2`/`_new`/`_copy`-style duplicates in real source trees, which is the anti-drift rule the user CLAUDE.md asks for.
**Why:** Umesh 2026-09-09, twice, escalating: approval prompts were costing hours and stalling the loop. Four causes, all measured, none of them "auto mode is off" -- `permissions.defaultMode` was already `auto` throughout. (a) The machine-wide drift guard returned permissionDecision "ask" for ANY source file whose stem ends in a digit -- and a hook "ask" cannot be overridden by any permission mode, so auto mode was powerless against it. FORTY-EIGHT files in this repo's `.work/` match that shape (run2.py, patch18.py, probe5.py, s5.py, p6.py), and the guard's allow-list covered `tests/` and `fixtures/` but not `.work/`, which this project's CLAUDE.md REQUIRES scratch to live in. Every checker subagent writes probe scripts, so every checker prompted. (b) Compound `cd X && cmd` chains require EVERY segment to match a rule, so an approved `Bash(python run2.py forms)` still prompted for the `cd` -- clicking yes never helped. (c) `Write(path)` rules are accepted and NEVER consulted; `Edit` is the canonical file-modification namespace, so several previously-approved rules bought nothing. (d) The 108-entry user allow-list was hyper-specific literals accumulated by clicking, which generalise to nothing.
**Result:** scratch writes and `cd X && cmd` chains no longer prompt; a `_v2` duplicate in `src/` still does. Verified by a before/after harness driving the real hook with valid JSON: the old hook asked on all three scratch cases, the patched one is silent on all three, and both still ask on `src/analyze_video_v2.py` and `src/ingest_new.py`. Known residual, stated rather than hidden: `~/.claude/settings.json` is rewritten from memory by the running session, so user-level grants only become live after a restart or `/permissions` -- a first attempt was reverted byte-identically within 20 seconds. Rollback: `.work/permfix-backup/*.bak`.
**Changes-authorized:** .claude/settings.json (permissions block only; the hooks block is untouched).
**Approved-by:** Umesh -- asked directly 2026-09-09 via an AskUserQuestion presenting three breadth options (broad-for-workflow / maximum / surgical) plus a second question on the drift guard's fate; he chose "Maximum -- stop asking almost entirely" and "Scope it to real source trees", and then approved the written plan twice, including after a mid-course correction.
**Links:** D-000; D-007; plan at C:/Users/Lenovo/.claude/plans/great-when-you-really-iridescent-ocean.md; rollback .work/permfix-backup/

## D-022 | 2026-09-09 | type: fix | status: ACTIVE
**What:** Reconnect EXPAND and COVERAGE to a human, closing AT-239, AT-240, AT-241 and AT-250 (T-135, "Track A6: coverage/merge/expand loops reconnected"). Five wires, no stage rewritten: (1) `cli.py` gains `autotester expand <project>` -- the first production caller of `stages/expand.py::expand`, which persists the generated cases through `ProjectStore.add_case` (the caller's job per expand.md's own no-fire list, not the stage's). (2) A new `ui/routes_learn.py` carries the operator-facing half of the same loop: `GET /projects/{slug}/flowspec` renders the FlowSpec for review, `POST .../flowspec/approve` and `POST .../flowspec/request-edit` are the review gate's two directions with a signer, `POST /projects/{slug}/cases/generate` is the UI's Generate-cases button, and `GET /projects/{slug}/requests` is the video-request queue -- the first surface on which the product's "ask the human for a video" promise is visible to the human it asks. (3) `stages/coverage.py` gains `queue_requests(store, gaps)`, one place that turns gaps into deduped persisted `VideoRequest`s; `unreached_screens` is deliberately NOT wired into it (coverage.md V5 forbids it). (4) `ui/routes_runs.py::trigger_run` calls it on the run's own `RawResult`s via `diff_coverage`, and (5) `ui/routes_crawls.py::start_crawl` calls it on the finished crawl's nodes via `diff_crawl`. Refusals on the new UI routes render as themed pages, not raw JSON (the AT-244 class, not fixed for the pre-existing routes here). REJECTED in this unit: making `expand()` persist its own cases (breaks expand.md's no-fire and its purity), and firing coverage from a GET page render (a read would then write).
**Why:** the business-truth campaign (`qa/verdicts/business-truth-campaign-2026-09-09.md`, VERDICT: FAIL, 4/10 business requirements met) measured the consequence of a gap this repo already knew about: `expand`, `diff_coverage`, `request_for` and `ProjectStore.add_request` had zero production callers, so across four projects the product holds 52 cases of which 49 are `happy` and no case has ever been generated (AT-250), and a `VideoRequest` has never been produced. Every contract passed and every unit PASSed while the two stages the north star rests on were unreachable. T-135 was already pending, which is the point: the wire, not the stage, was the missing work.
**Result:** T-135's unit `t135-reconnect-expand-coverage`; T-100 reopened to `pending` because the campaign disproved its own acceptance note ("full onboarding -> report without touching the CLI") live in a browser (AT-241).
**Changes-authorized:** docs/ARCHITECTURE.md (Pipeline section -- name the entry points each stage is reached from; Concept-to-file table -- the expand/coverage rows and a row for ui/routes_learn.py; Status section); new src/autotester/ui/routes_learn.py; stages/coverage.py (additive `queue_requests` only -- V1-V5 functions byte-unchanged); .goal/goal.json T-100 status.
**Links:** T-135; T-100; AT-239; AT-240; AT-241; AT-250; D-004; qa/verdicts/business-truth-campaign-2026-09-09.md; qa/QUEUE.md

## D-023 | 2026-09-10 | type: decision | status: ACTIVE
**What:** Expand AutoTester's product contract from its current video-first and bounded-crawl
foundations into one reusable, project-agnostic testing loop. A project intake accepts a URL,
domain-scoped credential references, optional user evals/conditions/business rules, and optional
video/audio/document/text/email or Google Drive sources. With teaching material, AutoTester learns
and reconciles the stated flows; without it, AutoTester authenticates and explores breadth-first.
Both paths converge on a durable Portal Persona, traceable best/worst/edge evals, regression runs,
and unified HTML/Excel/screenshot reporting. "Complete exploration" means the actionable BFS
frontier was exhausted or a named safety/budget bound stopped it; skipped, denied and unreached
actions remain visible and can never be presented as covered. Register T-160 through T-169 for
this missing product layer. Existing Tracks A, B and C remain foundations rather than being
reimplemented.
**Why:** Umesh corrected the active goal on 2026-09-09: the directory must accept any project's
URL and test-account credentials, optionally learn from user-provided evals, use cases, recordings
or Drive material, otherwise explore the whole portal using the portal-explorer discipline, avoid
single happy-path DFS behaviour, preserve the learned portal persona and workflows, and act as
post-development damage control with clear issues, diagrams, text and screenshots. The current
goal tracker contains working parts of this design but has no explicit owner for Drive and generic
source intake, learn-or-explore orchestration, durable portal persona generation, API-derived
evals, release-triggered regression or final two-mode acceptance. Its 69 percent therefore
overstates progress against the corrected objective until these tasks are registered.
**Result:** `plan.md` gains the revised product layer and acceptance sequence; `.goal/goal.json`
gains T-160..T-169 and a north star that names both taught-input and credentials-only modes.
Every new task carries a task-specific command or rubric that can fail. Implementation remains
maker -> manifest -> independent checker -> PASS/fix cycle -> commit -> push -> post-push browser
validation. Brain guidance applied: bounded iterative loops, durable checkpoints and evaluation at
component/workflow/application levels. Portal-explorer guidance applied: browser-first operation
plus a durable Quick Re-Run/Profile/flow/findings/change-history artifact.
**Changes-authorized:** `plan.md` (additive revised-product-layer section), `.goal/goal.json`
(north_star and T-160..T-169 registration), `.goal/dashboard.html` and `docs/SNAPSHOT.md`
(generated views only).
**Approved-by:** Umesh -- direct corrected-goal instruction in this active task, 2026-09-09.
**Links:** goal.md; D-014; D-015; D-016; D-017; T-100; T-125; T-135; T-145; T-150..T-155;
portal-explorer skill; active /goal objective 2026-09-09

## D-024 | 2026-09-10 | type: decision | status: ACTIVE
**What:** Implement T-161 as one no-CLI onboarding form over the existing Project, SecretRef,
Source and ProjectStore concepts. The form accepts the base URL and allowed-domain boundary,
zero or more domain-scoped credential key declarations, optional user evals, conditions/business
rules and use cases, plus optional source declarations. Raw credential values remain outside the
artifact path and are entered only through the existing masked credentials editor. All submitted
fields are validated before project or source persistence so a malformed intake cannot leave a
partial project. Source declarations become canonical Source rows rather than a second intake-only
registry; T-162 remains responsible for fetching and adapting Drive, audio, documents and email.
**Why:** D-023 and the active goal require any project to begin from one operator form, while the
current onboarding stores only name, URL and domains and then makes the operator hand-assemble
credentials, rules and sources across separate pages. Reusing the existing typed artifacts keeps
the UI a thin file-backed editor and preserves the secret boundary and one-concept-one-place rule.
**Result:** T-161 owns the typed project intake fields, onboarding rendering/parsing and canonical
source registration, with an end-to-end TestClient acceptance suite and independent headed-browser
checker proof. Later tasks consume these inputs; this unit does not claim orchestration or adapters.
**Changes-authorized:** src/autotester/schema/project.py; src/autotester/ui/app.py;
src/autotester/ui/routes_project_edit.py; src/autotester/ui/routes_sources.py;
tests/test_ui_project_intake.py; docs/ARCHITECTURE.md (Project data-model and UI intake wording);
qa/manifests/t161-unified-project-intake.md.
**Approved-by:** Umesh -- active /goal explicitly requires the unified form and instructed the
maker-checker loop to continue through commit, push and live-browser validation.
**Links:** D-023; T-161; T-162; qa/contracts/core-invariants.md; qa/contracts/ui.md

## D-025 | 2026-09-10 | type: decision | status: ACTIVE
**What:** T-161's unified onboarding form accepts both domain-scoped credential declarations and
their optional values in the same submission, in addition to URL, user evals, conditions/business
rules, use cases and source declarations. Values are atomically written only to the repo-root
gitignored `.env`; Project stores SecretRef keys/scopes and Sources store non-secret statements.
The whole submission is parsed and validated before any file write. Repeated source statements
are content-addressed and idempotent. Source adapters/fetching remain T-162.
**Why:** The active product goal says the user fills one form with URL and account credentials.
D-024 kept values on a later Credentials page, preserving safety but failing that actual one-form
experience. Atomic batch persistence is safer than sequential field writes because an invalid
second credential cannot leave a half-configured account, while the same SecretStore boundary
still prevents values entering project artifacts, prompts, logs or rendered responses.
**Result:** One browser form can create a credentials-only project or a richly taught project
without CLI or JSON editing; the existing later credentials page remains available for rotation.
**Supersedes:** D-024 -- the earlier split-page credential approach is removed because it missed
the user's one-form requirement; atomic secret-only persistence is both more faithful and safer.
**Changes-authorized:** src/autotester/schema/enums.py; src/autotester/schema/project.py;
src/autotester/ui/project_view.py; src/autotester/ui/app.py;
src/autotester/ui/routes_project_edit.py; src/autotester/ui/routes_sources.py;
src/autotester/ui/env_editor.py; tests/test_ui_project_intake.py; docs/ARCHITECTURE.md
(Project data-model, UI intake and storage wording); qa/manifests/t161-unified-project-intake.md.
**Approved-by:** Umesh -- active /goal explicitly requires the URL-and-credentials form and
instructed autonomous maker-checker execution through commit, push and live-browser validation.
**Links:** D-023; D-024; T-161; T-162; qa/contracts/core-invariants.md;
qa/contracts/browser-and-secrets.md; qa/contracts/ui.md

## D-026 | 2026-09-18 | type: decision | status: ACTIVE
**What:** `doctor`'s checks are split by what they read. `src/autotester/doctor.py` keeps the rules
over SOURCE -- line caps, function length, banned filenames, root clutter, duplicated concepts --
plus `Violation` and `run()`. The rules over the project's own RECORDS -- `check_ledger` and
`check_qa_issue_rows`, with `ISSUE_ID`, `_MARKER_LEAD` and `_is_marker_line` -- move to a new module
`src/autotester/ledger/checks.py`, inside the existing `ledger` package rather than as a new
top-level concept. `run()` imports them function-locally, the idiom `doctor.py` already used for
`ledger.render` and `ledger.store`, so no import cycle is created by `checks.py` importing
`Violation`. Behaviour is unchanged; the split is the whole change.
**Why:** Three consecutive units (AT-496, AT-500, AT-504) grew `doctor.py` from 264 to 287 lines
against C2's 300-line cap, and all three landed in the record-rules half. `doctor` itself would not
have said a word until 301, so the file was one ordinary unit away from failing its own rule with
no warning -- the checker filed AT-506 for exactly this. The seam is real rather than arithmetic:
the two halves read different trees (`src/` and `tests/` versus `docs/FEATURES.jsonl` and `qa/`)
and answer different questions (did the code stay readable, versus did the project's account of
itself stay true). Splitting on a line count alone would have been drift with a cap for an excuse.
**Result:** `doctor.py` 287 -> 204 lines, `ledger/checks.py` 105, `tests/test_doctor.py` 282 -> 133,
new `tests/test_ledger_checks.py` 165 -- every file with real headroom. Behaviour proved identical
by a fingerprint of both checks over the live `qa/` corpus AND over a copy with five ledger rows
deleted (11 violations across 11 artifacts), byte-identical before and after. The mutation coverage
of the three units that built these rules is proved to have survived the move by re-running their
falsifying edits against the new module path; the closed units' own evidence files are deliberately
NOT rewritten, because they document what was verified at the commit they were verified at.
**Changes-authorized:** src/autotester/doctor.py; src/autotester/ledger/checks.py;
tests/test_doctor.py; tests/test_ledger_checks.py; tests/test_ledger.py; docs/MAP.md (generated);
docs/ARCHITECTURE.md (the concept-to-file map row for design enforcement, line 46 -- so it no
longer names doctor.py as the home of ledger validity); qa/manifests/at506-record-rules-leave-the-
source-rules.md.
**Links:** AT-506; AT-496; AT-500; AT-504; AT-488; AT-502; qa/contracts/core-invariants.md (C2, C10)

## D-027 | 2026-09-18 | type: fix | status: ACTIVE
**What:** Remove the hand-maintained `## Status` section (lines 146-150) from
`docs/ARCHITECTURE.md`. It duplicates the job `docs/SNAPSHOT.md` already does -- generated,
always fresh, explicitly routed for exactly this ("the whole project in one screen -- what is
live and why ... what is next") -- and it had drifted false: it claimed "the P0-P5 goal backlog
is closed" while `.goal/goal.json` currently carries 10+ `pending` tasks (T-122, T-123, T-136,
T-145, T-125, T-126, T-150-T-153) and `docs/SNAPSHOT.md`'s generated "Next (open goal tasks)"
section lists five of them. No information is lost: what the section tried to say is already
covered, correctly and automatically, by `docs/SNAPSHOT.md`, which `CLAUDE.md`'s router already
points to for this exact purpose. This is the only prose in the file found to be genuine,
safely-removable redundancy (see Why for what was measured and rejected).
**Why:** AT-507 -- `docs/ARCHITECTURE.md` sits at exactly its 150-line C2 budget (doctor.py
`check_architecture_budget`, `ARCHITECTURE_MAX_LINES` in `ledger/render.py`) with zero headroom,
so the next prose change has nowhere to go. Measured before choosing a fix, per AT-506's own
precedent (D-008/D-010 raised this same budget 100->150 once already, and D-026 shows the file
has been edited at the cap via pure row-swaps ever since): (1) the file has NO generated content
of its own to deduplicate -- the "Directory map and schema summary" was already split out to
`docs/MAP.md` at genesis (commit 2785312) specifically to stay under this budget, so all 150
lines are already hand-written prose, not a generated/prose mix `doctor` could discount; (2) the
34-row "Concept -> file" table is concept-oriented and does not literally duplicate `docs/MAP.md`
(module-oriented, 117 rows) -- verified every one of its 41 referenced file paths resolves on
disk, none stale; (3) the `## Commands` section overlaps 4 of 7 lines with `CLAUDE.md`'s own
Commands section but is not a literal duplicate (different flags: `pytest` vs `pytest -q`, `ruff
check src tests` vs `...tests scripts`) and carries 3 commands (`map`, `snapshot`, `ledger add`)
`CLAUDE.md` does not -- removing it would delete information, and fixing the overlap needs an
edit to `CLAUDE.md`, which is out of this unit's file set (a second build subagent owns it
concurrently); (4) hard-wrapped paragraphs (e.g. the FlowSpec/Execution-model/Security prose)
could be collapsed onto single physical lines to cut the raw newline count, but that is a fake
saving -- it does not reduce the character/token cost an agent actually pays reading the file,
which is the reason C2 exists, so I rejected it as gaming the line-count proxy rather than
fixing what it stands in for. Net measurement: the `## Status` section is the only place where
removing lines removes zero real information (it is redundant with, and already contradicted by,
a generated doc) -- 5 lines recovered at the same 150-line budget. This is smaller than a
budget-raise would buy, but it directly answers the stated problem (zero headroom) without
touching `doctor.py`'s cap, and per the task's own framing a raise is legitimate only for what
trimming fails to recover -- trimming was not skipped here, it was attempted, measured, and
found to have exactly one safe target. Not raising the budget in this unit; if the table keeps
growing by one row per unit, that is arithmetic, not drift, and can be re-measured next time it
recurs (as D-026 recorded for `doctor.py`'s own cap).
**Result:** `docs/ARCHITECTURE.md` 150 -> 145 lines. `docs/MAP.md` and `docs/SNAPSHOT.md`
regenerated (`uv run autotester map`, `uv run autotester snapshot`) and unchanged byte-for-byte
except SNAPSHOT's own `Last decisions` tail (D-027 added). `uv run autotester doctor` ends clean.
No code or test changes -- the budget constant is untouched.
**Changes-authorized:** docs/ARCHITECTURE.md (the `## Status` section only, plus the trailing
blank-line cleanup it leaves); docs/MAP.md (regenerated only); docs/SNAPSHOT.md (regenerated
only); qa/manifests/at507-architecture-doc-regains-its-headroom.md.
**Links:** AT-507; AT-506; D-008; D-010; D-026; qa/contracts/core-invariants.md (C2)

## D-028 | 2026-09-18 | type: fix | status: ACTIVE
**What:** Correct D-027's `**Result:**` line count. D-027 said `docs/ARCHITECTURE.md` went
"150 -> 145 lines"; the actual, applied edit (removing the blank line before `## Status` along
with the section itself, six physical lines total, not five) produced 144 lines. D-027's code
change and its choice of what to remove are correct and are NOT re-litigated; this entry supplies
the accurate line count only, per the Lab Protocol's append-only rule (D-027 itself is never
edited) -- the same pattern D-011 used to correct D-010's authorization text.
**Why:** Re-counted `docs/ARCHITECTURE.md` immediately after applying D-027's edit as part of
AT-507's own verification step, before running `doctor`: `wc -l docs/ARCHITECTURE.md` reports 144,
not the 145 the entry's Result line states. The discrepancy is a one-line arithmetic slip made
while drafting the entry (miscounting the blank separator line as staying) rather than a
different edit being applied -- the file on disk matches D-027's `**What:**` and
`**Changes-authorized:**` exactly.
**Result:** `docs/ARCHITECTURE.md` is confirmed at 144 lines (150 - 6), 6 lines of headroom under
its 150-line C2 budget, not 5. No file changes as a result of this entry beyond `docs/DECISIONS.md`
itself.
**Changes-authorized:** none (this entry corrects the D-027 record only; no file besides
`docs/DECISIONS.md` changes as a result of D-028).
**Links:** D-027; AT-507; D-011 (the precedent for this correction pattern)

## D-029 | 2026-09-21 | type: decision | status: ACTIVE
**What:** Amend D-016's typing column and `qa/contracts/explore.md` X10/X5 for one narrow,
approved surface: the AutoTester explorer MAY fill post-login forms with SYNTHETIC values
(fixed, non-PII generator output) under the `TEST_ACCOUNT`/`ALLOW_WRITES` write policy, on the
Pathlynks dev environment only, with the standing prohibition on destructive actions (delete,
permanent or irreversible changes) unchanged. At every other policy level (`READ_ONLY`,
production targets, any other project until its own gate answers), X10's "nothing is typed"
remains exactly as it was. Authorization source: Umesh in chat 2026-09-21, verbatim: *"what is
actually login form and details like apni best intelligence se system ko fill krr lena chahiye
like auto tester kya krta hai, they cases and cases various different combinations ki like usse
hota kya hai and next time kis aur ways se kr ke dekhta hai"* — recorded in
`qa/gates/post-login-forms.md` (option b), which this entry cites as its authorization source.
**Why:** The gates `post-login-forms.md` and `live-crawl-target.md` (opened 2026-09-17 and
2026-09-16 by checker sweeps) were both answered by Umesh on 2026-09-21: Pathlynks is the first
live end-to-end crawl target, and its coverage holes that sit behind submitted forms (search
results, created records, wizard steps) are unreachable under the absolute typing ban, leaving
V7 coverage permanently partial for no safety gain on a dev-environment test account. The ban's
original purpose (D-016) was to stop the crawler mutating a real product it does not
understand; synthetic generated values on a test account in a dev environment keep that
purpose intact while letting the explorer observe what a form actually does — which is the
north star's own best/worst/edge combination behaviour Umesh explicitly asked for. The
destructive-action prohibition and the per-run RunApproval consent gate (D-018) are NOT
relaxed by this entry; every live form-typed run still passes consent gate 2.
**Result:** `qa/contracts/explore.md` X10 and the X5 matrix are amended by the checker (critical
amendment, its write surface) to encode the X10-b rule: typing allowed ONLY under
TEST_ACCOUNT/ALLOW_WRITES + synthetic values + dev-environment target + non-destructive;
violations of any one of those four conditions remain refusals. The first live use is the
Pathlynks stage-2 form-exploration crawl after the READ_ONLY map crawl. Until that amendment
lands, no typed run is authorized.
**Changes-authorized:** qa/contracts/explore.md (X10 + X5 amendment only, by the checker);
qa/gates/post-login-forms.md (already updated with the Answered line); no code files.
**Links:** qa/gates/post-login-forms.md; qa/gates/live-crawl-target.md; D-016; D-018;
AT-016 (X10's origin); qa/contracts/explore.md

## D-030 | 2026-09-21 | type: fix | status: ACTIVE
**What:** Landplane recovery of 88 uncommitted working-tree changes left by prior sessions'
closed ticks and checker runs. Committed: (1) 75 `qa/evidence/` files — checker evidence from
nine PASSed units (at500, at521, browser-at435/446/452/455/457/458, 458-c2/c3, 459, 459-c2/c3),
the same committed asset class as the 335 evidence files already tracked; (2) the two generated
`.goal/` tick files (dashboard.html, goal.json); (3) `projects/pathlynks/approvals.jsonl` — the
D-018 gate-2 per-run consent records; (4) five small demo/validation project dirs referenced by
tests and contracts (`projects/{xssprobe,saucedemo,checkerdemo,t161-final-smoke,t161-pushed-live}`),
matching the existing per-project metadata precedent (erp/pathlynks/regression-demo/vidysea-erp).
Ignored via .gitignore (Changes-authorized below): `.codex/` (another agent tool's local hook
config — T-161's own checked-PASS manifest classifies it a runtime artifact); `projects/*/sources/`
(transcripts, observations, analysis of ERP tester videos — the standing rule bars transcripts and
product internals from the public repo; same class as recording.*/chunks/frames);
`projects/*/sources.jsonl` (the erp registry labels carry the recorded trainer's name);
`projects/*/screenmap.json` and `projects/*/issues.jsonl` (portal-explorer outputs on a real
product — internal screen structure and found issues; the D-015 rationale verbatim).
**Why:** The session-start hook printed `[RECOVERY] 88 uncommitted change(s)` and the Lab
Protocol requires the tree landed before new build work. Classification was by class evidence,
not case-by-case taste: evidence dirs are a committed class (335 tracked files; these 13 dirs are
checker runs of PASSed units); .goal tick files are tracked and were modified by the last tick;
approval records are the audit trail for live runs; demo project dirs are referenced by
`tests/test_migrate_url_patterns.py` and `qa/contracts/explore.md`. The ignored set was measured
first: erp transcripts quote the trainer's spoken words on ERP internals ("CIPSA certificate we
should mention CITS certificate"); erp sources.jsonl labels name the person recorded;
screenmap/issues map the real ERP. Committing any of these would put student-surface product data
in a PUBLIC repo (github.com/umeshsugara-ai/autoTesting).
**Result:** All five new ignore patterns verified with `git check-ignore -v`; the staged tree
contains only the committed classes above. Verification gate on the staged tree:
`uv run pytest` -> PASS (per-module sweep: 100+ files, all green; full-suite run times out under the 10-min shell cap -- per-module evidence in .work/parallel-watch.md); `uv run ruff check src tests scripts` -> PASS (all checks passed);
`uv run autotester doctor` -> PASS (doctor: clean). DECISIONS staged diff verified additions-only.
No code changed; no contract or ARCHITECTURE prose edited; no enforcement path touched.
**Changes-authorized:** .gitignore (the five pattern additions above only); the recovery commit
itself (qa/evidence/*, .goal/*, projects/* as classified, projects/pathlynks/approvals.jsonl).
No Approved-by required (no enforcement path in scope).
**Links:** D-015 (crawl-artifact rationale for real products); D-018 (per-run approval records);
qa/manifests/t161-unified-project-intake.md (runtime-artifact classification of .codex/);
AT-500; AT-521

## D-031 | 2026-09-22 | type: decision | status: ACTIVE
**What:** Correct `docs/ARCHITECTURE.md`'s "Execution model" section to describe the system
that actually exists. Today it claims: "**Per case: script-first** (run the durable Playwright
script if one exists) â†’ agent fallback ... on success the agent emits a script. So a stable
suite costs ~zero tokens to re-run; the agent only pays for new or broken cases." None of that
exists: `Script` (`src/autotester/schema/case.py:87`) is never instantiated in `src/`;
`case.script_ref` (`:31`) is declared and copied through, never read for behaviour;
`stages/agent_loop.py::run_with_fallback` has zero production callers â€”
`stages/run_case_pipeline.py:95`, `stages/explore.py:109` and the UI all call
`stages/execute.py::run_case` directly. Every re-run today is a fresh vision-graded run.
Verified independently by the 2026-09-22 sweep (AT-540's fold; verdict
qa/verdicts/sweep-2026-09-22.md) and by the TestSprite research audit
(docs/research/testsprite-2026-09.md, Â§7 row 1 â€” filed as AT-253's re-verification).
**Why:** Under the Lab Protocol, generated docs must not claim behaviour the code does not
have; a false execution model misleads every reader (human or agent) who plans work on top of
it, and it blocks the upcoming script-first wiring unit (D-entry for that unit will cite this
correction as its prose baseline). The replacement prose describes today's reality: per case,
`run_case` performs the steps in a real browser and produces a RawResult; judgement belongs
entirely to the independent grader (`stages/grade.py`); there is no durable-script replay and
no token amortization yet â€” that is the design goal of the queued script-first unit, not a
shipped fact. The `Script` schema and the unwired `run_with_fallback` are described as
scaffolding for that queued unit.
**Result:** The "Execution model" section is rewritten to: (1) per-case execution = `run_case`
direct, producing RawResult; (2) grading = independent stateless judge, multimodal;
(3) an honest "Not yet built" sentence naming script-first replay + agent fallback as the
queued wiring unit's goal (AT-253 answered: wire, not retire â€” Umesh 2026-09-22). No other
section changes. The concept-to-file table row for agent fallback is reworded to
"unwired (queued)" so MAP and ARCHITECTURE agree.
**Changes-authorized:** docs/ARCHITECTURE.md (the "Execution model" section only + the one
concept-to-file table row's wording).
**Links:** AT-253; AT-540; qa/verdicts/sweep-2026-09-22.md; docs/research/testsprite-2026-09.md;
schema/case.py (Script, script_ref); stages/agent_loop.py; stages/run_case_pipeline.py:95

## D-032 | 2026-09-22 | type: decision | status: ACTIVE
**What:** Make the executor's deterministic assertion layer real (AT-540, adoption B of
docs/research/testsprite-2026-09.md). Today `ExpectedState.absent_text/dom_asserts/visual_signal/
network` (schema/flowspec.py:65-68) have zero read sites in src/, `Action.ASSERT` is
`lambda session, step: None` (stages/execute.py:43), and `BrowserSession._poll_for_expected`
(browser/session.py:238-251) is a settle hint that returns normally on timeout, recording no
failure. 100% of pass/fail judgement is an LLM reading a screenshot (stages/grade.py:123).
**Why:** Umesh approved assertions-first (2026-09-22): the grader's opinion on a screenshot is
currently the only oracle in the system, and a deterministic assertion is the cheapest defence
against both false PASSes and false FAILs. TestSprite ships an explicit `type: "assertion"`
plan-step class; we have the schema for one and no implementation. This does NOT break C7
("the executor never grades itself", qa/contracts/core-invariants.md): an assertion result is
EVIDENCE â€” a recorded fact about the DOM/URL at a moment in time â€” and `grade.py` still owns
the Verdict. What changes is that the grader will now have deterministic facts to weigh, and a
`RawResult` whose own recorded assertions failed can no longer be graded PASS without the
grader contradicting recorded evidence (grade.py's existing self-consistency/downgrade logic
already distrusts evidence-contradicting verdicts; this gives it real evidence to contradict).
**Result:** (1) New `BrowserSession.assert_expected(expected, timeout_ms)` â€” evaluates the
deterministic fields (`url` contains, `visible_text` present, `absent_text` truly absent,
`dom_asserts` selectors exist) by polling like `_poll_for_expected`, records each result as
`EvidenceKind.DOM` evidence with an explicit `assert <field>: met|unmet (<detail>)` label, and
raises nothing â€” the executor reads the recorded results and decides outcome-only consequences:
an unmet assertion on a step's own `expected` or on an `Action.ASSERT` step makes `run_case`
return a new `Outcome.ASSERTION_FAILED` (a fourth observation, not a judgement: it states a
declared expectation did not hold, which is observation, not grading). (2) `Action.ASSERT`'s
handler evaluates `step.expected` through the same method (a no-expected ASSERT records
`assert: nothing expected` DOM evidence and stays harmless). (3) `network` stays
observer-derived (PageObserver already records NETWORK evidence; no per-step wait is added) and
`visual_signal` stays the judge's (E1's existing no-fire line). (4) The execute.md contract is
amended by the checker (E1's "never compares the captured evidence against Step.expected" line
is superseded by this D-entry; E1's three-outcome list gains ASSERTION_FAILED; the
"executor only observes" line is reworded to "the executor never grades â€” a declared
expectation either held or did not, and the grader still owns the verdict"). (5) ARCHITECTURE.md's
corrected Execution-model section (D-031) gains one sentence: deterministic assertions are
evidence; the grader still owns every verdict.
**Changes-authorized:** src/autotester/schema/enums.py (Outcome.ASSERTION_FAILED);
src/autotester/browser/session.py (assert_expected + _poll_for_expected reuse);
src/autotester/stages/execute.py (Action.ASSERT handler + post-step expected evaluation);
qa/contracts/execute.md (E1 supersession + amendment log, by the checker);
docs/ARCHITECTURE.md (the one sentence in the corrected section).
**Links:** AT-540; AT-253 (D-031, the prose prerequisite, already landed); docs/research/
testsprite-2026-09.md Â§4B; qa/contracts/execute.md E1; qa/contracts/core-invariants.md C7;
Umesh approval 2026-09-22 (assertions-first order, chat, quoted in qa/feedback-inbox.md)

## D-033 | 2026-09-22 | type: decision | status: ACTIVE

**What:** Add narrow, outage-safe allow rules to `.claude/settings.json` so this project's `/maker`
loop survives an auto-mode classifier outage. Rules added: `Bash(uv run pytest*)`,
`Bash(uv run ruff check src tests scripts)`, `Bash(uv run autotester doctor)`,
`Bash(powershell -ExecutionPolicy Bypass -File scripts/append_decision.ps1 *)`, and
`Bash(python D:/ai_os/scripts/delegate_unit.py *)`. The bare `Bash` allow stays for normal use but is
inert in auto mode (dropped as over-broad).

**Why:** In Claude Code auto mode every tool call is classified by a model; when that model is
unavailable the call fails closed. Measured across all transcripts: 837 such refusals, 16 of them
`ScheduleWakeup` — a silently dead loop. Only NARROW allow rules resolve before the classifier and
survive an outage (proven under `CLAUDE_CODE_AUTO_MODE_MODEL=does-not-exist`). This repo currently has
only a bare `Bash` allow, which auto mode drops — so during an outage its whole loop freezes (the
D-088 failure elsewhere: `append_decision.ps1` itself could not run). The rules above are the verify
commands from `qa/adapter.json`, the decisions-appender, and the delegation entrypoint — each a
narrow, argument-scoped form, never a wildcard interpreter. Cross-ref: `D:/ai_os/umesh/decisions/log.md`
2026-09-22 "Auto-mode classifier outages".

**Result:** the five rules are present in `.claude/settings.json`, and a forced-outage harness
(`CLAUDE_CODE_AUTO_MODE_MODEL=does-not-exist`, then a bogus base-URL model) confirms the verify
commands and `append_decision.ps1` run under the outage while a non-allowlisted command still blocks.
Evidence recorded in `D:/ai_os/umesh/decisions/log.md` after the validation run.

**Changes-authorized:** `.claude/settings.json` (add the five narrow allow rules above; no deny-list
or hook change).

**Approved-by:** Umesh (chat, 2026-09-22 — "Haan, D-entry + settings karo").

**Links:** D-088 (the outage failure that prompted this), `D:/ai_os/umesh/decisions/log.md` 2026-09-22
classifier-outage entry, `qa/adapter.json` (source of the verify commands).

## D-034 | 2026-09-22 | type: decision | status: ACTIVE

**What:** ACCEPT (option A) that the owner-only local credential editor may render saved secret
values. `GET /settings/providers` and the per-project env editor serve the real saved credential
VALUE behind a show/hide toggle so the operator can verify and edit it; this is a deliberate,
authorized exception to the credential boundary, not a leak to fix (AT-554). No src/ change; the
behaviour stands, and test_ui_settings.py::test_settings_page_shows_the_stored_value_masked +
test_ui_env_editor.py remain green as its codification.

**Why:** Checker live-browser validation (2026-09-22,
qa/evidence/browser-live-checker-2026-09-22-checker/report.json) confirmed a live GEMINI_API_KEY value
in the raw HTML of the settings page. Read literally against core-invariants.md C5 ("masked from logs,
prompts, and artifacts") that was a boundary violation with no authorizing entry. But the AutoTester UI
runs owner-only on 127.0.0.1 for the operator who already owns .env, so showing the saved value to that
same operator is not an exposure to anyone new. The boundary's core intent is unchanged and still
enforced: a secret value never reaches a MODEL, a LOG, a SHARED/committed artifact, or a captured
PRODUCT screenshot (core.redact.Redactor.scrub and contract B7 stay exactly as they are). Residual,
accepted knowingly: the value reaches the local operator's own HTTP response, DOM, and any screenshot
of the settings/env page -- such a screenshot must never be fed to a model or shared; the checker's own
live-browser snapshots that captured it are gitignored and were deleted.

**Result:** core-invariants.md C5 gains an owner-only-editor exception bullet + amendment-log row;
browser-and-secrets.md gains a clarifying amendment-log row (B7 substance unchanged); AT-554 flips to
`wontfix` (accepted by decision, not a code fix). The full suite stays green (1534 passed, 0 failed at
HEAD a30f535) and ruff + doctor clean.

**Changes-authorized:** qa/contracts/core-invariants.md (C5 only -- the exception bullet + amendment-log
row, by the checker); qa/contracts/browser-and-secrets.md (amendment-log clarifying row only; B7
substance unchanged). No src/ or test change.

**Approved-by:** Umesh (chat, 2026-09-22 -- "A").

**Links:** AT-554; qa/gates/at554-credential-value-in-ui.md; qa/evidence/browser-live-checker-2026-09-22-checker/report.json; qa/evidence/live-quality-validation-2026-09-22b-checker/report.json.

## D-035 | 2026-09-22 | type: decision | status: ACTIVE

**What:** Finalize `qa/contracts/source-adapters.md` from gate-A-approved DRAFT to an active,
checker-owned contract. No wording changed from the draft the maker authored at intake; this entry
is the authorizing D-record the contract's own header requires before its DRAFT status can be
lifted.

**Why:** The contract was authored as a review artifact from `qa/gates/t162-contract-approval.md`,
answered **(A) Interview now** by Umesh in chat 2026-09-21 (source-kind phasing: TEXT+DOC+AUDIO in
phase 1, DRIVE+EMAIL as phase 2; Drive OAuth device flow, not service-account; audio Gemini-first
via the existing Provider seam with Whisper as no-API fallback; email limited to local .eml/.mbox,
no mailbox credentials). T-162 phase-1a (the adapter seam + TEXT + DOC) was then built against this
draft and checker-PASSed (`qa/verdicts/t162-source-adapters-1a.md`, cycle 1): SA1 (one `Source`
model, one `sources.jsonl`, `SourceKind.TEXT`/`SourceKind.DOC` reused from the existing enum, no
second store or parallel enum), SA2 (sha256 content-addressed dedupe, tested and mutation-proven),
SA4 (extraction addressable by `Source.id`), SA5 (honest `extraction_error` degradation for a
corrupt `.docx`, a DOCTYPE-bearing `.docx`, and an undeclared-dependency `.pdf` — never silent empty
text), and SA6 (no `Provider` parameter anywhere in the seam — a model cannot be called, structurally,
not just by convention) are all evidenced by a passing test suite (11/11 unit tests,
1549 passed/0 failed across the full repo suite) and by 4/4 capability-coverage rows independently
reproduced by the checker in a throwaway copy (single-hunk falsifying edit -> named test reddens for
the claimed reason -> revert -> green). A contract that already governed a checker-PASSed unit is no
longer merely a review artifact; leaving its header at DRAFT after that point would misstate its own
status to the next reader.

**Result:** `qa/contracts/source-adapters.md`'s header changes from "DRAFT for Umesh's review" to
active/checker-owned, citing this entry; no criteria (SA1-SA6), phase-1/phase-2 scope split, or
no-fire list text changes. T-162 phase-1a is `checked-PASS`.

**Changes-authorized:** `qa/contracts/source-adapters.md` (header status line only, by the checker —
this is a contract, not an enforcement path).

**Approved-by:** Umesh — the contract's substance was approved via `qa/gates/t162-contract-approval.md`
Option A, chat, 2026-09-21 (the four verbatim design answers quoted there); this entry records that
approval as the contract's authorizing D-record per its own header requirement.

**Links:** T-162; `qa/gates/t162-contract-approval.md` (Answered: 2026-09-21, Option A);
`qa/manifests/t162-source-adapters-1a.md`; `qa/verdicts/t162-source-adapters-1a.md`; unit commit
5e243b7; `qa/contracts/core-invariants.md` C1/C3/C7/C10 (all judged in the same check).

## D-036 | 2026-09-23 | type: decision | status: ACTIVE

**What:** Build T-163, the resumable learn-or-explore orchestrator, and promote DISCOVER + MODEL to
named canonical stages. Add `schema/run_state.py` (RunState + StageCheckpoint + a StageName enum) and
`stages/orchestrate.py::run_or_resume`. Use the existing per-stage filestore artifacts (T-020) as the
durable checkpoint substrate — no LangGraph / database dependency is added. Resume = re-enter the first
stage whose artifact is missing (the checkpoint's status is not done/skipped). Entry-path selection is
recorded on RunState (`mode`: teaching Sources present -> learn/INGEST; absent -> explore/DISCOVER via
the existing bounded-BFS crawl). Both paths converge on MODEL (FlowSpec assembly) and PROPOSE into a
DRAFT spec, stopping at the existing review gate (`stages/review.py::require_reviewed`); merge uses the
existing `merge_flowspec` which already resets to DRAFT (F-035) and refuses to discard an APPROVED spec
(F-037). Add a new contract `qa/contracts/orchestrator.md` (OR1-OR6) and take it DRAFT->ACTIVE on the
unit's checker PASS. Default run keying: one run_id per invocation, sequential per project (a later
superseding entry can widen to concurrent same-project runs if the operator needs it).

**Why:** The T-16x reusable-platform roadmap (D-023) named T-163 as the orchestrator that promotes
DISCOVER/MODEL; T-162 (all source adapters) is now done, clearing its last dependency. Reusing the
strongest thing already built — durable artifact-per-stage persistence — instead of introducing an
orchestration engine keeps the change small, keeps the human-reviewed-truth invariant that F-035/F-037
already enforce, and makes DISCOVER/MODEL first-class per the approved roadmap. Design grounded in the
operating brain (concepts/langgraph/persistence.md checkpointer+resume model; concepts/langgraph/hitl.md
draft-review archetype) — see `.work/t163-orchestrator-design.md`.

**Result:** Pending build. On checker PASS: `schema/run_state.py` + `stages/orchestrate.py` land,
`qa/contracts/orchestrator.md` goes ACTIVE, and `docs/ARCHITECTURE.md` Pipeline + execution-model
sections gain the `{INGEST | DISCOVER} -> MODEL -> ...` framing (regenerated within the 150-line budget).

**Changes-authorized:** docs/ARCHITECTURE.md ("Pipeline" and the stage-execution paragraph — add
DISCOVER/MODEL and the resumable-run framing, kept within the 150-line budget) · qa/contracts/orchestrator.md
(new, DRAFT->ACTIVE on this unit's checker PASS).

**Links:** T-163, T-160/D-023 (roadmap that registered it), T-162 (F-044, the dependency now cleared),
`.work/t163-orchestrator-design.md`, brain trace 0ee72e8c9a36.

## D-037 | 2026-09-23 | type: fix | status: ACTIVE

**What:** Add `EnterWorktree` and `ExitWorktree` to `permissions.allow` in `.claude/settings.json` so
auto-mode approves them without a human click. These tools were NOT allowlisted, so when a parallel
build subagent used `EnterWorktree` to relocate into its worktree, auto-mode fell back to a permission
prompt; with nothing running between turns, the T-163 build sat frozen on that prompt for ~3 hours
overnight. The two build briefs are also hardened to forbid the worktree tools and run verify via the
already-allowlisted `Bash` tool (defense in depth), but the allowlist is the durable fix: a gated tool
must never be able to silently kill the maker loop.

**Why:** Umesh reported the freeze directly (screenshot of the `EnterWorktree` prompt) and asked why the
loop waited all night despite permissions being granted. Root cause: the standing allowlist covered
`Bash`/`Edit`/`Read` and specific commands, but not the worktree tools the parallel-wave pattern relies
on. Allowlisting them removes the only human-click dependency in the otherwise self-driving build loop.

**Result:** `permissions.allow` gains `"EnterWorktree"` and `"ExitWorktree"`. The frozen T-163 build was
stopped and re-dispatched with the tools forbidden; it completed (commit 6cad8e0, ready-for-check).

**Changes-authorized:** .claude/settings.json (permissions.allow: add EnterWorktree, ExitWorktree).

**Approved-by:** Umesh

**Links:** T-163, the 2026-09-23 freeze Umesh reported; user CLAUDE.md "run, don't ask" / maker
CONTINUATION-RULE (nothing runs between turns, so a gated prompt is a loop-killer).

## D-038 | 2026-09-23 | type: decision | status: ACTIVE

**What:** Build T-164, the durable Portal Persona. Add `schema/portal_persona.py` (a Pydantic
`PortalPersona` model: profile, auth shape, screens, transitions, taught flows, gotchas, screenshot
refs, and a dated `history` list) and a stage `stages/portal_persona.py` that BUILDS/UPDATES the
persona from a crawl's screen graph (screen_graph.py/screenmap.py) + the reviewed FlowSpec, persisting
it as a durable cross-run artifact at `projects/<slug>/portal_persona.json` (the T-020 filestore) and
regenerating the human-readable `projects/<slug>/knowledge.md` page from it. Cross-run means: a later
run MERGES into the existing persona (new screens/transitions/flows appended, never silently dropping
prior knowledge) and records a dated `history` entry with a change summary (change detection). Add a
new contract `qa/contracts/portal-persona.md` (criteria PP1-PPn), DRAFT->ACTIVE on the unit's checker
PASS. This does NOT change the canonical pipeline in ARCHITECTURE.md — the persona is a durable
artifact and a stage, documented via the generated MAP/SNAPSHOT, not a new pipeline stage.

**Why:** The T-16x reusable-platform roadmap (D-023, milestone M9) named T-164 as the durable Portal
Persona: today portal-explorer knowledge is per-crawl scoped and lost between runs. T-163 (the
resumable orchestrator) is done, so a run now has a stable place to build/update the persona from.
Making the persona durable + versioned is the substrate T-166 (eval compiler) and T-167
(release-triggered regression) later read from.

**Result:** Pending build. On checker PASS: `schema/portal_persona.py` + `stages/portal_persona.py`
land, `qa/contracts/portal-persona.md` goes ACTIVE, and each run updates a durable persona +
knowledge page with dated history.

**Changes-authorized:** qa/contracts/portal-persona.md (new, DRAFT->ACTIVE on this unit's checker
PASS). No ARCHITECTURE.md prose change (generated MAP/SNAPSHOT reflect the new module).

**Links:** T-164, T-160/D-023 (roadmap M9), T-163/F-045 (orchestrator, the run substrate now cleared),
D-036 (the filestore-as-durable-store precedent this reuses).

## D-039 | 2026-09-24 | type: decision | status: ACTIVE

**What:** Authorize building T-125, the test catalog, exactly as `plan.md` §5A specifies. It adds a
pure stage `stages/catalog.py::catalog(project, spec, store) -> Catalog`, a schema
`schema/catalog.py` (`CatalogEntry`, `Catalog`, enum `BlockedReason` with the closed vocabulary
`no_flowspec`, `flowspec_not_approved`, `missing_credential`, `no_ground_truth`, `needs_write_policy`,
`no_live_endpoint`), and a `tier` for each `CaseClass` (`static` -> `behavioural` -> `adversarial`) so runs go
cheap-to-expensive. It also adds a read-only page `GET /projects/{slug}/catalog`. Add a new contract
`qa/contracts/catalog.md` (criteria CT1-CTn). /checker authors it from §5A as DRAFT, and it goes
DRAFT->ACTIVE on this unit's checker PASS.

**Why:** `stages/expand.py` generates cases without saying which ones can actually run. A tester then
sees a case count that silently includes cases blocked on a missing credential, an unapproved
FlowSpec or a write policy. The catalog makes "what is runnable now, what is blocked, and the one
action that unblocks it" explicit. T-152 (Track C check registry) and T-166 (traceable eval compiler)
both depend on T-125 and must reuse this one Catalog, never a second one. T-125 has been ready since
D-023 registered it, but no contract existed, so no maker could build it.

**Result:** Pending build. On checker PASS: the catalog stage, schema and page land, and
`qa/contracts/catalog.md` goes ACTIVE. `tests/test_catalog.py` and `tests/test_ui_catalog.py` are
the registered done_check. No ARCHITECTURE.md prose change: the catalog is a derived view over
existing artifacts, reflected in the generated MAP/SNAPSHOT, not a new pipeline stage.

**Changes-authorized:** qa/contracts/catalog.md (new, authored by /checker as DRAFT, DRAFT->ACTIVE on
this unit's checker PASS). No ARCHITECTURE.md prose change.

**Links:** T-125; plan.md §5A; D-023 (registered T-125, Approved-by Umesh 2026-09-09); T-152; T-166;
qa/gates/t165-d039-traversal-scope.md (that proposal is renumbered D-040, since this entry takes D-039)

## D-040 | 2026-09-24 | type: decision | status: ACTIVE

**What:** Widen T-165 in place and register two split-out units, following the crawl-reuse spike
(`docs/research/crawl-reuse-2026-09.md`).
- **T-165** keeps BFS frontier completeness and adds the following:
  - a traversal `strategy: bfs | hybrid`. Hybrid means BFS maps the portal, then a bounded DFS goes
    deep through each workflow, using Crawljax's depth-first candidate ordering ported as fresh
    Python (Apache-2.0, idea only, no code copied).
  - form-input replay: `_replay_discovery` re-issues a discovering step's `fill` values, not only
    its click.
  - an incremental crawl: the frontier is seeded from `portal_persona.json`, and a screen whose
    `(url_template, structural_signature)` matches the stored `PersonaScreen.signature` is skipped
    (Stagehand cache-key pattern, MIT, idea only).
  - change tracking: a persona revision records new, changed, missing and broken screens and flows.
    This extends `portal_persona.py::_merge` beyond add-only PP2 and feeds T-168.
- **T-170 (new, built first, no dependency on the traversal work):** first-party API/network
  assertions during a crawl or run. It ADOPTs Playwright `page.on('response')` (already a
  dependency). T-165's original "first-party API/network assertions" clause moves here.
- **T-171 (new):** permission-surface coverage. Every control the role can reach is either
  exercised or listed as blocked with a reason. Writes happen only under `write_policy=TEST_ACCOUNT`
  plus a per-run `RunApproval`, and destructive actions are ordered last.
- **Parked:** a Playwright Test Agents healer spike. Its internals are not public, so it is not
  blocking.

**Why:** Umesh, 2026-09-23 (qa/feedback-inbox.md): "video is optional, i also have to explore by
itself. and apart from bfs do dfs also … saving the website schema and flow … so the next time it
really need to retrace everything … agar koi chiz break ya update hogi tho vo bhi track ho", and
"jo account mai dunga usme jitni permission hogi utni tho testing ho hi jaani chaiyee". The hybrid
strategy is explicitly NOT a revival of D-023's rejected single happy-path DFS: BFS still maps the
whole portal, and the DFS is bounded per workflow. Splitting T-170 and T-171 out keeps T-165
checkable in one cycle. T-170 has no reuse candidate to wait on, so it ships value first.

**Result:** Pending build. T-165 stays critical (dual check). T-170 and T-171 are registered in
`.goal/goal.json`: T-170 has no dependency on T-165, and T-171 depends on T-165. T-166 now depends
on T-165 and T-170. Contracts: `qa/contracts/crawl-traversal.md` (new, T-165) and
`qa/contracts/network-assertions.md` (new, T-170) are authored by /checker as DRAFT and go
DRAFT->ACTIVE on each unit's first checker PASS.

**Changes-authorized:** docs/ARCHITECTURE.md "Pipeline" section: add one line naming the explore
traversal strategy (bfs | hybrid) once T-165 PASSes. qa/contracts/crawl-traversal.md and
qa/contracts/network-assertions.md (new, checker-authored DRAFT). .goal/goal.json: register T-170
and T-171, and widen T-165's note and done_check.

**Approved-by:** Umesh -- "go on" to the D-040 gate (qa/gates/t165-d039-traversal-scope.md), chat 2026-09-24, with the recommended answers 1 yes, 2 split, 3 park, 4 yes.

**Links:** T-165; T-166; T-168; T-170; T-171; D-023; D-038 (T-164 persona); D-039; docs/research/crawl-reuse-2026-09.md; qa/gates/t165-d039-traversal-scope.md; qa/feedback-inbox.md 2026-09-23T07:30

## D-041 | 2026-09-24 | type: decision | status: ACTIVE

**What:** Set AutoTester's AI-framework layering, its knowledge-graph and observability approach, and
register seven units for the add-ons and competitor features Umesh chose.

1. **Framework layers** (Vidysea agentic standard, 4 layers):
   - Workflow: **LangGraph 1.x, starting at T-167** (release regression: checkpointer and `interrupt()` for consent/review). Existing stages migrate to LangGraph nodes only when a unit touches them. No whole-pipeline rewrite.
   - Agents: typed Pydantic outputs. No multi-agent framework.
   - Skills: `SKILL.md`.
   - Tools: Playwright stays the deterministic actuator. browser-use (MIT) is the fallback for unknown screens, and AutoTester is exposed as an MCP server.
   - Model routing: LiteLLM.
   - Tracing: Langfuse self-hosted, phase 2.
2. **Knowledge graph** = the existing portal-persona screen graph (`PersonaScreen`/`PersonaTransition`), extended with typed nodes and edges for screen, control, flow, scenario, case, verdict, API and release. It stays JSON on the filestore (D-002). No graph database and no GraphRAG. Folded into T-166 as a traceability-graph criterion.
3. **Observability:**
   - Phase 1 (T-172): a local, redacted `trace.jsonl` per run.
   - Phase 2: export to Langfuse self-hosted (`TELEMETRY_ENABLED=false`, OSS edition, never Langfuse Cloud) once AutoTester runs on a server.
4. **Refused:** "regenerate tests instead of maintaining them" (docs/research/testsprite-2026-09.md §6).
5. **Deferred to Umesh:** the differential base-vs-head oracle (research item E). It needs two deployable builds of the app under test.
6. **New units:**

   | Unit | What it is | Depends on |
   |---|---|---|
   | T-172 | run trace | T-163 |
   | T-173 | parallel case execution in N isolated browser contexts, bounded by measured RAM/CPU and `project.max_parallel`; write-policy cases run serially | T-163 |
   | T-174 | CLI contract (`--output json`, documented exit codes, `--dry-run`) + AutoTester MCP server | T-125 |
   | T-175 | prompts become `SKILL.md` | none |
   | T-176 | persist and replay the generated script, plus semantic locators and a declared test-id attribute priority | T-165 |
   | T-177 | browser-use fallback actuator; revives `agent_loop.run_with_fallback`, closes AT-253 | T-176 |
   | T-178 | atomic failure bundle, case priority p0–p3, and human pruning of proposed cases | T-125 |

**Why:**
- Umesh asked whether AutoTester should use an AI framework, a knowledge graph and observability. On 2026-09-24 (AskUserQuestion) he chose LangGraph from T-167 (Recommended), plus a browser-use fallback, AutoTester as an MCP server, prompts as SKILL.md and tracing. He also asked for "other functionality that competitors use or what we had built till now, parallel processing".
- The Vidysea standard (`umesh/operating-brain/wiki/patterns/agentic-architecture-standard.md`, 2026-09-23) sets the defaults: LangGraph for products, SKILL.md + MCP + typed schemas + LiteLLM as the portable core, and Langfuse self-hosted for tracing. It also says to use the simplest layer that fits, and to go multi-agent only with a measured gain.
- D-002 kept the stages node-shaped for exactly this migration. Adopting LangGraph at T-167 puts it where durable pause/resume pays, without rewriting working stages.
- Competitor items A, C, D, F, G and H come from docs/research/testsprite-2026-09.md §4. B, the assertion layer, is already built (AT-540).
- Parallel runs address the observed serial bottleneck: TestSprite fans out to parallel browsers, and ours runs one case at a time.

**Result:**
- Pending builds. `.goal/goal.json` gains T-172 to T-178, T-167 gains a LangGraph note and T-166 gains a knowledge-graph note.
- The roadmap guard pins the new rows.
- /checker authors each new contract as DRAFT: run-trace.md, parallel-run.md, cli-mcp.md, skills.md, script-replay.md, agent-fallback.md and failure-bundle.md. Each goes ACTIVE on its unit's first checker PASS.
- Dependencies (langgraph, browser-use) are added to pyproject.toml only by the unit that builds with them.

**Changes-authorized:**
- `.goal/goal.json`: register T-172 to T-178, and add notes to T-166 and T-167.
- `tests/test_goal_done_checks.py`: pin the new rows; the count goes from 57 to 64.
- `pyproject.toml`: langgraph and browser-use, added only within T-167 and T-177.
- New checker-authored DRAFT contracts under `qa/contracts/`, as listed in Result.
- `docs/ARCHITECTURE.md` "Pipeline" gets one line on the LangGraph workflow layer once T-167 PASSes.

**Approved-by:** Umesh -- AskUserQuestion answers and plan approval, chat 2026-09-24.

**Links:** T-163; T-165; T-166; T-167; T-172; T-173; T-174; T-175; T-176; T-177; T-178; AT-253; AT-540; D-002; D-036; D-040; docs/research/testsprite-2026-09.md; umesh/operating-brain/wiki/patterns/agentic-architecture-standard.md

## D-042 | 2026-09-24 | type: decision | status: ACTIVE

**What:** AutoTester's product agent layer is built on **LangChain Deep Agents** (on LangGraph 1.x), after Wave 1 (T-170, AT-110, T-172, T-173, AT-086/087, T-175, T-126, AT-335).

- **Lead tester agent** (`create_deep_agent`): plans each job as a to-do list (Deep Agents planning middleware) and delegates to subagents. The project artifacts under `projects/<slug>/` are its filesystem backend.
- **Subagents:** explorer, test-designer, runner, **grader** and reporter.
  - The grader runs in its own context and holds **no action tools**. It only reads evidence and returns a verdict, so C7 still holds: the executor never grades itself.
- **Skills:** the `SKILL.md` folders from T-175, loaded through `skills=`.
  - The grader rubric, test design (best/worst/edge), bug-hunting, ingest, scenario-list coverage and worst-case-default detection are all skills.
  - Prompts are skills, not tools.
- **Tools:** the existing deterministic stages, wrapped rather than rewritten:
  - crawl, run_case, get_persona, get_catalog, capture_network, grade_case and report;
  - a browser-use step for unknown screens (T-177).
  - The safety policy, credential boundary (`{{SECRET:KEY}}` refs only, never values), write_policy and consent/RunApproval checks stay in code **inside** the tools. They are deterministic guards the model cannot bypass (Vidysea standard rule 3).
- **Scope of subagents:** used only where judgement is needed. Everything else stays a plain tool call (standard rule 2: multi-agent costs ~15x tokens).
- **Tracing:** every agent and tool span goes through T-172's trace, and later to Langfuse self-hosted.
- **New units:**

  | Unit | What it builds | Depends on |
  |---|---|---|
  | T-179 | Deep Agents lead tester + stage tools + deepagents dependency (skills need deepagents >= 1.7) | T-170, T-172, T-175 |
  | T-180 | subagents (explorer, designer, runner, independent grader, reporter) | T-179 |
  | T-181 | agent guardrails + measured gain: deterministic guards before every acting tool, a per-run token/cost budget, and a fixture comparison of agent vs pipeline on bugs found, false positives, tokens and time. The layer stays only if it shows a gain | T-180 |

  T-177 (browser-use) becomes one of the runner's tools. T-167 (release regression) runs the lead agent on LangGraph checkpoints.

**Supersedes:** D-041 -- D-041 point 1 said "Agents: typed Pydantic nodes. No multi-agent framework", with LangGraph starting only at T-167. That is replaced by a Deep Agents layer, because the users want AutoTester to plan and delegate like a real tester using skills and tools. D-041's other points (knowledge graph, observability, SKILL.md, MCP server, browser-use, competitor units, parallel runs, the refusal and the deferral) remain in force unchanged. The new approach is better because the deterministic stages keep every safety guarantee inside tools, while planning, test design and judging get the Deep Agents harness (planning, subagents, skills). That harness is the Vidysea standard for products that need skills and subagents. T-181 must prove a measured gain before the layer is kept.

**Why:** Chat 2026-09-24: "and for subagents and all deepagents use ho rhee hai?" and "tho humko deepagents with skills and all bnaane hai with tools . prompts as tool dene hai right /maker". AskUserQuestion answers: "Haan, Umesh approve (Recommended)" and "Wave 1 ke baad (Recommended)". The Vidysea agentic standard (`umesh/operating-brain/wiki/patterns/agentic-architecture-standard.md`) names LangGraph 1.x + Deep Agents as the product default where skills or subagents are needed.

**Result:** Pending. `.goal/goal.json` gains T-179, T-180 and T-181, and the roadmap guard pins them (64 -> 67 tasks). /checker authors the DRAFT contract `qa/contracts/agent-layer.md` before T-179 builds. `target.md` M10b is updated.

**Changes-authorized:**
- `.goal/goal.json`: register T-179 to T-181, and note on T-167 and T-177.
- `tests/test_goal_done_checks.py`: pin the new rows; the count goes to 67.
- `target.md`: M10b.
- `pyproject.toml`: add deepagents, within T-179 only.
- `qa/contracts/agent-layer.md`: new, checker-authored DRAFT.
- `docs/ARCHITECTURE.md` "Pipeline": one line naming the agent layer, once T-179 PASSes.

**Approved-by:** Umesh -- AskUserQuestion option "Haan, Umesh approve (Recommended)", 2026-09-24 (qa/gates/d042-deep-agents.md).

**Links:** D-041; D-002; T-167; T-170; T-172; T-175; T-177; T-179; T-180; T-181; qa/gates/d042-deep-agents.md; umesh/operating-brain/wiki/patterns/agentic-architecture-standard.md; umesh/operating-brain/wiki/concepts/krishnaik/deep-agents.md

## D-043 | 2026-09-25 | type: decision | status: ACTIVE

**What:** Scope core-invariants.md C8's prompt-location line to the T-175 migration. C8 said "Prompts
live in `src/autotester/prompts/*.md` as versioned files, never inline string literals." Since T-175
merged (9b3fd5e), four prompts -- grade, expand-case, ingest-video, video-issues -- live as
`src/autotester/skills/<name>/SKILL.md` and are loaded through `providers.base.load_skill_prompt`;
the remaining prompts (e.g. relitigation_v1.md, agent_fix_v1.md) still live in `prompts/*.md`. C8 now
names both locations. The invariant's substance is unchanged: every prompt is a versioned file, never
an inline string literal.

**Why:** D-041 (Approved-by Umesh, 2026-09-24) decided prompts become SKILL.md (point 1 "Skills:
SKILL.md"; point 6 "T-175 | prompts become SKILL.md"), but its Changes-authorized did not name
qa/contracts/core-invariants.md, so the contract was left describing a location the four migrated
prompts no longer use. The t175 checker ruled the migration authorized (not a C8 violation) and
proposed scoping the prose; under the Lab Protocol a contract edit needs an authorizing entry, so this
entry records the consequence of D-041 rather than a new direction. It weakens nothing: the
never-inline rule and the Provider seam are untouched, and the loader fails loudly on a missing or
malformed skill (verified in the t175 verdict), so a prompt can never silently become empty.

**Result:** core-invariants.md C8 prompt line names `prompts/*.md` and `skills/<name>/SKILL.md` as
the two versioned-file locations, plus one amendment-log row. No src/ or test change. doctor clean.

**Changes-authorized:** qa/contracts/core-invariants.md (C8 prompt-location line + one amendment-log
row, by the checker). No enforcement path.

**Links:** D-041; T-175; qa/verdicts/t175-prompt-skills.md; AT-563.

## D-044 | 2026-09-25 | type: decision | status: ACTIVE

**What:** Scope execute.md E4's evidence clause to the case being run. E4 said the returned
`RawResult` carries "every `Evidence` the session recorded". Since at576-577 merged (8e50efc), the
serial route reuses one `BrowserSession` across several cases, and `run_case` returns only the
evidence recorded from its own start index (`evidence_start`, AT-577). The network assertion reads
the same scope (AT-578). E4 now reads "every `Evidence` recorded during this case".

**Why:** The old wording, read literally, requires exactly the defect AT-577 fixed: case 2's result
carrying case 1's screenshots, so a judge grades on another case's pages. The at576-577 builder
reported the stale wording through qa/feedback-inbox.md, and the checker PASSed the unit (cycle 2)
with the per-case scope proven in a real browser. Under the Lab Protocol a contract edit needs an
authorizing entry. This entry records the consequence of that fix and gives no new direction. It
tightens the criterion: a result that carries evidence from outside its own case now violates E4.

**Result:** qa/contracts/execute.md E4 evidence clause reworded, plus one amendment-log row. No src/
or test change. doctor clean.

**Changes-authorized:** qa/contracts/execute.md (E4 evidence clause + one amendment-log row, by the
checker). No enforcement path.

**Links:** AT-577; AT-578; qa/verdicts/at576-577-serial-runs.md (cycle 2 PASS); merge 8e50efc.

## D-045 | 2026-09-26 | type: decision | status: ACTIVE

**What:** Add two tightening criteria from the checker's goal-coverage review of the 2026-09-25 counselor-tool meeting.
(1) qa/contracts/execute.md E6: a case whose class names an execution condition (VIEWPORT_MOBILE, LOCALE_I18N) must
run under that condition, or be recorded as not run. It must never produce a PASS from a default-condition run.
(2) qa/contracts/report-export.md RE6: both exports carry, for every failed or inconclusive verdict, each failure's
criterion, reason and fix_hint, plus the case's own steps as repro, verbatim from the stored artifacts.

**Why:** Both close gaps where AutoTester currently misleads the people it reports to.
- **AT-581:** mobile and locale cases are generated but run at a hard-coded 1366x850 desktop viewport in the default
  locale (browser/launch.py:30), so a PASS on them is a false pass. That is exactly the false-positive the north star
  counts.
- **AT-582:** the judge already writes a reason and a fix_hint (schema/verdict.py:54-62), but the developer-facing
  exports drop them. The meeting asked for exactly this: "tell the development team what broke and how to fix it".

Both only add duties (RE1's "verbatim, never recomputed" still holds for the new fields), and neither weakens an
existing criterion. So this records a tightening, not a new direction. The direction-changing items from the same
review (user personas plus advisory UX judging; run video) are HUMAN_GATEs for Umesh, not part of this entry.

**Result:** execute.md gains E6 and report-export.md gains RE6, each with one amendment-log row naming the issue that
tracks the current gap (AT-581, AT-582). No src/ or test change. doctor clean.

**Changes-authorized:** qa/contracts/execute.md (new E6 + one amendment-log row); qa/contracts/report-export.md (new
RE6 + one amendment-log row); both by the checker. No enforcement path.

**Links:** AT-581; AT-582; AT-583..AT-589 (same review); plan you-are-the-checker-cozy-stardust.md.

## D-046 | 2026-09-26 | type: decision | status: ACTIVE

**What:** Add core-invariants criterion C11: "Every third-party import is a declared dependency". It is checked by the new `autotester doctor` check `check_dependencies_declared` (src/autotester/doctor.py:142).

**Why:** AT-130 showed that `google-genai` (and later `starlette`) were imported directly but resolved only as transitive dependencies of another package. One upstream change would have broken the provider layer with no warning. The at130-genai-dep unit made the rule machine-checked (checker PASS cycle 1, merged 235fdd5), but no contract named it, so a later edit could remove the check without failing any criterion. This is a tightening: it adds a duty and weakens nothing.

**Result:** qa/contracts/core-invariants.md gains C11 plus one amendment-log row. The doctor check's known over-reach, which flags TYPE_CHECKING-only and try/except-ImportError optional imports as hard dependencies, is tracked as AT-590 and named in C11 as a known false-positive class, not a licence.

**Changes-authorized:** qa/contracts/core-invariants.md (new C11 + one amendment-log row), by the checker. No enforcement path.

**Links:** AT-130; AT-590; qa/verdicts/at130-genai-dep.md; merge 235fdd5.

## D-047 | 2026-09-26 | type: decision | status: ACTIVE

**What:** The checker authors qa/contracts/loop-status.md. It gives `autotester loop-status` its first contract, codifying four behaviours:
- LS1: what `--strict` exits non-zero for.
- LS2: every structured anomaly is rendered.
- LS3: write-order corruption is report-only.
- LS4: loop-status stays out of doctor.

LS3 records Umesh's answer to qa/gates/at610-strict-out-of-order.md: "A, keep report-only", 2026-09-26, recorded in 7fce333.

**Why:** Three units (at399, at424, at592) were judged against no contract that names loop-status. The at592 manifest says so and asks the checker to decide whether a contract is warranted. It is, because each of those units pinned an exit-code or rendering rule that a later unit could silently undo.

The at610 answer is the fourth rule. `out_of_order` is counted over file order, but liveness is judged from the sorted credible ticks (loop_status.py:245 vs :251), so write-order corruption never hides an outage. Gating `--strict` on it would add a false alarm, for example two sessions with skewed clocks, and no safety.

LS1, LS2 and LS4 describe behaviour already shipped and tested (tests/test_loop_status_integrity.py), so they add no new duty. LS3 pins a behaviour the code already has; the maker's unit at610-strict-out-of-order-pin adds the test. None of this weakens an existing criterion.

**Result:** New file qa/contracts/loop-status.md, ACTIVE, with an init amendment-log row. No src/ or test change by the checker. AT-610 closes when the pinning unit passes and merges.

**Changes-authorized:** qa/contracts/loop-status.md (new contract, authored by the checker). No enforcement path.

**Links:** AT-610; AT-592; AT-424; AT-399; AT-368; qa/gates/at610-strict-out-of-order.md; 7fce333; unit at610-strict-out-of-order-pin.

## D-048 | 2026-09-26 | type: decision | status: ACTIVE

**What:** Umesh answered 12 open HUMAN_GATEs in one sitting on 2026-09-26, through AskUserQuestion in the checker session. The checker raised them at his request ("jo jo chaiyee mujhe properly raise krkee maang lee"). Each answer is recorded verbatim in its gate file. This entry authorizes the changes they imply.

**Tests and detectors**
- **at438 = a+b+c.** U14(b) is judged against the pre-unit detector. The checker re-scores cycle 3 on that baseline. AT-453 becomes its own unit, capped at 2 cycles. AT-454 is a documented known limitation.
- **at416 = B.** The held both-directions candidate (wave/at408-416-scroll-reach) becomes a checkable unit. It needs real-Chromium Mode D plus the 50-shape scroll-invariance corpus. This is not the checker's recommendation (A); Umesh chose B.

**ERP**
- **erp-credentials = provide.** Umesh enters a TEST account himself in the UI. The keys are verified by name only, never by value.
- **t135 = B.** One Analyze re-run on erp, approved for that single vision call.

**Product direction**
- **meeting-user-persona-ux-judging = A.** An advisory UX track that never changes PASS/FAIL.
- **meeting-run-video-scope = A.** Record video on FAIL or inconclusive only, keep the last 20, and mask secrets as in screenshots.

**Process**
- **at383 = C.** Session-start hook now; the shared sweep routine later.
- **at147 = C.** An expiry date means the end of that day, for new approvals only.
- **at218 = 2.** Every new guard ships with a recorded falsification proof.
- **commit-before-verdict = C.** Unit branch before check; merge to master only after a PASS.
- **at520 = 3.** scripts/ stays outside the numeric caps and the duplicate-definition check.
- **at516 = (c).** A stale evidence spec stays byte-intact and gets a "stale on purpose" tag.

**Why:** These are product-direction and process choices that only the Approver can make. Several had waited since 2026-09-09. Writing all twelve down in one entry lets the maker build from them and the checker fold contract criteria against a single authorizing record, instead of from chat memory.

**Result:**
- All 12 gate files carry a dated Answered line.
- The maker turns them into goal tasks: at416-B check, AT-453 unit, at147-C, at383-A hook, at516-c tagging, a persona/UX track, run video, the t135 Analyze re-run, and T-122 once the keys are present.
- The checker folds the matching contract criteria. Criteria for units not yet built are folded when each unit's contract is written.

**Changes-authorized:**
- qa/hooks/mc-sessionstart.ps1: call `autotester loop-status --strict` at session start and print its report (at383 part A). This is an enforcement path.
- qa/contracts/core-invariants.md, by the checker:
  - C2: an explicit sentence that scripts/ is deliberately outside the caps (at520).
  - C7: new guards carry a recorded falsification proof (at218).
  - C10: unit branch before check, merge only after a PASS (commit-before-verdict).
- qa/contracts/loop-status.md: an LS5 for the session-start consumer, once it is built.
- qa/contracts/consent.md: the at147 end-of-day expiry for new approvals.
- New or existing contracts for the persona/UX track and run video, written by the checker when their goal tasks exist.
- The at516 tagging rule, in the contract that owns evidence specs.
- The src/ and test changes each of those units needs, through the normal maker-checker handshake.

**Approved-by:** Umesh (AskUserQuestion answers, checker session, 2026-09-26; the at383 option he chose names the session-start hook explicitly)

**Links:** qa/gates/{at438-u14b-baseline, at416-clip-vs-reach-direction, erp-credentials, meeting-user-persona-ux-judging, meeting-run-video-scope, at383-loop-status-consumer, at147-expiry-end-of-day, at218-vacuous-guard-class, commit-before-verdict, at520-scripts-line-cap, at516-evidence-spec-splitting-policy, t135-url-pattern-data-migration}.md; AT-438; AT-453; AT-454; AT-416; AT-379; AT-583; AT-584; AT-587; AT-383; AT-368; AT-147; AT-150; AT-218; AT-520; AT-488; AT-516; T-122; T-145; T-135; D-047

## D-049 | 2026-09-26 | type: decision | status: ACTIVE

**What:** The checker amends qa/contracts/ui.md U14 to carry out Umesh's at438 gate answer, a+b+c (D-048):
- U14(b): "pre-change detector" now means the detector at the unit's branch point, the parent commit before its first cycle. It never means a failed or committed earlier cycle of the same unit.
- U14(c): the disclosed blind set gains AT-454, a display:contents child slotted through a mode:"closed" shadow root that is reported although it does not paint. It is filed, never charged.

Under this baseline, at438-display-contents cycle 3 (9fc937d) is re-ruled PASS. AT-453 is split out as its own unit, capped at 2 cycles (gate option b), and stays open and charged. It is not added to the blind set.

**Why:** Cycles 2 and 3 were charged under U14(b) against the cycle-1 probe c687b73. That probe itself FAILED (AT-442, high) and could never ship. The gate asked which baseline U14(b) means, and Umesh answered (a), the pre-unit detector.

The checker re-measured in real headed Chromium (qa/evidence/browser-at438-rerule-2026-09-26-checker/): 70 layouts, run against 3 detector versions pulled from git.
- Against c687b73^, cycle 3 and master drop zero texts the old detector reported.
- False negatives: OLD 26, C3 2, MASTER 2. The remaining 2 are AT-453's A3/A4, which OLD also misses.
- visual_order.js on master is byte-identical to 9fc937d.
- An adversarial skeptic tried 16+ more shapes and could not refute this.

This narrows what U14(b) charges. A later cycle may now lose ground an earlier rejected cycle of the same unit had gained, provided it never falls behind pre-unit master. That narrowing is named here deliberately, because it is exactly what gate option (a) chose. AT-453 is not lost: option (b) keeps it as its own charged unit.

**Result:**
- qa/contracts/ui.md: U14(b) and U14(c) are amended, with an amendment-log row.
- qa/verdicts/at438-display-contents.md: gains a cycle-3 re-ruling section.
- Ledger:
  - AT-438, AT-449 and AT-450 flip to fixed, since 9fc937d is an ancestor of master.
  - AT-454 becomes wontfix, a documented limitation that needs CDP-level shadow inspection.
  - AT-453 stays open for its own unit.

**Changes-authorized:** qa/contracts/ui.md U14(b) and U14(c) wording plus the amendment log (checker). No enforcement path.

**Links:** D-048; qa/gates/at438-u14b-baseline.md; AT-438; AT-442; AT-449; AT-450; AT-453; AT-454; 9fc937d; c687b73; qa/evidence/browser-at438-rerule-2026-09-26-checker/

## D-050 | 2026-09-26 | type: decision | status: ACTIVE

**What:** The checker writes two contracts that D-048 authorized:
- qa/contracts/persona-ux-advisory.md for T-190, criteria PU1-PU9;
- qa/contracts/run-video.md for T-191, criteria V1-V8.

It also amends qa/contracts/report-export.md RE3 with one named exception. A kept run video (EvidenceKind.VIDEO, T-191) is linked from the exported HTML by a path relative to the run directory, never embedded. The HTML stays self-contained for everything else: screenshots are still base64-embedded, and the page still opens with no server or network.

**Why:**
- D-048 fixed Umesh's two gate answers:
  - meeting-user-persona-ux-judging = A: an advisory UX track that never changes PASS/FAIL;
  - meeting-run-video-scope = A: record on FAIL or INCONCLUSIVE only, keep the last 20, mask secrets as in screenshots.
- D-048 authorized the checker to write these contracts once the goal tasks existed. T-190 and T-191 now exist.
- Each contract was drafted against the code and then critiqued by a fresh agent that opened every cited file:line.
- A 15-20 minute recording cannot sensibly be base64-embedded in a portable HTML report. RE3 predates video evidence and did not anticipate it. Leaving RE3 as written would make T-191's V8 ungradeable.

The exception narrows RE3 for video only. It is named here as a deliberate narrowing, not a silent one. Screenshot embedding and every other RE3 property are unchanged.

**Result:** Two new ACTIVE contracts, each with an init amendment-log row. report-export.md RE3 gains the video-link exception plus an amendment-log row. No src/ or test change by the checker.

**Changes-authorized:**
- qa/contracts/persona-ux-advisory.md (new);
- qa/contracts/run-video.md (new);
- qa/contracts/report-export.md RE3 (the video-link exception) and its amendment log.

No enforcement path.

**Links:** D-048; T-190; T-191; AT-583; AT-584; AT-587; qa/gates/meeting-user-persona-ux-judging.md; qa/gates/meeting-run-video-scope.md

## D-051 | 2026-09-27 | type: decision | status: ACTIVE

**What:** T-125 proceeds by specifying relevance first, then exactly one scoped cycle (option A)

**Date:** 2026-09-27
**Decider:** Umesh (asked at the `qa/gates/t125-stalled-at-cycle-cap.md` gate, answered A)
**Approved-by:** Umesh
**Status:** ACCEPTED
**Links:** T-125 · T-152 · T-166 · T-174 · T-178 · `qa/gates/t125-stalled-at-cycle-cap.md` ·
`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` · `qa/debug/t125-catalog-cycle3.md` ·
`ISS-t125-1` · `ISS-t125-5` · D-039
**Result:** T-125 unblocks by specification, not by another guess. The checker amends
`qa/contracts/catalog.md` to define flow relevance; the maker then gets exactly one cycle (cycle 4)
against that written rule. Releases T-152 / T-166 / T-174 / T-178 once T-125 lands.

**Why:** No criterion in `catalog.md` ever defines which secret key belongs to which catalog row, so
each of the three failed cycles was a guess at unwritten ground truth. Three independent parties
reached that diagnosis separately (both cycle checkers, recording it as outside their blast radius at
`qa/verdicts/t125-catalog.md:132-146` and `:340-343`, plus the read-only review in
`qa/debug/t125-catalog-cycle3.md`). The 3-cycle cap exists to stop a maker grinding at a *specified*
task; that premise was never met here, so fixing the specification changes the conditions rather than
buying a fourth guess. The ambiguity traces to `docs/plan.md:521-523`, which predates any maker
touching the file.

**Changes-authorized:** none in `docs/ARCHITECTURE.md`. Authorizes the checker to amend
`qa/contracts/catalog.md` (CT2/CT5/CT8 as needed) to define flow relevance, and authorizes exactly
one additional T-125 fix cycle (cycle 4) after that amendment lands.

### Decision

T-125 does **not** get a fourth guess. The checker first amends `qa/contracts/catalog.md` to define
**which flows a catalog row is about**, and only then does the maker build once against that written
rule. This breaks the 3-cycle fix cap by one cycle, deliberately and on the record.

### Why the cap is broken rather than respected here

The cap exists to stop a maker from grinding at a task it keeps failing. That is not what happened.
Three independent parties reached the same diagnosis from different angles: **no criterion in
`catalog.md` ever defines which secret key belongs to which catalog row.** CT5 and CT8 judge the
blocked state and its `unblock_action`, so a checker can prove an answer *wrong* without the contract
ever saying what is *right*. Both cycle-2 and cycle-3 checkers hit the same wall and each recorded it
as outside its own blast radius rather than filing it
(`qa/verdicts/t125-catalog.md:132-146` and `:340-343`); the read-only review in
`qa/debug/t125-catalog-cycle3.md` then confirmed it independently. The ambiguity traces to
`docs/plan.md:521-523` — the only worked example D-039 authorizes — which says "an unset secret …
naming the key", singular and spec-wide, and **predates any maker touching the file.**

So the cap's premise — a maker failing at a *specified* task — was never met. Fixing the
specification changes the conditions rather than buying another guess. **The rule must be written
before the cycle, not guessed inside it.** That is the whole content of this decision, and the single
extra cycle is conditional on the amendment landing first.

### Why the alternatives were not chosen

- **B (revert to cycle 1) was corrected during the gate and is not the safe fallback it looked
  like.** `cfc13b0b:catalog.py:128` threads the same global unscoped union into the gate that cycle 3
  does, so **cycle 1 carries the identical `ISS-t125-5` defect** — and `cfc13b0b` was never a passing
  commit (no manifest; the cycle-1 check failed it on CT5/CT6). The standing regression rule assumes a
  last *good* state to return to; in this function's history there is none. Reverting buys nothing on
  correctness and loses cycle 3's genuinely-correct `ISS-t125-3` fix and its test.
- **C (ship with no credential gate)** is honest but gives up a feature AT-588 asked for, and still
  requires amending CT5/CT8 — so it is a contract change either way, with less delivered.
- **D (amend CT2 to allow >1 row per `CaseClass`)** addresses the root shape and remains the fallback
  if the amendment cannot express relevance at the current schema level. It costs the catalog's best
  property — a fixed-length table an operator can scan — and is the largest change of the four.

### Constraint the amendment must respect

`stages/explore_merge.py:50-51` states the repo's own discipline: **`secret_key` is deliberately never
inferred.** Any rule built on a keyword or structural classifier fails in the same shape again — the
review demonstrated this with a fifth fixture (a Google button clicked to import a Drive file, not to
authenticate). The two candidate shapes that respect the discipline are a **flow dimension on
`CatalogEntry`** or a **human-declared relevance field on `SecretRef`**. The checker chooses; the
maker does not.

### Blast radius

`src/autotester/stages/catalog.py` does not exist on `master`. The entire stage and both regressions
live only on the unmerged `wave/t125-catalog`. No shipped behaviour is affected and no operator has
ever seen a wrong catalog row. `wave/t125-catalog` stays unmerged and un-reverted until cycle 4.

### Still open, and not answered by this entry

`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` is a **second, independent** reason T-125 cannot reach
8/8. This decision does not touch it.

## D-052 | 2026-09-27 | type: decision | status: ACTIVE

**What:** Trust-number path: Pathlynks first, a fixture trust number now, Track C built but not fired

**Date:** 2026-09-27
**Decider:** Umesh (asked in-session; selected three options together)
**Approved-by:** Umesh
**Status:** ACCEPTED
**Links:** T-136 · T-150 · T-154 · T-155 · T-169 · `target.md` M7 / M11 / M12 ·
`qa/gates/erp-credentials.md` · `qa/gates/t136-model-credentials.md` ·
`qa/gates/live-crawl-target.md` · D-023 · D-048 · `schema/bench.py`
**Result:** Pathlynks stays the first product (T-122/T-145/T-136 held for a second). A
fixture-derived trust number is built now so the scoring harness is proven before real inputs exist.
T-150/T-151/T-152/T-153/T-154/T-155 are unblocked for BUILD; adversarial probe traffic against any
real target still requires a separate per-run approval naming target and consent scope.

**Why:** Umesh selected Pathlynks-first, a fixture trust number, and unblocking Track C together. The
finish line T-169 is gated on inputs only he can supply, so the value of this routing is that it takes
everything *else* off the critical path: when the inputs arrive, only the run remains. The build/fire
split on Track C is written because the maker flagged at the gate that unblocking T-154/T-155 implies
real probe traffic and that a target and consent scope would need naming; none was named, so the
machinery is built and the firing still gates to a human. Consent gate 2 existing is not permission to
use it.

**Changes-authorized:** `target.md` M7/M11/M12 status rows may be updated to reflect this routing.
No `docs/ARCHITECTURE.md` prose change.

### Decision, in three parts

1. **Pathlynks stays first** (confirming D-023 / the 2026-09-24 scoping). T-122, T-145 and T-136
   remain held for a *second* product; no credentials are requested for ERP or anything else until
   Pathlynks is proven.
2. **A fixture-derived trust number is built now.** The recall / false-positive / time machinery of
   T-136 is built and checker-reviewed against a fixture product, so the scoring harness is proven
   before real credentials or a real truth sheet exist.
3. **T-154 and T-155 are unblocked for BUILD, not for FIRING** — see the boundary below, which is the
   operative half of this entry.

### Part 2 — what a fixture trust number may and may not claim

The point is to have the measurement apparatus reviewed before it is pointed at anything that matters,
so that the first real number is trustworthy on arrival instead of being debugged under pressure.

- Every output is labelled **fixture-derived** at the point of production — in `schema/bench.py`'s own
  fields, not only in prose around it. A fixture number is never rendered in a position where a reader
  could take it for the real one.
- It is **not** the T-136 acceptance number and does not tick M7. T-136 stays `pending` and still needs
  `ERP_Issues_Trainers.xlsx` or its Pathlynks equivalent.
- Its purpose is falsifiable: the harness must be shown to produce a *wrong* score when fed a known-bad
  fixture, or it has not been proven at all.

### Part 3 — the boundary on Track C, stated because it is the risk

**The build is unblocked; probe traffic is not.** T-150 (governance), T-151 (read-only discovery),
T-152/T-153 (registry and behavioural checks), T-154 (the bounded adversarial pass and
`adversarial_proof.py`) and T-155 (the tiered report) may all be built. What stays gated:

- **No adversarial probe traffic against any real target** without a *separate, per-run* approval from
  Umesh that names the target and the consent scope. Consent gate 2 is the mechanism T-154 builds; the
  mechanism existing is not the same as permission to fire it.
- T-154 is developed and proven **against a fixture target only**. `adversarial_proof.py` must
  demonstrate the bound holds — i.e. that the pass refuses to exceed its declared scope — as its
  primary evidence, before any live use is contemplated.
- T-151 is **read-only by construction** and unchanged by this entry: signals come from grep and file
  inspection, never a model, and every `Signal` cites a real `file:line`.
- `write_policy` stays `read_only`. Nothing here authorises a write to a live product.

**Why the boundary is written rather than assumed:** the maker flagged at the gate that unblocking
T-154/T-155 implies real probe traffic and that the target and consent scope would need naming first.
Umesh selected the option and did not name a target. The faithful reading of that — and the one this
entry records — is that the *machinery* is wanted now and the *firing* still gates to a human. If the
intent was broader, this entry is the thing to correct.

### Consequence for the finish line

T-169 remains the definition of done and remains gated on inputs only Umesh supplies. This entry does
not move that date; it removes everything *else* from the critical path, so that when the inputs arrive
the only remaining work is the run itself.

## D-053 | 2026-09-27 | type: decision | status: ACTIVE

**What:** `ALLOW_WRITES` is the authorized write-policy CEILING on every target including production
(Umesh, `qa/gates/write-policy-tier.md`, commit 88ab7638). **No project is flipped to it by this
entry.** All nine `projects/*/project.json` stay `write_policy: read_only` (verified 2026-09-27).
Raising an individual project's tier is a separate act, taken when a unit actually needs it, under its
own entry and its own per-run `RunApproval`. This entry also corrects a claim the maker made to Umesh
about the credential boundary, and records `AT-653`'s constraint on T-136's comparison artifact.

**Why:** Three separate things needed recording and none of them is a code change.

1. **The ceiling is Umesh's and is not re-litigable.** D-018 already said *"ALLOW_WRITES is Umesh's
   switch"*; this is the switch being thrown, consistent with four prior records
   (`at052-bfs-video-corpus-grill.md:43`, `DECISIONS.md:860`, `at110-approval-forgery.md:38`, and this
   gate). The checker put the consequences in the question **before** he chose — that at `ALLOW_WRITES`
   the 19-term deny-list goes off, so on production a crawler-invented click may hit `Delete` on a real
   record, `Send` a real email to a real person, and `Pay` real money, and that an account having the
   *right* to an action is not the same as the action being reversible. He chose it with that in front
   of him. **A future session may report what a run actually did; it may not reopen this gate.**
2. **A ceiling is not a setting, and this is where the safety actually lives.** The gate itself lists
   what it does not waive: per-run approval governs every outward-facing run, logout is never clicked
   at any tier (`DEFAULT_NEVER_CLICK_PATTERNS`, `schema/crawl.py:41`), real user accounts are never
   used, and `T-154`/`T-155` stay held. The checker's recorded residual is the operative point:
   **`send` and `pay` are outward-facing to THIRD PARTIES and no policy, approval or rollback undoes
   them.** So a run should routinely be approved with a **narrower** scope than the tier permits, and
   when T-171 wires the permission surface it wires against that narrower per-run scope — not against
   the tier. Flipping nine projects to the ceiling today would convert a considered authorization into
   a standing default, which is the opposite of what the gate's own limits ask for.
3. **A correction the maker owes, stated plainly because it was told to Umesh wrong.** The maker
   reported that `CLAUDE.md`'s credential boundary contradicts the code in a way that weakens domain
   scoping, and that `core/paths.py:51` exposes a per-project `.env` path the credential flow does not
   use. **Both halves were wrong.** `ProjectPaths.env_file` returns the **repo root** `.env` by design
   — its own docstring says *"One credential file for the whole repo, at the root (Umesh,
   2026-09-03). Keys are namespaced per project (`PATHLYNKS_*`) and declared in each project's
   `SecretRef[]`; a project can only resolve the keys it declares."* — and it **is** the path the
   credential flow uses (`ui/routes_credentials.py:124,153,168`). Scoping is real; it is enforced by
   key namespacing plus declared `SecretRef[]`, not by file location. The actual defect is narrower and
   purely documentary: `CLAUDE.md` names `projects/<slug>/.env`, **a file that has never existed**
   (filed `AT-652`, high, by the peer session). Nothing is or was exposed — `.gitignore:2` is
   `**/.env` and no `.env` appears in the git log across all refs, verified twice independently.
   **`AT-651` does not reduce to this and must not be folded into it:** its mechanism is
   `browser/secrets.py:88-90` `_host_matches`, `host == domain or host.endswith(f".{domain}")`, so the
   suffix match makes `dev-new.vidysea.com` fill-eligible for production `pathlynks` secrets declared
   against `['vidysea.com']`. Moving a file would change nothing. Raised medium → high.

**Result:** The ceiling is recorded and closed to re-litigation. Every project stays `read_only` until
a unit needs otherwise. T-171 is built against per-run `RunApproval` scope, not the tier. T-154/T-155
remain held with Umesh's new condition — *"Pehle proof run ho, phir kholenge"* — which is compatible
with D-052's build-not-fire split, since C4/C5 are not in that split. T-136's comparison artifact gains
the ordering requirement below. The maker's credential-boundary claim is corrected on the record.

**Links:** `qa/gates/write-policy-tier.md` (88ab7638) · D-018 · D-052 · `AT-651` · `AT-652` ·
`AT-653` · T-136 · T-154 · T-155 · T-171 · `schema/crawl.py:41` · `browser/secrets.py:88-90` ·
`core/paths.py:44-51` · `ui/routes_credentials.py:124,153,168`

**Changes-authorized:** none. No `docs/ARCHITECTURE.md` prose change, no `projects/*/project.json`
change, no `CLAUDE.md` change (that file is Umesh's surface; `AT-652` carries the fix request).

### AT-653 — the ordering requirement on T-136, recorded before the artifact is built

Umesh will author the human findings **after** reading AutoTester's report (*"mai humn side ki bnaa krr
de dungaa baad mai"*). A ground-truth list written after seeing the machine's output is anchored to it,
and **the bugs AutoTester MISSED are exactly the ones such a list is least likely to contain.** So
**false-positive rate survives that ordering and recall does not** — an unrecorded ordering yields a
recall number that flatters the machine by construction.

Therefore, whichever fix Umesh picks, T-136's comparison artifact is built with these fields from the
start: an **ordering** field (did the human author before or after reading the report), and, when he
reads first, an **independent-vs-prompted** mark per human item, with **recall computed from the
independent subset only**. This is the same failure shape as the O4 rounding defect — a number whose
provenance is not carried alongside it — so the fields exist before the number does.

## D-054 | 2026-09-27 | type: decision | status: ACTIVE

**What:** Authorize `/checker` to author four new checker-owned DRAFT contract files from the criteria
filed in `qa/feedback-inbox.md` (2026-09-27, `at638-remainder` unit):
`qa/contracts/permission-surface.md` (PS1–PS4, T-171, D-040), `qa/contracts/eval-compiler.md`
(EC1–EC4, T-166, D-041), `qa/contracts/release-regression.md` (RR1–RR5, T-167, D-041),
`qa/contracts/damage-control-report.md` (DC1–DC4, T-168, previously unauthorized by any decision).
Each goes DRAFT → ACTIVE on its own unit's first checker PASS, same as every prior batch.

**Why:** `AT-638` (checker sweep, high) found these four capabilities have **zero checkable contract
criteria**. D-040 and D-041 registered the goal tasks but never named contract files for them, and
**T-168 was never named by any decision at all** despite existing in `.goal/goal.json` since
2026-09-10. A unit with no contract has nothing to be judged against, so the maker-checker pair cannot
build T-166/T-167/T-168/T-171 at all — this one missing authorization gates four tasks.

The governance case is already made and was verified twice. Every checker-authored contract in this
repo — **5 for 5** — was named in a `Changes-authorized` line of an `Approved-by: Umesh` entry *before*
the checker wrote it (D-017/D-018 → `ai-target.md`, `adversarial.md`; D-039 → `catalog.md`; D-040 →
`crawl-traversal.md`, `network-assertions.md`; D-041 → the seven T-172–178 files; D-042 →
`agent-layer.md`). The four now proposed had no such line, and the checker read D-040's and D-041's
`Changes-authorized` text directly (`docs/DECISIONS.md:871-874` and `:923-928`) rather than trusting
the manifest's summary of them. This entry closes that gap the same way D-039/040/041/042 closed it
everywhere else.

**Worth keeping about how this gate arrived:** the build subagent filed 17 criteria, the checker judged
**all 17 sound and buildable as worded** — reproducing every pasted grep and confirming
`schema/portal_persona.py` really can carry the knowledge graph EC1 requires — and the unit still
FAILED cycle 1, on governance alone. Both the subagent and the checker found the missing authorization
independently and **neither wrote a decision entry to manufacture it**, which is the correct refusal:
an authorizing entry needs Umesh's `Approved-by:` and cannot be self-granted. No cycle 2 was spent,
because a fix cycle is for a maker defect and there was none.

**Result:** `AT-638` closes once the four files exist. T-166/T-167/T-168/T-171 become buildable under
the pair. `wave/at638-remainder` can merge and its manifest close out. Carried forward for whoever
authors the files, from the checker's own disclosures rather than found later: **RR2's authority tag is
overstated** — it claims to extend `consent.md` CN5/CN6 but its stated `Verify` only exercises
CN1-shaped behaviour, unlike its named precedent AD2 whose Verify tests CN5's exactness and CN6's
bound-shortfall; so either strengthen RR2's Verify or drop the CN5/CN6 claim. **PS2 is
`[D-040 verbatim]`, not arguable** (the maker's dispatch wrongly called it a free `[maker]` addition);
the genuinely arguable ones are PS4, DC3 and RR3, all reviewed and accepted as low-risk. And the
`at638-remainder` check **did not complete `uv run pytest`** — it ran ruff and doctor live (both clean)
and accepted the diff-stat on the grounds that zero `src/` or `tests/` files were touched. Sound for a
contracts-only unit, disclosed rather than claimed green, and recorded here as an evidence gap.

**Approved-by:** Umesh — approved 2026-09-27, option A of
`qa/gates/at638-four-contract-files-authorization.md` (all four, not the three-file subset).

**Changes-authorized:** the four files named above (new, checker-authored DRAFT). No
`docs/ARCHITECTURE.md` prose change. No amendment to any existing contract.

**Links:** AT-638 · `ISS-at638-remainder-1` · T-166 · T-167 · T-168 · T-171 · D-040 · D-041 · D-042 ·
`qa/verdicts/at638-remainder.md` · `qa/gates/at638-four-contract-files-authorization.md` ·
`qa/feedback-inbox.md` (2026-09-27)

### Not authorized by this entry

T-167's dependency contradiction is **not** settled here. D-042 says T-167 *"runs the lead agent on
LangGraph checkpoints"* (implying a T-179 dependency) while `.goal/goal.json`'s T-167 `deps` is
`["T-166","T-110"]` and `docs/plan.md` row 21 omits T-179 — and the contradiction sits *inside T-167's
own `note` field*, which echoes D-042's sentence next to the deps array that omits it. Umesh's
instruction on 2026-09-27 was to resolve it properly first rather than choose between the two readings,
so it is being investigated against the text and the code, and will carry its own entry. Whoever
authors `release-regression.md` must not encode a dependency stance before that lands.

## D-055 | 2026-09-27 | type: decision | status: ACTIVE

**What:** T-167 (commit/release-triggered visible-browser regression) depends on **T-166 and T-110
only**. It does **not** depend on T-179/T-180 (the Deep Agents layer). `.goal/goal.json`'s
`deps: ["T-166","T-110"]` and `docs/plan.md` row 21 are **correct as written and are not changed**.
D-042's sentence *"T-167 (release regression) runs the lead agent on LangGraph checkpoints"* is
clarified as a statement of eventual **composition**, not a dependency declaration. T-167 is built on
LangGraph 1.x — `stages/orchestrate.py` → checkpointer plus `interrupt()` for consent/review — with no
agent-layer precondition. Whoever authors `qa/contracts/release-regression.md` (authorized by D-054)
encodes **no** T-179 dependency.

**Why:** Umesh's instruction on 2026-09-27 was *"clear kroo properly phle isko"* — resolve it properly
rather than choose between two readings. So it was resolved against the text and the code, and the
evidence runs one way. Five findings, each independently checkable:

1. **D-042 declares dependencies in a column, and T-167 has no row in it.** D-042's "New units" table
   (`docs/DECISIONS.md:953-957`) carries an explicit **"Depends on"** column — T-179 → T-170/T-172/T-175,
   T-180 → T-179, T-181 → T-180. **T-167 does not appear in that table at all.** The disputed sentence
   sits on line 958, *after* the table, paired with *"T-177 (browser-use) becomes one of the runner's
   tools."* Both sentences describe how pre-existing units will compose with the new layer. Reading a
   dependency out of a sentence, when the same decision states every dependency it means in a labelled
   column, inverts the document's own structure.
2. **D-042's own `Changes-authorized` authorizes a NOTE on T-167, not a deps change** (`:967`):
   *".goal/goal.json: register T-179 to T-181, and note on T-167 and T-177."* That line enumerates
   changes precisely enough to name files and fields. Had D-042 intended a new dependency edge, it would
   have authorized one. So `deps: ["T-166","T-110"]` is not stale and was never overwritten — **it is
   exactly what D-042 left standing.**
3. **D-042 supersedes only D-041's point 1, and T-167's LangGraph mandate is a different point.**
   D-042's `Supersedes` (`:960`) replaces *"Agents: typed Pydantic nodes. No multi-agent framework"* and
   states explicitly that *"D-041's other points … remain in force unchanged."* D-041's workflow point
   (`:886`) is separate: *"Workflow: LangGraph 1.x, starting at T-167 (release regression: checkpointer
   and `interrupt()` for consent/review). Existing stages migrate to LangGraph nodes only when a unit
   touches them."* **T-167's LangGraph requirement therefore descends from D-041 and carries no agent
   coupling.** The two decisions are consistent; only the prose at `:958` reads otherwise.
4. **The decisive argument, and it is about falsifiability rather than bookkeeping.** T-181 exists to
   test whether the agent layer earns its place: D-042 says *"The layer stays only if it shows a gain"*
   and *"T-181 must prove a measured gain before the layer is kept."* If T-167 — a release-triggering
   regression capability, `criticality: critical` — depended on T-179, then a **negative T-181 result
   would strip a dependency out from under a shipped capability.** The experiment becomes one nobody can
   act on, because you cannot remove a layer a core capability sits on. So the T-179-dependency reading
   **contradicts D-042's own falsifiability condition.** Keeping T-167 independent is what makes T-181 a
   real experiment instead of a formality.
5. **No implementation fact contradicts any of this, because neither layer is built.** `langgraph` and
   `deepagents` are both absent from `pyproject.toml` (grep empty), and no file under `src/autotester/`
   references `deepagents` or `create_deep_agent` (grep empty) — consistent with D-041/D-042, which
   admit each dependency only inside its own unit. `docs/plan.md` row 21 describes T-167 as
   `stages/orchestrate.py` → LangGraph 1.x, *"a release trigger runs the approved suite; consent via
   `interrupt()`; resumes after a crash"* — no agent.

**Result:** The contradiction is closed in favour of the backlog, not the prose. T-167 is buildable as
soon as T-166 lands, without waiting for the agent layer — which matters, because T-166 is itself gated
behind T-125 and adding an agent-layer edge would have pushed a critical capability behind an experiment
that may be removed. `release-regression.md` is authored with no T-179 dependency. When the agent layer
exists **and** T-181 proves a gain, the lead tester may run **on** T-167's checkpoints; that is a later
composition implemented inside T-179/T-180 and requires no change to T-167.

**Remaining defect this entry cannot fix, disclosed rather than left implicit:** the misleading sentence
is echoed **inside T-167's own `note` field** in `.goal/goal.json`, sitting next to the deps array it
appears to contradict — which is why two readings survived. Correcting that note is a `.goal/goal.json`
edit, and this maker's writes to that file are currently refused by the harness safety classifier (the
same block that holds the T-122/T-145/T-136 Pathlynks re-scope). **This entry is now the authority; the
note is stale prose, not a competing dependency claim.** The note correction is queued with Umesh
alongside the re-scope.

**Links:** T-110 · T-125 · T-166 · T-167 · T-177 · T-179 · T-180 · T-181 · D-041 (`:886`, `:923-928`) ·
D-042 (`:936-976`, especially the units table `:953-957`, the composition sentence `:958`, the
supersedes clause `:960` and `Changes-authorized` `:967`) · D-054 ·
`qa/gates/at638-four-contract-files-authorization.md` · `docs/plan.md` row 21 · `qa/contracts/consent.md`

**Changes-authorized:** none. No `docs/ARCHITECTURE.md` prose change, no `.goal/goal.json` change (the
deps array is already correct; the stale note is queued separately), no contract amendment. This entry
is a clarification of two existing decisions, and it creates no new scope.

## D-056 | 2026-09-28 | type: decision | status: ACTIVE

**What:** Waive the D-014 round cap ONCE for the `qa/hooks/mc-sessionstart.ps1` seam, authorizing a
single bounded cycle 2 of unit `at673-sessionstart-unclosed-detector` with exactly this scope and
nothing beyond it: AT-713 (read the MAXIMUM cycle field, not the last one), AT-714 (drop the
bare-whitespace alternative from the cycle boundary, keeping the heading-prefix allowance), and
AT-715 (make the new test module's docstring raw). Cycle 1 as built and checked stands; round 4 is
accepted. After cycle 2 PASSes the seam is closed again and any further visit needs a new waiver.
This entry also retroactively supplies the authorization the cycle-1 code landed ahead of, which the
manifest disclosed in writing at the time rather than landing silently.

**Why:** The seam has 3 prior PASSes (`at097-session-start-hook-regression`,
`at383-sessionstart-loop-status`, `t005-living-ledger`) against a non-security cap of 2, and this
unit is the 4th visit. The maker escalated rather than argued past the cap, correctly declining both
available escapes: it is an enforcement path, which is adjacent to the security class and not in it,
and stretching the one into the other is the rationalisation the cap exists to stop.

The evidence argues for the cap rather than against it, which is why the waiver is bounded to three
named rows instead of reopening the file. Inside this single unit the seam produced four defects:
two of the maker's own, caught by measuring (an anchored `^## Status:` read that would have silently
skipped ~37 of 263 manifests; a `Fix cycle` pattern that broke on `**Fix cycle:** 2`), plus the
checker's AT-713 and AT-714.

What makes the fix worth spending a waiver on rather than filing as debt: AT-713 and AT-714 resolve
to ONE change, and it is a correctness change, not a tightening. Cycle numbers only ever increase,
so reading the MAXIMUM is correct under both orderings, while last-wins is correct only under the
manifest ordering. LS6 is a rule about manifests and was applied to verdicts, which order their
history the opposite way — measured over all 280 verdicts, 40 carry multiple cycle values, 39
ascend and exactly one descends. Under max the bare-whitespace boundary becomes actively harmful
rather than merely possible, so both rows land in the same cycle by necessity.

Cycle 1 is a real fix and the waiver preserves it: the old phrase read flagged `t182-viewport-locale`
(whose manifest merely keeps superseded history) and MISSED `at483-orphaned-running-crawl` (a genuine
cycle-2 PASS never flipped). The headline count stayed 1 across the fix while the set inverted, which
is why no capability row asserts a count. Option C (revert) would return the hook to that state
permanently.

**Result:** Cycle 2 authorized with the three-row scope above. Not authorized by this entry: any other
change to `qa/hooks/mc-sessionstart.ps1`, and the separate question of whether `W` joins the ruff
select list (AT-715's second half), which stays a contract question for the checker.

**Changes-authorized:** `qa/hooks/mc-sessionstart.ps1` (enforcement path) — `Get-CycleNumber` only,
for the max-over-last read and the boundary tightening; `tests/test_mc_sessionstart_unclosed.py`
docstring.

**Approved-by:** Umesh

**Links:** AT-673 · AT-713 · AT-714 · AT-715 · T-673 · `qa/gates/at673-round-cap.md` (answered
2026-09-28, option B) · `qa/gates/at673-sessionstart-unclosed-detector.md` (answered 2026-09-28,
option A) · `qa/verdicts/at673-sessionstart-unclosed-detector.md` (cycle 1 PASS) ·
`qa/contracts/loop-status.md` LS6 · `qa/contracts/core-invariants.md` C12 · D-014

## D-057 | 2026-09-29 | type: decision | status: ACTIVE

**What:** Umesh answered three open questions on 2026-09-29. This entry records all three before
anything acts on them.

1. **`qa/gates/new-module-authorization.md` → A.** Create `src/autotester/ledger/citations.py`
   (plus its own test module) to hold `check_decision_citations` for **AT-710 only**. The
   standing-rule variant ("any future check may take a new module") was **not** chosen, so AT-697
   and later checks meet this gate again on their own merits.
2. **`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` → A, "order only, never skip".** `catalog.md` CT6
   is narrowed from *stop before an empty tier* to *dispatch cases in cheap-to-expensive tier order
   and report each tier's runnable count*. `ui-run.md` RU3 (run every case on file) and F-058 (a
   pinned case runs every time) stay intact. `stages/catalog.py::tiers_to_run()` is wired into the
   run trigger as an ordering helper, never as a filter.
3. **T-167 deps gain T-179.** They become `["T-166","T-110","T-179"]`, matching D-042's statement
   that T-167 "runs the lead agent on LangGraph checkpoints". This settles the contradiction that
   D-054 explicitly left unsettled.

**Why:**
- *(1)* The implementation is built and falsified (held in `.work/at710/`). Every conceptual home is
  at or near the 300-line cap: `ledger/checks.py` 288, `doctor.py` 279, `render.py` 300,
  `tests/test_doctor.py` 300. Two independent build subagents stopped at this gate instead of
  granting themselves the exception, which is the behaviour the design rules want.
- *(2)* Honouring the old CT6 would filter which cases execute. That breaks RU3 and would let a
  pinned regression case be skipped, which is the one guarantee F-058 exists to make. Ordering keeps
  CT6's intent (cheap structural failures show first) without skipping anything.
- *(3)* The deps array contradicted the task's own note and D-042.

**Result:** AT-710 leaves HUMAN_GATE and returns to build. T-125 can reach CT6 PASS on the narrowed
criterion. `.goal/goal.json` T-167 deps and `docs/plan.md` T-167 row are corrected.

**Changes-authorized:**
- new `src/autotester/ledger/citations.py` and its test module (AT-710 only);
- `qa/contracts/catalog.md` CT6 wording (checker-authored amendment to ordering + reporting);
- `ui/routes_runs.py::trigger_run` calls `tiers_to_run()` for ordering only;
- `.goal/goal.json` T-167 `deps`, and `docs/plan.md` T-167 row.

No `docs/ARCHITECTURE.md` prose change. No enforcement-path change.

**Approved-by:** Umesh. Answers given 2026-09-29 via AskUserQuestion in session autotesting-23, then
re-confirmed directly to the maker session the same day ("Yes, all three").

**Links:** AT-710 · AT-697 · T-125 · ISS-t125-1 · T-167 · T-179 · F-058 · D-042 · D-054 ·
`qa/gates/new-module-authorization.md` · `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` ·
`qa/contracts/catalog.md` CT6 · `qa/contracts/ui-run.md` RU3

## D-058 | 2026-09-29 | type: decision | status: ACTIVE

**Supersedes:** D-057 -- D-057's point 3 added T-179 to T-167's deps and reversed ACTIVE D-055 without
flagging it, which the Lab Protocol forbids. That question was put to Umesh in session autotesting-23
without D-055 in view, and the maker recorded the answer without checking the decision index. This
entry is better because it restates D-057's two sound answers unchanged, withdraws point 3 on Umesh's
informed answer, and records the at673 scope decision.

**What:**
1. **AT-710 new module (restated from D-057, unchanged).** Create `src/autotester/ledger/citations.py`
   and its test module to hold `check_decision_citations`, for AT-710 only. The standing-rule variant
   was not chosen.
2. **CT6 order-only (restated from D-057, unchanged).** `catalog.md` CT6 is narrowed to: dispatch
   cases in cheap-to-expensive tier order and report each tier's runnable count, never skipping a case.
   `ui-run.md` RU3 and F-058 stay intact. `tiers_to_run()` orders and never filters. The checker's
   amendment made under D-057 (sweep 98f8365a) stands under this entry.
3. **T-167 deps: D-055 stands.** T-167 depends on `["T-166","T-110"]` only. Today's T-179 edit is
   reverted in three places: `.goal/goal.json`, `docs/plan.md` row 21 and
   `tests/test_goal_contract_registration.py:50`.
4. **at673 cycle 3: revert the strip.** Cycle 3 removes the per-line inline-code strip at
   `qa/hooks/mc-sessionstart.ps1:77`, and its test, from unit `at673-sessionstart-unclosed-detector`.
   The strip was a fourth change that D-056 did not authorize (cycle-2 verdict FAIL on scope, AT-741).
   With cycle 3 the unit is back to exactly D-056's three rows. Nothing else on this seam changes.

**Why:**
- **(3)** The maker explained both options plainly, and Umesh chose Option 1 knowing what each costs.
  If T-167, the critical release safety net, sat on T-179's agent layer, a negative T-181 result
  ("the layer must show a measured gain to stay", D-042) could never be acted on. The experiment would
  become a formality.
- **(4)** The checker measured three things:
  - The strip's premise does not reproduce. The quoted-heading misread it targets pre-dates cycle 2.
  - The strip adds a fail-open regression. The AT-722 odd-backtick line read -1 under cycle 1 and
    reads 42 now.
  - With the strip removed, the AT-713 and AT-714 tests still pass.
  Removing it is safer than ratifying it.

**Result:** AT-710 is buildable and T-125's CT6 is passable, both as under D-057. T-167 is back to
D-055. at673 goes to fix cycle 3, bounded to the removal. The seam closes again after cycle 3 PASSes.

**AT-740 note:** gate files that pre-reserved "D-057 (NOT YET WRITTEN)" for the write-policy decision
now point at spent numbers. Those citations are repointed to "the write-policy decision (not yet
written; number assigned when written)". Numbers are never reserved ahead of writing again.

**Changes-authorized:**
- `.goal/goal.json` T-167 `deps`;
- `docs/plan.md` row 21;
- `tests/test_goal_contract_registration.py:50`;
- `qa/hooks/mc-sessionstart.ps1` (enforcement path), removal of the `:77` inline-code strip only, plus
  removal of its test;
- the `D-057 (NOT YET WRITTEN)` citations in `qa/gates/write-policy-tier.md`,
  `qa/gates/pathlynks-user-account-first.md` and `qa/gates/at654-d029-dev-only-vs-production-pathlynks.md`,
  wording only.

No `docs/ARCHITECTURE.md` prose change.

**Approved-by:** Umesh. Recorded 2026-09-29 from two AskUserQuestion answers in the maker session:
"A: Revert it" for at673, and "Option 1: No, keep D-055" for T-167.

**Links:** D-055 · D-056 · D-057 · D-042 · AT-710 · AT-740 · AT-741 · AT-722 · ISS-t171-3 · AT-743 ·
T-125 · T-167 · T-179 · T-181 · `qa/gates/at673-cycle2-scope.md` ·
`qa/verdicts/at673-sessionstart-unclosed-detector.md` (cycle 2 FAIL)

## D-059 | 2026-09-30 | type: decision | status: ACTIVE

**What:**
1. **T-168 drops its dependency on T-155.** T-168 (damage-control report) ships without the AI-test
   section. That section is added when Track C is released. `.goal/goal.json` T-168 `deps` become
   `["T-164","T-165","T-167"]`. `docs/plan.md` row 26 already omits T-155 and is unchanged. T-154 and
   T-155 stay HELD.
2. **This maker session is the single maker** and drives the remaining wave plan. The checker seat
   (a separate session) stays checker-only and takes over only if the maker session dies.

**Why:** Track C is held on `qa/gates/write-policy-tier.md` and per-run approvals, and T-168 sat behind
T-155 as a result. The report is useful without the AI-test section, and its `blocked/unvisited is never
rendered as pass` guarantee does not need it. Deferring the section removes a hold-induced block without
weakening the report.

**Result:** T-168 depends on T-167 (and, through it, T-166). It is no longer gated on Track C.
`qa/contracts/damage-control-report.md` line 8 ("Depends on T-155, T-164, T-165, T-167") is checker-owned
and needs the matching amendment. The maker files it through `qa/feedback-inbox.md` and does not edit the
contract.

**Not adopted by this entry:** the relayed wave plan (autotesting-23, 2026-09-29) lists T-167 as needing
T-179. D-058 stands. T-167's deps remain `["T-166","T-110"]`, per D-055.

**Changes-authorized:**
- `.goal/goal.json` T-168 `deps`;
- `tests/test_goal_contract_registration.py:51` pin;
- `qa/contracts/damage-control-report.md` line 8 (checker-authored amendment).

No `docs/ARCHITECTURE.md` prose change. No enforcement-path change.

**Approved-by:** Umesh — decision relayed by session autotesting-23 as his answer of 2026-09-29
("Drop T-155 dep (Recommended)"), and confirmed to the maker session on 2026-09-30 by the session's
user, whose account shows abhinav@vidysea.com. That the confirming user is the Approver is not
established from the session alone. Umesh should ratify or reverse this at his next review.

**Links:** T-168 · T-155 · T-154 · T-167 · T-166 · D-055 · D-058 · `qa/gates/write-policy-tier.md` ·
`qa/contracts/damage-control-report.md`

## D-060 | 2026-09-30 | type: decision | status: ACTIVE

**What:**
1. **L9's wrong-subject bullet is split out into a new criterion L10.** `qa/contracts/living-ledger.md`
   L9 ("Resolution is necessary and not sufficient -- the SUBJECT must match too") moves, verbatim,
   into L10 "a citing line's claimed subject must match the cited entry's What:". L9 keeps a one-line
   pointer to L10 and its Verify clause stops requiring the moved bullet. Every other L9 sub-clause is
   unchanged. AT-710 (unit `at710-decision-citation-resolver`, branch `wave/at710-citations`) therefore
   closes against L9's own Verify clause. The subject-match check becomes its own later unit.
2. **`qa/contracts/damage-control-report.md` line 8 is brought in line with D-059.** "Depends on T-155,
   T-164, T-165, T-167" becomes "Depends on T-164, T-165, T-167".

**Why:**
- *(1)* This is the checker's choice of option (a) for ISS-at710-1 (at710 cycle 1 FAIL, verdict
  b385910f). The resolver already yields 0 dangling citations on the tree and 9 of 9 capability rows
  reproduce; the only unbuilt part is the wrong-subject bullet. L9 itself says a non-claiming occurrence
  is "declared, not inferred", and no machine-readable declared form for a citation's claim exists, so
  the bullet has no buildable shape yet. Option (b) (a fuzzy `cites-for: D-NNN - <subject>` marker
  checked by keyword overlap with the entry's What:) would add a matcher whose false-positive rate is
  unmeasured. This weakens nothing: the obligation is preserved verbatim in L10; it stops blocking at710
  and is owned by a later unit that first defines the declarable form.
- *(2)* D-059 already dropped T-155 from T-168's deps and named this line in its Changes-authorized. The
  maker filed the ask through `qa/feedback-inbox.md`; the checker owns the contract and makes the edit.

**Result:** at710 can close against L9's Verify clause. L10 is recorded as "not yet buildable: needs a
declarable form for the claim; own unit". The damage-control contract and `.goal/goal.json` T-168 deps
agree again.

**Changes-authorized:**
- `qa/contracts/living-ledger.md` L9 (wrong-subject bullet moved out) + new criterion L10 + Amendment
  log (this entry);
- `qa/contracts/damage-control-report.md` line 8 (Depends-on line brought in line with D-059).

No `docs/ARCHITECTURE.md` prose change. No enforcement-path file touched.

**Links:** AT-710 - ISS-at710-1 - b385910f - D-057 - D-058 - D-059 - T-168

## D-061 | 2026-09-30 | type: fix | status: ACTIVE

**What:** Reopen AT-113 and T-165 completion acceptance after independent executable evidence
proved that an abandoned seed still reports completed/frontier empty/success=true. Repair the
existing runtime, legacy display and persona deletion-evidence seams under the reviewed plan.

**Why:** The user's whole-portal breadth-first tester must distinguish exhausted actionable
frontier from a queue drained after failed visits. Otherwise reports hide incomplete testing
and stored learning may invent regressions. Preserve useful partial exploration and siblings,
login precedence, actual named bounds, credential scoping and existing safety policy.

**Result:** Independent real run_crawl fixture reproduced completed/0 actions/one aborted_error/
success=true/issues=1; the actual fresh Pathlynks crawl agrees. Existing targeted baseline is
32 passed, showing the missing assertion. T-165 reopened; isolated codex/at113-crawl-completion
worktree created. Revised preimplementation plan explicitly approved by a fresh independent
reviewer. Implementation, mutation evidence, headed browser validation and dual PASS remain
pending; this entry is not a release or whole-goal completion claim.

**Changes-authorized:** Existing source/tests named in .work/at113-completion-plan.md; .goal/goal.json
T-165 status and resolution note. No architecture prose, schema, contract or enforcement change.

**Links:** AT-113; T-165; T-145; qa/verdicts/sweep-2026-09-30-crawl-recovery.md;
qa/evidence/sweep-2026-09-30-crawl-probe.py; .work/at113-completion-plan.md.

## D-062 | 2026-10-06 | type: decision | status: ACTIVE

**What:** Define T-196 L10's declarable citation claim as a visible bounded
quotation from the cited decision's What section, with an equivalent strict
JSON decision-claim marker. Require independently reviewed complete occurrence
coverage; optional markers beside unrestricted authorization prose are insufficient.

**Why:** D-060 deferred the form and rejected unmeasured keyword matching.
Independent review found that a correct but irrelevant quotation could hide a
wrong surrounding claim. Exact attribution plus coverage closes that loophole
without pretending that textual matching proves operational authorization.

**Result:** Authorizes checker-owned contract adoption only, not product PASS.
Canonical form: `Decision claim D-001: "Exact quotation from What" <!-- decision-claim: {"id":"D-001","what":"Exact quotation from What"} -->`.
Require same-line visible/JSON agreement, strict id/what fields, nonempty
case-sensitive contiguous What quotation with whitespace-only normalization.
Reject detached/malformed/conflicting markers and ambiguous decision bodies.
Archive full entries may supply What; index summaries alone are unavailable.
Preserve L9 foreign-entry and reasoned per-occurrence exemptions.
Coverage reviews bind path, exact text, cited id and multiplicity; changes
invalidate review. Independently classify every occurrence in the existing five
globs, migrate mutable authorization claims, and record attributable historical
reviews without rewriting immutable decision history. Unknown/disputed claims
remain reported; ordinary-reference classifications require reasons/attribution.
Added unclassified resolving claims must fail coverage even when L9 passes.
Known wrong-subject examples remain test oracles; do not restore historical
incorrect citations currently replaced by WP-DECISION placeholders.
Keep T-196 critical; new feature uses active .3 tier L and dual final checks.
No historical generic human-required alert substitutes for an explicit gate;
the task's HUMAN-free-on-form condition applies once the form is adopted.

**Changes-authorized:** qa/contracts/living-ledger.md L10 and its amendment log,
checker-owned only. No L9 weakening, source/schema/enforcement/architecture edits,
goal completion, runtime launch, production write, or release authorized here.

**Links:** D-060; T-196; AT-710; AT-718; ISS-at710-1;
qa/feedback-inbox.md (2026-10-06 design and independent coverage challenge).

## D-063 | 2026-10-06 | type: decision | status: ACTIVE

**What:** Adopt the account-derived authorization answer already given by Umesh
for the Pathlynks USER run: provisioned declared credentials, exact target and
allowed domains permit a newly derived signed LIVE_CASE grant. System bounds
are positive finite operational brakes, not quantities a human must guess.

**Why:** qa/gates/at674-approval-key-and-live-case-grant.md's Answer rejected
manual count/key entry, but consent.md still excludes every auto-granting path.
That mismatch must be resolved explicitly before implementation, not bypassed.
Maintain unconditional verification and never sign or rescue loaded approval rows.

**Result:** Authorizes checker-owned contract reconciliation and independently
approved implementation in existing seams. Preserve exact project/kind/target,
expiry, positive operational bounds, signatures and pre-action fail-closed checks.
Only credentials actually referenced by the requested case set are preconditions;
unused COUNSELLOR keys are not a USER-run gate. Credential substitution remains
per-reference host-scoped at page.fill; no value enters a model/log/artifact.

First-use key provisioning is an explicit preparation operation called by the
authorized grant path, never by import/load/signature verification. Generate a
random key only if none exists, preserve process overrides and stored keys,
use the existing owner-only atomic env writer with serialized create-if-absent,
and fail closed if signed historical state has lost its verification key.
Keep legacy approvals unchanged. Derive grants only from validated current
account/target/scope inputs; no wildcard, cross-project or adversarial auto-grant.

Use one aggregate RunBudget across serial, entry and parallel case execution.
Report any stopped/truncated run and its named operational brake, never as
completed E2E. Recorded actions/evidence must be redacted; secret prior values
are never copied into an audit log. Explicit human FlowSpec review, adversarial
authorization, production promotion and model-spend gates are not removed.

**Changes-authorized:** qa/contracts/consent.md purpose, auto-grant exclusion,
new account-derived LIVE_CASE criterion and amendment log, checker-owned only;
approved subsequent existing core consent/id, env writer, CLI grant-default,
UI run/preflight, shared budget/executor and existing test seams. No enforcement
path edits, new product module, blanket live-account writes or paid model run.
Existing architecture prose remains unchanged unless separately authorized.

**Approved-by:** Umesh — AT-674 direct Answer and 2026-10-06 instruction to continue
with existing approvals; exact decision-entry file creation separately approved.

**Links:** T-122; AT-674; AT-570; AT-651; D-018;
qa/gates/pathlynks-user-account-first.md;
qa/gates/at674-approval-key-and-live-case-grant.md;
qa/contracts/consent.md CN1-CN10; qa/contracts/core-invariants.md C5/C12;
qa/manifests/pathlynks-exact-host.md.

## D-064 | 2026-10-06 | type: session | status: ACTIVE

**What:** Record the bounded T-196 build checkpoint: independently reviewed
citation inventory adoption, exact existing-file claim migrations and corrected
foreign/doctor acceptance fixtures. This is a progress record, not task closure.

**Why:** Real-tree attribution and causal test evidence must remain distinct from
fixture green, and a cloud-feasibility discussion must not imply migration.

**Result:** The corrected citation test file passed all 61 tests in 19.15s on
SHA256 FDE194E9512684B270AC93F2CF41F34E06EB0422D0AAE5ABC0610226E3C4FDEC.
Two current isolated foreign-exemption/doctor-caller proofs reached named assertions
and restored byte-identically. At this recorded checkpoint, 721 independently
reviewed rows were adopted; the earlier 613-row root binding check had zero errors.
Remaining decision bodies and other five-glob records are not certified covered.
Two gate claim migrations preserve original scope. Historical field/subject
conflicts need an owner reconciliation choice, asked once; no exemption implemented.
Latest measured free RAM666936KiB does not satisfy the existing4GiB acceptance
headroom. No full suite, final checker verdict, browser/account/provider call,
product PASS, new commit, push, deployment or cloud migration occurred.
The objective remains58done/24pending. Verification/persistence gate is unpassed.

**Changes-authorized:** none. No contract, architecture or enforcement change;
no historical-disposition exception or retrospective operational permission.

**Links:** T-196; qa/manifests/t196-citation-subject-check.md;
qa/feedback-inbox.md (checkpoints D/E/F and independently approved fixture/gate plans);
tests/test_citations.py; .goal/goal.json.

## D-065 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Authorize three additions made by the T-151 target-discovery build that D-017 did not name:
(1) the runtime dependency `pyyaml==6.0.3` in pyproject; (2) the new target-discovery prompt file;
(3) the `act` hunk in `src/autotester/providers/mock.py`.

**Why:** Umesh approved all three (gate answer "T-151: A"). PyYAML is a widely used, pinned dependency;
the prompt is a file, as the design rules require; the mock hunk keeps the deterministic test provider
in step with the provider interface. Rejected alternative: stdlib-only parsing (option B).

**Result:** Gate answered; T-151 build may continue on branch codex/t151-target-discovery to
ready-for-check. No code changed by this entry.

**Changes-authorized:** pyproject.toml / uv.lock (add pyyaml==6.0.3) · the T-151 target-discovery
prompt file under prompts/ · src/autotester/providers/mock.py `act` hunk. Nothing else; T-151 still
reaches PASS only through /checker.

**Approved-by:** Umesh — chat answer 2026-10-07 ("A: Teeno approve"), recorded in
qa/gates/t151-dependency-authorization.md.

**Links:** T-151; D-017; qa/gates/t151-dependency-authorization.md; qa/verdicts/t151-plan-approval.md.

## D-066 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Two gate answers from Umesh. (1) T-196: L10 gains a sealed-record disposition for immutable
history (gate t196-l10-coverage, option B). (2) D-063 self-grant: add an Origin/CSRF check on the
state-changing UI routes (credential edits and run triggers) (gate d063-self-grant-csrf, option B);
role-based authentication is deferred to a later unit.

**Why:** (1) "logic badalte rehte hai, product evolve hota hai, purane ka acha part rakh kar later
update kar sakte hai." Reviewing ~1200 occurrences in closed records one by one (option A) costs a
lot and adds little; a hash-bound, self-invalidating seal keeps the rule strict for anything new or
changed. (2) The CSRF check is a small change that closes the cross-site POST hole. Umesh noted the UI
will run on a server URL after go-live, not localhost, so real auth is a required follow-up, not optional.

**Result:** L10 amended by /checker on wave/t196-citation-subjects (2749e38d). The two disputed
historical claims K1 (DECISIONS.md:80) and K2 (DECISIONS.md:209) remain open pending Umesh's ruling and
are tracked as ISS-t196-citation-subjects-k1k2. The CSRF fix is not yet built; it rides the next
d063-grant-budget fix cycle.

**Changes-authorized:** qa/contracts/living-ledger.md L10 (sealed-record disposition, as committed in
2749e38d) · src/autotester/ui/ state-changing routes (Origin/CSRF check) on the d063-grant-budget branch.

**Approved-by:** Umesh — chat answers 2026-10-07, recorded in qa/gates/t196-l10-coverage.md and
qa/gates/d063-self-grant-csrf.md.

**Links:** T-196; D-062; D-063; D-064; qa/gates/t196-l10-coverage.md; qa/gates/d063-self-grant-csrf.md.

## D-067 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Group 10 "Team loop" is added at top priority, ahead of groups 5–9 of the 2026-10-05
nine-batch plan. It has five tasks: T-197 video INGEST with human timestamp-pointers and a confirm-list,
T-198 developer video intake (zip upload and Drive fetch), T-199 a bug loop into the PathLynks
Tracker sheet (file, update, close), T-200 scheduled auto-test at a configurable frequency, and T-201
a team on-demand Test button with the report sent to the person who clicked. Developer demo videos
are a first-class teaching source for the flow model and the future knowledge graph (T-166).

**Why:** Umesh said on 2026-10-07 that the team is waiting on this ("team wait kar rahi hai bahut
zor se"). In the 2026-10-06 meeting the CEO described his own video-review skill: approximate
timestamps plus 2–3 pointers in, then a summary and 4–5 checks out. It cut a 3 h review to about
30 min. His review of Navnit's three partner-portal videos (Drive doc 1FjABvhH…) is the target
output shape and a ready human oracle. Developers who explain "how it is built and what it is for"
on video give AutoTester the intended flow up front, instead of only what a crawl can infer.

**Result:** goal.json now has 87 tasks, 28 pending: 23 of the original 24 plus these 5. All 9 old
groups are still open; only T-185 has closed since 2026-10-05. Navnit's three videos (17:46, 33:33,
16:18) were downloaded through gws, size-verified and registered as pathlynks sources
src_e8fcdc4a15ce, src_44e2f1f6c64c and src_8540cc84081e. Himanshu's promised video had not arrived
when this was written. Each new task still passes the maker PLAN gate before any code.

**Changes-authorized:** .goal/goal.json (append T-197..T-201). No contract or ARCHITECTURE change;
the PLAN gate authorizes those later.

**Approved-by:** Umesh — chat answer 2026-10-07 ("New tasks, top priority").

**Links:** T-197; T-198; T-199; T-200; T-201; T-166; AT-570; .work/pathlynks-dev-videos-oracle-2026-10-07.md.

## D-068 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Three gate answers from Umesh. (1) cn5 (gate d063-cn5-vs-cn11): provisioned credentials are
the run approval. When a project declares a credential pair in its SecretRef[], a run against that
project's declared target and allowed_domains proceeds with no per-run human approval, for every run
kind (live case and crawl/explore). An account-derived approval row may cover any (project, run_kind,
target) match (option B). Approval rows are still minted and HMAC-signed automatically, as an audit
record, not as a human step. (2) t196 disputed claims K1 (DECISIONS.md:80) and K2 (DECISIONS.md:209):
an independent second confirmation runs first; then the record is corrected (option i). Umesh allows
old entries to be changed or removed if that is needed; a correcting entry is the first route, and a
direct edit to an old entry would still need its own entry with Approved-by, since the append-only
hook stays. (3) Build order: all open groups run in parallel, scheduled only by real dependencies
(the agent layer waits for the stages it wraps).

**Why:** (1) "credentials de dena sabse bada approval hai" -- the account Umesh provisions already is
the scope (D-053, qa/gates/write-policy-tier.md); repeated per-run approvals add a human step with
no added safety. The test-account-only rule and the allowed_domains scope are unchanged. (2) "2nd
confirmation le lo aur sabhi update kar do". (3) "parallelly all".

**Result:** d063-grant-budget's next fix cycle drops the CN5 exclusion and keeps the D-066
Origin/CSRF check. T-145 no longer needs a per-run human approval. No code changed by this entry.

**Changes-authorized:** the qa/contracts rows holding CN5/CN11 and the explore pre-crawl approval
criterion (checker-owned amendment) · src/autotester/core/consent.py and
src/autotester/stages/explore_consent.py (credential-derived approval for every run kind) ·
.goal/goal.json T-145 note (drop "per-run RunApproval required").

**Approved-by:** Umesh — chat answers 2026-10-07, recorded in qa/gates/d063-cn5-vs-cn11.md and
qa/gates/t196-l10-coverage.md.

**Links:** T-145; T-196; D-018; D-053; D-063; D-066; qa/gates/d063-cn5-vs-cn11.md; qa/gates/t196-l10-coverage.md.

## D-069 | 2026-10-07 | type: fix | status: ACTIVE

**What:** Correct two historical citation claims, K1 and K2, without editing the old entries.
K1 (D-006, DECISIONS.md:80): D-006 cites D-000 `Changes-authorized` for the append_decision.ps1
UTF-8 fix. D-000 authorizes `scripts/append_decision.ps1` only at the file level, as enforcement
wiring, and never names the UTF-8 fix. The fix was verified by /checker in the T-005 cycle-1 check
(qa/feedback-inbox.md:111) and shipped in 2785312d. The authorization holds at the file level; the
specific claim is imprecise. K2 (D-014, DECISIONS.md:209): D-014 item (1) attributes BACK to D-005.
D-005 approved only HOVER, PRESS_KEY and SCROLL (DECISIONS.md:74). BACK is an additive amendment
first authorized by D-014 itself (Approved-by: Umesh, plan.md section 4, plan.md:204). It was verified
in qa/verdicts/track-b1-observation-primitives.md:117-120 and shipped in ce1b624b. The docstring at
src/autotester/schema/enums.py:26 repeats the wrong "discharge D-005" attribution.

**Why:** Umesh's ruling on the T-196 disputed claims (option i, after a second confirmation):
"2nd confirmation le loo aur sabhi update krr doo". An independent second review confirmed both
findings. A correcting entry fixes the record without breaking the append-only history. Editing
D-006 and D-014 in place was not needed.

**Result:** K1 and K2 now have a recorded disposition: both changes stand as authorized, and the
attribution is corrected here. T-196 may treat ISS-t196-citation-subjects-k1k2 as resolvable once
/checker records the disposition. The enums.py:26 docstring fix rides the next unit touching that file.

**Changes-authorized:** src/autotester/schema/enums.py:26 docstring wording (BACK attributed to
D-014, not D-005). Nothing else.

**Approved-by:** Umesh — chat answer 2026-10-07, recorded in qa/gates/t196-l10-coverage.md.

**Links:** T-196; D-000; D-005; D-006; D-014; D-068; ISS-t196-citation-subjects-k1k2; qa/gates/t196-l10-coverage.md.

## D-070 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Umesh answered the open runtime gate and set direction for the video and team-loop work. Five parts:
1. **Browser/full-suite runtime: option A, generalized.** AutoTester runs a local visible browser and the
   full suite directly on whatever machine it is installed on. The native-egress sandbox precondition
   recorded in `qa/gates/t125-fullsuite-browser-egress.md` and `qa/gates/t125-stalled-at-cycle-cap.md`
   is dropped. The target is never Pathlynks-specific: any product given by URL plus the credentials
   supplied for it (the boundary stays the supplied account's own rights, D-053/D-068). The test suite
   keeps its own guards: no real credentials or `.env` values in tests, no paid model calls from tests,
   and no external network from unit tests.
2. **Video flows are reconciled by the system, not approved by a human.** There is no human-approval
   dependency for video-derived flows. Each video yields its own knowledge graph: screens, actions, and
   the flow the narrator says they are doing (speech is evidence of intent). It is re-mapped onto the
   product knowledge graph built by the crawl. Every flow is kept: the ideal flow, each narrated flow
   and each variant. Reports highlight where a video's path differs from the crawled or ideal one, as
   an "another possibility" view for developers. The FlowSpec DRAFT review gate remains as a status
   only, and it never blocks case generation from reconciled flows. Contract changes come through the
   checker's inbox fold-in.
3. **Group 10 scope widens to an in-product developer portal (T-198, being grilled).**
   - Accounts with a role hierarchy that follows the company structure (CEO, developer, tester, admin,
     sub-admin…).
   - Users are mapped to projects. A developer uploads a video inside their project, and gets a
     shareable URL to send by mail. Viewers with access watch it; others request access.
   - Viewers leave timestamped comments on the video, Udemy-style, visible to everyone with access.
   - The details come from the grill that is in progress.
4. **Parked, must-have:** an in-product tracker with auto-validation, plus a Test button anyone can
   press for a real-time run. Re-runs update the ledger and the tracker, log new issues and close fixed
   ones. Optional sync to the team's Google/Excel sheet comes later (T-199 becomes the in-product
   tracker first, sheet sync second).
5. **Push:** everything built and validated (checker PASS) is committed and pushed. This restates D-007
   and applies to the maker's own close-out merges as well.

**Why:** In Umesh's words (chat, 2026-10-07): "Not only path links, but any of the account or website which
is provided with the help of the URL ... along with the user credentials"; "it can run in any of the
machine just via the browser"; "Don't make any human dependency ... the system should be intelligent
enough"; "we can have like either n number of flows, but we have understanding of each and every
flow"; "park it that it is a must and we must need to add"; "jo jo build hokrr validate hota jaa rha hai
commit and push". The sandbox path had been BLOCKED-CAPABILITY since 2026-10-05 with no end in sight,
and it held most of groups 3, 4, 6 and 7.

**Result:** T-125 and T-165 (AT-113 cycle 4) are unblocked for runtime: the gate files carry
`Answered: 2026-10-07` lines. The three Navnit videos already give a 38-screen, 4-flow DRAFT, which is
now an input to the video-KG → product-KG reconciliation and not something waiting on a human. The
group-10 grill continues with the developer-portal scope. The tracker loop is parked as a must-have.

**Changes-authorized:** `qa/gates/t125-fullsuite-browser-egress.md`, `qa/gates/t125-stalled-at-cycle-cap.md`
(Answered lines); `qa/feedback-inbox.md` (verbatim answers for the checker fold-in); `.goal/goal.json`
(T-166 note, T-197..T-201 notes). No contract or ARCHITECTURE text is changed by this entry: those are
folded in by `/checker`.

**Approved-by:** Umesh — chat 2026-10-07 (answers to the five asks).

**Links:** T-125; T-165; T-166; T-197; T-198; T-199; T-200; T-201; D-007; D-053; D-067; D-068; AT-113.

## D-071 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Gate answers and go-live direction from Umesh. (1) t151: A, one narrow extra cycle (one
scan-path deadline test; repair checker B only). (2) ct6: A, CT6 is amended to tier ordering and
reporting, not skipping: every case runs, cheapest tier first, cheap failures shown first. RU3 and
F-058 are unchanged. (3) T-174: the `mcp` SDK dependency is authorized. The CLI stays a first-class
surface next to MCP. (4) Any-model provider: model calls must work with any AI API (Gemini, Claude,
OpenAI, local Ollama, any OpenAI-compatible endpoint), chosen by config. New task T-202 adds a
LiteLLM-backed Provider behind `providers.base.Provider`, and `litellm` is authorized in that unit.
LangChain stays where it is already used. (5) T-199 widened: a generic tracker integration for any
project, with a per-project column mapping proposed on first use and confirmed by the user, and the
first live write shown and confirmed. (6) Go-live: AutoTester is hosted as a website on a
Linux/Ubuntu server for the Vidysea internal development and product teams. New tasks T-203
(hosting) and T-204 (team login, a go-live blocker; role-based authorization stays later).

**Why:** Umesh, chat 2026-10-07: "mcp: haan … CLI bhi"; "kisi bhi AI ki API se chala paaye, Gemini ya
Ollama ya kuch bhi"; "jab user dega kisi bhi project ke liye tracker tab usko"; "abhi Vidysea ki
internal development team aur product team ke paas chalega, host properly website mai hoga". A
server-hosted UI without login would let anyone with the URL run tests through the provisioned
test account, so team login is required before go-live (D-066 already flagged it).

**Result:** gate answers recorded in qa/gates/t151-cycle2-stalled.md and
qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md. goal.json gains T-202, T-203 and T-204, and the T-199 and
T-174 notes are updated. No product code changed by this entry.

**Changes-authorized:** qa/contracts/catalog.md CT6 (checker-owned amendment to ordering and
reporting) · pyproject.toml / uv.lock: `mcp` (T-174) and `litellm` (T-202) · .goal/goal.json
(T-202..T-204 added, T-174 and T-199 notes) · tests/test_discover_hardening.py on
codex/t151-target-discovery (one test).

**Approved-by:** Umesh — chat answers 2026-10-07.

**Links:** T-151; T-125; T-174; T-199; T-202; T-203; T-204; D-066; D-068; qa/gates/t151-cycle2-stalled.md; qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md.

## D-072 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Umesh answered every open go-live, Group 10 and unit gate in one sitting (chat, 2026-10-07):
1. **T-122 login oracle: A.** The "YOUR PROGRESS" section was removed from the Pathlynks dashboard on purpose. Re-author the BEST login case's step-4 marker to a stable signed-in marker (the Logout control plus the dashboard heading), update `login_case_id`, and re-run.
2. **New modules: yes to all.** This covers T-176 (`browser/locators.py`, `browser/locator_derive.py`, `stages/script_replay.py`), T-202 (the LiteLLM provider), T-203/T-204 (hosting, auth), the Group 10 split modules, T-190's six paths, and `agents/`. Every file stays at or under 300 lines with a one-job docstring, and the checker judges it.
3. **Login (G3):** the simplest scheme, email and password. **Anyone can sign up**, and an admin can act on any account (disable, delete, change access). A new account starts with no access until an admin puts it in a group.
4. **Access (Group 10 Q2):** AWS-IAM-like **groups with checkbox permissions**. The admin creates groups, ticks the permissions each group has, and adds users to groups. Permissions are additive, and the first account created becomes admin.
5. **Secrets display (G4):** saved credential values are shown **only to admins**, which here means holders of a `credentials.view` permission that by default only the admin group has. Everyone else sees "set / not set".
6. **Concurrency (G6):** a **server setting**, admin-configurable, sized to the server (default 2 concurrent browser runs server-wide, with one run per project at a time and the rest queued).
7. **Server (G1/G2):** production is an **Ubuntu server**, and development continues on **Windows**. The code must run on both. Docker and Ubuntu are the deploy target, with a deploy guide. The domain comes later.
8. **Reports:** shown on the website, plus email **by user preference** (a per-user checkbox).
9. **Schedule:** a run starts on a button press, at a fixed time, or at a custom time the user selects, configured per project.
10. **Videos:** the upload limit is admin-configurable, default **2 GB**. A **Google Drive video link** is also accepted, and the system fetches the video itself.
11. **Script replay:** a replayed run is still graded by the judge (`judge_replays` stays True by default).
12. **Host allow-list (AT-758):** extends the D-066 Origin guard. Every request's Host must be loopback, a host from `AUTOTESTER_ALLOWED_ORIGINS`, or an exact `AUTOTESTER_ALLOWED_HOSTS` entry. The hosted server must set one of these.

**Why:** Everything open on the path to the hosted team MVP was waiting on these answers. Umesh asked to be asked properly, once, and answered every question. Open signup with admin moderation and default-no-access is the simplest scheme that still keeps outsiders away from credentials and runs.

**Result:** Gates `qa/gates/t122-stale-login-oracle.md` and the new-module gates are answered. T-176 can merge. T-122, T-202, T-203, T-204 and Group 10 move to build. The checker amends contracts where these answers change a criterion: secrets display, the auth/roles contract for T-204, and the concurrency and schedule rows for T-203 and Group 10.

**Changes-authorized:** new modules for T-176, T-202, T-203, T-204, Group 10 (T-197..T-201), T-190 and `agents/`; `src/autotester/ui/` auth, permission and group routes and middleware; the queue and concurrency setting in the run path; the Host allow-list in `ui/helpers.py` (AT-758); `.env.example` keys `AUTOTESTER_ALLOWED_HOSTS`, SMTP and run concurrency; the re-authored `projects/pathlynks` login case and `login_case_id`; the Docker and Ubuntu deploy files and guide.

**Approved-by:** Umesh (chat, 2026-10-07)

**Links:** D-066, D-068, D-071, T-122, T-176, T-197..T-204, AT-758..AT-761, qa/gates/t122-stale-login-oracle.md

## D-073 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Create the new module `src/autotester/stages/reconcile.py` (about 250 lines). It reconciles
video-derived flows into the product knowledge graph with no human approval step (D-070 part 2). It
matches video screens to crawl screens by route, title or element signature, and sends ambiguous
matches to a Provider judge: a score of 0.8 or more is matched, 0.5 to 0.8 is ambiguous. It keeps every
flow and records divergences as "another possibility" alternatives in reports.

**Why:** Every existing candidate module is at or near the 300-line cap, so the reconcile logic cannot
be added in place without breaking the design rules. The design is RC1-RC10, recorded in
`qa/feedback-inbox.md` (the "D-070 part 2 reconcile design" block).

**Result:** The module is authorized. A contract `qa/contracts/reconcile.md` follows from the checker.

**Changes-authorized:** `src/autotester/stages/reconcile.py` (new), plus in-place edits to the schema
models needed for step-to-screen linkage. Changing `require_reviewed` in review.py is NOT authorized
here; it is a separate L unit.

**Approved-by:** Umesh (chat, 2026-10-07)

**Links:** D-070; T-166

## D-074 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Umesh answered five open questions in chat (2026-10-07):
(a) **Group 10 plan approved.** Build units G1-G10 per `docs/plan.md` and `qa/gates/plan-approved-g10.md` (intent O8-O15, spec R32-R65, T-205 and T-206 as the new rows).
(b) **Judge rule A.** A deterministic assertion that failed can never become PASS. For a run with a failed assertion the judge may only return FAIL or INCONCLUSIVE. This **amends D-032** (partial): the part of D-032 that let the judge weigh and overrule a recorded failed assertion is removed. The rest of D-032 (assertion evidence, `Outcome.ASSERTION_FAILED`, the executor never grading) stays in force, which is why this is an amendment and not a full Supersedes: `append_decision.ps1` computes a supersede as total, so a Supersedes line would retire all of D-032.
(c) **Password hashing uses `argon2-cffi==25.1.0`.** It is the new dependency for T-204 AU1. The scrypt fallback is not used.
(d) **The first admin is a fixed email**, set through `AUTOTESTER_FIRST_ADMIN_EMAIL`. Umesh sets the value in the server's `.env` at deploy time. With the variable unset, the hosted server must not auto-promote the first signup. Local dev keeps first-account-admin.
(e) **Cookie Secure is off (`AUTOTESTER_COOKIE_SECURE=0`) only until the domain and HTTPS exist.** This is the default until then; Umesh can override it.

**Why:** (a) Nothing in Group 10 could start without the plan being approved. (b) AT-773 measured 6 of 6 false PASSes in T-122, each one a run where a deterministic assertion had failed and the judge still said PASS. Failing closed is the safe direction: the worst case becomes an INCONCLUSIVE a human looks at, not a bug shipped as green. (c) argon2id is the current default recommendation for password hashing and pinning the version keeps the lock file reproducible. (d) First-signup-wins on a public-facing host lets whoever signs up first take admin; a fixed email removes that race. (e) Secure cookies are never sent over plain HTTP, so setting Secure before HTTPS exists would break every login.

**Result:** Gate `qa/gates/plan-approved-g10.md` is answered. T-205 and T-206 are added to `.goal/goal.json` as tasks. The judge rule is authorized for build; the checker amends `qa/contracts/` rows that cite D-032 (execute and grade). Follow-up for T-204 (nothing is built yet: `src/autotester/auth/` does not exist, so no code auto-promotes today): `docs/plan.md` row 13 and `qa/contracts/auth.md` still say "first account becomes admin" and must be reworded to "first account becomes admin only in local dev; on the hosted server only the `AUTOTESTER_FIRST_ADMIN_EMAIL` account is promoted, and an unset variable promotes nobody". Cookie Secure must default from `AUTOTESTER_COOKIE_SECURE`.

**Changes-authorized:** `src/autotester/stages/grade.py` and `src/autotester/stages/run_case_pipeline.py` (the judge rule); the `argon2-cffi==25.1.0` dependency in `pyproject.toml` and `uv.lock`; the Group 10 modules per `docs/plan.md` G1-G10; the first-admin and cookie-Secure env handling in `src/autotester/auth/` (new, T-204); `.env.example` keys `AUTOTESTER_FIRST_ADMIN_EMAIL` and `AUTOTESTER_COOKIE_SECURE`.

**Approved-by:** Umesh (chat, 2026-10-07)

**Links:** D-032, D-072, AT-773, T-204, T-205, T-206, qa/gates/plan-approved-g10.md

## D-075 | 2026-10-07 | type: decision | status: ACTIVE

**What:** The `browser-use` dependency is authorized for T-177 (agent fallback), pinned exactly as
`browser-use==0.5.9` (the same way litellm==1.104.0 and argon2-cffi==25.1.0 are pinned), with its
anonymized telemetry disabled (`ANONYMIZED_TELEMETRY=false` set by AutoTester before the import,
not left to the user's environment). `browser/session.py` gains a read-only `cdp_url` property so
the browser-use backend can attach to the session AutoTester already opened. The UI wiring
(`agent=`/`actuator=` into `run_and_grade_case` in ui/routes_runs.py) waits until T-203 and T-204
land, to avoid a three-way conflict with the peer session's branches.

**Why:** Umesh, chat 2026-10-07, answering the dependency question: "Approve, pin exact". The peer
session (autotesting-07) flagged that no D-entry covered browser-use, unlike D-071 (litellm) and
D-074 (argon2). Telemetry is turned off because Pathlynks screens and URLs must not reach a third
party without per-use approval.

**Result:** T-177 merges only after both dual-check coordinators PASS and the pin and telemetry
change has had its repair check.

**Changes-authorized:** pyproject.toml / uv.lock: `browser-use==0.5.9` (T-177) ·
src/autotester/browser/session.py: read-only `cdp_url` property (T-177).

**Approved-by:** Umesh — chat answer 2026-10-07.

**Links:** T-177; D-071; D-074; qa/contracts/agent-fallback.md; qa/gates/at253-agent-fallback-wiring.md.

## D-076 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Records the contract consequence of D-072 item 3 (a new account starts with no access), as written into `qa/contracts/auth.md` AU27 by the checker in commit 0f8c19d0 (D-074 amendment). AU27 states the safe default: a caller can grant only the permissions (key and scope) it already holds, and only members of the Admin/CEO group can change Admin/CEO membership, tick `users.manage`, `groups.manage`, `settings.manage` or `credentials.view`, or reset the password of an Admin/CEO account. No new product choice is being made: D-072 item 3 already decided that a new account has no access, and AU27 only closes the escalation path that a literal reading of AU8 and AU10 would leave open. D-074's own text states only items (a) to (e); the AU27 rule came from the dispatching brief, so this entry gives it a decisions record.

**Why:** Without a record, AU27 cites "D-074 safe default" while D-074 does not contain it, which makes the criterion look like an invented requirement. A `users.manage` or `groups.manage` holder who is not an admin could otherwise promote themselves or another account to full access, which would undo the no-access default of D-072 item 3. Keeping the entry as a pure consequence, not a decision, lets Umesh veto it by superseding it if he wants a different rule.

**Result:** `qa/contracts/auth.md` AU27 stays as written; its `serves:` line (D-074 safe default, D-072#4) is read as D-072 item 3 plus this entry. T-204 builds to AU27. No code change is authorized by this entry.

**Links:** D-072 item 3, D-074, qa/contracts/auth.md AU27

## D-077 | 2026-10-07 | type: decision | status: ACTIVE

**What:** The AGPL-licensed `pymupdf` package that `browser-use==0.5.9` (D-075) pulls in transitively
is accepted as is. We do not strip, replace or vendor around it.

**Why:** Umesh, chat 2026-10-07, answered "Accept AGPL" after T-177 checker A found the licence. The
autoTesting repo is already public, so the AGPL source-disclosure duty is met for now. The risk
applies only to a future closed, paid or customer-hosted build of AutoTester.

**Result:** T-177 is not blocked on licensing. **Re-open trigger:** before AutoTester is sold,
hosted for customers, or the repo is made private, this entry must be superseded, either by removing
the dependency or by a fresh licence decision.

**Changes-authorized:** none (pyproject/uv.lock pin already authorized by D-075).

**Approved-by:** Umesh — chat answer 2026-10-07.

**Links:** T-177; D-075; qa/verdicts/t177-agent-fallback.a.md.

## D-078 | 2026-10-07 | type: decision | status: ACTIVE

**What:** Umesh decided (chat, 2026-10-07) not to add the `tzdata` package. Schedules (Group 10 G5, team-schedule.md) support exactly two time zones: UTC and IST, the fixed +05:30 offset with no DST. Any other zone is refused with an error. The implementation uses fixed offsets (`datetime.timezone`), with no ZoneInfo and no zone database, so it behaves the same on Windows dev and Ubuntu prod.

**Why:** Windows ships no IANA zone database, so a city zone such as America/New_York fails there without `tzdata`. Umesh chose not to take a new dependency. The team works in IST, and UTC covers the server.

**Result:** The G5 schedule slice drops its DST handling and DST tests. The checker amends the qa/contracts/team-schedule.md timezone/DST wording to "UTC or IST only, no DST".

**Changes-authorized:** `core/localtime.py`, `schema/schedule.py` and `stages/schedule_*.py` in the G5 slice. No change to pyproject.toml or uv.lock.

**Approved-by:** Umesh (chat, 2026-10-07)

**Links:** D-072 item 9, D-074, T-201 or the G5 schedule unit, qa/contracts/team-schedule.md

## D-079 | 2026-10-08 | type: decision | status: ACTIVE
**What:** The canonical AutoTester GitHub destination is now https://github.com/vidysea-admin/autoTesting (public, default branch master). Future ordinary pushes from D:/autoTesting and its linked worktrees use origin at this destination; remote.pushDefault is origin. The previous personal repository remains available as the legacy remote.
**Why:** Umesh requested moving all currently published AutoTester code into the Vidysea organization so DevOps can use it for server deployment, and instructed this chat to carry out the migration. Keeping the existing master history preserves commit identities and avoids mixing uncommitted or unfinished branch work into the deployment branch.
**Result:** Created the public organization repository and pushed master at 40e8f1047bc250ee745587ef9713efd26b28ef38: 2,167 commits and 1,984 tracked paths. The public GitHub branch and git ls-remote independently returned that same SHA. A scan of its 6,104 reachable blobs found no matches against 15 current configured secret values or six credential patterns; twelve positive/negative pattern controls passed. The shared origin fetch/push URLs and default push remote were updated and verified from the combined and hosting worktrees. Repository deployment workflows, repository webhooks and deployment records were all empty at migration time: automatic server deployment is not configured or claimed. Auth/provider repairs and other work on separate branches retain their existing checker/integration state.
**Links:** Umesh's 2026-10-08 repository migration request and follow-up; source commit 40e8f1047bc250ee745587ef9713efd26b28ef38; https://github.com/vidysea-admin/autoTesting; D-007 standing push-on-PASS policy (retained); T-203 and T-204 go-live work (not closed by this operational migration).
