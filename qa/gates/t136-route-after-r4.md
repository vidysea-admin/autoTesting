# HUMAN_GATE: T-136 route after live run 4 (opened 2026-10-19T03:05+05:30)

Question: T-136 cannot finish from run output alone: runs r3 and r4 report 0 findings, so the acceptance comparison check exits 1 (INCOMPLETE: false_positive_rate unavailable). Which way?

Options:
1. Supply the independent human bug list (qa/gates/t136-independent-human-list.md); the comparison then scores AutoTester against it.
2. Switch to route (b) as defined in qa/gates/live-acceptance-runs.md.
3. Stay on route (a) and wait for a Pathlynks build with known defects.

Two related product decisions the r4 run raised:
- Negative-path cases (e.g. case_a5ea57c0961a, met visible_text assertion) are held INCONCLUSIVE by the C12 note guard (stages/grade_note_guard.py:193). May a negative-path case PASS?
- case_efaed2c0eb91, case_7a978722a38c and case_093f5070df79 have no deterministic assertion (093f step 4 has expected: None), so B11 (stages/grade_images.py:35, :89) holds every judge PASS. Should these cases get expected assertions?

Answer format: "T-136: option <n>; negative-path PASS yes|no; add assertions yes|no".
Blocks: T-136 close; T-169 and T-206 use the same comparison path.
Evidence: D:/autoTesting/.work/t136-live-report-r4.md (run-01M58F744J7R3CB99CMH9S7FQ3), -r3.md.

Answered: 2026-10-19 — option 2 (route (b): crawl-issue -> findings converter; crawl issues count as findings); negative-path PASS yes; add assertions yes — Umesh chat 2026-10-19 "go with the best way possible and with your recommendtation" (accepting the maker's recommended defaults); D-106. Units: t136-route-b, t136-negpath-assert.
