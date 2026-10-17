# at854-loop-md — rewrite qa/loop.md to the current maker policy (AT-854, folds AT-754)

Status: merged-no-check (docs-lane)
Fix cycle: 0
Branch: wave/at854-loop-md (base int/1017 ab99c07d)
Lane: docs (only `qa/loop.md` and this manifest changed; no code, test or contract)

## What changed (qa/loop.md)
- :7-14 Prompt paragraph: sweep-due rule and work sources now as SKILL.md:13, 663-665.
- :79-82 Choose: open issues, sweep findings and Candidates rows are not built without `approved:`.
- :92-97 On FAIL: fix-cycle cap 2 then STALLED (was "max 3 cycles"), plus no-progress stop.
- :104-131 terminal states: ADVANCED evidence rule; BACKLOG_EMPTY = goal met; HUMAN_GATE gate file,
  notify, `Answered:` line, pointer to D-081 and the three open gate files (replaces the T-050/T-060
  example, which is AT-754); STALLED and EXHAUSTED diagnose first.
- :132-141 PAUSED: three writers (user, .9-16b no-progress, .9-16c quota/rate limit), resume by user
  message only, SendMessage resume (.14-5), and the .12 closure-mode note.
- :146-152 Human gate, live Pathlynks: signed RunApproval, production:true (D-096), D-081 item 3,
  D-104 item 3, Tracker write still gated. :153-156 DECISIONS bullet now cites D-103, not AT-015.
- Kept unchanged: D-100 block, the BLOCKED cap of 6 (AT-566, status fixed in qa/issues.jsonl).

## Verification (commands run)
- Policy sources read: SKILL.md:13, 34, 57, 157-165, 167-176, 663-665, 756-762, 1691; .9-16 text at
  proportional-verification-pattern.md:238 (grep "The loop speaks (.9-16)").
- `sed -n 2332,2352p docs/DECISIONS.md`: D-081 items 3 and 7 as cited. D-096, D-103, D-104 item 3 read
  at docs/DECISIONS.md:2586, 2682, 2696.
- `grep -l -E "HUMAN_GATE \((OPEN|PARTIAL)\)" qa/gates/*.md` -> t136-independent-human-list.md,
  t199-first-live-write.md, t203-host-and-dns.md (the three named). `ls` confirms live-acceptance-runs.md.
- `grep PATHLYNKS_MONGO_URI` -> src/autotester/browser/db.py (the key exists).
- goal.json: rubric_ref done_check on T-050, T-110, T-120 (loop.md:21 unchanged and correct).
- `grep -n -i "max 3|T-060|AT-015" qa/loop.md` -> 0 hits (T-050 remains only at :21, correct).
- `uv run autotester doctor` -> "doctor: clean". loop.md is 164 lines.

## Needs code
- None. Open point for the owner: SKILL.md:158/165 still list the .9-16b no-progress pause while .12
  (SKILL.md:57, 1691) says no automatic qa/.paused; loop.md reports both and does not resolve it.
