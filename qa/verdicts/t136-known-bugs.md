# Verdict - t136-known-bugs

Cycle checked: 1
Verdict: PASS
Checker: independent (not the maker), diff review of wave/t136-known-bugs plus tests on the merged tree.

- Privacy: the diff adds nothing under `.work/` and no corpus data; tests use synthetic rows (X-1, X-2...). The only mention of the source is the name in D-094 and the gate note, as Umesh's decision text. `scripts/known_bugs_corpus.py` refuses any output path git does not ignore (test covers it).
- Provenance labelling: new corpus mode `known_bugs_ai_assisted` accepts only provenance `ai_video_review` (validator rejects `human_independent`); denominator population is `ai_video_review`; `recall_basis` = "AI-assisted video review, not independent" is stored in the artifact and printed first by the renderer; FP rate stays unadjudicated without a human list. It is never mapped to `human_independent`.
- Reuse: scoring goes through `bench.scorecard` and `BenchTrial`; the converter only builds a `BenchCorpus`. `DENOMINATOR_PROVENANCE` replaces two inline conditionals with the same results for fixture and human_confirmed.
- Schema: `recall_basis` added to a model that keeps extra="forbid" via its base; Literal types widened additively.
- DECISIONS.md is a pure append on master (16 added lines, 0 removed). Contract K12 and the gate note are additive; K1-K11 unchanged.
- Notes (non-blocking): the branch edited qa/contracts/bench.md itself under a "/checker fold-in" label; accepted here because it records D-094. Result line of D-094 says K11 where the contract section is K12.
- Runs: test_acceptance_comparison + test_bench_from_run 21 passed; ruff clean.
