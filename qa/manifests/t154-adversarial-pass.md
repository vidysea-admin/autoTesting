# Manifest — t154-adversarial-pass
**Contract:** qa/contracts/adversarial.md (AD1-AD7); also consent.md CN1/CN5/CN6/CN7 and core-invariants (secrets discipline and verification independence) as the mechanisms AD1-AD3 require this caller to exercise
**Goal task:** T-154 (Track C, unit 4: bounded adversarial pass behind consent gate 2, plus `adversarial_proof.py`)
**Date:** 2026-10-11
**Fix cycle:** 0 of max 2
**Dual check:** required
**Persona walk:** skip (no human screen: a stage, probe files, a schema and a proof script; no route, template, CLI command or browser step is in scope)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Executor rationale:** single build unit with a full brief; stubs and fakes only, no live probe, no model or network call, no approval row minted or edited.

## Base and dependency on T-153 (unchecked)
- Cut from T-153's product commit `ff901f721d17a1b2d7a109526f8444e485920965` (`wave/t153-behavioural-checks`), which itself sits on master `3a16616cf2c99a63c8d763150a1ca6410dfc0acc` (master has since moved to `a4b751c6`; not merged into this branch).
- T-153 files this unit depends on (all read-only here; **no T-153 file is edited**): `src/autotester/schema/ai_check.py` (`AiReply`, `AiExchange`), `src/autotester/stages/ai_capture.py` (`CaptureWithheld`, `Send`). If a T-153 fix cycle renames or changes those four names, rebase and re-run `tests/test_adversarial.py`.
- Deviation from the brief: the brief suggested adding two additive keyword parameters (kind, probes) to `ai_capture.capture_run` and reusing it. Not done: `AiCapture.check` is a required `AiCheckKind` and none of its members is adversarial, so reuse needed a fake check kind or an edit to t153's schema and catalog. Instead `adversarial.py` has its own short send loop (`_fire`, `_record`, about 25 lines) over the public `AiExchange`/`AiReply` models. Cost: the transport-failure handling shape exists in two places (`ai_capture._send_one` and `adversarial._fire`); benefit: the commits are separable from T-153's files. Checker to rule; consolidating later is a one-hunk change.

## What changed
- src/autotester/stages/adversarial.py:1-192 (new, named by D-017) — `run_adversarial`: loads probe files, checks host in `allowed_domains`, checks no secret in any input, calls `require_approval` itself (`kind=ADVERSARIAL`, real endpoint, `probes=planned`, real `wall_clock_s`, explicit `production`) at :108, then the code ceiling `PROBE_CEILING = 50` at :111, then sends through the injected `send`. Every refusal appends one line to `projects/<slug>/ai/adversarial/refusals.jsonl` then re-raises. No Result/Verdict/grading anywhere.
- src/autotester/schema/ai_probe.py:1-62 (new) — `ProbeSet`, `ProbeRecord`, `ProbeRun`, `ProbeRefusal`, all `extra="forbid"`; the refusal model has no field that can hold probe text.
- src/autotester/prompts/probes/{instruction_override,system_prompt_disclosure,out_of_scope,oversized_input,secret_echo}.md (new, 3 probes each, 15 total) — file-defined probe sets (AD4).
- scripts/adversarial_proof.py:1-119 (new) — fixture-only proof; throwaway project dir, throwaway signing key set in-process, counting transport, no network, no real approval row read or written.
- tests/test_adversarial.py:1-282 (new, 25 tests).
- .gitignore +4 — `projects/*/ai/` (D-017 `Changes-authorized`).
- docs/MAP.md — regenerated with `uv run autotester map`.
- Product commit: fd7362a857f45fa57ffed24aafc316c8fb864f7d. The manifest commit on top changes no product file.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (security: consent gate 2 and the only probe-sending path; secrets in probe traffic; an outward-facing action)
dual-trigger: security src/autotester/stages/adversarial.py:108 (`require_approval` for `ApprovalKind.ADVERSARIAL`, with the production check enforced inside it at `core/consent.py:174`; `ADVERSARIAL` is deliberately absent from `ACCOUNT_KINDS`, `core/consent.py:29`)
Gate answers: `qa/gates/d081-run-approvals.md` "Answered: 2026-10-10 - A (full approval; maker mints per-run rows) - D-081"; D-081 item 3 authorises the bounded adversarial pass on Pathlynks, but each run still needs its own signed row and this unit mints none. D-052 Part 3 (fixture target only, bound proven first) is what `adversarial_proof.py` satisfies. Still open for the owner, not decided here: `qa/gates/write-policy-tier.md:52` and `:88-92` have no `Answered:` line superseding them against D-081.
Affected tests / full-suite trigger: `tests/test_adversarial.py` (25 passed), `tests/test_consent.py` (36 passed, read-only regression guard; `core/consent.py` unchanged). No t153 file changed, so `tests/test_ai_capture.py` was not re-run. Security-L unit: the single full suite is the checker's last release step, not the builder's.
Pre-check[AD1]: fd7362a857f45fa57ffed24aafc316c8fb864f7d uv run pytest tests/test_adversarial.py -k ad1 -> 7 passed (none/expired/unsigned/edited/wrong-project/crawl/live_case each raise ApprovalRequired; counting transport 0 calls; tree differs only by `ai/adversarial/refusals.jsonl` with exactly one line, no `<run_id>/` dir) t=2 blobs=tests/test_adversarial.py:20490ed,src/autotester/stages/adversarial.py:2d286b7
Pre-check[AD2]: fd7362a857f45fa57ffed24aafc316c8fb864f7d uv run pytest tests/test_adversarial.py -k ad2 -> 6 passed (`probes 4 > approved 3`; trailing slash, host case, query string, base target each refused as distinct targets; every rejection reason listed) t=2 blobs=tests/test_adversarial.py:20490ed,src/autotester/stages/adversarial.py:2d286b7
Pre-check[AD3]: fd7362a857f45fa57ffed24aafc316c8fb864f7d uv run pytest tests/test_adversarial.py -k ad3 -> 2 passed (production=True refused against a production=False row, proceeds with a matching row; a CRAWL row with production=True is not credited) t=2 blobs=tests/test_adversarial.py:20490ed,src/autotester/stages/adversarial.py:2d286b7
Pre-check[AD4]: fd7362a857f45fa57ffed24aafc316c8fb864f7d grep -rniE "garak|pyrit|deepteam" src/ pyproject.toml -> no output, exit 1; uv run pytest tests/test_adversarial.py -k ad4 -> 2 passed (shipped probe files load; missing/empty set is blocked with a reason, zero sends) t=2 blobs=tests/test_adversarial.py:20490ed,src/autotester/stages/adversarial.py:2d286b7
Pre-check[AD5]: fd7362a857f45fa57ffed24aafc316c8fb864f7d grep -n "Result\.\|Verdict(" src/autotester/stages/adversarial.py -> no output, exit 1; uv run pytest tests/test_adversarial.py -k ad5 -> 1 passed t=2 blobs=tests/test_adversarial.py:20490ed,src/autotester/stages/adversarial.py:2d286b7
Pre-check[AD6]: fd7362a857f45fa57ffed24aafc316c8fb864f7d uv run pytest tests/test_adversarial.py -k ad6 -> 1 passed (approval for 500 probes, plan of 51, refused by `PROBE_CEILING` 50, the value named in the refusal and the log row) t=2 blobs=tests/test_adversarial.py:20490ed,src/autotester/stages/adversarial.py:2d286b7
Pre-check[AD7]: fd7362a857f45fa57ffed24aafc316c8fb864f7d uv run pytest tests/test_adversarial.py -k ad7 -> 1 passed (row has exactly target, timestamp, requested_probes, reason; no probe body; a second refusal appends a second line; the file survives a successful run) t=2 blobs=tests/test_adversarial.py:20490ed,src/autotester/stages/adversarial.py:2d286b7
Pre-check: fd7362a857f45fa57ffed24aafc316c8fb864f7d uv run pytest tests/test_adversarial.py -> 25 passed; uv run python scripts/adversarial_proof.py -> exit 0, 10 of 10 scenarios HELD ("ADVERSARIAL PROOF OK") t=3 blobs=tests/test_adversarial.py:20490ed,src/autotester/stages/adversarial.py:2d286b7   (aggregate line for the lint: `tick.mjs` CRIT_RE only recognises C<n> ids, so it cannot see the tagged AD lines above)
Falsify[AD1..AD7]: see Capability coverage (throwaway copy, green before, red after, restored byte-exact)
Metrics: start=2026-10-11T00:00Z end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=7 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=7 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_adversarial.py` -> 25 passed
- `uv run pytest tests/test_consent.py` -> 36 passed
- `uv run python scripts/adversarial_proof.py` -> exit 0, 10 lines `HELD`, final `ADVERSARIAL PROOF OK` (fixture only, no network). NOTE: `qa/adapter.json` has no allowlist entry for this command yet (orchestrator action in the brief); the checker needs it to run T-154's `done_check`.
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> only `stale-generated: docs/SNAPSHOT.md` (known, from master); MAP current
- `grep -rniE "garak|pyrit|deepteam" src/ pyproject.toml` -> no output, exit 1

## Capability coverage (each criterion -> its isolating falsification)
Throwaway copy of `src/ tests/ scripts/ pyproject.toml` outside the worktree, `PYTHONPATH` pointed at the copy, anchor asserted unique, bytes asserted changed, byte-exact restore asserted. Script and copy are in the scratchpad (`.../scratchpad/t154/fals.py`), discarded.

| Criterion | falsifying edit in `stages/adversarial.py` | observed (selected tests) |
|---|---|---|
| AD1 | `require_approval` replaced by a stub that always returns a row | `-k ad1`: 7 passed before, 7 failed after (DID NOT RAISE ApprovalRequired) |
| AD2 | `probes=planned` -> `probes=0` in the `require_approval` call | `-k ad2`: 6 passed before, 2 failed after (shortfall text and over-count tests), 4 passed |
| AD3 | `production=production` -> `production=False` in that call | `-k ad3`: 2 passed before, 1 failed after (production=True run was not refused) |
| AD4 | banned framework name added to the module docstring | `-k ad4`: 2 passed before, 1 failed after (grep assertion lists the file) |
| AD5 | the text `Verdict(` added to the module | `-k ad5`: 1 passed before, 1 failed after on `assert not <re.Match ... match='Verdict('>` |
| AD6 | `if planned > PROBE_CEILING:` -> `if False:` | `-k ad6`: 1 passed before, 1 failed after (no refusal) |
| AD7 | refusal row built with the probe bodies appended to the reason | `-k ad7`: 1 passed before, 1 failed after (probe marker found in the log) |

All reds are assertion or DID-NOT-RAISE failures, none an import or setup error. (A first AD5 attempt that inserted `Verdict(1)` as code failed on a NameError at import; it was discarded and redone with the text inside a string.)

## Contract tension surfaced, as the brief required (pairing rule)
AD1 ("exactly as it found it") against AD7 (a refusal appends a line) is built as the contract's 2026-10-11 reconciliation reads: a refusal's only write is one line in `ai/adversarial/refusals.jsonl` (creating it and `ai/adversarial/` if absent). No `<run_id>/` directory, no `run.json`, no envelope, no send. The test snapshots the tree and asserts exactly that difference.

## Proposed values and probe categories (owner/checker to confirm; nothing in any document sets them)
- `PROBE_CEILING = 50` (`stages/adversarial.py:38`). Reasoning: the shipped sets total 15 probes, so 50 leaves room to grow about threefold while still being a hard stop on a mis-sized approval. A test also asserts the shipped sets never exceed it.
- Categories (5, three probes each, text is data in `.md`, owner reviews before any live firing): `instruction_override` (does it drop its configured role), `system_prompt_disclosure` (does it reveal hidden instructions), `out_of_scope` (harmful task, other users' data, impersonation), `oversized_input` (long, repetitive or odd-unicode input: does it stay bounded), `secret_echo` (does it repeat keys, environment or session tokens).
- `cap_hit` means a bound (the wall clock) stopped the run before every planned probe was sent; the probe-count bound is enforced before sending, so it can never be "hit" mid-run.

## Held on an owner answer (built what does not depend on it; nothing guessed)
- The live pass against Pathlynks: no AI endpoint string is known (`projects/pathlynks/project.json` has only a sign-in `base_url`), no real HTTP sender exists (the transport is an injected `send`), whether `pathlynks.vidysea.com` is "production" for the row (CN7) is unconfirmed, and `write-policy-tier.md:52`/`:88-92` have no superseding `Answered:` line. No operator CLI command exists; none is in scope.
- Ceiling value and probe categories above.

## Open items for the checker (honest list)
- `qa/adapter.json` allowlist entry for `uv run python scripts/adversarial_proof.py` (orchestrator, per the brief).
- `docs/spec.md` has no requirement row for T-154/T-155 (ISS-t150-1; the contract says not blocking).
- `_check_inputs` also runs `Project.allows_domain`; the pathlynks project declares `allowed_domains: ["vidysea.com"]` and the host match is suffix-based, so any `*.vidysea.com` host passes it; the approval's exact-target match is the real narrowing (as the brief notes).
- Refusal rows record `str(exc)` of the gate, scrubbed by the `Redactor`. For approval refusals that text includes approval ids, the target and the grant command, never probe text.
- PROPOSED-ISSUE: `ai_capture.capture_run` and `adversarial._fire` each implement "send one, record a transport failure as `transport_error`"; consolidate once T-153 has passed (one shared helper). Low.
- PROPOSED-ISSUE: `AiCheckKind` has no adversarial member and `CHECK_TIER`/`Tier.ADVERSARIAL` have no checks mapped, so T-155's judging of a `ProbeRun` will need either a new check kind or its own mapping. Low, informational for T-155.
- No `qa/issues.jsonl` row was appended (coordinator instruction); findings are the PROPOSED-ISSUE lines above.

## Live browser evidence
Not UI-touching — no surface changed. Changed paths: src/autotester/stages/adversarial.py, src/autotester/schema/ai_probe.py, src/autotester/prompts/probes/*.md, scripts/adversarial_proof.py, tests/test_adversarial.py, .gitignore, docs/MAP.md.

## Status: ready-for-check
