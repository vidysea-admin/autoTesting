# Contract — Multi-vendor provider fallback (T-055)

**Covers:** goal task T-055. **Owner:** /checker. **Criticality:** HIGH — removes the
single-vendor dependency that blocked T-050's grading and every high-value task after it.
**Depends on:** `core-invariants.md` (all).

## Purpose

No stage should ever be unable to get a judge/agent answer just because one vendor's key is
missing, rate-limited, or down. `LangChainFallbackProvider` implements the existing
`providers.base.Provider` seam (so `grade.py`/`agent_loop.py` need zero changes) by trying an
ordered list of LangChain chat models — Anthropic → Gemini → Ollama → ChatGPT — falling through
on any failure, and reporting which vendor actually answered. Umesh, 2026-09-03: "no dependency
on any one model... there should be a fallback system and use LangChain."

## Criteria

### LC1 — Drop-in `Provider` implementation, zero caller changes
`LangChainFallbackProvider` subclasses `providers.base.Provider` and implements `act`/`judge`
with the same signatures as every other provider. `grade.py` and `stages/agent_loop.py` are not
modified by this unit — the seam already accepted any `Provider` instance.

### LC2 — Ordered fallback, each tier conditional on its own credential
The chain order is Anthropic → Gemini → Ollama → ChatGPT (Umesh's stated priority). A tier is
only added to the chain when its credential/service is actually configured
(`ANTHROPIC_API_KEY`/`GEMINI_API_KEY` or `GOOGLE_API_KEY`/`OLLAMA_BASE_URL`/`OPENAI_API_KEY`) — an
unconfigured tier costs nothing and does not require its SDK to be importable.

### LC3 — Falls through on ANY tier failure, reports the real winner
If a tier raises (auth error, network error, structured-output parse failure, or a `None`
parsed result), the provider tries the next configured tier without raising to the caller,
until one succeeds or the chain is exhausted. On success, `provider.id` becomes the winning
tier's name (e.g. `"gemini"`), read by the caller AFTER the call returns — so
`Verdict.grader_provider` and `ProviderUsage.provider` both name the vendor that actually
answered, never a generic `"langchain-fallback"` label.

### LC4 — Exhausted chain fails loudly, with every tier's error
If every configured tier fails, `_call` raises `ProviderError` naming each tier and its error —
never a silent `None` or an unexplained exception from deep inside a vendor SDK.

### LC5 — No live network call in the default test suite
`tests/test_langchain_fallback.py` exercises the fallback loop entirely against fake chat-model
objects mimicking LangChain's `with_structured_output(..., include_raw=True).invoke(prompt)`
shape — no test in the default suite calls a real vendor API.

## No-fire list

- `see_video` / vision role — not implemented by this provider (Gemini's own dedicated provider,
  when it exists for T-060, owns that role); `Provider.see_video`'s base-class `Unsupported`
  applies unchanged.
- Retry/backoff within a single tier (a tier either answers or it doesn't; retry policy is a
  future enhancement, not required here).
- Streaming responses, tool-call chains beyond the single structured-output call, or caching a
  constructed chat-model client across calls (each `_call` rebuilds tiers lazily — a deliberate
  v1 simplicity tradeoff, not a defect).
- Ollama/ChatGPT tiers actually working end-to-end in THIS environment (no Ollama server or
  OpenAI key is configured here) — LC2 only requires that the mechanism is genuinely
  vendor-agnostic and conditionally includes a tier when its credential exists; proving Ollama or
  ChatGPT specifically work is out of scope until someone configures one.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for T-055 — no contract existed before this cycle.

## 2026-10-15 completion amendment (D-099)

Owner authorization: Umesh approved the complete Ollama-first plan in chat
2026-10-15 and requested implementation through checker PASS. The clauses
below take precedence only on the named behavior; other criteria remain.

### OC1 — Default model-chain versus explicitly selected legacy providers
The shipped default for vision, agent and judge is `model-chain`, ordered
`ollama_chat/glm-5.3-flash` then `ollama_chat/deepseek-v4.1-flash`. Its default
order contains no implicit non-Ollama tier. Explicit project/server overrides
remain supported and must be honored or rejected visibly (C9). LC2's original
multi-vendor order describes the explicitly selected legacy `langchain-fallback`
provider only; it does not define the application's defaults. This amends the
Gemini-fallback default recorded in `qa/manifests/ollama-primary.md` without
rewriting that historical evidence.

### OC2 — Every physical attempt is guarded, bounded and observable
All application model calls, including optional agent calls, use the guarded
Provider seam. Each actual request (including a failed request, fallback and JSON
repair) consumes the applicable call budget and has a finite deadline. Usage
records distinguish unknown usage from measured zero. Exhaustion is a visible
failed/inconclusive result, never a successful partial answer. Provider/model
attribution identifies the actual attempt/winner. Ollama Cloud answers undergo
Pydantic validation and at most one bounded JSON repair; no cloud schema-enforcement
claim or reliance on undocumented native structured-output support is permitted.
Verification: fake transports prove request counts, guards, deadlines, unknown
usage, invalid JSON, failed-tier accounting and no implicit Gemini fallback.
