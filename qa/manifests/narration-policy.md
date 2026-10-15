# Manifest — supplied-first bounded narration policy core

- Status: ready-for-check
- Fix cycle: 2
- Base: 40f5b4b20e91d3806ee313fb8e67af109b62b0ae (checked D-101/D-102 policy)
- Candidate: exact evidence-wrapper SHA in .work/narration-policy-cycle2-packet.md; immutable source SHA a16c2a53
- Authorization: approved completion goal; D-101/D-102; source-adapters SA8 (policy/core subset), SA2-SA6/SA7; ingest I8; core C1-C7; D-100 scoped verification.

## Implemented behavior and immediate consumers
Supplied stored/sidecar transcripts take precedence, including empty and unreadable evidence.
Media prep does not overwrite existing supplied narration or run local ASR first, even when
local ASR was explicitly opted in. Default transcribe(), prepare(), and CLI ingest prep never
implicitly invoke/download local ASR. --local-asr is explicit opt-in; --no-whisper skips missing
transcription while retaining supplied evidence. Audio registration has no Whisper fallback.

New media/narration.py owns audio-only extraction under existing 60s ffprobe timeout, 120s
ffmpeg timeout, maximum one-hour source duration and 128MiB audio byte bound. Truncation at
that byte ceiling is refused, not passed off as complete. Temporary audio is removed after
provider success/failure; original video is never uploaded by this helper. Only fixed error
messages are persisted; generated transcript text is scrubbed against known secrets.

Transcription response models moved to schema/transcription.py with compatibility exports.
The typed AudioTransportCapability is a safety prerequisite, not a completed implementation:
real Gemini SDK media is WITHHELD until a checked provider implementation earns shared deadline,
physical-attempt accounting and audio-only capabilities. Mock transport is offline only.

## Explicit remaining work
This unit is narration POLICY/CORE and media-prep integration only. It does NOT claim functioning
production Gemini audio, budgeted SDK networking, aggregate caller-before-fingerprint wiring,
live audio/vision acceptance or completed SA8. Gemini SDK upload/poll/generate safety must land
separately, followed by CLI/UI fresh-run narration resolution before teaching snapshot freeze.
Do not set the capability merely to enable calls. Existing supplied-transcript flow works now.

## Verification and proof
Evidence: qa/evidence/narration-policy/. Focused synthetic tests use actual ProjectStore/prep
and Provider mocks; no browser, real inference, model download or live target action.
Initial sandbox test runs had Windows temporary-directory ACL setup errors (no tests ran).
Scoped elevated offline tests succeeded; safe temp artifacts were removed within unit root.
Original 13-mutation proof is preserved as historical evidence. Final evidence: 27 tests
passed; full Ruff clean; five source doctor checks clean; 15/15 attributable mutations killed
(final mutation run elapsed 148.67s), including stored-prep precedence and immediate consumer. The standard mutation harness asserts green baseline, one anchor, changed copy,
named assertion failures and restoration; copied source excludes pycache and PYTHONPATH points
at disposable copied src. No source under review is mutated by proof.

Maker active time/tokens/cost unavailable: null, never padded. Command durations are measured.
D-100 full combined release gate remains parent-owned. Only an independent matching-cycle
checker verdict may PASS this unit.


## Cycle 2 — maker readiness repair only
Cycle 1 HOLD is preserved at e30a5ab8b6ffe36e68a96c115c42d228a59b7f13 and in the
canonical verdict history. The checker ran no runtime tests: historical proof lacked
contemporaneous identity bindings and restored-green runs. No source defect was asserted.
Original receipts and specs remain unchanged; no retrospective provenance is claimed.

Fresh evidence lives under cycle2/. Source/test/script/config bytes remain the immutable
a16c2a53 candidate (all 1004 copied source/fixture/script/config files verified). Shared
17-defender GREEN is reused only while source/environment identity is byte-identical.
Each of 15 guard claims has a unique-anchor named RED, exact byte restoration and an
actual per-defender restored GREEN. All 31 commands have before/after receipts binding
source candidate/base/proof checkout, entire source inventory, actual copied imports,
interpreter binary/version, installed dependency versions, clean safe environment, lock,
harness, invocation wrapper, mutation spec, command, raw output and timestamps.

readiness.py validated all 15 triples, 31 receipts and raw file hashes before resubmission.
cycle2/.gitattributes preserves exact evidence bytes through Git on this CRLF host.
The first attempt stopped BEFORE tests on Windows-vs-POSIX inventory-key spelling;
prep1-proof.py and prep1-failure.json preserve that invalid setup, with no proof claimed.

These are maker readiness proofs, not independent verification or checker PASS. Actual
maker active time/tokens/cost stay null. No new source/runtime/SDK/capability, API/key,
model download, browser, broad suite or live product change is part of this repair.
Full production SA8, SDK safety and caller-before-freeze integration remain separate.
