# Umesh decisions 2026-10-17 (asked via AskUserQuestion in the maker session; his chat instruction: "fix all of these too")

- AT-927 (T-155 open product choices 1-2): store behavioural captures + judge verdicts under projects/<slug>/ai/; report format = the Excel workbook only (no new surface).
  Answered: 2026-10-17T14:38:00Z — projects/<slug>/ai/ + Excel — maker session chat (AskUserQuestion)
- AT-665 (video corpus purpose): the team's existing screen recordings are the labelled human-tester BENCH BASELINE for the AutoTester-vs-human scorecard (T-136/T-169). Case generation and heuristic tuning not chosen.
  Answered: 2026-10-17T14:38:00Z — bench baseline — maker session chat (AskUserQuestion)
- AT-858 (qa/hooks/mc-sessionstart.ps1 UTF-8 output encoding before first non-ASCII print): Approved-by: Umesh. DECISIONS entry to follow via scripts/append_decision.ps1.
  Answered: 2026-10-17T14:38:00Z — Approved-by: Umesh — maker session chat (AskUserQuestion)
- ISS-t192-url-pattern-heal-1: Umesh ratifies `uv run autotester ingest map erp` as satisfying gate t135 answer B in place of the literal `analyze` command.
  Answered: 2026-10-17T14:38:00Z — ratified — maker session chat (AskUserQuestion)
- AT-750 / AT-752 / AT-616 / AT-376: "fix all of these too" — routed: AT-750 checker HOLD-or-flake decision; AT-752 contract re-anchor via feedback-inbox fold (D-? 2026-09-27 ground truth = parallel human tester); AT-616 second checker red/green re-run; AT-376 fix in D:/ai_os shared validation (no push).

## Second round (Umesh, maker session chat, 2026-10-17T18:10:00Z)
- Stale .git/index.lock: "go for it, i allow you" -> deleted by the maker.
- Live acceptance runs T-136/T-169/T-206: "hnn tho tu autotester se test krwaa aur report ready krr, humman ka mai dekh krr validate kr lungaa, tujhe human ka wait kyu krna hai tu run krr". Approve live runs: YES. T-136 route: (a) live graded run, AutoTester column first; Umesh validates the human side afterwards.
  Answered: 2026-10-17T18:10:00Z — approve live runs yes; T-136 route a; Karunn doc not confirmed (not blocking) — maker session chat
- AT-281 comparison format: "close it agar ho gya hai tho human dependency naa k barabar rakho". Format accepted; human dependency kept to Umesh's after-the-fact validation only.
  Answered: 2026-10-17T18:10:00Z — format ok, close when done — maker session chat
- G11 multi-role (T-207..T-220): "tu build krrlee, multi role authentication laakr dunga tho krr legaa naa tu bhi". Build approved now; real role credentials arrive later from Umesh. D-104.
  Answered: 2026-10-17T18:10:00Z — Approved-by: Umesh, build now — maker session chat
- AT-697/699 new src module: "yes go for it". D-104.
  Answered: 2026-10-17T18:10:00Z — yes — maker session chat
- projects/pathlynks/bench/pathlynks-acceptance.comparison.json uncommitted change: "jo jaruri hai vo rakho, baaki remove". Maker kept it (only a regenerated created_at and the new recall_basis field emitted by current code).
