# Independent verdict - acceptance-baselines

Verdict: PASS
Status: PASS
Cycle checked: 2
Reviewed SHA: 8ace681a3e4ae48cbb0f383fc121bf3c44d13a4e
Code/test SHA: 35624de61e94b6b94286b0fe679141566892304d

Bounded DELTA PASS: the two-hunk repair resolves both source-project directory and config under the resolved supplied root before config reads, input copies or output creation. Reading uses the validated config. The separate approved teaching-input root policy remains unchanged. Core C1/C2/C5/C6/C7/C8/C9/C10 and D-100 isolation/proof boundaries are satisfied within this unit scope; this does not close T-169/T-206/T-136 or certify combined integration.

Independent authentication: retained cycle2 seal assertions authenticated all 1,020 raw source-copy entries, six command/log/spec/harness/lock chains, source Git bindings, GREEN three cases, named outside-project-junction RED, exact restored source and three GREEN. Current candidate evidence blobs match Git. Installed dependency versions match retained identity. Prior compatibility receipt hash and historical identity match reuse.json. All 1,018 unchanged raw inventory entries match the prior inventory; original tests are byte-prefix preserved, and exact source delta inspected. Historical 13 chains remain prior-SHA evidence authenticated by cycle1; they were not relabelled or rerun. Direct unrelated Git blob versus Windows checkout equality at cli.py differed because recorded raw representation is distinct; no bytes were normalized. Reuse is justified by unchanged helpers/schema/script/tests and boundary-only source delta.

Independent runtime: retained Python 3.11.16 imports this checkout. Preflight first failed temp ACL (preserved), one authorized escalated retry passed. Ordinary valid in-root config succeeded with one config read and output. Actual project.json directory junction resolved outside source root while project directory remained inside: source-project refusal, zero config reads, no output. This discriminates the config branch independently of project-directory escape. Real file symlink attempts failed WinError1314 even under escalation; that limitation is preserved. The directory junction is not a readable valid config and does not prove successful file-symlink relocation. Maker's legitimate in-root project junction succeeds; source inspection permits legitimate resolved in-root configs. Evidence/harnesses: qa/evidence/acceptance-baselines/checker-cycle2/.

Cycle1 FAIL and actual escaped-source success reproducer remain authoritative history at 93d9ad143937fbf4b5353441da4a2a0e930e5259 and cycle2/cycle1-verdict.git.md, with checker-cycle1 raw logs unchanged. This PASS judges only the repaired cycle2 candidate.

Accounting: prior 170s/5300 tokens retained; additional conservative allocations readiness20s600, runtime40s1100 and protected finalization30s800, cumulative260s7800. Maker and reviewer actual active time/tokens/cost remain null; phase monotonic actual measurements unavailable, so no budget-efficiency or ratio compliance claim. Parent-authorized finite escalation and phase assessments retained. Wait/CPU queues are not invented as maker time. Full pytest/Ruff/doctor remain parent combined integration gates; real acceptance, independent human recall and build verification remain open. No merge/push, project account or approval mutation.
