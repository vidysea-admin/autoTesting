# Contract — ui-settings (global AI/API provider keys)

**Status:** ACTIVE. Plan §3d, `C:/Users/Lenovo/.claude/plans/great-when-you-really-iridescent-ocean.md`.

## Why this exists

Umesh: "ai, api set kar paaye" — a non-technical user must be able to configure the model
provider keys the whole system runs on, without opening `.env` in a text editor. These are
**global** provider keys (`providers/langchain_fallback.py`/`gemini.py` read them straight from
`os.environ`), a different concept from a project's own declared `SecretRef`s
(`qa/contracts/ui.md` U3's per-project credential editor) — hence a separate route group and
contract, not an extension of U3.

## Criteria

- **US1 — the known provider key set, and only that set.** `GET /settings/providers` shows
  masked status (set/not set — never the value) for exactly: `ANTHROPIC_API_KEY`,
  `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OPENAI_API_KEY`. No
  other `.env` key is exposed through this page.
- **US2 — a real value is never rendered, ever.** Same discipline as U3's credential editor: once
  a value is saved, the page shows only whether it is set, never the value itself — not in the
  page body, not echoed back after a POST.
- **US3 — writes go through the one legitimate `.env` write path.** `POST /settings/providers`
  updates one key at a time via the existing, unchanged `env_editor.set_env_value` (owner-only
  file perms, newline-injection rejection) — no second `.env`-writing code path.
- **US4 — reachable from the nav.** The shared `theme.NAV` gets a "⚙ Settings" link so the page
  is discoverable without knowing the URL.

## No-fire list (out of scope for this contract)

- Validating that a key actually works (a real call to the provider) — this page only records
  presence, exactly like U3's per-project credential editor does for `SecretRef`s.
- A generic "add any env key" form — the six keys above are the complete, closed set this page
  manages; a new provider key means a code change here, not a dynamic field.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · init · contract created for the global AI/API provider settings page unit
  (plan §3d, US1-US4), checker-PASSed cycle 1 (`qa/verdicts/ui-settings-providers.md`,
  ledger F-026).
