# Task-level verdict - T-201 team Test button (independent close-out, 2026-10-13)

Contract `qa/contracts/team-test-button.md` TT1-TT7. TT8 and TT9 (email) are DEFERRED TO PRODUCTION (D-093 item 2) and not judged.

VERDICT: PASS

| Row | Result | Evidence |
|---|---|---|
| TT1 gate, no trace on refusal | PASS | t201b r3.a and r3.b (cycle 2); live: anonymous 302, cross-origin 403 (t201-live) |
| TT2 request not a run, status page | PASS | r3 verdicts; live: press to status page in 0.36 s, running then done (t201-live); queued-with-position under a one-slot real RunQueue in test_inbox_scope |
| TT3 attribution from the session | PASS | r3.a, r3.b (requested_by_id on entry and Run, forged body ignored, golden run.json loads); live header "Started by dev@live.test (user #2)" |
| TT4 one launcher | PASS | r3 verdicts (AST test, unedited RU tests); live run executed in a real headed browser |
| TT5 queue seam | PASS | r3 (fake queue) and t201-live (real queue file, second press returns the same run, one entry) |
| TT6 credential-derived approval, refusal leaves no trace | PASS | r3; live: refused page names the state, queue file and runs/ byte-identical |
| TT7 inbox filtered to report.view, label, DeliveryRecord | PASS | t201c cycle 1 FAIL (missing inbox DeliveryRecord) then cycle 2 PASS (qa/verdicts/t201c-inbox.r2.md); scope table 4 users x 2 projects; label defined once |
| Persona walk (Mode D) | PASS for the website half | qa/evidence/t201-inbox-walk/: dev presses Test, run appears in My reports as running then done with the label INCONCLUSIVE (mock judge, expected) and links to the report; tester with no relation sees no rows and the direct run URL is the same 404 as a missing run; admin sees it; anonymous GET /inbox is 302 to login. Email steps deferred with TT8. |

Notes: the label INCONCLUSIVE is the mock judge, not a grading claim. Dependency T-200 is still open (its TS5 inbox-for-blocked-slot gap); no TT row depends on it, so T-201 is closed on its own contract.
