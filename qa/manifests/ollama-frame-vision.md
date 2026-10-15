# Bounded Ollama frame transport

Status: ready-for-check
Fix cycle: 1
Root: C:/Users/product/Desktop/autoTesting/.work/wt-vision
Base SHA: 6db4580ed73d283ff62ce0842028a0ae9a6dd6ab
Packet: .work/vision-packet.json (written after candidate commit)
Risk tier: high_risk (visual privacy and shared provider/schema interfaces).

## Authorized unit

D-099, ingest I4 amendment, browser-and-secrets B11, providers-litellm LL amendment,
langchain-fallback OC2 physical attempts; core C1-C9/C12 and D-100 unit verification.
This is an offline transport unit, not live capability or end-to-end teaching acceptance.

`LiteLLMProvider.see_video` samples real PNG frames through media.probe/extract_frame,
sanitizes each separately, checks decoded PNG MIME/pixels/bytes, and sends actual
base64 pixels paired with original sample indices and clip-relative timestamps.
Sampling distributes the capped count across the clip rather than dropping its tail.
The default caps are 16 frames, 4 million pixels per image, 2 MB per image and 16 MB
total image bytes (base64 encoding adds bounded overhead). FPS must be finite in (0,10].
These are sparse layout observations: all text and audio remain explicitly unavailable.

The existing guarded structured JSON transport handles parsing and one repair.
Seed, token cap and optional temperature are forwarded; unsupported nondefault
thinking/resolution/system settings explicitly refuse. Each vision call opens a
two-request/240-second attempt scope and inherits all enclosing physical budgets.
This is cooperative SDK deadline enforcement, not a hard cancellation guarantee.
ModelChain forwards vision arguments, synchronizes failed usage, and retains the
final visual shortfall. It only tries explicitly configured/default existing tiers.

`VideoObservation.visual_coverage` persists sparse/withheld/text/audio evidence;
provider failures carry typed FrameCoverage for caller persistence. Frame status
`included` means payload inclusion; it never asserts physical delivery or successful
model understanding (a zero-request budget can refuse before SDK transport). Frame sanitation
paths live only inside the context, while the call consumes encoded safe bytes.
No original unsafe image is transmitted or overwritten.

## Capability boundary and remaining work

Vision refuses without a passed typed receipt bound to model, endpoint hash,
synthetic fixture hash and behavioral-output hash. Test receipts are OFFLINE FIXTURES,
not measured model capability. No actual GLM/DeepSeek/Gemini vision or audio probe ran.
The behavioral verifier and live synthetic probe remain separate work, as do role
defaults, saved-project migration, CLI/ensemble routes, explicit vendor fallback,
supplied-transcript/narration policy, and consumers persisting failed-call coverage.
No real project data, browser, credentials, model endpoint, ASR or external application
was used. Full combined integration pytest/ruff/doctor remains owed by the owner.

## Changed paths and new-module reason

- providers/video_frames.py: owns bounded sample/sanitize/encode transport.
- schema/video_frames.py: owns limits, capability receipt and coverage models.
- providers/litellm_provider.py: vision delegation and existing structured transport reuse.
- providers/model_chain.py: vision forwarding and failure-coverage retention.
- schema/observation.py: optional persisted coverage, backward compatible with old files.
- skills/frame-vision/SKILL.md: file-backed limitations prompt.
- tests/test_video_frames.py, tests/test_video_frame_schema.py: synthetic boundary tests.
- tests/test_litellm_provider.py: historical fixed-unsupported expectation becomes
  behavioral-capability refusal.
- qa/evidence/ollama-frame-vision/: instrument, exact outputs and bound receipts.

## Verification and accounting

Final offline regression baseline and restored run: **75 passed each**. Three
immediate-consumer checks passed; scoped application/test lint and scoped AST,
module docstrings, file/function caps passed. Exact commands, output hashes and
source bindings are in qa/evidence/ollama-frame-vision/checks.json and receipts.json.
The corrected r4 proof completed **41 attributed mutation kills**. Every credited
mutation has one exact byte
anchor, changed-byte assertion, attributable named pytest failure and exact restoration.
The identical full green/restored source snapshots are shared across mutation rows.
mutations.json enumerates every guard, exact mutation and named defending node;
each complete red log/JUnit failure is retained beside receipts.json. Final self-
readiness verified exact candidate source bytes, instrument hash, all named failures,
complete restoration and bound fixture/dependency fingerprints before review.
Copy excludes all __pycache__; includes src, tests (including
tests/tests_mutation_fixtures.py), scripts, pyproject.toml and uv.lock.

Earlier r1 failed before any mutation because scripts/regression_proof.py was missing
from the isolated copy. R2 produced partial attributed kills but was stopped when
self-readiness noticed its missing copy-specific pre-test preflight. Neither is
credited as complete proof; both remain under .work/vision-proof*.

R3 was stopped before completion to correct `sent` to the truthful `included`
status and add a zero-request transport-refusal check. Its partial receipts remain
preserved and are not offered as final-source evidence.

Actual total maker active seconds/tokens/cost: unknown/null. Individual command
durations and r4 timestamps are recorded and are only a lower-bound subset of maker
work. Preserve earlier setup/retry costs as unknown where unmeasured. No efficiency
ratio is claimed; parent dispatches fresh bounded independent review. No self-PASS,
merge, push, release certification or live capability claim.
