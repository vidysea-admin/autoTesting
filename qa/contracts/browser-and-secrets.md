# Contract — browser session and credential handling

**Covers:** goal tasks T-010 (`browser/session.py`) and T-011 (`browser/secrets.py`).
**Owner:** /checker. **Criticality:** T-011 is CRITICAL — it is the control that keeps
credentials out of models, logs, and artifacts.
**Depends on:** `core-invariants.md` (all criteria apply, C5 especially).

## Purpose

Drive a real, visible browser through a target product on behalf of the tester, authenticated,
without ever exposing the credentials to a model or writing them to disk outside `.env`.

## Criteria — T-011 `browser/secrets.py` (build this first)

### B1 — Loading
- Loads the **repo-root `.env`** (`d:/autoTesting/.env`, resolved via `core/paths.py::ProjectPaths.env_file`)
  into a `SecretStore` keyed by the `SecretRef[]` declared in that project's `project.json`. The file is
  one credential file shared across projects; keys are namespaced per project (`PATHLYNKS_*`) and a
  project can only ever resolve the keys it declares.
- A declared key missing from `.env` raises a named error identifying the key; it never falls back
  to an empty string or to a process environment variable.
- A key present in `.env` but not declared in `project.json` is **ignored for use, still masked**: it is
  reported (`store.undeclared`), can never be `resolve()`d, and its value still feeds the `Redactor`
  and the prompt gate (B4 wins over silence — in a shared root `.env` these are other projects' credentials).

### B2 — Placeholders only, in every direction
- `resolve(step_value, host)` accepts `{{SECRET:KEY}}` and returns the real value **only** when
  `host` is within that `SecretRef`'s `domains`; otherwise it raises.
- A value returned by `resolve` is never stored, logged, or returned to a caller that persists it.
- Any string headed for a provider passes `core.redact.assert_no_raw_secrets` first; a raw secret
  value in a prompt raises rather than being masked-and-sent.

### B3 — Domain scoping is enforced, not advisory
- A secret whose `domains` do not include the current page host cannot be resolved, even when the
  host is otherwise in the project's `allowed_domains`.
- "Current page host" means the host the **browser** will use. A destination that URL parsers
  disagree on (userinfo `@`, backslashes, an empty/unparseable host) is refused outright — the
  gate fails closed rather than trusting `urlparse` over WHATWG. (Edge case recorded from AT-007.)
- Navigating outside `allowed_domains` is refused by the session.

### B4 — Evidence is clean
- `Redactor` built from the loaded store masks every secret value in logs and artifacts.
- Screenshots mask inputs whose field carries a `secret_key` before capture (see B7).

**Verify:** `uv run pytest tests/test_secrets.py` exits 0, covering: missing key, undeclared key,
wrong-host refusal, correct-host resolution, prompt gate, redaction of a resolved value.

## Criteria — T-010 `browser/session.py`

### B5 — Real visible browser by default
- Launches Chromium headed when `Project.headed` is true (the default); headless only on explicit request.
- Uses a persistent profile at `profiles/<slug>/` so an interactive login survives to later runs.

### B6 — Bounded navigation
- Refuses to navigate to a host outside `Project.allowed_domains`, raising a named error.

### B7 — Evidence capture with masking
- Captures screenshots to the run directory; before each capture, inputs bound to a `secret_key`
  are masked so the rendered image cannot contain a credential.
- Produces `Evidence` records (schema) with `masked=True` and run-relative paths.

### B8 — Human-in-the-loop for OTP
- When a flow needs a one-time code, the session surfaces a `blocked_hitl` state carrying a prompt
  for the human, rather than guessing, retrying, or failing silently.

### B9 — Cleanup does not harm the developer's own browser
- Teardown closes only the contexts this session opened, identified by its own `user_data_dir`.
- No process-wide `taskkill`/`pkill` of Chrome anywhere in the codebase.
  (Brain recipe `selenium-browser-cleanup-targeted.md`: a naive kill destroyed a developer's open tabs.)

**Verify:** `uv run pytest tests/test_browser.py` exits 0. Tests that need a real browser are
marked and may be skipped when Playwright browsers are not installed, but the domain-refusal,
masking, and cleanup-scope tests must run without a browser.

### B10 — Unified intake treats a credential batch as one guarded secret transaction
- A route accepting new credential values validates the entire repeated batch before any artifact
  write, then guards every same-request non-secret field against the union of pre-existing root
  secrets and the newly submitted values. No earlier validator or refusal may echo one of those
  values; hostname-shaped credentials are secrets too.
- A submitted key colliding with any root `.env` key or another project's declared `SecretRef` is
  refused, including when the other declaration has no current value. Duplicate keys inside one
  batch are refused.
- The `.env` batch is rendered completely before persistence and committed with a same-directory
  owner-only temporary file, flush/fsync and atomic replace. A bad later row or failed replace leaves
  the previous `.env` byte-identical, and rotating a key replaces every duplicate existing line.
- Project artifacts retain only `SecretRef` keys/scopes; a refusal body, browser page, log, project
  artifact or source artifact never contains a submitted raw value.

## Out of scope for these units

Real Pathlynks credentials, live login against a production host, and any write to a real account.
Those belong to T-030 and require the human gate. These units are proven against a local fixture
page and mocks.

## No-fire list

- Absence of Gemini/Anthropic providers (later tasks).
- Absence of a UI (T-100).
- Cross-browser support beyond Chromium (not required by any criterion).
- Performance of browser startup.

## Amendment log (append-only; git history is the version)

- 2026-09-03 · routine · B1: credential file is the repo-root `.env`, keys namespaced + declared per
  project (was `projects/<slug>/.env`) · why: user instruction 2026-09-03 ("place .env too in the
  root directory of d/autoTesting/.env"), folded from `qa/feedback-inbox.md`; non-safety-weakening —
  scoping still comes from per-project `SecretRef.domains`, and undeclared keys stay unresolvable.
- 2026-09-03 · routine · B1: undeclared keys are "ignored for use, still masked" (was "ignored and
  reported, not used") · why: resolves the B1-vs-B4 tension filed as AT-004; a shared root `.env`
  makes undeclared values other projects' credentials, so masking them tightens B4 without
  weakening B1's no-use rule.
- 2026-09-03 · routine · B3: recorded edge case — parser-divergent destinations (userinfo,
  backslash, unparseable) must fail closed · why: AT-007 demonstrated `urlparse` and WHATWG
  disagreeing on the host of `https://evil.test\@pathlynks.test`. Tightening only.
- 2026-09-03 · SUPERSEDED (see 2026-09-04 row below) · Mongo/DB credential (`PATHLYNKS_MONGO_URI`
  as a `SecretRef`, read-only backend assertions) · why: belonged to a future `execute` contract,
  not B1–B9; left `unfolded` in the inbox with that note.
- 2026-09-04 · routine · resolves the row above in the opposite direction: `PATHLYNKS_MONGO_URI`
  is REMOVED as a forced `SecretRef` on the Pathlynks project rather than added elsewhere · why:
  Umesh, 2026-09-04 (`qa/feedback-inbox.md`) — a tester should watch the real browser like a human
  would, not need DB access by default; manual one-time login (new `autotester login <slug>`,
  `browser/secrets.py`+session persistence) is the no-password default, `.env` auto-fill and OTP
  HITL both stay unchanged. Built and checker-PASSed as unit `manual-login` (cycle 1,
  `qa/verdicts/manual-login.md`; ledger F-020). `browser/db.py`/`ReadOnlyCollection` itself is
  NOT removed — the capability stays available for a future case that specifically needs backend
  verification, only the forced-by-default declaration on Pathlynks is gone. Non-safety-weakening:
  nothing here was ever a binding B-criterion, only a proposal that never shipped.
- 2026-09-10 · /checker (t161-unified-project-intake cycle 1) · **new criterion B10 added** — folds
  D-025/T-161's all-secret guard, cross-project key ownership and atomic repeated `.env` batch into
  the credential contract before judging. Tightening only: B1-B9 are unchanged, and accepting a raw
  value at this one UI boundary does not license it to cross into a response, log or artifact.
- 2026-09-22 · CRITICAL (D-034, Approved-by Umesh) · **refines the B10 line above** ("does not license
  it to cross into a response"): the owner-only local credential editor is the one authorized surface
  where a saved value DOES appear in the (local, 127.0.0.1) HTTP response/DOM, for operator verify/edit.
  B1–B9 and B7 (product-screenshot masking) are unchanged; the value still never reaches a model, log,
  shared artifact, or product screenshot. Full scope lives in core-invariants.md C5's owner-only-editor
  exception. Found live by checker Mode D (AT-554); decided by Umesh (option A).
