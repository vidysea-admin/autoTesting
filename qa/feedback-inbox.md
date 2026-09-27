# Feedback inbox

Verbatim user feedback, appended by any session, never edited. `/checker` folds items into
`qa/contracts/` (criticality-gated). The maker never edits a contract directly.

Format: `## <ISO datetime> — <source>` then the feedback verbatim, then `**Status:** unfolded | folded → <contract> | GATED`.

---

## 2026-09-03 — Umesh, initial vision (goal.md, Hinglish, transcribed)

> auto testing tool banane ka … AI based system banayenge, jisme UI bhi rahega … user us project ki
> saari details provide kar de … user apne product ki video bhi daal sakta hai, email daal sakta hai
> ki process kaise hona chahiye … Gemini ki API vagera bhi use kar lenge … un testing videos se
> Gemini vision model se step by step flow samajh lenge aur iske basis par eval methods bana denge …
> issue sabse zyada yahi rehta hai ki naye features banate waqt, ship karte waqt, purane features,
> purani API break ho jaati hai … jab bhi testers ya developer develop karenge, test karenge, uske
> baad hamara system run karega aur wo saare eval check … agar wo sab nahi hain to system video maang
> lega, video ke basis par workflow diagram kind of bana le, screen by screen … isme saare best case,
> worst case, edge cases cover hone chahiye, usually AI ka nature ye rehta hai ki wo best case
> scenario se portal explore karke nikal jaata hai, but is project ka worst case scenario, edge cases
> ko bhi test karna hai … real visible browser mein testing kare … cloud sign in … ya koi advance
> model use kar lenge jiska user API key de dega

**Status:** folded → plan v2 §1/§4/§5, `qa/contracts/core-invariants.md`, `qa/contracts/browser-and-secrets.md`

## 2026-09-03 — Umesh, on schema and system design

> sabse important iska schema aisa rakhna jo scalable ho and system design ko bhi pehle plan kar le
> properly … kyunki ye scalable hoga toh DRY principle use ho … humne abhi recent mein ek ERP product
> banaya … usme schema aur system design kaise flow hoga, wo kuch nahi decide hua, aur uske baad ye ho
> gaya ki jab main cloud chalata hoon toh cloud itne zyada tokens khaata hai just for holding the
> context … uska koi schema, koi structure hi nahi, har jagah code repeated hai … na main acche se
> khud se read kar paata hoon, na kuch wo kar paata hoon, toh human agar kuch karna chahe toh at the
> end wo control hi nahi le paayega … human engineer bhi usko samajh paaye, uske hisaab se kaam kar paaye

**Status:** folded → `qa/contracts/core-invariants.md` C1–C4, C6 (the whole contract exists because of this)

## 2026-09-03 — Umesh, on credentials

> isme ek file aur place credentials daalne ki bhi honge jo .env file mein aayenge and it must need to
> be highly secure so that our system and /portal-explorer and all can use the portal in live visible browser

**Status:** folded → `core-invariants.md` C5, `browser-and-secrets.md` B1–B4

## 2026-09-03 — Umesh, north star

> end goal ye hai jo tu north star rakhna ki at the end we will conduct a competition like google and
> all jahan ek taraf ek manual tester hoga who is expert in the field aur ek taraf hamara tester hoga
> and dono ko same document and flows and videos ya jo kuch material milenge and our system should beat them

**Status:** folded → `.goal` north star, `schema/bench.py` (BenchCorpus/BenchTrial/score), task T-120

## 2026-09-03 — Umesh, mid-cycle (chat)

> nhi place .env too in the root directory of d/autoTesting/.env

**Status:** folded → `browser-and-secrets.md` B1 + `core-invariants.md` C5 (2026-09-03, /checker
cycle-2 check of t011-secret-store; routine, non-safety-weakening — see each contract's amendment
log; commit: the cycle-2 verdict commit). Code side (`core/paths.py::env_file` → repo root) verified.

## 2026-09-03 — Umesh, on DB (chat)

> isme db and all bhi tho hoga naa mongo and all ka dunga mai tujhe tere .env mai

**Status:** SUPERSEDED (2026-09-04, see the Mongo/login entry below and
`browser-and-secrets.md` amendment log) — Umesh's later instruction reversed this proposal:
`PATHLYNKS_MONGO_URI` was removed rather than formalised as a `SecretRef`. `EvidenceKind.DB` for
backend assertions remains a real future idea (`browser/db.py` still exists, unwired) but is no
longer tied to this proposal's shape; re-propose fresh if/when an `execute` contract needs it.
*/checker 2026-09-03 (cycle-2 check): deliberately left unfolded — no B1–B9 or C1–C8 criterion
covers backend assertions; fold when the `execute` contract is initialised. Recorded in the
browser-and-secrets amendment log so it is not lost.*

## 2026-09-03 — checker AT-004, contract tension (browser-and-secrets B1 vs B4)

B1 "undeclared keys are ignored" vs B4 "masks every secret value". **Maker resolved in code toward
B4** (undeclared values are masked and prompt-guarded, never resolvable). Checker to confirm and
amend B1 wording to "ignored for use, still masked". Especially relevant now that `.env` is
repo-root and shared across projects.

**Status:** folded → `browser-and-secrets.md` B1 ("ignored for use, still masked"; 2026-09-03,
/checker cycle-2; routine — tightens B4, does not weaken B1; commit: the cycle-2 verdict commit).
Code behaviour independently reproduced, AT-004 marked fixed.

## 2026-09-03 — maker (T-005 cycle 1), defect found in a protocol tool

`scripts/append_decision.ps1` (copied from `D:/ai_os/templates/lab-protocol/`) reads the entry file with
Windows-PowerShell default encoding, so D-005's `·` and `—` landed in `docs/DECISIONS.md` as `Â·` / `â€”`.
DECISIONS is append-only, so D-005 stays as written; a `session` entry (D-006) records the fix.
Maker is correcting the script's read/write encoding to UTF-8 under D-000 `Changes-authorized`
(`scripts/append_decision.ps1` is listed). Checker: please verify the fix and consider filing the
template-level defect upstream (`D:/ai_os/templates/lab-protocol/scripts/append_decision.ps1`) — that is
outside this project's root, so the maker does not touch it.

**Status:** unfolded (tooling defect, not a contract change)
*/checker 2026-09-03 (T-005 cycle-1 check): the in-repo fix is verified - ran the working-tree `scripts/append_decision.ps1` (`-Encoding UTF8` on the entry read, the live-file read, and the raw read before append) against a scratch copy of `docs/DECISIONS.md`; the appended entry carried `·` and `—` as clean UTF-8 (`c2 b7`, `e2 80 94`), no `Â·`/`â€”`. Authorization: D-000 `Changes-authorized` lists `scripts/append_decision.ps1` with `Approved-by: Umesh`; D-006 records the change. The template-level copy at `D:/ai_os/templates/lab-protocol/scripts/append_decision.ps1` is outside this root - left unfolded here on purpose; it is a note for Umesh / the AIOS session, not a contract item for this project.*

## 2026-09-03 — Umesh, on provider architecture (mid T-050 build)
**Source:** chat, this session, while T-050 was blocked on ANTHROPIC_API_KEY being empty.
**Verbatim:** "मैं पहले से ही यह discuss करके confirm कराया, right? कि किसी भी एक model पे कभी dependency नहीं होगी, it should be lang chain system और whatever की, हम जब चाहेंगे, हम anthropic में भी shift होंगे, अगर गो नहीं होगा, Gemini यहीं पे होंगे, Gemini नहीं होगा, तो Olama में होंगे, Chat, GPT में होंगे, तो there should be either fallback system और lang chain का use कर ले, ताकि कोई भी API. चलो वो अलब sign up process है, तो वो बन जाएगा conditional, otherwise बाती सब का lang chain भी तुरू कर ले,"
**Reading:** no single-provider dependency; a fallback chain across Anthropic → Gemini → Ollama →
ChatGPT; built on LangChain rather than a hand-rolled per-vendor Provider class.
**Status:** folded → `qa/contracts/langchain-fallback.md` (T-055, new contract) — delivered and
checker-PASSed (`qa/verdicts/t055-langchain-fallback.md`, PASS). The automatic
Anthropic → Gemini → Ollama → ChatGPT fallback chain now exists; see that contract for the
criteria actually shipped.
*/checker 2026-09-04 (sweep): reconciled — this entry sat at "unfolded (deliberate)" after T-055
had already shipped and PASSed.*

## 2026-09-03 — Umesh, on Docker + live-watch + UI polish
**Source:** chat, this session.
**Verbatim (Hinglish):** "mai khaa dekh sakta hu. live runn krr aur system mai docker mai runn
krr and ui ko user friendly bnaana hai bss functionalty nhi bnaani hai" — "Where can I watch?
Run it live, run the system in Docker, and make the UI user-friendly — just don't build new
functionality."
**Reading:** three infra/presentation asks, explicitly scoped away from pipeline logic: (1)
dockerize the system, (2) a live-watch view for the headed browser inside Docker (clarified with
Umesh: noVNC embedded in the browser, local dev machine only — no remote/cloud hardening in
scope), (3) CSS-only UI polish across existing routes.
**Status:** folded → `qa/contracts/docker.md` (D1-D6, new) + `qa/contracts/ui.md` amendment log
(2026-09-03, /checker, docker-live-ui unit) — shared-layout invariant and `/live` route now
recorded. Verified: `qa/verdicts/docker-live-ui.md` (PASS, cycle 1).

*/maker 2026-09-03 (housekeeping pass): this item's status text still reads "unfolded" but the
proposal was actually delivered by T-090 -- `qa/contracts/db-assert.md` exists,
`browser/db.py::ReadOnlyCollection` is built, `EvidenceKind.DB` is a real enum member, and
`PATHLYNKS_MONGO_URI` is declared as a `SecretRef` in `projects/pathlynks/project.json`. Flagging
for the checker to reconcile the status line to "folded -> db-assert.md" -- not editing it myself
since contract/ledger status is checker-owned.*

## 2026-09-04 — Umesh, on Mongo/DB access and login credentials
**Source:** chat, this session, looking at the live credentials page.
**Verbatim (Hinglish):** "ye btaa mongo db ya mongo uri kyu chaiye tujhe db kyu chaiye hoga
tester ko. jaise ek tester test krna hai live browser mi jaake vese krega naa tu browser prr aur
ek project k liye tujhe bss login id and password hi tho chaiye vo bhi user se ya tho le lee ya
better ki usre ko browser khol kr bolo ki login krkee de dee." Follow-up on login options: "hamare
paas bhi rakho but only in specific cases after the user somehow ignore the first 2 jaise
pathlynsk test krna hoga tujhe tho mai tujhe system mai filll kreke de dunga bss like teeeno rakho
option."
**Reading:** (1) why does the system need Mongo DB access — a tester should just watch the real
browser, like a human would; (2) for login, prefer NOT storing a password at all — open the
visible browser and let the human log in manually once (the persistent profile means this only
ever needs to happen once per project); (3) keep all three mechanisms available: manual login,
.env auto-fill (Umesh will keep providing this for Pathlynks specifically), and the existing
OTP/2FA pause — never remove any of them, just make manual login the no-password-needed default
path for new projects.
**Status:** folded → `qa/contracts/browser-and-secrets.md` amendment log (2026-09-04 row) —
investigated and confirmed `PATHLYNKS_MONGO_URI` was declared in `projects/pathlynks/project.json`
(added by T-090) but genuinely unused by any real case (`browser/db.py` exists and is
unit-tested in isolation, never wired into an actual test case); removed the declaration since
Pathlynks doesn't currently need it, keeping `browser/db.py` available for a future case that
specifically needs backend verification. Built the new `autotester login <slug>` command for
manual one-time login. Shipped and checker-PASSed as unit `manual-login` (cycle 1,
`qa/verdicts/manual-login.md`; ledger F-020) — all three mechanisms (manual login, `.env`
auto-fill, OTP/2FA HITL pause) confirmed still present per Umesh's "teeeno rakho option."
*/checker 2026-09-04 (sweep): reconciles the maker's 2026-09-03 housekeeping flag on the older DB
entry above too — that entry's T-090 delivery is now itself superseded by this one.*

## 2026-09-04 — Umesh, on report-export: a flow diagram idea
**Source:** chat, this session, right after report-export (Excel + HTML) shipped.
**Verbatim (Hinglish):** "tu chahee tho testing report mai ek binary tree flow bhi dikha sakta hai
ek mindmap wise screen by screen kya kya hai and branch by branch reporting too. getting user k
liye bhi flow easy to understand rhegaa. aur tere liye bhi. getting. note it accha hai yee."
**Reading:** the HTML tester report (`stages/report_export.py::export_html`) could additionally
show a tree/mindmap-style visualization of the flow -- screen by screen, branch by branch (worst/
edge/best cases sharing a common entry screen, diverging from there) -- so the overall shape of
what was tested is easy to grasp at a glance, for Umesh and for a future Claude session reading
the same report. Explicitly framed as optional ("tu chahee tho") and asked to be noted, not
necessarily built immediately.
**Status:** folded → `F-028` (DFS single-path trace + click-to-enlarge lightbox on run-view,
shipped 2026-09-04, `qa/verdicts/ui-run-view-flow-and-lightbox.md` cycle-1 PASS) and `F-029` (BFS
merged branch-tree diagram per flow at `GET /projects/{slug}/flow-diagram`, shipped 2026-09-04,
`qa/verdicts/ui-flow-diagram.md` cycle-1 PASS). Both the DFS-refinement and the original BFS/
mindmap ask below are delivered — F-028 covers a run's own path, F-029 covers every case in a
flow merged from a shared entry. Natural data source used: `FlowSpec.flows[].steps` +
`Case.case_class`/`kind`, exactly as scoped here.
*/checker 2026-09-17 (Mode B sweep consolidation): folded — re-derived against `docs/FEATURES.jsonl`
rows F-028/F-029, both checker-PASSed and live. Nothing residual from this entry.*

**Refinement (2026-09-04, later in the same session, per plan §4):** rendering the *full* branch
tree (every worst/edge/best path, BFS-style — "covering all branches") is the expensive,
worst-case version. What Umesh actually wants is simpler and cheaper: **trace the one path a
given run actually took, DFS-style** — the literal sequence of screens/steps that case followed,
not every hypothetical branch. Re-scoped for whenever this is picked up: a linear step-by-step
trace per case (cheap, always renderable) rather than a full FlowSpec tree (expensive, only
meaningful once a project has many recorded flows). Still not scheduled this cycle — this is a
scoping refinement to the same deferred idea, not a new task.
*/checker 2026-09-04 (sweep): folded in per the plan's own note that this refinement belongs
here; was written into the plan file but not yet mirrored into this inbox until now.*

## 2026-09-04 — Umesh, on report/run-view UI quality (verbatim)

Screenshot of `/projects/pathlynks/report`: "still very bad ui and very non professional, test
dekho kesa dikh rhaa hai, no summary, no overview" — the report page's run-history list has no
at-a-glance summary/overview, just a raw table of run ids and badges.

Screenshot of `/projects/pathlynks/runs/run-01M1NF7RP82ADB72JDW4B47DKF`: "jo ye reporting hai vo
bhi very bad hai non informational too, big images and all" — the run-detail page's per-case
screenshots render oversized and the surrounding info (what was checked, why it passed/failed,
criteria) is thin/non-informative.

Source: direct chat message with an attached screenshot, not a manifest/checker finding.

*Resolved 2026-09-04: qa/manifests/ui-report-informativeness-fix.md, checker-PASSed cycle 1
(qa/verdicts/ui-report-informativeness-fix.md), ledgered docs/FEATURES.jsonl F-027. Report page
now leads with a real overview (total runs, overall pass rate, cases in latest run) and compact
per-run badges; run-detail cards show scoreboard/grader/failure info and screenshots render in a
responsive thumbnail grid instead of native size.*

## 2026-09-04 — Umesh, follow-up on run-view screenshot sizing (verbatim intent)

After seeing the fixed report/run-view pages live: screenshot thumbnails are readable at a
glance but too small to read detail without clicking. Asked (via AskUserQuestion) whether to
add a click-to-enlarge lightbox, make thumbnails bigger directly, or leave as-is — chose
**click-to-enlarge lightbox** (keep the compact thumbnail grid, but clicking a thumbnail opens
a full-size view).

*Resolved 2026-09-04: implemented as the DFS-style step flow on the run-detail page
(qa/manifests/ui-run-view-flow-and-lightbox.md) rather than a separate page/export — matches
this entry's own 2026-09-04 refinement (linear trace per case, not a full branch tree). Umesh's
mid-build follow-up "/workflow-diagram type kuch add kro" confirmed this scope: the flow arrows
between step thumbnails ARE the workflow diagram, at exactly the re-scoped DFS granularity.*

## 2026-09-04 — Umesh, explicitly wants the BFS branch-tree version too (verbatim intent)

After the DFS-scoped step-flow (F-028) shipped: "abhi bhi tune bfs wala setup kiya nhi hai" —
the DFS single-path trace was only half of what was originally asked (the 2026-09-03 mindmap
entry): the full branch tree, every case's path merged from a shared entry screen, branch by
branch. Explicitly asking for that now, not deferring it further.

*Resolved 2026-09-04: qa/manifests/ui-flow-diagram.md, checker-PASSed cycle 1
(qa/verdicts/ui-flow-diagram.md), ledgered docs/FEATURES.jsonl F-029. The full mindmap ask from
2026-09-03 is now closed in both halves: F-028 (DFS single-run trace) + F-029 (BFS merged
branch tree per flow) -- one case's actual path, and every case's path merged from a shared
entry, respectively.*

## 2026-09-04 — Umesh asked to rerun testing on pathlynks; found a real regression

Triggered `POST /projects/pathlynks/run` via the live UI (the same Run button F-024 shipped) —
result: all 3 cases INCONCLUSIVE, same failure class as the original INCONCLUSIVE-report bug
fixed earlier this session (`pathlynks-login-test-fresh-profile`), but that fix only patched
`scripts/run_pathlynks_first_cases.py`'s standalone script — the generic `trigger_run`/
`run_and_grade_case` pipeline (the one the actual UI button calls) still uses the shared,
persistently-logged-in `pathlynks` profile with no cross-run wipe and no run-order safeguard.
Confirmed via real verdict evidence: `TimeoutError: waiting for locator("input[name=\"identifier\"]")`
— the sign-in form never appeared because the profile was already authenticated. This is a real
regression in the flagship feature (Run button), not a request — filing and fixing now.

## 2026-09-04 — Umesh: "go whatever is best" on AT-046, led to a critical finding (AT-049)

While investigating AT-046 (residual grading flakiness) more deeply, discovered the actual root
cause: `stages/grade.py` never attached real screenshot images to the judge call — every Verdict
this system has ever produced was graded from evidence *filenames* in a text prompt, never real
pixel content. Confirmed live: a screenshot clearly showing "Invalid credentials" in red text was
graded FAIL with "no evidence of rejection," because the judge literally never saw it.

Asked Umesh how to proceed (AskUserQuestion): fix now, ship what's built and file separately, or
explain more first. Chose "fix now." Fixed as AT-049 — providers now genuinely attach real image
bytes; verified with 5 consecutive real Pathlynks reruns, all PASS every time (was flaky before),
verdict notes now describing real visual content.

## 2026-09-04 — Umesh: add a project sidebar/TOC (verbatim intent)

Asked for "TOC features" -- clarified via AskUserQuestion into a concrete scope: a persistent
sidebar listing all onboarded projects, visible on every page, for quick switching without
going back to the homepage first.

**Status:** folded → `qa/contracts/ui-sidebar.md` (US1-US5, new) — shipped and checker-PASSed
(`qa/verdicts/ui-sidebar.md`, cycle 1, PASS), ledgered `docs/FEATURES.jsonl` F-032.
*/checker 2026-09-06 (sweep): closing the loop — this entry had no Status line even though the
unit shipped and PASSed two sweeps ago.*

## 2026-09-06 — Umesh, on whole-platform BFS exploration + video-derived eval methodology (goal.md, Hinglish, scribed from an uncommitted addition to the root `goal.md` vision file — not yet spoken in this session's chat)

**Source:** found as an uncommitted diff to root `goal.md` at sweep time (`git diff goal.md`), the
same informal capture file whose 2026-09-03 entry above was already transcribed into this inbox
once before. Scribed verbatim per that precedent; not independently confirmed with Umesh this
session.

> एक feature यह भी था कि अगर कोई team video upload capture to पूरी platform testing कर ही नहीं पा
> रहा है. सारे feature सारी possibilities को explore कर ही नहीं पा रहा है. BFS वाली functionality
> तो तेरी बनी नहीं है platform पर. तू बस dashboard में जा रहा है dashboard में कौन कौन से icons हैं?
> कौन कौन से button clickable हैं? उनको click करके कौन कौन सी screen आती है? फिर forward जाकर क्या
> होगा? Backward जाकर क्या होगा? तू एक screen से दूसरी screen में चला गया. वह screen क्या तूने पहले
> देखी है या नहीं देखी है? यह सब proper testing करके यह button काम कर रहा है नहीं कर रहा है. यह API
> से data आ रहा है नहीं आ रहा है. essay पूरी proper testing होनी चाहिए थी वह तो तू कर नहीं रहा है और
> कर भी रहा है तो वह तेरी reporting में बिल्कुल भी नहीं पता चल रहा ना reports proper clear हैं और उस
> सबके अलावा भी एक एक और functionality यह थी कि अगर तुझे flow नहीं पता है और कभी कभार यह भी होगा कि
> तू बस एक अपने flow के हिसाब से चल लेगा जितना तेरी platform की understanding है. तो उस case में user
> क्या करेगा? User एक video upload करेगा. वह video के basis पर तू क्या करेगा? जैसे हम मैं एक तेरे को
> folder दूंगा वहां देखना videos के through हम क्या करते हैं? और इसके अलावा यह भी तो करें system की
> light data bases में रख लिया और सारी learning excel में हुआ transcription रख ली screenshot by
> screenshot workflows रख लिया. Work flow diagrams बनाकर रख लिया और फिर उसके बाद समझ लिया कि अच्छा
> flow कैसा है और user ने कैसे कैसे testing करी थी तो अच्छा use case क्या है? वह भी user बताएगा.
> इसके लिए हम Gemini API की use कर लेंगे और अभी recent के जो models आए हैं जैसे Gemini three point
> one pro or Gemini three point eight flash आया है. तो इन दोनों के combination से हम time stamp
> wise, user wise, screen wise, flow bnaa dengee aur uske basis se bhi testing hogi , like business
> case and use case and flow ki better undersstanding hogi tho , esse video, audio, document and
> all for flow understand and for creating eval methods.
>
> jaise testing k liye proper evals chaiye tho vo hone chaiyee
>
> C:\Users\Lenovo\Videos\Screen Recordings
>
> iss directory ko explore krr aur samjh like aaj takk hum videos ko kese kese various way se test
> krte hai and issues nikalte hai. automated way se humko ye krna hai phle
>
> aur abhi wali reporting ko bhi dekho, is it the best way, issi directory mai dekho, issues ki
> reporting excel sheet mai bhi kese krri hai humne aur bfs for overall ya dfs type jo best hoga

**Reading (checker's, unconfirmed):** three distinct asks, none currently covered by any
contract: (1) a **BFS-style whole-platform crawl** — icon/button discovery on the dashboard,
click, observe the resulting screen, track visited-vs-new, forward/back — explicitly broader than
today's scope (a reviewed FlowSpec's *known* flows only; ingest/expand never crawl for undiscovered
screens); (2) **local video corpus as testing-methodology ground truth** — a real folder,
`C:\Users\Lenovo\Videos\Screen Recordings`, outside this repo and outside any project's declared
`allowed_domains`/inputs, that Umesh says already contains examples of how testing/issue-finding
has actually been done, to be mined for eval-method design (referencing Gemini 3.1 Pro / 3.8
Flash by name — models this codebase's provider seam does not currently name); (3) a repeat
challenge to whether the **current reporting format is right** ("abhi wali reporting ko bhi
dekho, is it the best way… bfs for overall ya dfs type jo best hoga") even after F-027/F-028/F-029
already shipped report-informativeness fixes and both the DFS single-run trace and the BFS
merged-branch-tree *report visualizations*— this reads as asking whether the underlying *test
strategy* should be BFS-driven, not just its diagram.

**Status:** folded (2026-09-17, Mode B sweep consolidation) — AT-052 is `verified` (fixed_date/
verified_date 2026-09-07) and its `GRILL:` row is no longer in `qa/QUEUE.md` (current GRILL rows
are AT-218/AT-281/AT-402 only). The gate `qa/gates/at052-bfs-video-corpus-grill.md` carries an
`Answered: 2026-09-07` line (Umesh, option 1 — scope both capabilities, all three tracks in
parallel; plan `C:/Users/Lenovo/.claude/plans/great-when-you-really-iridescent-ocean.md`). Per-
sub-ask disposition, so nothing here is silently dropped:
- **Whole-platform BFS crawl (Track B):** delivered and actively worked — `qa/contracts/explore.md`
  + `qa/contracts/coverage.md` (X17/X18/V7), built by AT-457 through AT-486; not a stub.
- **BFS-vs-DFS reporting format:** answered directly in the gate text — "unchanged and not
  re-litigated"; F-027/F-028/F-029 stand as the report visualizations, the crawl produces a
  separate *product* graph, not a replacement report format.
- **Video-corpus mining (Track A, mining `C:\Users\Lenovo\Videos\Screen Recordings` as
  testing-methodology ground truth):** the video-LEARNING capability (ingest/transcribe a given
  recording, AT-465/466/468 etc.) is built, but mining *that specific local folder* as ground
  truth for how the team already tests is **not built and not queued** — carried forward here as
  a residual, not a new gate (the scoping decision already exists in the answered gate; this is
  an implementation gap, not an open question).
2026-09-06 · umesh (live, mid-session, Hinglish) · "bhai ye kessa ui bnaya hai na dashboard na kuch user kese testing krr payegaa" — the AutoTester UI's home page ("/") is a bare project-card grid (`ui/app.py::index`), no dashboard-style overview (no aggregate stats, no recent-run summary across projects, no at-a-glance health view). PATTERN: a non-technical user landing on "/" sees a list of names and case counts, nothing telling them what's passing/failing/stale across their portfolio without clicking into each project one at a time. EVIDENCE: read `ui/app.py:69-85` live during this session — `index()` only ever renders `_project_card` tiles in a grid, no stat tiles, no "N projects, M failing" summary. Contrasts with the already-shipped per-project report page (`routes_report.py`) which DOES have stat tiles (total runs, pass rate, cases in latest run) — that pattern exists and works, it's just never been pulled up to the home page. APPLIES NEXT: any home-page/dashboard redesign work — reuse `theme.py`'s existing stat-tile component instead of inventing a new one.
**Status:** folded -> ledger row AT-552 (2026-09-22b sweep; residual -- not yet built).
2026-09-07 · umesh (live, using the UI) · "dekh maine abhi ERP project ki details daali, there is no back button for easy navigation" — after entering the ERP project's details through the AutoTester UI, there is no back button anywhere for easy navigation. PATTERN: pages that take a user *into* a flow (onboarding form, project detail, env editor, settings, report/run views) give no way back out except the browser's own back button or the top nav — a non-technical user who lands on a sub-page has no visible "← back" affordance. EVIDENCE: reported live by Umesh while onboarding the ERP project through the UI. APPLIES NEXT: any UI route that isn't the home page — the fix belongs in the shared layout (`ui/theme.py::page`) or a shared breadcrumb helper, not per-route one-offs, so no future page can ship without it.
**Status:** folded -> delivered by unit ui-back-nav-and-live-clarity (verdict qa/verdicts/ui-back-nav-and-live-clarity.md); the empty-project dead-end half was filed and verified as AT-057.
2026-09-07 · umesh (live, using the UI) · "and live preview and all mai kuch bhi nhi ho rhaa" (nothing at all is happening in the live preview). PATTERN: two distinct causes, both real. (1) The /live page embeds a working noVNC iframe, but when no run is in progress the container's X display is genuinely empty, so it renders as a large dead black rectangle with no explanation — it reads as broken software when it is actually correct-but-idle. Its tip text also still pointed at a stale script command (scripts/regression_proof.py) instead of the ▶ Run tests button that has since shipped. (2) MORE IMPORTANT, found while verifying: a freshly-onboarded project has ZERO cases, so its ▶ Run tests button renders permanently disabled and there is NO UI path anywhere to add a case — onboarding leads to a dead end for a non-technical user, who can create a project and then literally cannot test anything with it. Cases today are only creatable via a Python one-liner against ProjectStore.add_case, or via stages/expand.py from a reviewed FlowSpec that itself requires an ingested video. EVIDENCE: live screenshot of /projects/erp showing "0 CASES" and a greyed-out Run tests button, taken 2026-09-07. APPLIES NEXT: the empty-project dead end is the single biggest "this is not a real product" gap left in the UI — a project with no cases needs either an add-a-case flow or an explicit, prominent next-step prompt telling the user exactly how to get one.
**Status:** folded -> delivered by unit ui-back-nav-and-live-clarity (same verdict -- noVNC idle-state explanation + stale-tip fix); the empty-project dead-end half is AT-057 (verified).

---

## 2026-09-07 — maker request: a new contract `qa/contracts/explore.md` (Track B3, T-143)

**Why a NEW contract and not an amendment to `execute.md`:** `execute.md` **E5** states
*"`run_case` performs exactly the actions in `case.steps` — it never invents an extra click,
submit, or navigation."* A crawler is by definition the invention of clicks. E5 must stay intact
and unamended for `run_case`; the explorer needs its own contract that explicitly says inventing
actions is *this* stage's job. Authorised by **D-015**.

**Covers:** T-140 (B1 primitives), T-141 (B2 identity), T-142 (B4 safety), T-143 (B3 crawl).
**Owner:** /checker. **Criticality:** HIGH — it drives a real logged-in browser against
production. **Depends on:** core-invariants.md (all), browser-and-secrets.md B5-B9,
execute.md E5 (explicitly preserved).

Criteria the maker built against, offered as a starting point (the checker owns the final text):

- **X1 — E5 stays intact.** `run_case` is unchanged in behaviour; `stages/explore.py` is the only
  stage permitted to invent a click or navigation, and it calls `run_case` for nothing except the
  human-authored login bootstrap case.
- **X2 — Every browser touch goes through `browser/`.** No `.page.` access and no `playwright`
  import in `src/autotester/` outside `browser/` (`tests/test_actuator_chokepoint.py`).
- **X3 — Screen identity is structural**, never URL-only and never model text. Two list pages
  differing only in row data are one node; two states at one URL with different controls are two.
- **X4 — Bounds fire and name themselves.** `max_screens`/`max_actions`/`wall_clock_s`/`max_depth`
  each end the crawl and are named in `Crawl.stop_reason`; no stop condition depends on provider
  output (the crawl takes no provider at all).
- **X5 — `write_policy` is enforced (the D-016 matrix)**, with the fixture proof that a
  Delete-labelled control is never clicked under READ_ONLY and is clicked under ALLOW_WRITES.
- **X6 — Session-ending controls are never clicked at any policy**; unnamed non-link controls are
  skipped and counted, not guessed.
- **X7 — The host is re-checked after every action**, not only on `goto`; a refusal produces an
  `OFF_DOMAIN_REFUSED` edge plus a `NAVIGATION` issue, then recovery.
- **X8 — Dialog circuit breaker.** Every dialog is recorded; `beforeunload` accepted, others
  dismissed; exceeding `dialog_repeat_limit` on one node aborts that node and the crawl continues.
- **X9 — Third-party noise is not an issue.** A failed request is an issue only when first-party;
  declared analytics hosts are dropped; other third parties are counted as noise only.
- **X10 — Nothing is typed.** The explorer never calls `fill`/`select_option`/`upload`; the only
  typing on a crawl is the login case through `run_case`.
- **X11 — Artifacts are incremental, human-readable files** under `projects/<slug>/crawl/<id>/`;
  a crash mid-crawl leaves a loadable partial graph. A node's final status reaches disk (this was
  a real bug found while building: `add_node` is idempotent, so a visited node stayed `queued`
  on disk until `update_node` was added).

**No-fire list offered:** filling forms with synthetic data; vision-guided action choice; resuming
an interrupted crawl; parallel tabs; CI triggers; `EvidenceKind.TRACE`; auto-generating cases from
crawl screens (that is `expand.py` after human review); auth bypass / 2FA automation; a wildcard
for `allowed_domains`; and crawl→FlowSpec merge + reporting (that is B5/T-144, not this unit).

---

## 2026-09-08 · maker (T-144, Track B5) · PATTERN: a criterion nobody owns is a criterion nobody checks

**Contract request — `qa/contracts/explore.md` needs X13–X16, and `qa/contracts/coverage.md` V1
needs an amendment.** Contracts are checker-owned; the maker never writes one. Filing the criteria
I built against so the checker can author, tighten or reject them.

- **X13 — A crawl may propose screens, never approve them.** `merge_screens` never rewrites an
  existing `Screen`; any real change resets `Review.status` to DRAFT and bumps `version`; merging
  the same crawl twice changes nothing (same fingerprint, no version bump, no duplicate conflict).
- **X14 — A disagreement is kept, never resolved.** When a crawled screen claims a `url_pattern`
  an existing screen already claims under a different name, both screens survive and a `Conflict`
  records both claims. **Deliberate exception the checker should judge:** two screens found by the
  SAME crawl sharing a `url_pattern` are NOT a conflict — X3 requires two SPA states at one URL to
  be two screens, so flagging that would file a false conflict on every SPA. Evidence: the fixture
  index page's filter toggle produces exactly this, 7 screens across 6 url patterns.
- **X15 — `Screen.url_pattern` is a host-less path, not the node's browsing template.**
  `node.url_template` carries a host; `coverage.py` compares paths. Copying the template verbatim
  would make every coverage diff miss.
- **X16 — The crawl report shows what was REFUSED and why it STOPPED**, not only what was found.
  Both the page and the workbook name `stop_reason`, every `DENIED_POLICY`/`SKIPPED_UNNAMED`/
  `OFF_DOMAIN_REFUSED` edge with its reason, and third-party noise counted-but-never-reported.
  A report that omitted these would read as full coverage of a bounded crawl.
- **`coverage.md` V1 amendment:** both sides of every coverage diff are normalised through
  `core.urls.url_template(..., keep_host=False)`. Before T-144, coverage compared raw paths, so a
  run that visited `/students/1` was reported as a gap against a screen whose pattern is
  `/students/{id}` — every id-bearing route looked permanently uncovered. `diff_crawl` and
  `unreached_screens` are the crawl-sourced twins of `diff_coverage`.

**No-fire list offered for this unit:** auto-generating cases from crawled screens (that is
`expand.py`, after human review); naming screens with a model (`prompts/explore_name_screen_v1.md`
is designed for and deliberately NOT built — the crawl stays provider-free, X12); background/async
crawling from the UI (synchronous, same trade-off `routes_runs.py` already makes); resuming an
interrupted crawl; merging crawl-discovered *flows* (only screens are merged); editing a merged
screen from the crawl page.

**APPLIES NEXT:** the same "propose, never approve" shape is what Track A's `merge_flowspec.py`
(T-135) needs, and the same two-direction coverage view is what T-125's catalog page reports.

---

## 2026-09-08 · maker (T-124, consent gates) · PATTERN: a guard each caller must remember is one a new caller will forget

**Contract request — a new `qa/contracts/consent.md`, criteria CN1–CN7.** Filing the criteria I
built against; contracts are checker-owned and the maker never writes one.

- **CN1 — Nothing outward-facing starts without an approval.** `run_crawl` raises
  `ApprovalRequired` **before** a crawl envelope, a browser navigation, a click or a screenshot
  directory exists. Proven at the transport, not by intent: `scripts/explore_proof.py`'s first
  invariant attempts a real ungated crawl and asserts no crawl directory was created.
- **CN2 — The gate lives at the seam, not in each caller.** The CLI and the UI both reach
  `run_crawl`; neither performs its own check. A guard each caller has to remember is one a new
  caller will forget.
- **CN3 — Consent cannot widen itself after the fact.** `RunApproval.id` is content-addressed over
  every bound field, and `require_approval` refuses a row whose id no longer matches its contents.
  `note` is deliberately outside the payload so a human may annotate without re-granting.
- **CN4 — Consent is never open-ended.** `expires_at` is required; an unparseable expiry is treated
  as expired, never as eternal.
- **CN5 — Approval does not transfer.** Matching on (project, run_kind, target) is EXACT. A prefix
  match would let an approval for one endpoint authorise another under the same host; consent to
  read is not consent to fire probes.
- **CN6 — Bounds are checked, not just existence.** A run wider than its approval is refused with
  the shortfall named (`actions 150 > approved 20`), and every rejection reason is reported rather
  than only the first — one bad row must not hide a good one, and a refusal that only says "no"
  teaches the operator nothing.
- **CN7 — Adversarial against production must say production.** `ApprovalKind.ADVERSARIAL` with
  `production=True` requested requires `production=True` granted. (T-154's surface; the criterion
  is filed now so the contract exists before the code that needs it.)

**Also for the checker's judgement, because it is a real trade I made:** the gate applies to
**every** crawl, including local fixture crawls in the test suite, rather than being conditional on
the target being remote. That cost me an update to four test entry points and the proof script. I
chose it because "is this localhost?" is a heuristic that fails **open** on a misconfiguration, and
because a guard only the production callers pass through is a guard tested nowhere. If the checker
disagrees, the alternative is worth stating in the contract rather than left implicit.

**No-fire list offered:** revoking an approval (expiry only, for now); approval for `ingest`/
`expand`/`run_case` (T-122's live-case gate is a separate unit); a UI grant form (CLI only this
unit — the credentials page is the right home and it is not built here); org-level or multi-project
approvals; any auto-granting path whatsoever.

**APPLIES NEXT:** T-154's adversarial pass is the reason CN7 exists, and T-151's discovery scan is
gate 1 (`ApprovalKind.READ`).

**FOLDED 2026-09-08 by /checker** into the new `qa/contracts/consent.md` (CN1–CN9). CN1–CN7 kept
in substance; CN1 tightened to hold at every shipped entry point (measured — AT-111), CN3's
limitation stated explicitly (AT-110), CN5's slash/case/query variants recorded, CN7's scope
boundary recorded (AT-112). The trade offered for judgement is **upheld** as CN9, and reversing it
is now a CRITICAL amendment. The no-fire list is the contract's Out-of-scope section. Verdict:
`qa/verdicts/t124-consent-gates.md` (FAIL, cycle 1).

---

## T-131 — `qa/contracts/ingest.md` I6–I9 requested (maker, 2026-09-08)

Track A2 shipped the first working half of the video pipeline. `ingest.md` today covers I1–I5
(provenance to the second). This unit adds behaviour nothing judges yet:

- **I6** — ingest PERSISTS via `save_flowspec`, and never overwrites an `APPROVED` spec without an
  explicit `--replace`. Rationale: overwriting one discards a human's review, not just data.
- **I7** — every ingested `Screen` carries `source_ref`, and a templated `url_pattern` **only when
  a url was actually observed**. Both sides of the video/crawl seam must use the same
  `core.urls.url_template`, or one screen becomes two rows.
- **I8** — narration is injected as ground truth and never re-transcribed or paraphrased. **The
  template must carry the placeholder the code replaces** — `str.replace` on a missing needle does
  not raise, so a template that loses `{{NARRATION}}` ships a prompt that runs blind with nothing
  failing.
- **I9** — the upload is polled to ACTIVE before any generate call; every SDK failure becomes a
  `ProviderError` carrying its cause; truncation (`MAX_TOKENS`) is reported AS truncation.

**Offered for judgement:** I left `google-genai` undeclared in `pyproject.toml` although the plan
put it in this unit. The import is lazy and nothing yet calls it for real, and declaring a runtime
dependency that no code path exercises seemed worse than declaring it in the unit that first does.
If the checker disagrees, the reasoning belongs in the contract rather than in my head.

**Also offered:** a hygiene line banning `git checkout` as a sabotage-restore mechanism while work
is uncommitted. I reverted my own uncommitted prompt rewrite that way during this unit (caught it,
rewrote it, no loss) — it is the same class of live-tree mutation AT-101 already bans for stash.

**No-fire list:** media prep / chunking / whisper (A3); the ensemble and adjudication (A4);
frames and `screenshot_ts` consumption (A3); merging into an existing FlowSpec (A6); any live
model call (this unit is MockProvider only).

**FOLDED 2026-09-08 by /checker** into `qa/contracts/ingest.md` as **I6-I10** (I10 added by the
checker: `register_source`'s content-identity rule was a real decision the four requested criteria
left ungoverned). All three sabotage transcripts reproduced verbatim in a `git archive` scratch
copy. **Ruling on `google-genai`:** real deviation from plan section 4 A2, filed as AT-130 and to be
closed in A3 -- but not a FAIL; the maker's reason is half wrong (the module IS importable today,
via a transitive pin, which is the hazard) and the reasoning is now in the contract's amendment
log and no-fire list. **Ruling on the `git checkout` hygiene line:** upheld in substance, refused
in a feature contract; filed as AT-131 extending AT-101. Nothing was lost -- the committed prompt
diff is the full rewrite, verified. Verdict: `qa/verdicts/t131-ingest-persists.md` (PASS, cycle 1).

---

## 2026-09-09 · maker · a FLAKY test in the adapter's own verify step

**PATTERN:** a browser-backed test whose outcome depends on timing makes `uv run pytest` — the
adapter's slot-1 verify — non-deterministic, so "the suite is green" stops being a fact and becomes
a probability. Every manifest in this project cites that command as evidence.

**EVIDENCE:** `tests/test_explore_live.py::test_the_dialog_page_does_not_trap_the_crawl` failed once
in a full run and passed on the next full run and in isolation (8 passed). The failure was
`assert 'aborted_error' in ('aborted_dialog', 'explored')` — under load the dialog page took the
ERROR path instead of reaching the dialog circuit breaker, so the assertion is on a state the crawl
reaches only when timing cooperates.

Not a regression from the unit in flight (nothing in `stages/explore*.py` was touched); observed
while verifying `at176-at178-render-not-scan`. Recorded here rather than fixed inside a unit about
something else.

**APPLIES NEXT:** the same shape lives in every `test_explore_live.py` assertion that pins a
terminal `NodeStatus` — X8's breaker is a race by construction, so asserting one exact status is
asserting the race resolved a particular way. A checker should decide whether these assert a SET of
acceptable statuses, gain a retry, or move behind a marker that keeps them out of the adapter's
verify command.

**FOLDED:** 2026-09-09 · checker of `at176-at178-render-not-scan` cycle 1 → `qa/contracts/core-invariants.md` C7 amendment log (routine) + ledger **AT-196** (medium). Ruling: confirmed a genuine flake, not a regression (no `stages/explore*.py` change in `e2f119f`; 7 consecutive clean runs including one under concurrent full-suite load). The `APPLIES NEXT` generalisation is upheld in substance but **narrowed**: the defect is not "pins one exact terminal status" — this test already allows two — it is that the test enumerates observed outcomes instead of asserting the invariant it is named for, which `crawl.finished_at is not None` already carries. No retry and no marker: keeping it inside the adapter's verify command is right, because its failure direction is a false FAIL, never a false PASS. Verdict: `qa/verdicts/at176-at178-render-not-scan.md`.

---

## 2026-09-10 · active goal + checker sweep · T-100 real-browser re-close

**PATTERN:** a no-CLI product promise is not satisfied by individually green route tests. The
operator journey must expose every safety control, count only real artifacts, explain metric
denominators, and return truthful HTTP/browser states under one independent interactive run.

**EVIDENCE:** D-022 reopened T-100 after the first business-truth browser campaign found
AT-243/244/245/246/247/248/251/252/257/259. The 2026-09-10 Mode-B sweep ranks T-100 first because
it directly blocks T-161. Current code still has CLI-only crawl approval, hidden default bounds,
all-directory run enumeration, a lifetime pass-rate headline, fabricated 200 pages for missing
run/crawl ids, raw review refusals, and a permanent favicon console error.

**APPLIES NEXT:** checker should amend `ui.md`/`ui-report.md` without weakening U1-U10: require an
in-UI domain-bound crawl approval and explicit bounds; themed refusal paths; 404 for unknown run
and crawl ids; valid persisted Run envelopes only; latest-run pass rate labelled with N cases and
M distinct flows; zero unexplained console errors; and one Mode-D journey from onboard through
masked credential, case/FlowSpec, approval, real run, report and portable downloads.

**FOLDED:** 2026-09-10 by `/checker` into `qa/contracts/ui.md` U11 and
`qa/contracts/ui-report.md` UR5-UR6 at `7d4c848`; independently PASSed in
`qa/verdicts/t100-ui-reclose.md` cycle 1 with Mode-D evidence.

2026-09-11T04:00+05:30 · maker (self-observed, corroborated by 3 independent checkers) · PATTERN: I have now shipped FOUR vacuous tests in one session — a test that passes while the property it is named for is false. (1) T-135 c1: a source-inspection test asserting `"resolve_requests" in inspect.getsource(...)`. (2) T-135 c2: a cross-seam test fed the SAME scheme-ful url on both sides, so it never exercised the shape that broke. (3) T-135 c3: a first-segment guard test asserting only DEEPER segments the regex could never match. (4) AT-298: `test_a_host_with_a_port_is_matched_either_way`, whose fixture declares both `127.0.0.1` and `127.0.0.1:46661`, so the port-fallback branch can be deleted with the suite still green. Every single one was caught by a checker running MUTATION testing, and none by me re-reading my own test. EVIDENCE: qa/verdicts/t135-coverage-merge-expand.md (c2 + c3), .b.md (c2), qa/verdicts/at298-migration-host-guard.md (AT-303, which explicitly notes it is "the maker's streak continuing into a fourth test, in this very unit"). APPLIES NEXT: this is not a discipline failure that resolving-to-be-careful fixes — the maker cannot see its own blind spot by inspection, four times running, while a mutation run finds it every time. Proposal for the checker to rule on: add a mutation step to `qa/adapter.json`'s slot-1 verify, so the MAKER runs it before writing the manifest instead of the checker discovering it after. Minimal viable form: for each test added by a unit, mutate the specific branch it claims to defend and require at least one failure; a zero-failure mutation is reported INCONCLUSIVE (C7), never as a pass. This would have caught all four before submission and is cheaper than a fix cycle.

**FOLDED:** 2026-09-11 by `/checker` into `qa/contracts/core-invariants.md` **C7**, as two new
clauses (kill-attribution; a mutation duty on any unit that adds or rewrites a test) plus an
extended Verify line. The **duty** was adopted and the proposed **mechanism** declined: not a
`qa/adapter.json` slot-1 step, because that file is the maker's own — a rule the maker writes for
itself is not a gate (same reasoning that refused `qa/loop.md` a home for the sabotage clause on
2026-09-08) — and because slot-1 runs on every unit while most add no test. Reason and evidence in
the contract's amendment log; verdict `qa/verdicts/at306-verification-artifact-integrity.md`.

2026-09-11 · maker (decision delegated by Umesh: "take the best decision as per the goal and keep going") · PATTERN: a guard with no written threat model cannot terminate, because the acceptance line moves with whoever is judging it. EVIDENCE: at345-346-fold-coverage took three fix cycles and three checker FAILs on one line of fold_credential; execution improved monotonically every cycle (1145 green, 10/10 mutations killed with attribution hand-verified, 11/11 false-positive probes accepted, doctor clean) while the score stayed pinned at 0/2. qa/contracts/ui.md U8/U9 pin a BYTE-FOR-BYTE property that none of AT-345/351/353/355 actually violates -- the cycle-1 checker said so and filed rather than charged on exactly that reading -- so what was really enforced was an unwritten rendering-equivalence standard whose edge MOVED mid-cycle when cycle 3 promoted a filed-only class to a charged failure on a fresh measurement. APPLIES NEXT: every guard in this repo that refuses input (the consent gate AT-110, the crawl safety deny-lists, assert_no_raw_secrets AT-347). PROPOSED AMENDMENT for /checker to fold as U11 in qa/contracts/ui.md: (1) state the threat model -- the credential guard defends against ACCIDENTAL exposure (a human pasting a value into a text box, an agent writing one into a git-tracked file) and NOT against a party who already holds the value, since anyone who can construct a deliberate re-spelling read it out of .env first; this is AT-110's tamper-evidence-not-tamper-proofing posture in another costume. (2) Name the in-scope transform classes: case, separator substitution, percent-encoding, whitespace, zero-width and format characters, control characters, and the curated homoglyph set. (3) Name the OUT-of-scope classes explicitly rather than leaving them to be discovered: bidi reordering beyond the override refusal, base64/base32/hex, HTML entities, double percent-encoding, reversal, and homoglyphs outside the curated map (AT-349, AT-352, AT-355's residue). (4) Add the rule the stall diagnosis identified: MOVING A CLASS FROM FILED TO CHARGED IS AN AMENDMENT, NOT A MEASUREMENT -- a checker may file a new class at any time, but charging it against a unit built before the class existed requires the contract to say so first. Gate with the full reasoning: qa/gates/at355-guard-shape.md. Diagnosis: qa/debug/at345-346-fold-coverage-cycle3.md.

**FOLDED:** 2026-09-11 by `/checker` (contract maintenance) into `qa/contracts/ui.md` as **U13** —
not U11: U11 (crawl authorisation) and U12 (unified intake) already exist, so the proposal's
number was stale, not the proposal. **Criticality ruled ROUTINE (documents, does not narrow),**
with the reasoning and the three pieces of evidence in that contract's amendment log: U8/U9 pin
raw values and byte-for-byte reassembly, so out-of-scope text removes nothing a criterion ever
said; no shipped defence is authorised away and the in-scope set is now a floor whose removal is
CRITICAL; and AT-349/AT-352/AT-356 stay OPEN at their filed severities — out of scope means not
charged, not closed. All four requested contents are carried (threat model, in-scope classes,
out-of-scope classes by name, amendment-not-a-measurement). Independent judgement on the maker's
two calls: **option B rightly rejected** (unbounded on the false-positive axis; AT-078/AT-086 are
measured precedents; it would not close AT-349 at all, since homoglyphs live inside an
allow-list), and the narrow half of A **upheld** as an in-scope criterion. The `visualOrder`
detector is **not** discharged by this amendment — filed as **AT-358** (medium). The gate's
"three refuted unreachability claims" item was treated as a **separate** amendment with its own
criticality judgement (also ROUTINE, a duty added) and folded into
`qa/contracts/core-invariants.md` **C7**.

2026-09-16 · agent-debugger stall diagnosis (at379 cycle 3), relayed by the maker · PATTERN: a module
with no contract criterion has no acceptance line, so the judge's line moves every cycle and the loop
cannot terminate. `grep "visual_text|visual_order" qa/contracts/` returns NOTHING; U13 names
`visualOrder` twice and both times says it is NOT covered (ui.md:237-240, :441-442) — yet the cycle-3
verdict charges U13. Each cycle's charge was a construct nobody had written down as required:
scrolled pane, then nested scrolled pane, then pane inside a clip. EVIDENCE: this repo already
diagnosed this exact failure mode in this exact file — U13's own rationale (ui.md:228-232) describes
"three fix cycles and three FAILs on one line of fold_credential… A loop whose acceptance line the
judge moves mid-cycle cannot terminate." That remedy was applied to the deny-list and never to the
positive detector U13 explicitly left undischarged; at379 then stalled the same way.
APPLIES NEXT: a new criterion **U14 — the positive rendering detector**, carrying (a) the
scroll-invariance floor (the reported glyph multiset must not change when the window or any
scrollable container is scrolled anywhere in its range), (b) the false-positive counterweight with
the north-star tie-break written down, and (c) a CONTRACT-OWNED "what this does not see" list, so
widening it becomes an amendment rather than a docstring edit. New criterion over a module no
criterion covers, softening nothing → routine lane on U13's own precedent. The maker does not edit
contracts; this is /checker's call.

**FOLDED:** 2026-09-16 by `/checker` (Mode B sweep) into `qa/contracts/ui.md` as **U14** — routine, a
new criterion over an uncovered module; scoped to submissions after the amendment so it does not
re-rule the live at438 cycle-1 verdict. Reasoning in that contract's amendment log.

2026-09-16T16:05:43+05:30 · Umesh (direct, via /maker continue) · VERBATIM: "continue and keep validating . sabb live browser mai validate krna hai"
  · PATTERN: validation evidence that never touches a real browser is not the validation Umesh is asking for — everything is to be validated in a LIVE BROWSER, not only by unit tests and CLI output.
  · EVIDENCE: arrives after a run of units (at335, at368, at386, at396, at399, at400, at405) whose LIVE-BROWSER field was honestly `not-applicable` because they touched CLI/tooling/prose only — correct per D-024's path rule, but it means the session's validation has lived almost entirely below the browser.
  · APPLIES NEXT: (a) prefer units that exercise the product's browser surfaces; (b) every UI-touching unit gets a checker-driven Mode D run, never a maker smoke pass cited as validation; (c) a unit with genuinely no browser surface still says so plainly rather than faking a browser check. Whether this should become a contract criterion (e.g. "each session ends with a live-browser pass over the running app") is the checker's fold, not the maker's.

  · **FOLDED:** 2026-09-16 by `/checker` (Mode B sweep) — recorded in `qa/contracts/ui.md`'s amendment
  log; (b) and (c) already hold under D-024 / checker Mode D, (a) is maker unit selection, and the
  session-end live pass was not made a criterion because no on-disk session boundary exists for a
  verdict to judge. Standing live UI validation verdicts serve its intent.

2026-09-16 · maker (self-reported, at429 close-out) · PATTERN: with two maker loops sharing one working
tree, `git add <explicit paths>` does NOT scope a commit. A bare `git commit` commits the WHOLE INDEX,
including whatever the other loop has already staged. Staging carefully is not enough; the commit
itself must name its paths: `git commit --only <paths>` (or `-o`). EVIDENCE: this session's maker
swept another loop's work into its own commits THREE times, each time having staged only its own
files: `git add tests/` caught a tracked file, then a `git rm --cached` "fix" removed it from HEAD,
and at429's close-out (30c7f02) committed the other loop's pre-staged at432 manifest and evidence.
The last one was undone with `git reset --soft HEAD~1` + `git commit --only`, leaving at432 staged
exactly as its owner left it. Each earlier fix was "stage more carefully", which cannot help when the
index is shared. APPLIES NEXT: every maker AND checker commit in this repo. The checker dispatch text
already says "narrow pathspec", but a narrow `git add` followed by a bare `git commit` satisfies that
wording and still sweeps. It should say `git commit --only <paths>`. /checker to decide whether this
belongs in a contract criterion or only in the dispatch prompt.

**FOLDED:** 2026-09-16 by `/checker` (Mode B sweep) into `qa/contracts/core-invariants.md` as **C10**
— ruled a criterion, not only a prompt line. Reasoning in that contract's amendment log.

2026-09-16 · maker (self-correction, at438 cycle 3) · PATTERN: CORRECTS my own earlier entry today
recommending `git commit --only <paths>`. That entry is incomplete and, as written, still sweeps.
`--only` does keep OTHER paths that someone else staged out of the commit, but it commits the ENTIRE
working-tree content of every path it names. On a file both loops edit (qa/issues.jsonl,
qa/.last-tick), `--only` therefore commits the other loop's uncommitted lines together with your own.
EVIDENCE: the at438 cycle-2 checker declined `--only` for exactly this reason, because the ledger held
the other loop's uncommitted AT-431/AT-433 edits and a new AT-446 row. It built the commit in a
TEMPORARY index instead (`GIT_INDEX_FILE=<tmp>`, seeded from HEAD, with only its own rows added), then
reset its paths in the shared index. The maker's own `.last-tick` commits today picked up extra lines
("2 ++" and "4 ++" where one line was appended), which is this same sweep, on a file where it happens
to be harmless. APPLIES NEXT: the whole rule is: (1) for a path only you edit, `git commit --only
<path>`; (2) for a SHARED path (ledger, .last-tick, feedback-inbox), commit HEAD plus only your own
change, built in a temporary index or written as a blob with `git hash-object` and
`git update-index --cacheinfo`, never from the working tree. /checker: fold the corrected rule, not
the earlier one.

## 2026-09-16T22:25+05:30 · Umesh (chat, verbatim) · PATTERN: judge the product by what it maps and tests end to end, not by how many small UI defects close
> "abhi tho hmara testing flow login k baad hi ruk jata hi, what the kind of testing you are really doing. system relaible kese bnega. puura product map hona chiaye na aend to end testing . each possible route"

EVIDENCE (maker, measured the same hour, counts only): every crawl on disk stopped at or before login.
- saucedemo: 1 screen, 0 actions, 3 denied (two unnamed inputs; the login button denied as "form submit under read_only").
- checkerdemo (two crawls): the same shape.
- pathlynks: LOGIN_FAILED with 0 screens.
The UI "Explore" route (`ui/routes_crawls.py:226`) calls `run_crawl` with no `login_case`, so a crawl started from the product UI can never get past a login wall. Only the CLI's `--login-case` can. Default bounds are 30 screens / 200 actions / 600 s, and read_only denies every form submit, so post-login forms and multi-step flows are never exercised. The maker's last 8 units today (AT-430..AT-455) were all small AutoTester-UI defects; none moved this.
APPLIES NEXT: the contracts need a coverage criterion stated against the product. Every distinct screen (url template) and every navigation control reachable after login should be mapped, with a coverage number, and every unreached one listed with its reason (bound, policy, unnamed, error). A crawl that ends at the login page must read as a failure, never "completed". /checker: fold this into explore.md / coverage.md.

**FOLDED:** 2026-09-16 by `/checker` (Mode B sweep #6) into `qa/contracts/explore.md` **X17** (UI crawl
uses the project's one declared login case) and **X18** (a crawl that never passes the login wall is
never COMPLETED, at any `actions_used`), and `qa/contracts/coverage.md` **V7** (coverage figure +
every unreached screen/control with one reason from a closed set). Every maker fact re-derived from
code and crawl.json counts; one corrected (the on-disk `completed` wall crawls predate AT-242 — the
live residual is the actions ≥ 1 path). Not folded: relaxing READ_ONLY after login (CRITICAL, D-016).
Issues AT-457/458/459 (high), AT-460 (medium). Live target opened as `qa/gates/live-crawl-target.md`.

---

## 2026-09-18 · maker (AT-503) · PATTERN: `pytest -q` on top of `pyproject.toml`'s `addopts = "-q"` becomes `-qq`, which prints no summary line at all — and this exact doubling appears in dozens of places this unit's file set cannot touch

**EVIDENCE (measured today, four captured logs in `qa/evidence/at503-pytest-a-summary-line-not-just-dots/`):**
- `uv run pytest --collect-only -q` → `collect.log`, exit 0, collection list only (no run).
- `uv run pytest tests/test_ledger_checks.py` (bare, no `-q` on the CLI — relies on the config's
  single `-q`) → `bare.log`: `19 passed in 0.61s`, exit 0. **Summary line present.**
- `uv run pytest -q tests/test_ledger_checks.py` (explicit `-q` stacked on the config's `-q`) →
  `single_q.log`: dots + `[100%]` only, **no `N passed` line**, exit 0.
- `uv run pytest -qq tests/test_ledger_checks.py` → `double_q.log`: identical to the `-q` case —
  confirms `-q` (CLI) + `-q` (config) behaves exactly like an explicit `-qq`.

**This unit's fix (in scope, done):** `qa/adapter.json`'s slot-1 verify command changed from
`uv run pytest -q` to `uv run pytest` (bare), and `d:/autoTesting/CLAUDE.md`'s Commands block
updated to match, with a one-line comment naming why. `pyproject.toml`'s `addopts = "-q"` is left
alone, per the coordinator's instruction — it is what makes the bare form's output readable at all,
and touching it would reach every other invocation in the tree, not just this one command.

**Residual — the SAME doubling exists in files this unit's file set does not include, so the fix
above is necessarily partial:**
- `AGENTS.md` (repo root) carries the identical three `uv run pytest -q` lines this unit fixed in
  `CLAUDE.md` (its Commands block and two prose mentions) — appears to mirror `CLAUDE.md` closely;
  not touched here (outside the declared file set: only `CLAUDE.md`'s Commands block was in scope).
- `d:/autoTesting/CLAUDE.md` itself still names `uv run pytest -q` twice **outside** the Commands
  block (the "Maker-checker discipline" adapter-summary bullet, and the Lab Protocol "Validators"
  bullet) — both prose references to the adapter's verify command, now stale against the actual
  `qa/adapter.json` value. Only the Commands block was in this unit's file set.
- `qa/contracts/core-invariants.md` **C7**'s Verify clause literally names `uv run pytest -q`
  (line ~120), and its 2026-09-09 amendment-log entry (line ~225) repeats the same string. Contracts
  are checker-owned; the maker never edits them — filing here per the standing rule.
- `qa/contracts/ui.md` (`uv run pytest -q tests/test_browser_scroll_invariance.py …`) and
  `qa/contracts/explore.md` (`the full suite (uv run pytest -q)`) — same pattern, per-file forms.
- `qa/loop.md` line 14 names `uv run pytest -q` as slot-1's command.
- **The broader latent finding, beyond adapter.json's own full-suite command:** every PER-FILE
  verify command in `.goal/goal.json` (`tasks[].cmd`, ~45 rows, e.g.
  `"uv run pytest tests/test_ledger.py -q"`) and in several contract Verify clauses and `plan.md`
  step rows explicitly types `-q` on the CLI. Given `pyproject.toml`'s `addopts = "-q"`, **every one
  of these also resolves to `-qq` and prints no summary line** — this is not unique to the full-suite
  invocation AT-503 was filed against. A manifest quoting `N passed` for any of these commands
  verbatim was either run with a different `addopts` override (several do use
  `-o addopts=`, which correctly clears it) or is pasting a number pytest did not actually print.

**APPLIES NEXT:** whoever next touches `AGENTS.md`, `qa/contracts/core-invariants.md`,
`qa/contracts/ui.md`, `qa/contracts/explore.md`, `qa/loop.md`, or `.goal/goal.json`'s per-file `cmd`
fields should drop the redundant CLI `-q` (or add `-o addopts=` where a *different*, more verbose
level is actually wanted) — the mechanical fix is identical everywhere: **stop typing `-q` when the
config already sets it**, never touch `pyproject.toml`. Whether this is worth a repo-wide sweep unit
of its own, or is cleaned up file-by-file as each one is next edited, is the checker's/maker's call,
not this unit's — its own file set is `qa/adapter.json` and `CLAUDE.md`'s Commands block only.

**Status:** folded → `qa/contracts/core-invariants.md` (C7 Verify clause + new 2026-09-18 amendment
log entry), `qa/contracts/ui.md`, `qa/contracts/explore.md`, `qa/contracts/living-ledger.md`,
`qa/contracts/browser-and-secrets.md` (B1-B4 and B5-B9 Verify clauses), `qa/contracts/pathlynks-
onboarding.md` — all six Verify clauses' stale `uv run pytest -q` corrected to `uv run pytest`
(2026-09-18, /checker, at503-pytest-a-summary-line-not-just-dots cycle-1 check). `AGENTS.md`,
`qa/loop.md`, and `.goal/goal.json`'s ~43 per-file `cmd` rows are outside the checker's contract
write-surface — filed to the ledger instead as AT-521 and AT-522 rather than edited here.

---

2026-09-22 · Umesh asked "what is TestSprite, how does it work, can we learn from it" → research doc
`docs/research/testsprite-2026-09.md` (commit `3ce3401`). Constraint he set: nothing leaves the
machine, so this is docs-only analysis; no product, URL or credential went to any vendor.

**PATTERN: reading a competitor's shipped architecture is a cheap way to audit our own claims, and
the audit is worth more than the comparison.** Writing the comparison required verifying our side,
and the three capabilities TestSprite ships turned out to be the three `docs/ARCHITECTURE.md`
asserts and our code does not have. None of this needed a competitor account — only an honest grep.

**EVIDENCE** (each verified directly on 2026-09-22, not taken from the research agent's report):
- `ARCHITECTURE.md` "Execution model" claims script-first replay and *"a stable suite costs ~zero
  tokens to re-run"*. `Script` (`schema/case.py:87`) is never instantiated in `src/`;
  `case.script_ref` (`:31`) is only declared and copied through (`:60`), never read for behaviour;
  `run_with_fallback` (`stages/agent_loop.py:67`) has **zero** callers in `src/` —
  `run_case_pipeline.py:95`, `explore.py:109` and the UI all call `execute.run_case` directly. Every
  re-run is a fresh vision call. **Under the Lab Protocol this prose is currently false.**
- No deterministic assertion layer. `absent_text`/`dom_asserts`/`visual_signal`/`network`
  (`schema/flowspec.py:65-68`) have **zero read sites in `src/`**; `url`/`visible_text` are read only
  in `browser/session.py:230,245` inside `_poll_for_expected`, which returns either way on timeout
  and records no failure; `Action.ASSERT` is `lambda session, step: None` (`stages/execute.py:43`).
  All pass/fail is an LLM on a screenshot (`stages/grade.py:123`).
- `CaseClass.REGRESSION_ANCHOR` appears only at `schema/enums.py:69,87` — absent from
  `CLASS_DESCRIPTIONS` and `applicable_classes`, so it can never be generated. Straight bug.
- F-039 claims a two-model ensemble; every erp issue row says `"models_agreeing": 1`.
- `stages/bench.py:51 oracle_human_trial` takes `duration_s: 300.0` as a literal, so "AutoTester
  wins on time" is 13.6s vs a hardcoded 300, over one seeded typo in one static HTML file.
  `stages/score.py` is careful code with no truth sheet in the repo (T-136 open).
- Feature ledger stops at F-043 / 2026-09-10; ~12 days of crawler work through 2026-09-21 unledgered.

**APPLIES NEXT:**
1. **These belong in `qa/issues.jsonl`, which is the checker's surface (AT-499), not the maker's** —
   that is why they are here verbatim rather than filed. Severities proposed in
   `docs/research/testsprite-2026-09.md` §7: the ARCHITECTURE.md falsehood and the dead assertion
   fields are **high**; `REGRESSION_ANCHOR`, F-039, the bench literal and the ledger drift are
   **medium**.
2. **Correcting the ARCHITECTURE.md Execution model is a prerequisite**, not a follow-up, for any
   unit that wires script-first replay — a Lab-Protocol `docs/DECISIONS.md` entry has to authorize
   the prose change first.
3. **A decision worth recording before someone re-proposes it:** refuse "regenerate the test instead
   of maintaining it" (TestSprite's answer to flakiness). If the oracle is regenerated from current
   app state, the oracle moves with the bug; they never address it. Reasoning in §6. If this ever
   needs revisiting it owes a `**Supersedes:**` entry arguing against that section.
4. **Open architectural question for a human, not a unit:** Meticulous's differential oracle (replay
   against base *and* head, baseline computed at replay time, recorded backend responses replayed
   for determinism) **needs no assertions at all** — so it is a genuine *alternative* to building our
   assertion layer, not merely a complement. It assumes two deployable builds, which we may never
   have for a hosted product like Pathlynks. §4E.
5. Standing caution for any doc that positions us: video→test is **not** unclaimed territory
   (`market-2026-09.md` already recorded Fume, Meticulous, Checksum, testRigor on 2026-09-03). Our
   differentiator is the reviewed oracle, the unknown-screen escalation and the scorecard — and two
   of those three are unproven (escalation has fired once on a 0-screen fixture; the scorecard has
   never run against a real human).

**FOLDED: 2026-09-22 by `/checker` (Mode B sweep, AT-539 confirmation + inbox fold).** Each claim
re-derived on this tree before filing, not taken from the research doc: ARCHITECTURE.md
script-first falsehood -> **duplicate of existing open high row AT-253** (filed 2026-09-09 with the
same three greps; re-verified today: Script never instantiated outside schema exports, script_ref
only copied at case.py:60, run_with_fallback zero src/ callers, run_case_pipeline.py:95 +
explore.py:109 + UI routes all call execute.run_case) — not re-filed, AT-253 stays open at high;
the four dead ExpectedState fields + no-op Action.ASSERT -> **AT-540 (high)**; REGRESSION_ANCHOR
unreachable -> **AT-541 (medium)**; F-039 ensemble-vs-1-model -> **AT-542 (medium)**; the 300.0
bench literal -> **AT-543 (medium)**; the ledger staleness (last row F-043/2026-09-10) ->
**AT-544 (medium)**; the orphaned running crawl -> **AT-545 (low)**. Item 2 (the ARCHITECTURE.md
Execution-model correction as prerequisite to any script-first unit) recorded here as the
DECISIONS-gate note it proposes: correcting that prose section requires a `docs/DECISIONS.md`
entry first per the Lab Protocol; the sweep files no defect row for it beyond AT-253's existing
coverage. Item 3 (refuse oracle-regeneration) needs its own `**Supersedes:**`-capable D-entry when
someone re-proposes — recorded, not gated. Items 4-5 (Meticulous differential-oracle alternative;
positioning caution) are strategy notes for Umesh, not ledger defects. Verdict file:
`qa/verdicts/sweep-2026-09-22.md`.

## 2026-09-23T07:30:10+05:30 · source: Umesh, chat (plan review, verbatim; approved plan C:/Users/Lenovo/.claude/plans/understand-what-all-we-zany-thunder.md)
> "video is optional, i also have to explore by itself. and apart from bfs do dfs also really need to be considered and also do it is also savin the website sccheam and flow anywhere so the enxt time it really need to retrace everything and also agar koi chiz break ya update hogi tho vo bhi track ho jaying. also kya market me esse tools nhi hai. how about you use some crawling tools like scrapling or esse autotesters. like unke code se you can buid and plant it in more industy standard way"
> "aur like jo account mai dunga usme jitni persmiison hogi uthi tho testing ho hi jaani chaiyee naa"
Decisions given via AskUserQuestion: Reuse = research spike, then PORT patterns (MIT/Apache/BSD only, no AGPL) · DFS = hybrid (BFS maps portal + bounded DFS per workflow; flagged vs D-023 "avoid single happy-path DFS" -- distinct, to be recorded in a D-entry) · Writes = ALL writes the role allows on a consented TEST_ACCOUNT, including delete (destructive ordered last).
PATTERN: persistence without read-back is not memory -- a durable model (portal_persona.json) must seed the next crawl and diff against it (new/changed/missing/broken), else every run retraces from zero · EVIDENCE: explore.py never reads the persona; persona merge is add-only (PP2) with no last_seen/missing marking · APPLIES NEXT: T-165 frontier, T-167 regression, T-168 damage report; coverage denominator = the role's permission surface, not the screens a read-only crawl happened to see.

**Status:** folded → D-040 approved the widened scope (2026-09-24, "go on"); the DFS/hybrid,
schema-persistence and change-tracking asks are now `qa/contracts/crawl-traversal.md` (T-165,
CR1/CR3/CR4) and the API-capture ask is `qa/contracts/network-assertions.md` (T-170, NA1-NA6). T-164
portion already folded → `qa/contracts/portal-persona.md` (PASS `05fc732`). The "permission = testing
surface" clause is routed to T-171 (not yet contracted; split out of T-165 by D-040), not dropped.


## 2026-09-24T16:10:00+05:30 · source: Umesh, chat — pasted transcript of a Vidysea product-demo meeting (parent/child/counsellor flow; verbatim excerpts, timestamps from the transcript)
> 02:08-02:49 Speaker 1: "Isme dikat yeh hai ki aapne father by default select kar rakha tha kya? … Compulsory karo choose karne ke liye … Nahi toh kya hoga sab flow flow me tak tak tak tak karte hue nikal jayenge. Baad me bolenge, 'Arey, hamara toh account me father dono father dikha raha hai'"
> 04:13-04:41 Speaker 1: "Ab yeh batao ki request aagayi aur 15 din tak kisi ne Vidhyarthi school khola hi nahi toh? … Nudge notification kuch to hisaab kitaab hona chahiye."
> 05:30-06:42 Speaker 1: "scenario likhe. Aur unhone scenario 1, 2, 3, 4, 5 … diya … usme ek ek cheez ke bache ne parent ne yes select kiya … toh kya ho raha hai, no select kiya toh kya ho raha hai. Woh recording ho … hum recording pe hi comment daal paate hain pause kar kar ke … Claude hi keh deta hai ki bhai yeh edge case check kar lo"
> 06:50-06:59 Speaker 1: "It will be able to tell you if it is running in the right phase or not, what are the UI glitches … Jaise maine abhi ek bataya parent me mother, father wala."
> 08:12-08:24 Speaker 1: "aadmi jab testing kar raha ho toh worst soch ke chalna chahiye."
> 08:52-09:19 Speaker 1: "Dono scenario record karo. Ek school ko ja raha hai toh kaise ho raha hai … apne prompt me you can ask, 'What could be the risk? … How can I make it better in terms of user experience?'"
> 09:28-09:47 Speaker 2: "jab yeh ek flow poora complete ho jayega next time woh ek hamara plan ban jayega ki kaise usse validate karna hai." Speaker 1: "Aur fir woh kya yeh stitch ho jate hain ek ke upar ek. Toh jab aap badi release karte ho toh yeh saare flow automatic check karke aapko last me log de dega ki yahan yeh yeh yeh yeh issues hain."
> 10:35-10:57 Speaker 1: "Sabse pehle scenario likhne zaroori hai taki aap koi scenario bhoolo nahi jab aap record kar rahe ho … us scenario me saare options test kar lena. Yes, no. Yes, no … hamara product check karta chala ja. Jahan jahan jo issue aa rahe hain usko lock karta chala ja."
> 12:33-12:40 Speaker 1: "fir isme gap bataye, fir aap usko theek karoge, fir koi manually dekhega, fir usme gap. Yeh teen loop automated tareeqe se ho sakte hain."
(Full transcript is in the 2026-09-24 session; excerpts above are verbatim.)

PATTERN: a scenario list is the input contract for a teaching recording — record against written scenarios (each branch yes/no enumerated), and report a scenario with no recorded branch as uncovered · EVIDENCE: 10:35-10:57, 05:30-06:05 · APPLIES NEXT: Track A video ingest (qa/contracts/video-learning.md), T-166 eval compiler (scenario → best/worst/edge cases), T-169 two-mode acceptance
PATTERN: "worst-case default" is a checkable UI defect class — a forced-choice field (relation: father/mother/other) that arrives pre-selected lets a user click through a wrong value; the explorer/grader should flag required choices with a default already applied · EVIDENCE: 02:08-02:49 · APPLIES NEXT: explore/grade heuristics, T-165 permission-surface pass
PATTERN: stalled-handoff checks — a request routed to a role (counsellor request → school admin / super admin) needs a "nobody acted in N days" nudge path; the tester should ask what happens when the next actor never opens it · EVIDENCE: 03:30-04:41 · APPLIES NEXT: multi-role flow cases (T-166), T-168 report "risk" section
PATTERN: per-flow validation plans accumulate and are stitched into one release regression that ends in an issues log — this is the product's own north star as the customer states it · EVIDENCE: 09:28-09:47 · APPLIES NEXT: T-167 release-triggered regression, T-168 damage-control report
**Status:** judged out of scope for D-039/D-040's three contracts (catalog.md, network-assertions.md,
crawl-traversal.md) — checked against each: the scenario-list pattern belongs to
`video-learning.md`/T-166 (not authored this pass); the worst-case-default pattern names "T-165
permission-surface pass," which D-040 split out to **T-171** (no contract yet); the stalled-handoff
and stitched-regression patterns belong to T-166/T-167/T-168. None fit CT/NA/CR criteria as scoped.
Left unfolded pending whichever unit builds T-171/T-166/T-167/T-168's contracts.


## 2026-09-24T16:33:00+05:30 · source: Umesh, chat (answers to the seven open decisions, verbatim)
> D-039 / decision-log append: "allow krr doo , goal pura hona chaiyee"
> D-040 / T-165 chain: "go on"
> AT-086 / AT-087: "go with the best"
> AT-365 data_class: "nhi ye dependecy user ne jo testing account diya hai usse depend krti hai , ye tho account dene wale tester ki galti hai hum concerende nhi hongee"
> ERP test account: "ye mai dungaa jab mai confident ho jaungee ki pathynks pr shi se chal rhaa, aur baaki koi bhi de skta hu , not only erp"
> T-126 adapter allowlist: "allow krr dee"
> AT-110 approval signing: "if needed tho krr dee"
PATTERN: acceptance is Pathlynks-first -- a new product's credentials (ERP or any other) are supplied only after AutoTester is proven on Pathlynks; the platform must stay product-agnostic ("not only erp") · EVIDENCE: ERP answer above · APPLIES NEXT: T-122/T-145/T-136 (ERP-named tasks should be re-scoped to "a second product"), T-169 two-mode acceptance
PATTERN: data exposure through a tester-supplied account is the account provider's responsibility, not a gate AutoTester enforces on its own repo scratch · EVIDENCE: AT-365 answer · APPLIES NEXT: AT-365 close-out, core-invariants data-boundary wording
**Status:** partially folded (2026-09-24, Mode B sweep) — PATTERN 2 (AT-365 data-boundary posture)
folded → `qa/contracts/core-invariants.md` amendment log (2026-09-24 row) + No-fire list entry;
ledger `AT-365` → `wontfix` with the same reasoning. PATTERN 1 (Pathlynks-first acceptance / ERP
task re-scoping) is a task-scope note, not a contract criterion — queued in `qa/QUEUE.md` for the
maker to re-scope T-122/T-145/T-136's ERP naming, not actioned by this sweep (checker never edits
`.goal/goal.json` task text). D-039/D-040/AT-086-087/AT-110/T-126 gate answers already recorded on
their own gate files (unchanged from the note below). Sweep: `qa/verdicts/sweep-2026-09-24b.md`.
Gate answers recorded in qa/gates/: t125-d039-entry-draft, t165-d039-traversal-scope,
at086-at087-credential-exemption-scope, at365-data-class-declaration, at110-approval-forgery.


## 2026-09-24T23:00:00+05:30 · source: chat (session under himanshu@ account; approval option selected: "Haan, Umesh approve")
> "and for subagents and all deepagents use ho rhee hai?"
> "tho humko deepagents with skills and all bnaane hai with tools . prompts as tool dene hai right /maker"
> AskUserQuestion: "Haan, Umesh approve (Recommended)" · "Wave 1 ke baad (Recommended)"
PATTERN: agents plan, deterministic tools act -- every AutoTester stage becomes a tool whose safety/credential/consent logic stays in code; the LLM layer only chooses what to do next · EVIDENCE: D-042 design · APPLIES NEXT: T-179..T-181, T-177
PATTERN: prompts are skills, not tools -- know-how ships as SKILL.md loaded on demand; tools are actions · EVIDENCE: user asked "prompts as tool"; corrected in chat · APPLIES NEXT: T-175, T-179
**Status:** folded 2026-09-25 by /checker Mode B sweep -> qa/contracts/agent-layer.md AL2/AL3 (deterministic guards run inside tools, in code; the agent layer only chooses what to do next) and AL4 (skills loaded via skills=, never inline prompt strings). Both patterns were already drafted into the T-179 criteria group (2026-09-24 init, grounded in D-042); no new criterion required. (Decision D-042; gate qa/gates/d042-deep-agents.md.)

---

## 2026-09-25 · maker (at576-577-serial-runs) · two items for the checker's judgement

**Status:** folded 2026-09-25 by /checker. Item 1 -> qa/contracts/execute.md E4 ("every `Evidence` recorded during this case") + amendment-log row, authorized by D-044. Item 2 -> filed as AT-578 (high), fixed in at576-577 cycle 2 (merged 8e50efc).

**1. `qa/contracts/execute.md` E4's wording is now imprecise.** AT-577's fix (`stages/execute.py::
run_case`) scopes a `RawResult`'s evidence to only the calling case's own slice of `session.state.
evidence` (via `evidence_start`), because the serial route reuses one `BrowserSession` across every
non-entry case in a run and the un-scoped return carried every earlier case's evidence too. E4
currently reads *"every `Evidence` the session recorded"*, which was true when a session ran
exactly one case but is no longer accurate now that a session can run several. Suggested correction:
*"every `Evidence` the session recorded for this case."* Not editing it myself — contracts are
checker-owned.

**2. A related, NOT-fixed cross-case contamination in `browser/assertions.py::_network_met`.**
While fixing AT-577 I found `_network_met` (used by `assert_expected` for a `network`-kind D-032
deterministic assertion) scans the WHOLE `session.state.evidence` for a matching NETWORK item, with
no case-scoping at all — unlike the `RawResult` field this unit fixed, this function reads the live
session list directly during a single `run_case` call. On a reused serial session, a case's `network`
assertion could in principle read `met` against a PRIOR case's captured traffic instead of its own.
I did not fix this: it is out of the two issues this unit addressed (AT-576/AT-577), touches
assertion-evaluation semantics rather than the RawResult reader shape the dispatch prompt asked me
to check, and no test in either new file exercises a `network`-kind expected state, so I have not
established whether it is reachable in practice (no case + rubric combination in this repo's fixture
projects currently declares one on a multi-case serial run). Filing for the checker to judge whether
it is real and worth its own unit.
