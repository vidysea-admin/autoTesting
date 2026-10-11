# Verdict t154-adversarial-pass (coordinator B) - Cycle checked: 0

Bound to D:/autoTesting. Judged diff ff901f72..575a7c3f in a git-archive copy. Policy proportional-verification/2026-10-10.9. Dual check, blind.

## Plan
Tier L (consent gate 2, the only probe-sending path; cited trigger `dual-trigger` src/autotester/stages/adversarial.py:108). Emphasis: try to get a probe SENT when it must not be, refusal-write containment, secrets. Checks: AD1..AD7 verify commands once, the proof script, my own attacks (about 55 counting-transport cases), one own falsification per criterion, step 4c diff-scope read. No full suite (other coordinator), no live probe, no model or network call.

VERDICT: PASS
SCOREBOARD: 7/7 criteria met, C5/C7 as exercised by AD5/AD7 hold
TIER: L (security: consent gate 2, only probe-sending path; adversarial.py:108)
FAILURES: none

- AD1 met: 7 refusal paths in the tests raise with 0 sends and the tree differs only by `ai/adversarial/refusals.jsonl` (plus parent dirs), one line. My attacks (expired, crawl/read row, other project, tampered rows, no key) gave the same.
- AD2 met: `require_approval(target=endpoint, probes=planned, wall_clock_s=...)` at :108; `probes 4 > approved 3`; trailing slash, host case, query string and base target each refused; sibling, suffix and userinfo hosts refused.
- AD3 met: production=True needs a production=True ADVERSARIAL row; a crawl row with production=True is not credited; a row flipped to production in the file is refused (signature).
- AD4 met: `grep -rniE "garak|pyrit|deepteam" src pyproject.toml` -> exit 1; 5 .md probe files, 15 probes, loaded via load_probe_sets.
- AD5 met: `grep "Result\.|Verdict(" adversarial.py` -> exit 1; ProbeRun has no verdict/passed/score field; no grade import.
- AD6 met: 51 probes with a 1e9 approval, and 60 via duplicate set names, both ProbeCeilingExceeded naming 50, 0 sends.
- AD7 met: the row has exactly target, timestamp, requested_probes, reason; probe text and the secret never appeared in the log in any refusal I triggered (secret in endpoint, in a probe_sets name, in probe text raw and base64).

Commands re-run: pytest tests/test_adversarial.py -> 25 passed; scripts/adversarial_proof.py -> exit 0, 10 HELD; ruff on changed files clean.

CAPABILITY-COVERAGE: 7/7 criteria reproduced with my own mutants, not the builder's: AD1 kind=CRAWL and refusal-also-makes-a-run-dir; AD2 probes=min(planned,3); AD3 ProbeRun.production=False; AD4 drop the empty-set block; AD5 add a `passed` field; AD6 `>` -> `> +1`; AD7 requested_probes=0 and append dropped. Each named test green in its own copy before and red after on an assertion (DID NOT RAISE or assert), none on import or setup.
DIFF-SCOPE (4c): new files only, plus .gitignore +4 and docs/MAP.md +12 (generated; includes two rows for T-153's ai_capture and ai_judge). Nothing removed or renamed; every file is in the manifest's What changed.
LIVE-BROWSER: not-applicable (no UI path changed)
ISSUES-WRITTEN: none (dual coordinator; findings below)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: No input made the transport send when it should not. Every gate holds (project, kind, exact target, signature and id, expiry, production, probe bound, wall-clock bound, ceiling, host, secret). A refusal writes one non-secret line only. The wall-clock latch is checked before every send: 0 extra sends after it, 2 of 4 sent when each send consumed the budget. The items below are test gaps and design notes, none a defect in the changed code.

PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":"No test refuses on a wall-clock shortfall: mutant wall_clock_s=0.0 in the require_approval call at adversarial.py:108-110 survives all 25 tests; the exact-ceiling case (50 probes allowed) and the wall-clock boundary are also unpinned","evidence":"qa/evidence/t154-adversarial-pass-b/attacks.md"}
PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":"The refusal log scrub of target= and reason= (adversarial.py:123-124) has no test: removing either survives; the live path is a secret in the endpoint or in a probe_sets name","evidence":"attacks.md Survivors"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"probe_sets names are joined into a path unchecked (adversarial.py:79): '../outside' loaded and sent a .md from outside prompts/probes; a send already in flight has no timeout (the wall clock is checked only between sends); operator-controlled, no CLI yet","evidence":"adversarial.py:79,144-148; attacks.md"}
PROPOSED-ISSUE: {"severity":"low","type":"design-note","title":"An approval is not consumed (3 passes on one max_probes=4 row sent 12, a per-run bound as AD2 words it); an invalid wall_clock_s raises ValueError with no refusals.jsonl row; host, secret and probe-file refusals raise AdversarialBlocked or CaptureWithheld rather than ApprovalRequired (nothing sent, still logged); production is stated by the caller and never inferred (CN7 boundary)","evidence":"attacks.md"}

Metrics: start=2026-10-10T20:09:02Z end=2026-10-10T20:28:00Z wall_min=19 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=12 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1140 mutants=10 defects_unit=0 defects_6c=0
