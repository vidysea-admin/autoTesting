# Conservative screenshot privacy and grading boundary

Status: ready-for-check
Fix cycle: 1
Branch: codex/image-privacy
Baseline: abc4a0ef49406936dd0047b7986b449bf3771ee2
Candidate: exact SHA in .work/privacy/packet.json (written after this commit)
Scope: reusable local sanitation plus functional grading; NOT full AT-840/B11 closure.

## Acceptance slice
- browser-and-secrets.md B11: grade sends masked temporary copies or withholds unsafe images;
  missing/readable-text evidence is explicit, cannot establish PASS, never overwrites originals.
- grade.md G1/G3/G4/G5/G6: evidence-only structured judging, persistent counts/notes,
  file-based privacy instructions, existing assertion restrictions retained.
- core-invariants.md C1-C3/C5/C7/C12: typed value-free batch, caps/unique helpers, no raw errors,
  attributable mutation proof and fail-closed visual-text claims.

## Changes and immediate consumers
- core/image_privacy.py: local Tesseract TSV and Pillow RGB/PNG masking of every recognized text
  band; uncertainty, invalid geometry, missing engine, limits or exceptions withhold that image.
- schema/image_privacy.py: temporary typed batch with paths, requested/withheld counts,
  value-free reasons, text_unavailable and missing-image incomplete flag.
- Nested sanitation reuses active temporary copies only while their SHA256 matches;
  changed/oversized files are rechecked. OCR reads the same decoded snapshot that is masked.
- stages/grade_images.py is the grading delivery helper, split to preserve grade.py's size cap.
  Sanitized files live through Provider.judge and disappear afterwards.
- grade.py records actual images delivered. Privacy/absent screenshot evidence caps PASS at
  INCONCLUSIVE; functional FAIL is retained. No-image callers retain text-only behavior.
- Prompts/image_privacy.md contains model-facing privacy instructions. Four legacy screenshot
  tests use valid PNGs and assert safe copies/explicit incomplete text coverage.

## Actual maker evidence
- .work/privacy/checks.json records exact commands, output hashes, durations and environment.
- Focused privacy/engine/grade/evidence/assertion/PII/schema selection:114 passed,1 warning;
  command exit0, pytest reports3.18s. Includes actual portable Tesseract5.5.3 with synthetic
  credentials, contact and custom-field text; no external model or browser calls.
- Scoped Ruff over changed Python files:exit0.
- Doctor exit1: undeclared Pillow (teaching integration dependency), stale generated MAP and
  SNAPSHOT only. Introduced314-line test finding corrected to298 lines.
- .work/privacy/mutations.json and mutation-results.json:21/21 killed,35 added/rewritten nodes
  covered. Existing mutation_check.py asserts green copied baseline, exact-once anchors,
  changed bytes, named failed nodes, restoration and60s per-command timeout.
- Mutation command duration222.188s; checks.json records final command durations. Total maker
  active time, tokens and cost unknown(null). Measured command time is partial, not an invented
  total or a proven checker-ratio denominator.

## Remaining integration obligations and limits
- Pillow declaration/lock from teaching c1f67d93 awaits independent review before merge.
  Installed Pillow12.3.0 runtime fingerprinted; no unreviewed dependency cherry-pick.
- Regenerate shared docs; mandatory combined pytest/Ruff/doctor remains required on final SHA.
- All-text OCR mode intentionally removes labels and cannot certify full visual text/UX coverage.
  Selective trusted-region masks, other outbound provider/video/UX paths and shared failure
  bundles remain subsequent units. OCR does not certify unknown glyphs/artwork/faces.
- No live product/account, cloud API, full suite, release, deployment or push was performed.

Earlier checkpoint:22 then24 tests passed. A broader command named a nonexistent test and ran
none. Initial mutation collection failed before proof because the instrument requires its own
sandbox; corrected run establishes the proof above. No checker verdict or PASS is claimed.
