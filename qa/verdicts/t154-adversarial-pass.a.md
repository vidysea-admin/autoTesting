# Verdict — t154-adversarial-pass, coordinator A (dual check)
Bound to D:/autoTesting. Checked HEAD 575a7c3f (product fd7362a8, diff ff901f72..575a7c3f). Cycle checked: 0. Resume: 0 of 2. Retry: 0. Date 2026-10-11.
Policy-Version: proportional-verification/2026-10-10.9. Blind to coordinator B (its verdict, checkpoint and evidence were not read). PASS here would have no side effects; PROPOSED-ISSUE lines only.

## Check plan
Tier L, dual (trigger cited `src/autotester/stages/adversarial.py:108`, confirmed by reading :108-110 and core/consent.py ADVERSARIAL path). Checks: AD1-AD7 by own re-run of `tests/test_adversarial.py` (25) and `scripts/adversarial_proof.py`; step 4c diff scope; one falsification per criterion in own copies; live-path grep (no browser, no UI); one checker full suite (security trigger).

VERDICT: CONTINUE-NEEDED
SCOREBOARD: 7/7 criteria met on every check run so far, 0/0 invariants violated; PASS withheld only because the mandatory full suite has not run
TIER: L (security: consent gate 2 and the only probe-sending path; `adversarial.py:108`)
REMAINING (copy into the next dispatch): ONE full suite of 575a7c3f via `shard_suite.py --repo D:/autoTesting/.worktrees/t154-adversarial-pass --ref 575a7c3f --shards 1 -- -o addopts=` (about 25-40 min once the lock is free). Cause: `BLOCKED: suite lock busy after 901s`, holder pid 38884 (land-integrate-combined, not ours), after pid 71416 (t167) held it first. Everything else below is reusable by evidence identity (qa/checkpoints/t154-adversarial-pass.a.md); tree hash unchanged is the condition.
FAILURES: none

## Criteria (each: my own run, not the manifest's)
- AD1 MET: 7 `-k ad1` tests (none/expired/unsigned/edited/wrong-project/crawl/live_case) each raise ApprovalRequired, counting transport 0 calls, tree gains only `ai/`, `ai/adversarial/`, `refusals.jsonl` (1 line), no `<run_id>/`. Own falsification (refusal path also creates `run_x/`): 7 passed -> 7 failed.
- AD2 MET: `probes 4 > approved 3` named; trailing slash, host case, query string and bare-host targets each refused. Falsification (`probes=min(planned,1)`): 6 passed -> 2 failed.
- AD3 MET: production=True refused against a production=False row, runs with a matching row, a CRAWL row with production=True is not credited. Falsification (production masked): 2 passed -> 1 failed.
- AD4 MET: `grep -rniE "garak|pyrit|deepteam" src/ pyproject.toml` exit 1, no output; 5 probe files x 3 probes load from `prompts/probes/*.md`; missing/empty set blocks with a reason. Falsification (banned name in a probe .md): 2 passed -> 1 failed. No `ProbeSource` adapter exists, which the contract allows (only "if the native sets prove too thin").
- AD5 MET: no `Result.`/`Verdict(`/grade in adversarial.py; `ProbeRun` has no verdict-like field and forbids extras. Falsification (add `passed` field to ProbeRun): 1 passed -> 1 failed.
- AD6 MET: approval for 500, plan of 51, refused by `PROBE_CEILING 50`, value named in the exception and the log row. Falsification (`> PROBE_CEILING * 100`): 1 passed -> 1 failed. Note: my first mutant (constant 50 -> 5000) survived because the test sizes its fixture from the constant; the criterion fixes no value, so that is not a defect (see P4).
- AD7 MET: row has exactly target, timestamp, requested_probes, reason; no probe body (marker absent); second refusal appends; file survives a good run. Falsification (log write disabled): 1 passed -> 1 failed.
All reds are assertion failures with a green run in the same copy first; the bound tree was never edited. Done_check run directly: `uv run python scripts/adversarial_proof.py` exit 0, 10 lines HELD (1 in-scope pass sends 4; 9 refusals send 0 and log 1 row), "ADVERSARIAL PROOF OK". Ruff clean. Doctor: only the known `stale-generated: docs/SNAPSHOT.md`.
Diff scope (4c): 12 files, none deleted or renamed, no removed line in MAP.md, no T-153, consent, adapter or contract file touched; all files are in the manifest's What changed.

## Rulings on the dispatch points
1. New files: every one is named or proposed by the builder brief (`qa/briefs/t154-adversarial-pass.md` lines 116-118: ai_probe.py "proposed", probes/*.md, adversarial_proof.py; `adversarial.py` named by D-017 and the goal note; the goal done_check names the script). None unrequested. C3 "new module needs a stated reason" holds via the manifest What changed and the brief.
2. Own send loop: not a violation. C3 is name-based ("no class or public top-level function name defined in two modules"), doctor's duplicate rule found none, and `_fire`/`_record` differ in name from `_send_one`/`_exchange`. The brief itself said to add parameters to `capture_run` or "import nothing private"; the builder took the second path and disclosed it. AD4/AD5 and the invariants do not forbid it. The duplicated try/except (transport_error) is real but small: P1, low.
3. `PROBE_CEILING = 50` and the five categories are the owner's to set: AD6 requires "a hardcoded ceiling" and fixes no value; AD4 requires files under `prompts/probes/` and fixes no categories. Not a FAIL; P4.
4. `qa/adapter.json` has no entry for the script (confirmed absent). It blocks nothing here: no AD criterion verifies through it (all by pytest) and I ran it directly. It does block a done_check-driven close of T-154 and any checker running it as an allowlisted command, so the orchestrator should add it (D-018 `Changes-authorized` covers verify.commands). The script writes only to temp dirs and sets a throwaway key in-process; it fits the allowlist note's limits.
5. Live path: grep of adversarial.py, ai_probe.py, the probe files and the proof script finds no endpoint URL, HTTP client, socket, subprocess, CLI command, or pathlynks/vidysea string; `send` is an injected callable. Fully judgeable offline: AD1-AD7 (every Verify clause is a stub-transport test). Partial until a live pass is approved: AD1's "through every shipped entry point" is trivially one entry point today (`run_adversarial`; no CLI exists), and AD2/AD3 on the real Pathlynks endpoint string and its production status are unresolved (CN7), so they bind only at the run that mints a row.

## PROPOSED-ISSUE (none written to the ledger)
P1: {"severity":"low","title":"ai_capture._send_one and adversarial._fire duplicate the transport_error handling; consolidate into one helper after T-153 passes","evidence":"src/autotester/stages/ai_capture.py:65-74 vs src/autotester/stages/adversarial.py:147-151"}
P2: {"severity":"low","title":"AdversarialBlocked (host outside allowed_domains, bad probe set) is not an ApprovalRequired and runs before the approval check; callers catching only ApprovalRequired (as adversarial_proof.py does) would miss it, and a probe-load refusal logs requested_probes=0","evidence":"src/autotester/stages/adversarial.py:92-93,171-178"}
P3: {"severity":"low","title":"wall_clock_s is checked only between sends; one hung send is unbounded unless the real sender has its own timeout. Require a per-send timeout when the real sender is built","evidence":"src/autotester/stages/adversarial.py:143-152"}
P4: {"severity":"low","title":"Owner to confirm PROBE_CEILING=50, the five categories and the probe text before any live firing; tests scale with the constant and do not pin it","evidence":"src/autotester/stages/adversarial.py:38; manifest 'Proposed values'"}
P5: {"severity":"low","title":"qa/adapter.json lacks an allowlist entry for `uv run python scripts/adversarial_proof.py` (T-154 done_check)","evidence":"qa/adapter.json read_only_allowlist.commands"}
P6: {"severity":"low","title":"Wording: manifest says '10 of 10 refusal scenarios'; the script has 9 refusals plus 1 in-scope pass","evidence":"scripts/adversarial_proof.py:98-110"}
Also open from before: ISS-t150-1 (spec.md has no T-154/T-155 row). Merge order: this unit cannot merge before T-153.

CAPABILITY-COVERAGE: 7/7 rows reproduced (own edits, own copies)
LIVE-BROWSER: not-applicable (stage, schema, probe .md files, script, tests; no UI path changed)
ISSUES-WRITTEN: none (dual coordinator)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Every criterion is evidenced and falsified by me; the only mandatory item left is the one full suite, which could not start because the machine-wide suite lock stayed with other checkers for the whole 15-minute wait. slow: lock wait 15 min (blocked_min).
Metrics: start=2026-10-11T01:37 end=2026-10-11T02:02 wall_min=10 agent_min=unavailable blocked_min=15 suite_runs=0 repeat_runs=0 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=1 defects_unit=0 defects_6c=0
