# Text availability and offline frame transport reconciliation

Status: checked-PASS
Fix cycle: 1
Risk tier: high-risk (shared Provider, privacy and physical-attempt boundaries)
Immutable runtime/test SHA: e2765afc59bbe00234af20badc3105a79ef103fe
Vision checked parent: 921a4ac5e8c8b8f77b1752bb285c82034ae2db26
Text checked parent: 5233ffb187cf8ccd4b804c4573d5ac261b125668
Root: C:/Users/product/Desktop/autoTesting/.work/provider-vision-integration
Packet: qa/evidence/provider-vision-integration/packet.json

## Authorized scope and exact reconciliation

D-101/D-102 and the parent's explicit reconciliation instruction authorize combining
the two independently checked units. This isolated merge preserves both histories.
No master merge/push, default/migration work, live model/browser/API/key access or
other worktree edit occurred. Previous private and committed evidence is preserved.

The two conflicting model_chain hunks combine constructor strict=True with typed
vision_capabilities/frame_limits, and safe availability reasons with visual coverage.
The media exclusion now includes see_video: adding that method must not activate the
text-only implicit Gemini tier for videos. Explicit configured verified tiers remain
eligible for vision fallback. Only capability_unverified raises the new narrow
FrameCapabilityUnavailable(FrameVisionError, Unsupported). Other frame errors
(sanitation/all-withheld/options/limits/media) retain generic FrameVisionError and
stop; privacy and malformed output never become availability failures. Shared budget
exhaustion still propagates immediately. Actual serving model and failure reasons
remain observable; final eligible failures retain coverage.

Auto-merged LiteLLM changes were inspected: generation options and actual frame
content_parts coexist with availability normalization, counted requests and strict
JSON validation on both parse paths. Frame generation supplies only seed/token cap/
optional temperature; reserve_attempt still sets the remaining-time transport timeout
after generation kwargs. SDK retries remain disabled. No Gemini SDK/media changes.

Owned runtime/test edits: providers/model_chain.py (two conflicts plus video exclusion),
providers/litellm_provider.py (automatic interaction merge), providers/video_frames.py
(narrow exception subtype/raise), tests/test_provider_vision_integration.py (new
combined cases), and two tests/test_video_frames.py failure fixtures. The historical
vision fixtures used arbitrary RuntimeError/two malformed replies to trigger another
tier; they now use eligible TimeoutError, preserving their order/shared-budget claims
under D-101. A new combined test proves malformed visual output instead stops after
its bounded repair and retains coverage. Historical PASS records are unchanged.

## Bound focused proof and selective reuse

Fresh own-source preflight and complete cache-free src/tests/scripts copy include
tests/tests_mutation_fixtures.py, pyproject.toml and uv.lock. No test ran before this
preflight. environment.json fingerprints every altered/mutated provider source,
tests, privacy/schema collaborators, fixture/config/lock and dependencies. Each
receipts.json phase records before/after source identity, exact command, exit and
output hash; mutations change one unique byte anchor in one inventoried source and
restore exact raw bytes. source-binding.json pins the final restored copy to the
immutable runtime/test head.

Exactly30 selected cases run green before edits and after restoration:15 text
availability cases,7 new combined cases and8 prior frame interaction nodes. They
cover auth/service/capability taxonomy, policy/secret refusals, strict/bounded repair,
outer count/deadline; constructor capability/limits, seed/token/temperature forwarding,
sanitized pixels/timestamps, partial/all withholding, actual tier/reason/coverage,
explicit verified capability fallback, and no implicit Gemini video.

Thirteen new interaction mutations have named red failures and focused restored
greens: constructor strict flag; capability forwarding; frame limits; implicit video
exclusion; failure coverage; safe reason retention; narrow capability eligibility;
terminal privacy/options type; terminal malformed visual output; terminal outer
budget; actual frame parts; generation kwargs; availability normalization. The two
rewritten vision fixture tests are included and independently falsified by the
global-terminal and availability-normalization mutations. Scoped changed-source/
test lint passes. Source caps174/299/151 and functions<=50; no new dependency/schema.

compared-segments.json and compared/ contain exact source segments, source/AST hashes,
line bounds and per-parent hunks for both old candidates and the actual combined
candidate. reuse-gate.json validates the same Python/dependencies/lock/config and
exact unchanged guard ASTs plus supporting source bindings. Compatibility applies
only to attempts, availability taxonomy and unchanged frame sanitation/options/
limits/delegation/redaction bodies. Changed constructors, chain dispatch/catches,
structured/completion methods and exception interaction are proved anew. Historical
100/75-test commands and whole-parent PASS results are explicitly NOT reused as
combined-candidate command evidence. No blanket41/18 mutation rerun was performed.

## Criteria, consumers and remaining obligations

OC2/OC3/D-102, ingest I4, provider LL5-LL7 and B11: availability-only fallback and
configured capability receipts retain bounded sanitized image transport; privacy,
caller options and global budget refusals remain terminal. C1-C3/C5/C8/C9/C12:
typed coverage, no raw values, exact explicit controls, actual attribution, null
unknown usage, and fail-closed outputs. Both parents' unaffected acceptance remains
historical; this unit claims only the reconciled seam and focused evidence above.

Immediate consumers: Provider registry/agent/judge callers, see_video via ingest and
analyze_video. The new exception remains both FrameVisionError and ProviderError for
existing catches. analyze_video still returns None on ProviderError and does not
persist failure coverage; that inherited caller limitation is separate work. Sparse
layout observations still cannot establish readable text or narration. Synthetic
capability fixtures are not live model verification. No SDK upload/poll accounting,
capability verifier, narration, default role migration or live acceptance is added.

Mandatory combined release gates (full pytest, full ruff, doctor and regenerated
shared docs) remain owed by the integration owner. No integration/release PASS or
self-PASS is claimed. Whole-maker active seconds/tokens/cost remain null/unknown;
recorded subprocess durations are not whole-active time. Checker ratios remain
unverified; use D-100 high-risk bootstrap/recorded allocations without invented totals.
