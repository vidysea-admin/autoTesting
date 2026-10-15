# Independent verdict - acceptance-baselines

Verdict: FAIL
Status: FAIL
Cycle checked: 1
Reviewed SHA: 417b3c011ec92308812a1436eb98a47b0bfb489a
Code/test SHA: 8d793363a2d0d3098ce4172eec8cf096036855c6

The source-project containment boundary fails for an actual Windows junction. A safe lexical slug can resolve outside the supplied source root. `prepare_baselines` resolves `source_dir` but only compares it with the destination, then reads the source configuration through the unresolved project path. The independent probe moved the fake product directory outside its source root and replaced it with a real junction. Preparation succeeded and wrote a success receipt: `source_escaped=true, refused=false, receipt=true`. Refuse resolved source-project escapes before reading config or creating output, and add a discriminating regression/proof. No real target or credentials were involved.

Evidence: `qa/evidence/acceptance-baselines/checker-cycle1/source-junction-probe.log`, exact probe/argv and hashes in `commands.json`, reproducible harness `checker.py`. This is a proven source-containment violation, not a setup gap. Core C8/C9 path isolation and the manifest's source-project containment claim remain unsatisfied.

Authenticated reuse: all 13 GREEN/attributable RED/exact restored GREEN chains, all 22 selected defenders, source/Git/lock/spec/harness/log/report hashes and 1,020 source-copy entries. Exact Python 3.11.16, installed versions, safe execution environment fingerprint and plugin hash independently matched (`compatible.json`). Seven draft variants are explicitly merged/unexecuted in maker selection; no repeated full suite or 13-mutation sweep.

Independent execution: retained Python preflight passed after one authorized ACL retry (original denial preserved). Focused script isolation, visible partial-write preservation and stale-config nodes passed (3 tests). Removing the stale-config comparison produced the named failure (exit 1); exact bytes restored and defender passed. Full argv, complete logs, exit codes, durations and hashes in `commands.json`; original failed preflight in `commands-sandbox-denied.json`. Production flag, SecretRef values/scopes, provider settings and no inherited approvals/truth were covered by positive execution and authenticated boundary proofs. Declared build remains unverified.

Accounting: BOOTSTRAP_REVIEW, maker/checker aggregate active seconds, tokens and cost remain unavailable/null; command durations are not maker denominators. Readiness and runtime conservative allocation debit is 140 seconds/4,500 tokens including retry; protected finalization is 30 seconds/800 tokens (within 180/6,000). Exact monotonic whole-phase accounting was unavailable; no efficiency-compliance claim. Budget inputs/results are preserved. Combined integration pytest/Ruff/doctor, real acceptance and original task completion remain parent-owned and uncertified. No merge or push.
