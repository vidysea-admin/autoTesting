# Verdict — g2-review-core (G2 video-review pure-core slice, T-197)

**Checker:** Mode A, fresh context, Tier M, one checker. Policy-Version: proportional-verification/2026-10-06.6.
**Date:** 2026-10-07. **Cycle checked:** 0 (manifest `Fix cycle: 0`).
**Bound:** branch `wave/g2-review-core`, worktree `D:/autoTesting/.worktrees/g2-review-core`, HEAD `f3587d5d` (tree `627c19e4`), base `c09debd1`.
**Contract:** `qa/contracts/team-video-review.md` TV1-TV10, in-slice parts only (blob `d160efc1`, byte-identical to origin/master) + `qa/contracts/core-invariants.md` (blob `7450f855`).
**Manifest:** `qa/manifests/g2-review-core.md` (blob `359632e6`), Status `ready-for-check`.

## Verdict: CONTINUE-NEEDED

remaining: full suite (combined G-core head).

Not a PASS. Findings F1-F4 below are fix-cycle items for the maker (cycle 1) that would have ended this check as FAIL had it been closed now; F1 and F2 are on the CRITICAL criterion TV7. The full suite is deliberately not run here: the maker runs ONE combined suite on the G2/G3/G5/G6 integration head.

## What I re-ran myself (worktree, uv)

- `uv run pytest tests/test_video_pointers.py tests/test_video_review.py tests/test_video_review_gates.py tests/test_video_review_redaction.py` -> **71 passed** (redaction file ran, real ffmpeg, no skips). Same 71 passed from a `git archive` copy under PYTHONPATH.
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean.
- Size/one-job: `video_review.py` 276, `video_review_items.py` 150, `_plan.py` 131, `_prompt.py` 98, `_render.py` 67, `media/redacted.py` 110, `paths.py` 297; all under 300, each has a one-job docstring; no `*_v2`/`*_new`; no dependency/pyproject change.
- No real model call; Provider was always the recording fake.

## Per-criterion (in-slice parts)

| Criterion | Result | Notes |
|---|---|---|
| TV1 grammar, count identity | PASS | 3000-case fuzz (BOM, CRLF, CR, pipes, `~`, `-`): `parsed + errors == non_blank` always; every error form returns the 1-based physical line; 4th free pointer refused, whole list returned; `PointerErrors` raised before any call (calls == 0). CLI exit 2 / HTTP 422 owed. |
| TV2 pointers prioritise | PASS | superset, depth 12 > 4, exact partition of `[0,d]` over 400 random plans incl. redaction holes (to 1 ms rounding), provider-level superset for 0/1/3 pointers, `Not reviewed` rendered in MD and HTML. Contract vocabulary puts the depth constants in `stages/video_pointers.py`; they live in `stages/video_review_plan.py` (F8). |
| TV3 shape, no padding | PASS | 2 valid -> 2 + "fewer than 4"; 9 -> 5 top-severity + 4 `overflow`; empty/None/wrong-type field -> `rejected`; non-JSON and empty-summary reply -> `failed`; zero-length, corrupt and audio-only files -> `unreadable`, calls == 0, nothing persisted. |
| TV4 real second | PASS | 99999, -3, DURATION+0.01 -> `time_outside_recording`; other source -> `unknown_source`; absent from stored items, MD and HTML; DURATION exactly kept. |
| TV5 provenance | **FAIL** | F3 (slack). Substring, case change, far segment, pointer-needs-line, no system "confirmed": all PASS. |
| TV6 silence | PASS | none / unreadable / speech-elsewhere phrasing in MD and HTML, banned phrases absent. Hardening gap F6. |
| TV7 (CRITICAL), in-slice 3 + 4 and the zero-call property | **FAIL** | F1, F2. PASS parts: gate is the first statement, required (no default), refusal => 0 calls, 0 probes, 0 frame work, nothing written to disk; no-op blackout (redact patched to a plain copy, real ffmpeg) -> `RedactionError` -> `ReviewRefused`, 0 calls; only PNGs under the review work dir are handed over, frames inside a window never sent; encoded secret in the LAST batch refuses before the FIRST call; preview makes 0 calls. Owed: permission via `authorize()`, per-use approval (T-204). |
| TV8 nothing secret | PASS | canary in transcript, pointer note, free pointer, model summary/seen/screen/suggestion/quote and a rejected item: absent from every file under the project, MD, HTML, prompts and root-logger output. Gap F7 (caller omitting `secrets`). |
| TV9 | OWED (not judged) | |
| TV10 id, idempotency, export | PARTIAL | same inputs -> same id, one artifact, no second spend; reorder stable, one pointer changed -> new id; human `confirmed`/`fixed` survive `refresh=True`; stored under `paths.review_path`. F4: Markdown carries no item ids. Viewing/export permission, UI, CLI owed. |
| core-invariants | PASS | C1 (models in `schema/`, `extra="forbid"`, Artifact base), C2/C3 (doctor clean), C5 (see F7), C6 (JSON under project). |

## Rulings requested

1. **Helper modules (D-072/D-074).** `video_review_plan`, `_items`, `_prompt`, `_render`: covered by D-072 item 2 ("the Group 10 split modules ... the checker judges it"). Each is one job (frame plan; reply -> items; prompt + narration state; render) and is 67-150 lines. Cohesion nit only: `clock`/`narration_state` live in `_prompt` and are imported by `_items` and `_render`. Also covered on the same reading but NOT named in the manifest's ruling request: `media/redacted.py` (not in D-072, D-074, plan G2 or the contract's list of six). The contract's no-fire list names only the six modules, so a record naming the four helpers plus `media/redacted.py` is owed (F8, process, not a code defect).
2. **NARRATION_SLACK_S = 1.0 vs "overlaps".** The contract has no slack: TV5 says a segment "whose time span overlaps the item's second", and the amendment log says "TV5 requires temporal overlap". Slack is a correctness finding (F3). Proof: segment 10-12, item at 12.9 s, quote exact -> kept as `narration`; segment 100-104, item at 99.2 -> kept. Set it to 0 (the 1.0 s was the builder's own decision to confirm). The same slack widens TV6's "no narration at this moment".
3. **Redaction verification.** A no-op blackout IS refused (own probe, real ffmpeg, plus the maker's test). Frames are cut only from the redacted copy when windows exist, and the Provider receives only PNG paths under the review work dir. Every prompt is scrubbed, then `assert_no_raw_secrets`-gated for ALL batches before the first call (own probe: base64 secret in the last batch refuses with 0 calls). BUT redaction is not complete: F1 (transcript text of a redacted window is sent), F5 (verification checks the window midpoint only and skips silently when a frame cannot be extracted).

## Findings (fix cycle 1)

- **F1 — TV7.3, CRITICAL, blocking.** `video_review_prompt.review_narration` (called from `build_review_prompt`) includes every transcript segment overlapping the batch window and ignores redaction windows. Probe: segment 100-110 "CANARY-SPOKEN-PASSWORD" with window 90-120 -> the text is in the prompt sent to the Provider. The contract: "no audio from inside a window is passed to the Provider", purpose line: "nothing that was redacted reaches a model". Fix: drop (or clip) segments overlapping a redaction window before building the prompt; also exclude them from `overlapping()` quote acceptance; test with a canary segment in a window.
- **F2 — TV7.4, CRITICAL, blocking.** The spend cap is inert for the real providers. `provider_cost` uses `estimate_cost(provider.label, ...)`, and `Provider.label` is `anthropic` / `gemini` (no `:model` suffix unless `options["model"]` is set), which `pricing._RATES_PER_1K` does not price; unknown label -> 0.0, so `cost >= max_cost_usd` is never true. Probe: default-labelled `AnthropicProvider`/`GeminiProvider` price 1M+1M tokens at 0.0; a fake with the default `cost_of` made 4 calls at `status=ok` under a 0.50 cap. The tests pass only because they inject `cost_of`. This is the contract's "ignore the cap" mutation, live in production wiring. Fix: fail closed (unpriced label with a cap -> refuse, or a conservative fallback rate / hard call-count bound) and test the default `cost_of` with a real provider class.
- **F3 — TV5, correctness.** See ruling 2. Set `NARRATION_SLACK_S = 0` (or have the maker propose a contract amendment to the checker with reason; do not keep it silently).
- **F4 — TV10 export.** `render_markdown` has no item id; HTML has `data-item-id`. The criterion says "export both formats and compare item ids". Add the id to the Markdown row/column and test equality of the id sets.
- **F5 — low, TV7.3 defence in depth.** `redacted.verify_blackout` samples only the window midpoint and `continue`s when the frame cannot be extracted (also when it fails for a reason other than "past the end"). Probe: a copy blacked only 2-3 s passes verification for window 1-3. Frames inside windows are never sent, so no leak today. Check start/mid/end, and treat an extraction failure inside the recording as `RedactionError`.
- **F6 — low.** `overlapping()`/`_quote_verbatim` do not consult `narration_state`; a Transcript with `engine="none"` or `"unreadable"` that still carries segments gives `origin=narration`. Unreachable from the sidecar loader today (those states have no segments); guard it anyway.
- **F7 — low/warning, C5/TV8.** `run_review(..., secrets=None)` builds an empty Redactor and a vacuous `assert_no_raw_secrets`: a caller that forgets `secrets` sends a known secret in transcript text (own probe: it reached the Provider). `gate` has no permissive default; `secrets` should be required (or resolved from the project's declared SecretRef set) so the CLI/route cannot omit it.
- **F8 — low, process.** TV2 vocabulary says the depth constants are in `stages/video_pointers.py` (they are in `video_review_plan.py`): move them or the checker amends the contract. And record `media/redacted.py` + the four helpers (ruling 1).

Info: `max_cost_usd=0` (cap reached before any call) returns `failed` ("spend cap $0 reached"), not `partial`; defensible, no criterion text. Spans are rounded to 1 ms, so the partition ends at `round(duration, 3)`.

## Manifest honesty

Honest and complete about the owed list (TV7 permission/approval, CLI exit codes, UI routes and `video.view`, TV9, live Navnit run, Linux run, no full suite, no real model). Two gaps: (a) it never says transcript text from a redaction window is not redacted (F1), and (b) it never says the cap depends on a priced label (F2). The gate is mandatory: `run_review(..., *, gate: ReviewGate, ...)` has no default (`TypeError` without it), `gate()` is the first statement, and nothing is probed, framed or written before it. A caller can still pass `lambda: None`; that is T-204's wiring, owed. `frames_fn`/`probe_fn`/`cost_of` are injectable seams that a production caller could misuse; keep them out of the CLI/route surface.

## Own falsifications (throwaway `git archive` copies, probe in scratchpad; each mutated copy built from the same base, base green on the target probe first)

Probe `probes/probe.py` sha256 `1a3a42cf…` (+ `mutate.py` `6de827a7…`), scratchpad `…/scratchpad/probes/`. 15 of 15 red:

| # | Criterion | Mutation | Red probe(s) |
|---|---|---|---|
| 1 | TV1 | parser `continue`s on a bad line | count-identity fuzz, forms, fourth-free |
| 2 | TV2 | analyse pointer windows only | provider-level superset, partition/superset property |
| 3 | TV2 | drop Coverage from the rendered summary | `Not reviewed` in MD/HTML |
| 4 | TV3 | truncate to 5, no `overflow` | nine -> 5 + 4 overflow `(5, 0)` |
| 5 | TV4 | skip the time-range check | out-of-range (red as a `ConfirmItem` ValidationError) |
| 6 | TV5 | skip the quote substring check | fake quote, case change, far segment |
| 7 | TV6 | map `unreadable` to `none` | engine phrasing |
| 8 | TV7 | `verify_blackout` no-op | no-op blackout NOT refused |
| 9 | TV7 | skip `gate()` | gate refusal |
| 10 | TV7 | ignore the cap | capped run no longer partial |
| 11 | TV7 | drop the all-prompts pre-pass | last-batch encoded secret: calls > 0 |
| 12 | TV7 | frames cut from the original (copy built but not used) | my colour probe stays green (frames inside a window are never sent, so colour cannot tell); the maker's `test_frames_handed_out_come_from_the_copy...` goes red (1 failed, 5 passed) |
| 13 | TV8 | skip the final `scrub_obj` | canary found |
| 14 | TV10 | id includes a timestamp | idempotent + id-changes |
| 15 | TV10 | skip `_merge_human_status` | human status reset to `open` |

Base failures proving F1, F2, F3, F4, F5, F6 are in the same probe (`TV7.transcript_inside_redaction_window_not_sent`, `TV7.real_provider_labels_are_priced`, `TV7.default_cost_fn_with_unpriced_provider_cap_binds`, `TV5.strict_overlap_*`, `TV10.exports_carry_comparable_item_ids`, `TV7.verification_covers_whole_window`, `TV6.*_engine_with_segments_present`).

## Checkpoint (resume point)

- Bound HEAD `f3587d5d`, tree `627c19e4`; contract blob `d160efc1`; core-invariants blob `7450f855`; manifest blob `359632e6`.
- Done and not to be repeated unless the code changes: affected tests (71 passed), ruff, doctor, all 15 falsifications, rulings 1-3.
- remaining: full suite (combined G-core head), after the maker's cycle-1 fix of F1-F4 (F5-F8 recommended in the same pass). On the fix I re-run the 4 test files, ruff, doctor, and the probe checks named above (they are the regression list for F1-F6).

## Proposed issues (not written to `qa/issues.jsonl`; the maker's integration head owns that ledger)

1. G2-F1 high: transcript text from a redaction window reaches the Provider (TV7.3).
2. G2-F2 high: spend cap never binds for default-labelled real providers (TV7.4).
3. G2-F3 medium: `NARRATION_SLACK_S` exceeds the contract's "overlaps" (TV5, TV6).
4. G2-F4 low: Markdown export has no item ids (TV10).
5. G2-F5/F6/F7 low: midpoint-only/fail-open blackout verification; narration accepted when state is none/unreadable with segments; `secrets` optional default.
6. G2-F8 low (process): name `media/redacted.py` + the four helpers in a record; depth constants location vs contract.
