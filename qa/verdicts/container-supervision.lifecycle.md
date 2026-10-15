# Container supervision lifecycle review

**Verdict:** HOLD
**Status:** NEEDS_EXTRA_REVIEW
**Cycle checked:** 1
**Reviewed SHA:** 326bf0a7ffa5296a81bcbe0bc5a112903bb68787
**Base SHA:** 40299c04cc1c7e9cc247a14cd1a4da89d6f58377

Independent lifecycle scope: docker/supervise.py and docker/entrypoint.sh. Source review covers startup readiness ordering, any-child-exit failure, startup signals, process-group TERM/KILL, tracked/adopted reaping, and platform branches. No demonstrated lifecycle acceptance violation identified in the reviewed source. This is incomplete verification, never PASS.

Read checker skill first. Independently read packet, manifest, supervisor, entrypoint, synthetic tests, docker contract and relevant hosting rows. git rev-parse HEAD matched reviewed SHA. Budget helper assess against primary-root .work/checker-dispatch/container-A.json exited 0 with BOOTSTRAP_REVIEW, ratio_verified=false, sibling debit90 active seconds/3000 tokens retained.

Read readiness.after.json and all14 guard definitions in mutations.json. Full independent verification of every source/environment/green-red-restored binding was not completed within the allocation; therefore no runtime tests were run and no receipt reuse is certified. Named readiness mutation receipt records exit1 and matching interpreter/source/lock fields, but inspection of one receipt does not establish all14 provenance chains.

Required next phase: finite newly authorized allocation preserving sibling90/3000 plus lifecycle90/3000 committed debits. First finish guard provenance validation; then interpreter/import/temp preflight and selected direct synthetic readiness, exit-cleanup, signal, POSIX-group/reaper/escalation tests plus an independently constructed lifecycle failure probe. Run applicable D-100 scoped AST/Bash checks. Integration owner retains full combined gates.

Windows/Git Bash synthetic evidence cannot certify Linux process groups, PID1 orphan behavior or Docker. Docker unavailable; actual Linux/Docker HO5 and D1-D3 acceptance, restart/healthz recovery and deployment gates remain pending. Exposure/nonroot/VNC review belongs to the separate reviewer.

Accounting: lifecycle allocation90 active seconds/3000 tokens inclusive reads/probes/verdict; sibling allocation90/3000, aggregate180/6000. Actual host tokens/cost and maker active usage unknown; measured10% success unverified. Review began approximately2026-10-15T08:20 UTC; exact monotonic start/end unavailable, so actual active time remains unknown. No child/retry or shared integration suite was run. Checkpoint follows budget exhaustion risk, not successful gate completion.
