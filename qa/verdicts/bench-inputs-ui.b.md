# Verdict - bench-inputs-ui (dual check, coordinator B, blind)

Cycle checked: 0
Reviewed SHA: c4c3dccc (code 16bcf2b4; base 8956c9bc; branch wave/bench-inputs-ui, integration branch int/1019)
Policy-Version: proportional-verification/2026-10-19.17
Bound to: D:/autoTesting/.worktrees/bench-inputs-ui. Dual check: PROPOSED-ISSUE lines only, no ledger rows, no goal-task close.

## Check plan (step 0)
Auth + private upload (L) -> affected-test re-run, 1 falsification per criterion plus security mutants (copies), diff-scope read (4c), Mode D own Playwright browser (localhost:8791, isolated context), HTTP probes (CSRF, permission denial, slug/id injection, upload limits, never-served), and one concurrency probe of the mark store. Sub-checkers: none.

VERDICT: FAIL
SCOREBOARD: C1 NOT MET (one defect), C2 met, C3 met; invariants: no function/route/test removed, diff scope matches "What changed"
TIER: L (auth + private-file upload; maker dual-trigger lines src/autotester/ui/routes_bench_inputs.py:49 and src/autotester/stages/bench_inputs.py:49, both read by me)

FAILURES:
- [C1] sev: medium - acknowledged rulings are lost under simultaneous marks. `stages/bench_marks.py::set_mark` (lines 42-51 at 16bcf2b4) is load -> modify -> `write_json` with no lock, and the route `ui/routes_bench_inputs.py::mark_finding` is a sync `def` (one thread per request). Reproduce: `.venv/Scripts/python.exe -I qa/evidence/bench-inputs-ui-B/race.py` against a `git archive 16bcf2b4` copy (output `race-16bcf2b4.txt`): 10 of 10 rounds of 20 simultaneous `set_mark` calls lost acknowledged marks (e.g. 10 acknowledged, 2 stored), 147 `PermissionError` on `os.replace`. Rulings are what `fp_rate` is computed from (C1), so a silently dropped ruling changes the rate. This agrees with coordinator A's live-server finding (14 of 25 pairs). I first filed it low from a code read without running it; the run makes it a FAIL. Fix direction: serialise the read-modify-write (process lock plus replace retry) and add a thread test. The worktree now holds uncommitted maker edits that appear to start this; I did not check them.

PROPOSED-ISSUE: {"severity":"medium","type":"data-loss","title":"bench marks: simultaneous marks lose acknowledged rulings and raise PermissionError","where":"src/autotester/stages/bench_marks.py:42-51 set_mark","evidence":"qa/evidence/bench-inputs-ui-B/race-16bcf2b4.txt: 10/10 rounds lost acknowledged marks, 147 PermissionError","fix":"lock around read-modify-write; tolerate os.replace race; thread test"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"atomic-list upload: 256 KiB cap applied after the whole body is received","where":"src/autotester/ui/routes_bench_inputs.py:71 (await request.form())","evidence":"http-probes.txt: a 40 MB upload was received in full, then refused 400 in about 0.3 s, stored list unchanged; ui/upload_stream.py already streams with a limit","fix":"stream with a limit of MAX_BYTES plus overhead; editor-only"}
PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":"size cap and error-echo guard are not pinned by tests","where":"src/autotester/stages/bench_inputs.py:50 (MAX_BYTES check), :41 (include_input=False)","evidence":"mutants.json: S-cap (`if False:`) survived 7 passed; S-echo (include_input=True) survived 7 passed (equivalent today: _reason reads only loc and msg). Live: 262144 bytes accepted, 262145 refused","fix":"a test at MAX_BYTES and MAX_BYTES+1 that is valid JSON"}
PROPOSED-ISSUE: {"severity":"low","type":"design-question","title":"adjudicated fp_rate excludes matched known-bug findings from its denominator","where":"src/autotester/schema/bench.py (adjudicated_fp_rate)","evidence":"label adjudicated_findings_only discloses it; confirm with Umesh that this is the intended rate","fix":"decision only"}
PROPOSED-ISSUE: {"severity":"low","type":"robustness","title":"marks and upload edge behaviour","where":"routes_bench_inputs.py, bench_inputs.py:65","evidence":"a bad upload shows a bare '400 Bad Request' page; a mark for any 16-hex key with no finding is stored (cap 5000); clear on an unknown key writes an empty marks file; a dot-segment `next` under /projects/{slug}/ passes (same-origin); fixed tmp name atomic-list.json.tmp under two concurrent editors","fix":"optional"}
PROPOSED-ISSUE: {"severity":"low","type":"process","title":"T-218 reader not wired; MAP.md stale; 6c full-suite trigger","where":"stages/bench_inputs.py::load_pinned_list (no caller); docs/MAP.md; affected-set tool","evidence":"C2 'pinned where T-218 reads it' holds as a location contract only. doctor reports 2 MAP.md stale violations (merge queue). full-suite trigger for 6c: security/auth L unit (.13-2(a)) and shard_suite --candidates returned integration-required (conftest imports; 406 of 543)","fix":"6c runs the full suite"}

## Evidence by criterion (all under qa/evidence/bench-inputs-ui-B/)
- C1: browser (browser-drive.py, report.json, screenshots) marks false positive / real / undo / re-mark on the crawl page and the run page (redirect back); unmarked stays unadjudicated; `scripts/check_acceptance_comparison.py` printed `fp_rate: 0.6667 (adjudicated_findings_only)` from 1 real, 2 false positive. Viewer: "read-only", no buttons, POST 403. Anonymous 302/401, pending account 403, edit-only-not-assigned 404, nothing written (http-probes.txt). Fails only on the concurrency defect.
- C2: editor upload stored at `.work/ceo-bench/<slug>/atomic-list.json`; sha256 equals the pin and the page; item ids and text never shown; no link; 8 GET paths (editor and anonymous) 404/403/405/302, no leak; 14 bad bodies (empty, not JSON, extra key, bad priority, duplicates, NaN, BOM, deep nesting, bad UTF-8, string, over cap) 400, nothing stored, no echo; traversal filename ignored; replace records `replaced_sha256`.
- C3: every control labelled (keyboard Enter submits); sidebar sub-link and project button reach /projects/demo/bench; only external requests are the base Google Fonts links already in theme_style.py at 8956c9bc (diff adds none); CSRF (cross Origin, Referer, Sec-Fetch-Site, bad-port Origin) 403 via the existing D-066 guard; slug injection 404/400; finding id `^[0-9a-f]{16}$`; stored XSS escaped.
- 4c scope: diff removes no function, class, route or test; all 20 files are in "What changed".

## Re-run and falsification (copies, green before, red after)
- Tests: scoped 36 passed; affected set of 18 files 274 passed (110 s); ruff clean; doctor 2 MAP.md violations only.
- Falsification[C1] bench_marks `marked()` -> `if True:` red. [C2] pin digest `raw[:-1]` red. [C3] label removed red. Security: auth `may_mark` weakened red; `_KEY` check removed red (2 failed); `next` unchecked red. Survivors: S-cap, S-echo (low, above). See mutants.json.
- Gap in the maker's tests: no concurrent-mark test at 16bcf2b4.

CAPABILITY-COVERAGE: 3/3 floor rows reproduced
LIVE-BROWSER: qa/evidence/bench-inputs-ui-B/ (6 screenshots, report.json; own Playwright on localhost:8791, console errors 2, both deliberate refusals; server PIDs mine, stopped)
ISSUES-WRITTEN: none (dual check)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: C2 and C3 hold on every probe, and C1 works end to end in the browser and the scorer, but the mark store is an unlocked read-modify-write: simultaneous editor requests silently drop acknowledged rulings and raise PermissionError (reproduced 10 of 10 rounds), and those rulings are what the false-positive rate is computed from. That one correctness defect fails the unit; everything else is low.
Metrics: start=2026-10-21T07:52:50Z end=2026-10-21T08:12:00Z wall_min=19 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=9 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1150 mutants=8 defects_unit=1 defects_6c=0
