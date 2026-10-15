# Neutral behavioral vision capability verifier

Status: ready-for-check
Fix cycle: 1
Root: C:/Users/product/Desktop/autoTesting/.work/wt-vision-probe
Base SHA: 00c9e13ded3cba6cfe57bd9d0c422f5154ed6e09
Packet: .work/probe-packet.json (written after immutable candidate commit).
Risk tier: high_risk (visual sanitation and shared capability schema).

## Scope and authorization

D-099/D-101/D-102; ingest I4 completion/capability amendments; browser-and-secrets
B11; provider physical-attempt accounting; core C1-C9/C12 and D-100 unit review.
This unit verifies one explicit LiteLLM Provider configuration. It selects no
fallback and changes no role defaults, saved projects, CLI/UI consumers or shared
model-chain/LiteLLM transport code. No actual model call is part of maker tests.

`providers.vision_probe.probe_vision(provider)` builds two independently randomized
neutral images, each containing two colored geometry objects and the same neutral
SAFE text anchor below them. Individual `sanitized_images` contexts remove the text
band; decoded PNG format, fixed 256x160 dimensions and <=100,000 bytes are checked.
Actual image bytes go through guarded `Provider.judge`, which needs no prior vision
receipt. Expected answers never enter the prompt or filenames. Closed-vocabulary
validated answers must match both independent image challenges in payload order.

A passed capability binds the explicit model, endpoint fingerprint (excluding keys),
ordered sanitized bytes (length-prefixed), prompt SHA256, validated output SHA256 and
the `sanitized-layout-pair-v1` protocol. An endpoint/model change or unproven physical
transport cannot issue a passed receipt. This verifies only the sampled neutral
layout task, not general visual quality, readable text, narration or regression recall.

The scope allows at most two physical requests/45 seconds across JSON repair and
inherits every enclosing call/deadline cap. Global exhaustion is re-raised with a safe
probe result, never converted to eligible fallback. Availability is explicit;
sanitation, mismatched answers, generic provider/privacy/schema failures remain
inconclusive with no capability. Artifact attempts are deep snapshots. Vendor errors
and user media never enter artifacts. SDK max_tokens is NOT newly capped because the
existing public judge interface has no per-call generation argument; no such cap or
hard cancellation guarantee is claimed.

## Paths and ownership

- providers/vision_probe.py: owns neutral challenge generation and verification.
- schema/vision_probe.py: closed answer/result family, including an Artifact result.
- schema/video_frames.py: optional protocol/prompt-hash receipt fields, preserving
  all existing transport fixture receipts.
- skills/vision-probe/SKILL.md: file-backed interpretation prompt.
- tests/test_vision_probe.py and tests/test_vision_probe_schema.py: self-contained
  offline pixel-reading transport and schema boundaries.
- qa/evidence/vision-capability-probe/: complete proof instrument and raw receipts.

## Verification plan and fixture isolation

The normal-conftest pre-proof run passed 29 checks (new probe/schema plus existing
receipt-schema consumers). The final probe test additionally asserts the entire
masked band at an originally white pixel, making the privacy mutation discriminating.

The owner/coordinator explicitly authorized `--noconftest` only for the two new
self-contained probe/schema modules. Each probe test imports and applies the real
`litellm_fake.no_network` fixture, which blocks non-loopback socket connect/connect_ex;
the module defines its own local transport/root/OCR fixtures. Schema tests make no
provider call. No global auth, consent, queue or consumer prerequisites are exercised
by these two modules. This optimization does not apply to consumer/auth/integration
checks; the combined integration/release run still uses normal pytest and full gates.

The proof copies complete src/tests/scripts inventories, including
tests/tests_mutation_fixtures.py, excludes caches, preflights the copied import/temp
root, then captures raw-byte source identities and named green/red/restored receipts.
Short serialized bursts share the identical bound baseline and finish with restored
green. All 30 selected behavioral representatives have attributable named failures;
each restored boundary passes all 24 focused cases. The original 20 proof chains are
preserved byte-for-byte in receipts-before-selection.json. The parent explicitly
authorized grouping equivalent schema variants by risk: eight planned variants were
not executed. selection-spec.json maps each to a representative and retains every
positive assertion; no claim of 38 executed proofs is made. The separate selection
wrapper binds the frozen original harness, full source inventory and exact chosen IDs.

Final scoped Ruff and AST file/function limits passed. readiness.json validates
complete live/copied inventories, raw-byte mutation reconstruction, named JUnit
failures, restored results, interpreter/dependencies/lock and log hashes. It is maker
readiness only, not an independent verdict. All source/test bytes stayed frozen.

After runtime proof, unit-specific Git attributes preserve source/manifest checkout
newlines and disable evidence text normalization. packaging.json separately checks
fresh index checkout byte equality; older runtime receipts are not relabeled as
testing that later configuration. The first packaging check found a manifest newline
gap, retained in packaging-attempt-1.*, then the exact manifest attribute repaired it.
No runtime/source change or repeated runtime tests accompanied this packaging fix.

Independent review should select a small justified set: actual sanitized-pixel receipt,
secret-model rejection, outer budget exhaustion, decoded-payload refusal and receipt
backward compatibility. The checker chooses its own representative sabotage and any
required affected privacy/secrets checks. Normal combined pytest/ruff/doctor remains
an integration/release gate; this unit does not certify that candidate.

Actual maker active time/tokens/cost are unknown/null. Command durations and waits
are recorded separately where measured, never turned into invented maker totals or
checker efficiency success. No self-PASS/merge/push or actual model capability claim.
