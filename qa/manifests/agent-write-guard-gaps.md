# Manifest - agent-write-guard-gaps

**Status:** checked-PASS
**Fix cycle:** 2
**Base SHA:** c4d48ad109f1ef77f73ee9172866cc5feeca7063
**Cycle-0 SHA:** 4119e0a0c153f86ff06ab7dd2eb5f2ffec224640 (FAIL, verdict commit 0d0b5b68)
**Cycle-1 SHA:** 5dbbe33cfebac0b8f0cf48388128184a45244416 (FAIL N1, verdict commit 2d4e426d)
**Candidate SHA:** the head commit of branch worktree-agent-a1af8a18cb4bcb723 that carries this manifest
**Issues addressed:** ISS-t179b-hg1-1, ISS-t179b-hg1-2

## What changed (cycle 2, closes N1)
- `agents/guards.py::_click_names` (the one click-name normalizer, extended in place):
  - Every policy gets the base two readings, byte-for-byte the base code (NFKC, Cf dropped or read as a space, lookalikes, casefold, `normalise_label`). ALLOW_WRITES and TEST_ACCOUNT use only these, the same as base.
  - READ_ONLY adds `_hidden_readings`. Every READ_ONLY name is therefore matched against a superset of the base readings, so anything base refused is still refused, by construction.
- `_hidden_readings` (new) works in four steps:
  1. Apply NFKC, then casefold, then the lookalike table. Casefold runs first, so capital Cyrillic lookalikes now fold too.
  2. Read whitespace and all Unicode punctuation (P*) as a space.
  3. Split the name at each run of `_hidden` characters (`is_ignorable_char` plus U+2800).
  4. A run that sits between two visible characters is a "joint". Each joint is read independently as a join ("") or a gap (" "): all 2^k combinations, with k ≤ 4 (`_MAX_HIDDEN_RUNS`), so at most 16 readings. Runs next to a space or at either end cannot change the result, so they are not counted.
- If a name has more than 4 joints, READ_ONLY refuses it ("hides invisible characters inside its text at too many places"). This fails closed.
- `schema/crawl.py`: the close/cancel/end/stop deny phrase allows up to 3 intervening words (was 2).

## Why per-run enumeration, not 4 class-based forms
- N1's root cause is that one global rule decides join-or-gap for every invisible character. The suggested fix uses 4 class forms (zero-width vs blank filler). It closes mixing ACROSS the two classes, but not mixing WITHIN a class.
  - Example: "De<ZWSP>lete<ZWSP>i<ZWSP>tem" gives "de lete i tem" with ZWSP read as a space, and "deleteitem" with it dropped, so neither reading matches "delete".
- Choosing per run covers every mix, whatever class the character is in. Capping k bounds the cost, and refusing above the cap closes padding attacks.
- Normal labels have at most a few joints: emoji ZWJ sequences, a VS16 before a space, a soft hyphen or two.
- U+3000, NBSP and other Zs are deliberately NOT hidden. NFKC folds them to U+0020, they render as a visible gap, and treating them as hidden would push NBSP-rich labels past the cap. Base treats them the same way.

## Bounds and false positives (documented)
- Gap of 3 words: "Cancel my current premium subscription" and "Cancel your Premium Plus subscription" are refused. Accepted false positives, in the safe direction, are refusals like "Close and view my plan". "Close account settings", "Plan your trip", "Subscription details", "Membership benefits", "View plan", "Change plan", "Close", "×", "Close dialog", "Close menu", "Cancel" and "Back" stay allowed (tested).
- Punctuation counts as a separator only in the READ_ONLY readings. `explore_safety.normalise_label` is unchanged, so the never-click result under ALLOW_WRITES stays identical.

## Side effect (declared, unchanged from cycle 1)
`explore_safety.is_destructive` reads the deny list at every policy. Under ALLOW_WRITES, the widened phrases now sort last in the crawl. This affects ordering only and blocks nothing. It is pinned by `test_is_destructive_reads_deny_list_at_every_policy`.

## Residual advisories
- Same-class mixing across more than 4 joints is refused, not read.
- Lookalikes cover only the small table: lowercase plus casefolded capitals of Cyrillic/Greek a e o p c x y i s j d h o v i. No full confusables skeleton exists in the repo.
- On the crawler side (`deny_reason` on a raw DOM name), punctuation is not yet a separator. Changing `normalise_label` would alter ALLOW_WRITES never-click.

## Consumers
- `guards.write_policy_refusal`, used by agents/tools.py, agent_actuator and browser_use_backend.
- `DEFAULT_DENY_PATTERNS`, through `explore_safety.deny_reason` and `is_destructive`.

## Required checks
- pytest on tests/test_agent_write_guard_gaps.py, test_never_click_destroy*.py, test_agent_tools.py, test_agent_destination_seam.py, test_browser_use_guard.py and test_explore_safety.py.
- ruff on the changed paths.
- autotester doctor.
- Maker probe, base vs candidate at three tiers: .work/make-awgg-c2/ (probe.py, cmp.py, cmp.out).
