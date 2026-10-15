# Contract — SOURCE ADAPTERS (T-162)

**Status:** ACTIVE — finalized 2026-09-22 by /checker (D-035), authorized by the T-162 gate
interview (`qa/gates/t162-contract-approval.md`, answered **(A)** by Umesh in chat 2026-09-21).
Phase-1a (the adapter seam + TEXT + DOC) is built and checker-PASSed against this contract
(`qa/verdicts/t162-source-adapters-1a.md`); AUDIO/DRIVE/EMAIL remain unbuilt fast-follow units.
**Covers:** goal task T-162 (multi-source adapters: Google Drive, video, audio, document,
email and text into one evidence model) — **phase 1: TEXT, DOC, AUDIO** (VIDEO exists,
T-060/T-131); **phase 2 (declared, fast-follow unit): DRIVE (OAuth device flow), EMAIL
(.eml/.mbox local files only).**
**Owner:** /checker. **Criticality:** CRITICAL — T-163 (orchestrator),
T-164..T-169 all sit behind this stage.
**Depends on:** `core-invariants.md` (all), `browser-and-secrets.md` B5-B9 (credentials
never reach a model/log/screenshot), `ingest.md` (the VIDEO half this extends, never
duplicates).

## Purpose

Any project's teaching material — typed text, an uploaded document, a voice note, a
screen recording, a Drive folder, an email thread — converges on ONE evidence model
(`Source`, already shipped in `schema/project.py`) with provenance, so the learn-or-
explore orchestrator (T-163) can consume every source kind through a single seam.
Adapters CONVERT; they never decide what the product is. Content-addressed (`sha256`)
dedupe: the same file uploaded twice is ONE Source.

## Phase-1 scope (build first)

| Kind | Input | Extraction path |
|---|---|---|
| `TEXT` | inline body / pasted text | stored verbatim on `Source.text`; no model call to register |
| `DOC` | .pdf/.docx/.md/.txt upload | text extraction (host-side, deterministic); Gemini only if pages are scanned images |
| `AUDIO` | .mp3/.wav/.m4a/.ogg/.opus | **Gemini-first** via the Provider seam (`providers/base.py`, Umesh's Gemini key; no new vendor); Track A3's `media/` probe+chunk reused; `media/transcribe.py` (Whisper) survives only as the no-API fallback |

## Criteria (checker to finalize wording at intake)

- **SA1 — One evidence model, no second store.** Every adapter converges on the existing
  `Source` model + `sources.jsonl` (C1/C3). New `SourceKind` values (`DRIVE`, `EMAIL`,
  plus `AUDIO` if absent at build time) are added to the enum in `schema/`, nowhere else.
- **SA2 — Content-addressed dedupe.** The same bytes registered twice is ONE Source
  (sha256); the UI says "already registered" instead of creating a duplicate row.
- **SA3 — Credentials never reach a model, log, or screenshot.** Drive OAuth refresh
  tokens are `SecretRef`s in the project `.env` (phase 2); email requires NO mailbox
  credentials in phase 1 (.eml/.mbox are local files). `assert_no_raw_secrets` gates any
  model call on extracted content.
- **SA4 — Extraction is provenance-tracked.** What the orchestrator later reads cites
  the Source id (and, for audio, the transcript segment) — same discipline as VIDEO's
  per-second SourceRefs.
- **SA5 — Degradation is honest, never silent.** No Gemini key -> audio falls back to
  Whisper with a note on the Source; an unreadable doc registers as a Source with an
  `extraction_error` note, never silently as empty text.
- **SA6 — A model may NAME, never DECIDE (D-017 boundary).** A model may summarise what
  a document says for the human; it may not choose which checks run or alter stored text.

## Phase-2 scope (declared now, built as a fast-follow unit)

- `DRIVE`: OAuth **device flow** (Umesh's answer #2) — interactive consent once, refresh
  token stored as a `SecretRef`; folder-scoped listing; every fetched file becomes a
  content-addressed DOC/VIDEO/AUDIO Source with its Drive id in `Source.url`.
- `EMAIL`: **.eml/.mbox local files only** (Umesh's answer #4); attachments extracted as
  DOC/VIDEO children; no IMAP/mailbox credential surface in this contract.

## Explicit no-fire list (do not raise these as findings)

- No IMAP/SMTP fetch, no mailbox credentials — phase 1 is local files only (gate answer #4).
- No service-account Drive auth — declined by Umesh (device flow chosen, answer #2).
- No Whisper replacement of Gemini for audio — Gemini-first is the recorded decision
  (answer #3); Whisper is the fallback, not a second competing path.
- The orchestrator (T-163) is NOT this contract — adapters produce Sources; what runs
  because of them is T-163's.

## Open questions for Umesh (blocking nothing else)

1. DOC text extraction library preference (pure-python vs a binary like pandoc) —
   default: stdlib-first (.md/.txt/.docx via zip+xml), no new heavyweight dependency.
2. Max upload size per Source (proposed: 200 MB; larger -> chunked like video already is).
3. Should TEXT sources be reviewable/editable in the UI before the orchestrator reads
   them (proposed: yes — the FlowSpec Review gate discipline, applied to Sources).

## Amendment log (append-only; git history is the version)

- 2026-09-22 · init · contract finalized from gate-A-approved DRAFT to ACTIVE (D-035), on the
  cycle-1 checker-PASS of `t162-source-adapters-1a` (the adapter seam + TEXT + DOC). No wording
  changed from the draft. AUDIO/DRIVE/EMAIL remain declared-but-unbuilt phase-2 scope. Verdict:
  `qa/verdicts/t162-source-adapters-1a.md`.
## 2026-10-15 completion amendment (D-099)

Owner authorization: Umesh approved the complete Ollama-first plan in chat
2026-10-15 and requested implementation through checker PASS. The clauses
below take precedence only on the named behavior; other criteria remain.

### SA7 — Complete registered-source dispatch and PDF evidence
All registered teaching material is dispatched by source type through the existing
Source/store seam: video, extracted document, text, local email content and existing
audio transcripts. Mixed inputs retain source provenance and never overwrite
APPROVED truth. Duplicate bytes remain idempotent under SA2. A registered but
unsupported/unreadable source must be reported, never silently omitted.
Searchable PDFs use host-side extraction; scanned pages use local OCR. Extracted
evidence retains page number, extraction method and available confidence, with
unknown confidence represented honestly. Corrupt/encrypted/unreadable inputs carry
explicit extraction errors; partial extraction identifies unprocessed pages.
The old DOC scanned-page Gemini requirement is replaced by local OCR. Existing
audio transcript/no-API fallback remains supported; this amendment does not require
an Ollama transcription endpoint or a replacement transcription engine. Any model
call uses the approved Provider/default policy; the old Gemini-first/no-Whisper-
replacement statements do not compel a non-Ollama call in the default application.
SA6 still holds: extraction does not autonomously decide which product checks run.
Verify text, scanned and mixed-page PDFs, explicit extraction failures, mixed-source
dispatch, provenance, dedupe and approved-spec protection using synthetic fixtures.

## 2026-10-15 provider policy amendment (D-101)

### SA8 — Supplied narration first, bounded Gemini audio fallback (D-101)
Use a supplied transcript first. If none is supplied and Ollama has no audio
capability, extract audio locally under explicit finite resource/time limits,
then use guarded Gemini audio transcription with the configured existing key.
Never auto-download a local ASR engine/model or silently invoke local ASR as this
fallback. Supplied transcript content remains authoritative evidence; generated
transcripts retain source/segment provenance and actual provider attribution.
Privacy refusal or global budget exhaustion stops the path without provider
fallback. Missing Gemini credentials, failed audio extraction, unsupported audio
or exhausted transcription produce explicit unavailable/incomplete narration,
never silent-content claims. Every physical request/retry is bounded and counted;
unknown usage remains unknown. SA7 PDF/local OCR and mixed-source rules are unchanged.
Verify supplied-transcript zero-call behavior, missing audio capability, bounded
extraction/transcription, missing key, no download/local-ASR invocation, sanitized
transport, provenance and prohibited privacy/global-budget fallback using fakes.
