# Gate — AT-052: whole-platform BFS crawl + video-corpus eval methodology

**Question:** should AutoTester's scope grow to (a) an autonomous whole-platform BFS crawl that
clicks every icon/button on a live logged-in product and builds the full screen graph itself, and
(b) a video-learning pipeline that mines `C:\Users\Lenovo\Videos\Screen Recordings` (and future
screen-recording uploads) as ground truth for how the team currently tests — and if so, how do
these relate to the already-shipped DFS-trace + BFS-merged-tree report visualizations (F-027/
F-028/F-029) and the existing reviewed-FlowSpec-driven ingest/expand pipeline?

**Options:** (1) scope both as new, explicitly-bounded capabilities with their own contracts —
building on the plan already drafted this session (video pipeline ported into this repo, 2-model
Gemini ensemble, BFS explorer generic/not URL-bound); (2) scope only one of the two now, defer
the other; (3) decide neither belongs in this repo's north star as currently written and this is
a separate project; (4) something else that emerges from the grill.

**Command:** `/grill "whole-platform BFS crawl + video-corpus eval methodology"`
**Capture path:** `D:/autoTesting/brainstorms/<tick-date>-bfs-video-corpus-grill.md` (this project
sits outside `D:/ai_os`, so `/grill`'s own path table routes it here, not to
`D:/ai_os/umesh/brainstorms/`).

**Blocks:** AT-052 (`qa/issues.jsonl`); the GRILL row in `qa/QUEUE.md`; any future unit that would
build Capability A (video learning) or Capability B (BFS explorer) from the earlier planning
discussion this session — none of that work should start before this gate is answered.

**Opened:** 2026-09-06T14:13:52+05:30 (first named by the checker sweep this session)

**Answered:** 2026-09-07 — **Option (1): scope BOTH as new, explicitly-bounded capabilities
with their own contracts** — plus a third, prerequisite capability the gate did not anticipate.

Answered by Umesh directly in conversation (2026-09-07), not by a `/grill` session. He was shown
the three gaps as limitations and replied:

> *"tho mere bhai mai account ki credentials dunnga na tujhe test krne ko. point ye hai ki tune
> maanga hi nhi mujh see"* — I would have given you the credentials; the point is you never asked.
>
> *"mere bhaai ye sab tho honaa mandatory"* — all of this is mandatory.

Four scoping decisions, captured via AskUserQuestion the same turn:

| Question | Answer |
|---|---|
| Order | **All three in parallel** (video learning, BFS explorer, logged-in testing) |
| Explorer blast radius | *"this will all dependent on the account of which credentials provided. jo jo uss account mai access hoga vo krr lengee"* — the test account's own permissions are the outer boundary |
| Credential handover | *"platform mai hoga credentials input krne ka option"* — typed into the tool's own UI, never into chat |
| Video outputs | *"product map, Test cases, issues excel and product flow end to end. like all maximum learning we can take"* — all four |

**Relationship to the already-shipped F-027/F-028/F-029 report visualisations:** unchanged and not
re-litigated. Those render a *run's own* trace; the crawl produces a *product* graph. The crawl
feeds `Screen`s into a FlowSpec so the existing `expand` can generate cases from them — it does
not replace the DFS-trace or merged-tree report.

**A third capability, discovered while planning and not in this gate's options:** credentials
cannot be entered in the platform at all today — no UI route writes `project.json::secrets`, so
`GET /projects/<slug>/env` renders "This project declares no credentials" and every POST 400s.
Umesh's chosen handover method therefore does not exist yet, and both other capabilities need a
logged-in app. This becomes Track 0 and lands first.

**Where the full scope lives:** `C:/Users/Lenovo/.claude/plans/great-when-you-really-iridescent-ocean.md`
(approved 2026-09-07) — Track 0 credentials, Track A video learning, Track B autonomous explorer,
each broken into individually contract-backed, checker-verified units.

**Not granted by this answer:** no wildcard for `allowed_domains` (still the boundary the browser
may not cross); no `CaseClass` enum expansion; video-derived issues get their own `Issue` schema instead.

Decision claim D-005: "`CaseClass` stays closed; `extra=\"forbid\"` stays." <!-- decision-claim: {"id":"D-005","what":"`CaseClass` stays closed; `extra=\"forbid\"` stays."} -->
