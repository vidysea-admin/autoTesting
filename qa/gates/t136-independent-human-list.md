# HUMAN_GATE (OPEN) - independent human bug list for T-136 and T-169

**Opened:** 2026-10-10 (D-081 item 2). **Decider:** Umesh. **Status:** OPEN. No Answered line.
**Blocks:** T-136 (trust number: recall, FP rate, time) and T-169 (generic two-mode acceptance, which depends on it).

Question: where does the human tester's bug list for Pathlynks come from? Options: (A) a tester who has not seen AutoTester's report writes it; (B) Umesh writes it before opening the report.

Why it is open: AutoTester's Pathlynks report is delivered first (`d081-pathlynks-report-first.md`). A list written after reading it cannot produce the recall number (AT-653, `qa/contracts/bench.md` K6-K9): recall is computed from the independent subset only, and the artifact must say `recall: unavailable (ordering not recorded)` rather than a number with absent provenance. FP rate survives either ordering.

T-136 and T-169 stay pending and are not buildable until a list exists. The ERP truth sheet is not on the critical path (D-080 item 4).

Answered (partial, ordering): 2026-10-12 - Umesh (chat): "phle ek level build krr dee, firr feedback deke fix krwaaungaa" - build the AutoTester column + comparison artifact first; Umesh gives his findings as feedback afterwards. Per AT-653 a list written after reading the report gives recall: unavailable (ordering not recorded); FP rate and time stay valid. D-086 item 4. Source of the human list (A tester / B Umesh before reading) still OPEN.

Answered 2026-10-13, see D-089: build T-136 now WITHOUT the human list; AutoTester produces its own analysis and report. Recall vs a human stays unavailable until Umesh provides a list later; FP rate and time are still measured. No-list is a supported mode, not an error.
