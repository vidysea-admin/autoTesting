# SMTP M1 — authenticated report-email preference

Status: ready-for-check
Fix cycle: 0
Risk: high (authenticated own-user write; no delivery or external requests)
Base: cec4b64e59e10019ba616fa031f550542d1350ca
Source candidate: 0f65c208588e2f2d8c5d74d0cb22b140f4e56fa6
Branch: codex/smtp-profile

## Contract and consumer map

- TT8 / HO26-27: session-only GET/POST /profile, own-account numeric ID, default-off checkbox,
  enable/revoke persistence, boolean-only SMTP configuration availability. User approval authorizes
  this local build; real sends and production acceptance remain outstanding.
- AU14 / AU18 / C5-C6: declared session route policies, inherited Origin middleware, no new
  credential reads, no recipient supplied by request, typed atomic JSON under the data root.
- Existing NotificationPref is the only preference shape; no schema/provider changes.
- The new store exists because no preference persistence exists. The new router fills the
  profile capability; the empty registered stub remains for existing router compatibility.
- Consumers: current signed-in user -> profile route -> numeric preference store. SMTP M2 will
  consume load_notification_pref; no mail worker or completion hook is added here.

## Exact runtime changes

New: src/autotester/store/notification_prefs.py, src/autotester/ui/routes_profile.py,
tests/test_notification_profile.py.
Bounded registration: src/autotester/auth/policy.py, src/autotester/ui/routers.py,
src/autotester/ui/theme.py.
Compatibility: tests/test_ui_auth_accounts.py adds the deliberate own-profile session route to
its existing session allowlist. Group-gated project/admin routes are unchanged.

## Immutable maker evidence

qa/evidence/smtp-profile/binding.json binds source/base, interpreter hash/version, dependency
inventory, lockfile, controlled environment, full 1012-file src/tests/scripts/config inventory,
raw proof/invoke/spec hashes. Each command has contemporaneous before/post receipts, actual
child import/runtime identity, full before/after source digest and log hash.

- green.log: 23 passed (profile, auth-account consumers, router-order/stub consumers).
- lint.json + lint.log: touched seven runtime/test paths, Ruff clean with no cache.
- mutation-ledger.json: eleven applied byte mutations, unique anchors, explicit changed bytes,
  named pytest failures, exact restoration hashes and real restored GREEN runs.
- Guard coverage: default off, session policy, handler auth, immutable account identity,
  revocation, input validation, existing Origin boundary, stored identity, corruption fallback,
  numeric path restriction and strict boolean store.
- readiness.py re-derived every receipt and restored source hash; readiness.json records
  MAKER_READINESS_VALIDATED, which is not an independent checker verdict.
- maker active seconds/tokens/cost: null (unavailable). Ratio remains unverified; do not infer
  active time from process wall-clock timestamps. No full suite/browser/network/SMTP runs.

## Checker scope and remaining integration gate

Read seven-path diff, validate sealed packet and independently probe auth/identity/Origin
rejection and default-off/persistence. Reuse immutable deterministic evidence when compatible;
no broad sweep. Bootstrap review target: 180 active seconds / 6000 tokens with unknown maker
denominator; unresolved criteria require NEEDS_EXTRA_REVIEW, never automatic PASS.

Full pytest, repository Ruff, generated map freshness and doctor remain required on the exact
combined release candidate. M1 does not certify SMTP sending, retry delivery or production.
