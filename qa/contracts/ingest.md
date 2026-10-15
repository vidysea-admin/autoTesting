# Contract — INGEST stage (T-060, video half)

**Covers:** goal task T-060 (video-ingest portion only — see no-fire list for what's deferred).
**Owner:** /checker. **Criticality:** HIGH — the entry point of the whole pipeline; everything
from T-065 onward depends on a `FlowSpec` existing.
**Depends on:** `core-invariants.md` (all).

## Purpose

Turn a demo video (a `Source`) into a `FlowSpec` — screens and flows, every step provenance-
tracked to the exact second it was observed — using a vision-capable provider (`GeminiProvider`,
the `see_video` role). This is the "video/docs → FlowSpec with SourceRefs" half of T-060's title;
the "docs" half and the full golden-test acceptance (">=90% step recall vs a hand-written list on
a real demo video") are explicitly out of scope for this contract — see the no-fire list.

## Criteria

### I1 — Screens and flows only from what was actually observed
`stages/ingest.py::ingest_video` maps a provider's `VideoObservation` (screens[], flows[]) into a
`FlowSpec` — it invents no screen, flow, or step beyond what the `VideoObservation` contains. The
mapping is deterministic: the same `VideoObservation` always produces the same screen/flow ids
(content-addressed via `content_id`, same discipline as `Case`/`Script`).

### I2 — Every step carries provenance to the second
Each `Step` the stage produces has a `SourceRef` naming the source video's id and the
`t_start`/`t_end` the vision model reported for that action — a human reviewing the resulting
`FlowSpec` can jump straight to the moment the system learned a given step.

### I3 — Flow entry_screen resolves to a real screen id when possible
When an `ObservedFlow.entry_screen` name matches one of the same observation's screen names, the
produced `Flow.entry_screen` is that screen's minted id, not the raw name — so
`FlowSpec.screen(flow.entry_screen)` actually resolves.

### I4 — The vision call is a real provider call, not text-only
`ingest_video` calls `provider.see_video(path, prompt, VideoObservation)` — the video file path is
passed to the provider, never inlined into the prompt text; `GeminiProvider.see_video` genuinely
uploads the file (`client.files.upload`) before calling `generate_content`.

### I5 — Prompt is a file, not an inline string
The ingest prompt lives at `src/autotester/skills/ingest-video/SKILL.md`, loaded by
`stages/ingest.py:31` `SKILL_NAME = "ingest-video"` via `load_skill_prompt` (T-175, D-043; the
old `prompts/ingest_video_v1.md` no longer exists), following the project's "prompts are
files" rule; the prompt itself instructs the model not to invent unobserved content and never to
write down a real-looking credential even as an example.

### I6 - Learning is persisted, and a human's review is never discarded by accident
`stages/ingest.py::persist_ingest` writes the produced `FlowSpec` through
`ProjectStore.save_flowspec`. Before T-131 `ingest_video` returned a spec and no caller saved it,
so a recording could be watched and leave no trace on disk; producing a spec is not the
deliverable, persisting it is. Persisting blindly is the opposite defect: an existing spec at
`ReviewStatus.APPROVED` is **refused** (`FlowSpecApproved`) unless the caller passes an explicit
`replace=True` / `--replace`, because overwriting an approved spec throws away a human's
judgement and not merely data. A `DRAFT` or `NEEDS_EDIT` spec carries no such judgement and is
overwritten freely. The refusal must be genuinely non-destructive - the approved spec is still
intact on disk after the refusal, not half-written.

### I7 - Every screen names where it came from, and the video/crawl seam uses ONE templater
Each `Screen` produced from a recording carries a `SourceRef` (`source_id`, `t_start`, `t_end`)
back to the second it was read from. `url_pattern` is produced by `core.urls.url_template` - the
crawler's own function, not a lookalike - so a screen learned from a video and the same screen
found by a crawl collapse to one row instead of two. It is set **only when a url was actually
observed**; a screen with no visible address bar gets `None`, because inventing a pattern would
report coverage of something nothing has seen. Asserting the literal templated string is not
sufficient on its own: the defending test must assert against `url_template`'s own output, so the
two sides of the seam cannot drift apart silently.
**And the defending test must feed the VIDEO side a SCHEMELESS url**, because that is what a
vision model reads off an address bar (browsers hide the scheme) and it is what this repo's real
recordings actually contain (`projects/erp` analyses: `url: vidysea.com/erp/trainers`). A test that
hands both seams the same `https://...` string proves only that one function is deterministic; it
cannot see the drift this criterion exists to prevent (AT-294).

### I8 - Narration is ground truth, injected, and never re-transcribed
When a `Transcript` exists it is injected into the prompt verbatim, and the prompt instructs the
model to **align** it to what is on screen rather than re-transcribe or paraphrase it: a
paraphrased complaint is a fabricated quote attributed to a real person, and this system treats a
tester's own words as evidence. When no speech exists, the prompt says so explicitly rather than
leaving a gap the model may fill.
**The template must carry the placeholder the code replaces.** `str.replace` on a missing needle
does not raise, so a template that loses `{{NARRATION}}` ships a prompt that runs blind with
nothing failing anywhere. A test defending the *template* - not only the code - is therefore part
of this criterion, not an extra.

### I9 - The upload is readable before it is used, and every SDK failure is typed
`providers/gemini_files.py::upload_and_wait` polls the Files API to `ACTIVE` before any
`generate_content` call. `files.upload` returns while the file is still `PROCESSING`, and passing
that handle onward fails sometimes loudly and sometimes as an **empty reading**, which is the
worse outcome because it is indistinguishable from a bad prompt. `FAILED` raises rather than
polling forever; a bounded timeout raises rather than hanging; every SDK exception (upload, poll,
generate) is re-raised as `ProviderError` **with its cause chained**. Truncation is reported AS
truncation: a `MAX_TOKENS` finish reason says the answer hit the output ceiling, not "structured
output did not parse", which sent the reader to their schema instead of to the chunk length.
An upload cache is permitted and must **degrade to a re-upload, never to an error**: a dead,
expired, non-`ACTIVE`, or corrupt-on-disk cache entry is a miss, not a failure.

### I10 - Sources are identified by content, and re-registering is not re-recording
`register_source` keys on the file's sha256, not its path: the same bytes registered twice return
the existing row. A shell command gets re-run by habit, and a doubled corpus would quietly skew
every recall number scored against a human's sheet. A missing file raises rather than registering
a phantom. Two different paths holding identical bytes are ONE source (the first registration's
path wins, and the second call's `label` is not applied) - the intended answer for a corpus keyed
on content, recorded here so it is a decision rather than an accident. Changed bytes at the same
path are a NEW source; the old row is never mutated, because a `SourceRef` that already points
into it must keep meaning what it meant.

### I11 - What we send is in the vendor's dialect, and the dialect is an ALLOW-list
Nothing leaves this repo as `response_schema` that Gemini's dialect cannot name. Concretely, for
every model the code actually sends: no `additionalProperties` (which this repo's own C1
`extra="forbid"` produces on every model), no `$defs`/`$ref` (references are inlined, because a
reference the dialect cannot resolve is a 400 on every call, not a warning), and no `anyOf` union
standing in for an optional (`X | None` collapses to `nullable`).
**The list of rejected keywords is a floor, not the criterion.** The dialect is
`google.genai.types.Schema`'s field set - `any_of, default, defs, description, enum, example,
format, items, max_items, max_length, max_properties, maximum, min_items, min_length,
min_properties, minimum, nullable, pattern, properties, property_ordering, ref, required, title,
type` - and the SDK passes a `dict` schema through **untouched**, so anything outside that set
reaches Google and fails there, exactly as `additionalProperties` did. A deny-list sanitiser is
therefore a statement about the keywords someone has already been burned by. Adding a model shape
that emits a keyword outside the allow-list re-creates AT-230, and the check for that is this
criterion, not a memory of which four keywords hurt last time.

### I12 - A keyword is only a keyword in keyword position
Inside a `properties` map the keys are FIELD NAMES. A field called `title`, `default`, `type`,
`format`, `items`, `enum` or `required` survives with its own subschema intact, while the same
word as an annotation on a schema node is dropped. The invariant behind it, which is the one that
actually 400'd (`required[3]: property is not defined`): **`required` never names a property the
schema does not contain**, at any depth.

### I13 - The wire is pinned, not just the renderer
`providers/gemini.py` sends the sanitised dict, never the Pydantic class, and a test asserts that
on the config the provider builds - with no client, no network and no key. A sanitiser with
complete coverage and an unpinned call site is the exact shape AT-230 shipped in: eleven
assertions all calling the renderer directly, and the one line that uses it defended by nothing.
**A behaviour this contract names is not evidenced by the code containing it; it is evidenced by a
check someone else can re-run** (C7). This applies to every clause here, I15 included.

### I14 - A schema that cannot be rendered is refused HERE, before it is paid for
An unresolvable or endlessly-expanding `$ref` raises `SchemaTooDeep` locally rather than being
sent, and **the message identifies the offending reference by name**, because the ceiling is on
`$ref` expansion depth and a large-but-finite model graph can reach it without being
self-referential at all - at which point "is a model self-referential?" with no name attached
sends the reader hunting. Counting `$ref` expansion and not structural nesting is part of the
criterion: a JSON schema is many levels deep before any model nesting starts, and a structural cap
refuses valid schemas.

### I15 - What comes back is validated on OUR side, where the dialect cannot reach
The provider validates the returned dict through the model and raises `ProviderError` (never a
bare `ValidationError`, never a silent pass-through) when it does not fit. This is deliberately
stricter than the request schema can be: `extra="forbid"` is C1's rule and Gemini's dialect has no
way to express it, so an unexpected key is caught only here or not at all. Per I13 this needs a
check, not merely the code - a stub response is enough; no network is required.

### I16 - Ingest leaves the review status DRAFT and nothing waits on it (D-070 item 2; added 2026-10-11)
A recording becomes a `FlowSpec` without a human step. `ingest_video` and `persist_ingest` leave
`review.status` at its default `DRAFT` (never `APPROVED`, never `NEEDS_EDIT`), do not call
`approve`, and do not call `require_reviewed`; no ingest output waits on a human approval before the
next stage (reconcile, `reconcile.md`) may read it. I6 stands: a human-`APPROVED` spec already on disk
is still not overwritten without `--replace`, because D-070 removes the dependency on a human, not the
protection of one's judgement. *Verify:* a `MockProvider` ingest followed by `persist_ingest` into an
empty project yields `review.status == DRAFT`, `review.by is None`, with no `approve` call;
`grep -nE "require_reviewed|approve\(" src/autotester/stages/ingest.py` returns nothing; the I6 refusal
test still passes. *Falsification:* make `persist_ingest` set `ReviewStatus.APPROVED` on write; the
DRAFT assertion must go red.

## No-fire list

- **The golden test itself** (">=90% step recall vs a hand-written list on a real demo video") —
  there is no Pathlynks demo video in this repo yet (a separate, standing blocker, tracked
  outside this contract). This contract is satisfiable with `MockProvider`-seeded tests only; the
  real-video acceptance is a follow-on once a video exists.
- **Doc ingestion** (the "docs" half of T-060's title) — this contract covers video only.
- **Merging into an existing `FlowSpec`** — `ingest_video` always produces a fresh `FlowSpec`;
  conflict detection (`Conflict` model) and merge logic are a later unit's job.
- **The review gate** (`FlowSpec.review.status` draft→approved) — that is T-065, a separate task
  the plan already names; since D-070 item 2 it is a status only (`review-gate.md` R5), and I16
  below states the one thing ingest owes it.
- **Live model calls.** No criterion above requires one; the whole stage is satisfiable against
  `MockProvider`, and `upload_and_wait` is judged on its state machine and error shape rather than
  against the real Files API. Exercising the real Files API is A3/A4 territory, and that is where
  the `google-genai` declaration (AT-130, see the amendment log) must be closed.
- **`ObservedScreen.screenshot_ts`** - requested in the prompt, defined in the schema, consumed by
  nothing. It lands with frames in A3. Verified as an honest, declared gap.
- **`VisionOptions.fps` and `thinking_level`** - carried in the schema and not applied by
  `_config` today (AT-126). Out of scope for I9, which governs upload and error shape only.
- **Media prep, chunking, whisper, the ensemble and adjudication** (A3/A4), and **merging into an
  existing FlowSpec** (A6).
- Real live calls to Gemini in the default test suite — `tests/test_ingest.py` uses `MockProvider`
  exclusively; `GeminiProvider` itself is exercised only for `available()`/error-path shape.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for T-060's video-ingest half — no contract existed
  before this cycle.
- 2026-09-08 - routine - added I6-I10 for T-131 (Track A2) - why: folded from
  `qa/feedback-inbox.md`, where the maker filed I6-I9 and the checker authored them. Each was
  judged on the checker's own execution rather than on the maker's framing, and I10 was added
  because `register_source`'s content-identity rule is a real decision this unit made that the
  four requested criteria left ungoverned. I8's placeholder clause is kept as a *criterion* and
  not a note: sabotage C reproduces three failures, one of which exists solely to defend the
  template, and that test is the only thing standing between the system and a prompt that ships
  without narration while every other test stays green. I9 gained the cache-degradation clause
  after probing - a dead handle, a `PROCESSING` handle, an expired entry and a corrupt cache file
  all fall back to a re-upload, and that is now required rather than incidental.
  **Ruling on the maker's first offered judgement (`google-genai` left undeclared in
  `pyproject.toml`, contrary to plan section 4 A2):** the omission is a real deviation from an
  approved plan, filed as AT-130, but it does not fail this unit. The maker's stated reason is
  partly wrong - `google.genai` IS importable in this environment today (verified), so the
  provider is not dead code - and that is the actual hazard: it resolves only as a transitive
  dependency of `langchain-google-genai`, so `GeminiProvider` works by the accident of somebody
  else's pin, which is exactly what a direct declaration exists to prevent. It must be closed in
  the unit that first calls the API for real (A3), and the no-fire list now names that so the debt
  cannot go quiet.
  **Ruling on the second (a hygiene line banning `git checkout` as a sabotage-restore while work
  is uncommitted):** upheld in substance, refused in this location. A feature contract judges the
  artifact, not how the maker held the tools; AT-101 already records this class against the
  `living-ledger` feature, and the extension belongs there - filed as AT-131. Verified
  independently that nothing was in fact lost to the accident: the committed prompt diff is a
  coherent 29-line rewrite carrying the full "align, never re-transcribe" section and exactly one
  `{{NARRATION}}` placeholder, not a degraded retype.
- 2026-09-09 · routine · added **I11-I15**, the provider-seam response-schema criteria, at the
  maker's request in `qa/manifests/at230-gemini-schema.md` (AT-230) · why: the change that made
  every real model call possible had no criteria to be judged against, because this contract's
  no-fire list had deliberately deferred "live model calls" to A3/A4 and A3 has now happened. Each
  is a tightening; nothing is weakened. Where I authored differently from the maker's five
  requested lines, and why:
  **(i) I11 is stated as an allow-list, not as the maker's three-keyword deny-list.** I probed the
  installed SDK (`google-genai` 2.22.0): `types.Schema` has exactly 24 fields, and
  `GenerateContentConfig(response_schema=<dict>)` performs **no local validation at all** - a dict
  containing `const`, `prefixItems`, `oneOf` or `allOf` is passed through byte-for-byte and fails
  at Google with the same `Unknown name` 400 that `additionalProperties` produced. Constructed
  probes confirm the current sanitiser emits `const` for a single-value `Literal`, `prefixItems`
  for a `tuple[int, str]`, and `oneOf` for a discriminated union, and passes each through
  untouched. **No model under `src/autotester/schema/` emits any of them today** - I rendered every
  one of them through `gemini_schema` and the rejected-keyword set came back empty - so this is a
  hazard rather than a live defect (AT-265), and it does not fail this unit. But writing the
  criterion as "not these four keywords" would have made the contract a record of past injuries
  instead of a rule, and the next model shape someone adds is the one that re-creates AT-230.
  **(ii) I14 keeps the maker's own "naming the reference" clause even though the artifact does not
  meet it** (the depth branch raises `$ref expanded 20 deep - is a model self-referential?` and
  drops the `node["$ref"]` it is holding; only the unresolvable branch names anything). Softening a
  criterion because the artifact fails it is the one thing this role may never do, and the clause
  is right on its merits: the ceiling counts expansion depth, so a deep-but-finite graph can trip
  it while being perfectly acyclic, and the message would then be actively misleading with no name
  to check it against. AT-267, low.
  **(iii) I13 and I15 carry an explicit "pinned, not merely present" clause.** The maker requested
  I15's behaviour as a criterion and it is genuinely implemented - I drove `_structured` with a
  stub client and a payload carrying an extra key and got `ProviderError`, not a silent pass and
  not a bare `ValidationError`. It is guarded by nothing: reverting the `model_validate` call to
  `return response.parsed` in a `git archive HEAD` extract passes all 910 tests, and grep confirms
  no test in the repo constructs a Gemini response at all. That is the AT-256 shape recurring one
  line below the line AT-256 was about, inside the very unit written to answer it, which is why the
  clause is written into the contract rather than left as a note. C7 already says a unit is
  complete only when a check someone else can re-run passes; I13/I15 say it where the next reader
  of this seam will look. AT-266, high.
  **Ruling on AT-130, which this contract's own no-fire list scheduled:** that list exempts live
  model calls "and that is where the `google-genai` declaration (AT-130) must be closed" - naming
  A3, the unit that first calls the API for real. This is that unit; `pyproject.toml` still
  declares only `langchain-google-genai>=4.4.0`, so `providers/gemini.py` and `gemini_files.py`
  import a package that resolves by somebody else's transitive pin while this repo now depends on
  it for its headline number. The debt is due and it is one line. AT-268, medium. Verdict:
  `qa/verdicts/at230-gemini-schema.md`.

- 2026-09-11 · routine · /checker (t135-coverage-merge-expand, cycle 2) · **I7 tightened with the
  schemeless-input clause above.** Non-weakening: it adds a requirement to the defending test and
  softens nothing. Two findings, both re-derived in a `git archive HEAD` (191be93) extract whose
  `autotester` import was verified to resolve to the extract before any result was trusted:
  **(i) The maker's claim that I7's stated purpose was DEFEATED before T-135 is UPHELD.** At
  `c3da666`, `stages/ingest.py:99` and `stages/product_map.py:40,60` called `url_template(...)` with
  the default `keep_host=True` while `stages/explore_merge.py:73` and `stages/screen_identity.py:53`
  passed `keep_host=False`. For every screen with a visible URL the two seams produced different
  strings, so "a screen learned from a video and the same screen found by a crawl collapse to one
  row instead of two" could not happen — for the entire life of this criterion. I7 asserted that
  each side calls `url_template` and never once asserted that they AGREE, which is why the contract
  could not see it. That is a real contract finding and it is recorded here rather than in a
  verdict that scrolls away.
  **(ii) The cycle-2 canonicalisation does not discharge I7.** Canonicalising all four producers to
  `keep_host=False` removes the disagreement between the FLAGS but not between the OUTPUTS:
  `url_template('vidysea.com/erp/trainers', keep_host=False)` is `/vidysea.com/erp/trainers` while
  the crawl's `https://vidysea.com/erp/trainers` reduces to `/erp/trainers`. Filed AT-294 (high);
  AT-287 reopened. Judged as an artifact failure, not a contract defect — I7 is right and the code
  does not yet meet it.
- 2026-09-28 - routine (correct) - the criterion's prompt path updated from `prompts/*_v1.md` to the
  `skills/<name>/SKILL.md` the code actually loads. Cause: the T-175 skills migration (D-043) moved
  the three stage prompts and amended core-invariants C8, but the three sibling per-stage contracts
  were never updated - so a criterion that says "verify by reading the prompt file" named a file that
  does not exist, making it UNCHECKABLE rather than merely out of date. Verified: src/autotester/
  prompts/ now holds only agent_fix_v1.md and relitigation_v1.md, and each stage's SKILL_NAME comment
  records the old filename it replaced. No behaviour claim changed. **Changes-authorized:** this
  contract's prompt-location line + Amendment log (this entry). **Links:** AT-670; T-175; D-043;
  core-invariants C8.
- 2026-09-28 - CORRECTION (id only) - the entry above cites `AT-670`; the correct id is **AT-690**.
  AT-670 was already spent by the t191 remap the same day, so the sweep row collided with it and was
  renumbered into the checker's new block (AT-690..AT-709). No criterion, claim or verification line
  changes. Appended rather than edited because this log is append-only. **Links:** AT-690; AT-664.

- 2026-10-11 · owner-authorized (D-070 item 2) · **I16 added; the no-fire note on the review gate
  updated.** The contract said nothing about what ingest owes the review status after D-070 removed the
  human-approval dependency for video-derived flows. I16 pins the one checkable part: ingest writes
  `DRAFT`, never approves and never calls the guard; I6 (an APPROVED spec is not clobbered) is
  unchanged. Tightening only. **Links:** D-070; `review-gate.md` R5; `reconcile.md` RC10.

## 2026-10-15 completion amendment (D-099)

Owner authorization: Umesh approved the complete Ollama-first plan in chat
2026-10-15 and requested implementation through checker PASS. The clauses
below take precedence only on the named behavior; other criteria remain.

### I4 amendment — Provider-neutral real visual transport
I4's Gemini upload is one implementation, not a mandatory vendor. Ollama video
analysis sends real readable sampled image bytes with their timestamps through
Provider. The request preserves frame-to-time correspondence; filenames, empty
images or transcripts alone cannot satisfy video understanding. A configured model
must pass a behavioral image-understanding capability check before serving vision;
unsupported/unverified capability produces an explicit unavailable/inconclusive
result, with no silent image dropping or automatic vendor substitution.
Verify real visual payloads and timestamps using synthetic frames and fake transport;
record a behavioral live probe separately before claiming live vision acceptance.
Video-learning completeness and narration-ground-truth rules remain in force.

## 2026-10-15 provider policy amendment (D-101)

### I4 amendment — Eligible visual fallback (D-101)
The D-099 visual requirements remain: actual readable visual payloads with source
time correspondence and behavioral capability verification. A configured Gemini
provider may serve visual fallback when Ollama key/auth/service is unavailable;
no privacy refusal or global budget exhaustion may cross to another provider.
Only capability-verified models serve visual interpretation. Unsupported visual
capability is explicit; it never becomes text-only pretend success. Provider,
reason and accounting identify the physical attempts actually made. This clause
changes provider eligibility only, not sanitation, provenance or completeness.

## 2026-10-15 capability eligibility correction (D-102)

The D-101 eligibility lists also include unavailable required Ollama capability.
A configured, capability-verified Gemini fallback may therefore serve that required
modality/capability even when Ollama text service itself is available. Without a
usable authorized fallback, unsupported capability remains explicitly unavailable.
All other boundaries remain: no fallback on privacy refusal, global budget or
deadline exhaustion; finite physical requests, actual provider/reason/accounting,
truthful unknown usage, and explicit configuration precedence are unchanged.
## 2026-10-15 I9 safe SDK diagnostic clarification

I9's cause-chain requirement is subordinate to core C5: raw SDK exceptions may
contain credentials, paths, request/response payloads or prompt echoes and must
not be exposed through ProviderError cause chains, logs or persisted artifacts.
A safe SDK exception category and sanitized diagnostic preserve the attribution
intent; a fixed safe category-only diagnostic is acceptable when content cannot
be sanitized reliably. Suppress rendering of raw SDK cause/context (for example,
`raise ProviderError(safe_diagnostic) from None`) or chain only a sanitized safe
surrogate; never chain the original secret-bearing vendor exception. Do not copy
its payload/attributes into the public error or artifacts.
The error remains a typed ProviderError. MAX_TOKENS/output-ceiling truncation is
still explicitly reported as truncation and must not become generic parse failure
or enter malformed-JSON repair. ACTIVE polling, bounded timeout, upload-cache
miss behavior, actual provider/reason/accounting and all D-101/D-102 fallback
privacy/budget boundaries remain unchanged. No new fallback eligibility is added.

Authority: existing core-invariants C5 and the approved safe-error/privacy policy;
clarifies compatible I9 interpretation without changing an enforcement path or
approach. Maker feedback is preserved verbatim in the gemini-media-guard unit's
qa/feedback-inbox.md section "Gemini media guard — I9 safe cause-chain conflict
(2026-10-15)". Runtime verification belongs to that separate unit: planted vendor
payloads must not appear in formatted tracebacks/artifacts; upload/poll/generate
failures remain typed, and MAX_TOKENS retains its distinct diagnostic.