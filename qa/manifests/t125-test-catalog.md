# t125-test-catalog — evidence manifest

## Status: ready-for-check

**Fix cycle:** 1
**Unit:** T-125 — the test catalog (which case classes apply, which are runnable, which are
blocked and why, plus cheap→expensive ordering).
**Contract:** `qa/contracts/catalog.md` (DRAFT → goes ACTIVE on this unit's first PASS), CT1–CT8.
**Branch:** `worktree-agent-aca539b488be4c248` · **Base:** `master` @ `b3060667`.

---

## What I did with the pre-existing `wave/t125-catalog` work, and why

**I brought it forward. I did not rebuild it, and I did not start fresh.** The merge commit is
`cbccc518`.

My dispatch said that branch "has code committed but **no manifest**, so it never entered the
maker-checker handshake." **That is factually wrong, and the correction matters**, so I am putting
it first rather than quietly acting on the true state. The branch carries
`qa/manifests/t125-catalog.md` (525 lines) *and* `qa/verdicts/t125-catalog.md` (760 lines). It went
through **three full checker cycles** and did not stall for lack of a handshake — it stalled at the
project's 3-cycle cap:

- cycle 1 → FAIL 5/8 (`3da63550`), raising ISS-t125-1 (CT6) and ISS-t125-2
- cycle 2 → FAIL 5/8 (`5eb9cebf`), ISS-t125-2 fixed (`72f71aa1`), ISS-t125-3 raised
- cycle 3 → FAIL, **STALLED at cap** (`a27f9794`), ISS-t125-3 fixed (`513a08c7`), ISS-t125-5 raised
- `ac66b4f5` recorded the cap-stall and gated it to Umesh

So the honest reading is: the code is **not** unsound. It is 5/8 against the contract with a
precise, independently reproduced account of what the remaining 3 cost. Discarding ~2,770 lines
that survived three adversarial checks — including live browser walks with committed screenshots —
to retype something similar would have destroyed verified work and re-earned every one of those
findings from scratch. So I merged it and spent this cycle on **the one open defect that is mine to
fix**, ISS-t125-5.

Disposition of each inherited issue:

| Issue | Severity | What I did |
|---|---|---|
| ISS-t125-1 (CT6 dispatch) | high | **Left open — HUMAN_GATE, not mine.** See below. |
| ISS-t125-2 (row names a union of keys) | high | Already fixed on the branch; **kept, and re-falsified** (row 11) so the fix is not taken on trust. |
| ISS-t125-3 (hybrid OAuth+password flow drops its key) | high | Already fixed; **kept, and re-falsified** (row 12). My rewrite had to preserve it while fixing ISS-t125-5 — the two pull in opposite directions. |
| ISS-t125-4 (manifest wording) | low | **Complied with** — see "Audience" below. No code change; it was a manifest-hygiene note. |
| ISS-t125-5 (gate over-blocks) | high | **Fixed this cycle.** Both of the checker's reproductions now have shipped tests. |

Merge conflicts were in three append-only files (`qa/feedback-inbox.md`,
`qa/delegation-ledger.jsonl`, `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md`) and were resolved as a
**union** — both sides kept, nothing dropped. The gate file's master-side note (explaining that a
gate belongs on master so Umesh can actually see it) is preserved verbatim.

---

## HUMAN_GATE (carried forward, still open): CT6 tiered dispatch vs `ui-run.md` RU3

`qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md` — **decider: Umesh, status OPEN.**

CT6 requires `ui/routes_runs.py::trigger_run()` to dispatch tier by tier and **stop** before an
expensive tier with no runnable entries. `qa/contracts/ui-run.md` RU3 (ACTIVE) requires the trigger
to run **every** case on file, which is what makes F-058's pinned-regression guarantee true.
Honouring one breaks the other.

**I did not resolve it, and I did not quietly wire it either way.** `stages/catalog.py::tiers_to_run()`
is implemented, pure, tested and **deliberately unwired**, with the gap stated in its own docstring.
Picking a side would be the maker amending ground truth to make its own unit pass. Four costed
options (A–D) are laid out in the gate file for Umesh.

**Consequence I am not going to dress up:** CT6's *ordering* half is proven below (row 7). CT6's
*dispatch-and-stop* half is **not satisfied by the shipped system** and cannot be until the gate is
answered. Whether that reads as FAIL or as gated is the checker's call, not mine.

---

## What changed this cycle (`file:line` on the post-merge tree)

**1. `src/autotester/stages/catalog.py` — ISS-t125-5, the gate stopped blocking on credentials the
row never reads.**

- `_auth_secret_keys()` (`catalog.py:56-84`) gained `login_fields: bool`. When set, it keeps only
  keys filled into a **credential-named field**, matching `target`/`note` and **never `value`** —
  the value *is* the `{{SECRET:...}}` placeholder, so matching it would re-admit every
  `*_PASSWORD`-shaped key in the spec and undo the scoping entirely.
- `_LOGIN_FIELD_WORDS` (`catalog.py:46-48`) — the vocabulary that decides it.
- `catalog()` (`catalog.py:268-287`) — replaced the spec-wide union gate. Each row is now gated on
  the keys **its own concern** reads: the auth rows on credential-named FILLs **anywhere** in the
  spec (so a hybrid OAuth+password flow keeps its key — ISS-t125-3), the OAuth pack on **its own
  flows'** keys. Fallback: if no field is recognisably a credential, gate on every declared key —
  "nothing unblocks this row" is the worse lie.
- **Removed the `name_keys=` parameter** from `_entry_for()` (`catalog.py:234`) and
  `_pack_entries()` (`catalog.py:195`). Gate and wording are now the same list by construction.
  This is the actual root-cause fix: the previous design *had two knobs* (block on X, word with Y),
  and ISS-t125-2 and ISS-t125-5 are both what happens when they disagree. One knob cannot drift.

**2. `src/autotester/ui/app.py:76-85` — 17 `include_router` lines became one ordered loop.**
Not cosmetic and not scope creep I chose: the catalog router is the **17th**, and master had grown
by 2 lines since this branch's base, so the merged file was **301 lines — over C2's 300 cap** and
`doctor` failed. The alternatives were a second app module (a new module is a HUMAN_GATE in this
repo) or deleting unrelated prose from a shared file. The loop preserves mount order **exactly**,
which matters where routers share a path prefix, and says so in a comment.

**3. `tests/test_catalog.py:255-300`** — the two ISS-t125-5 reproductions, written **before** the
fix and confirmed RED against the pre-fix tree (transcript below).

**4. `qa/feedback-inbox.md`** — the CT5 disagreement, verbatim, not as a contract edit. I did not
touch `qa/contracts/`.

### Size discipline

`stages/catalog.py` came out at **313 lines** after the fix and I brought it to **299** by
compressing prose and call formatting — no logic and no stated reasoning removed. `tests/test_catalog.py`
is at **300**. Both are *at* the cap: **the next change to either file will need a split, which is a
HUMAN_GATE.** Flagging it now rather than letting the next unit discover it.

### Audience (ISS-t125-4, complied with)

Persona walk skipped: **internal-tool audience** — an operator diagnostic page, not a Vidysea
end-user screen. The previous manifest said "no UI surface", which was wrong: this unit ships
`ui/routes_catalog.py`, a real route. Using the checker's own corrected wording.

---

## Capability coverage — every row falsified

Method: copy the file to `.work/falsify-saved/`, apply a **single-hunk** edit to the exact line the
capability rests on, run the named test, restore **from the saved copy** — never `git checkout --`
(AT-701). Harness: `.work/falsify_t125.py`; all 12 anchors verified unique before running.

| # | Capability (the claim) | Named test | Falsifying edit | Observed result |
|---|---|---|---|---|
| 1 | **CT1** `catalog()` is pure: same inputs on disk → byte-identical `Catalog` | `test_catalog_is_pure_same_inputs_same_output` | `_entry_for(cc, project, missing_login)` → `_entry_for(cc, project, missing_login + [str(id(object()))])` | **RED.** `'set 2727638302256 in the repo-root .env' != 'set 2727638302272 …'` — the two calls diverge |
| 2 | **CT2** every `CaseClass` gets exactly one entry | `test_every_case_class_gets_exactly_one_entry_approved` | `for cc in CaseClass` → `for cc in list(CaseClass)[1:]` | **RED.** `assert 14 == 15` (`len(entries)` vs `len(CaseClass)`) |
| 3 | **CT3** a runnable entry never carries a `blocked_reason` | `test_runnable_entries_never_carry_a_reason` | terminal `CatalogEntry(…runnable=True)` → `…runnable=True, blocked_reason=BlockedReason.NO_GROUND_TRUTH` | **RED.** `assert <BlockedReason.NO_GROUND_TRUTH> is None` |
| 4 | **CT4** no FlowSpec → every entry blocked `no_flowspec` | `test_no_flowspec_blocks_every_class_no_flowspec` | `reason=BlockedReason.NO_FLOWSPEC` → `reason=BlockedReason.NO_GROUND_TRUTH` | **RED.** `assert False` — the `all(...)` over entries |
| 5 | **CT4b** the *page* renders that reason on every row, not a generic empty state | `test_no_flowspec_page_renders_the_reason_on_every_row_not_a_generic_empty_state` | same single hunk as row 4 | **RED.** rendered HTML no longer carries the no-flowspec reason per row |
| 6 | **CT5** a `missing_credential` row names the KEY, never a value | `test_missing_credential_names_the_key_never_a_value` | `action = "set " + ", ".join(blocking_keys) + …` → `action = "set the credential in the repo-root .env"` | **RED.** `assert 'DEMO_PASSWORD' in 'set the credential in the repo-root .env'` |
| 7 | **CT6 (ordering half)** `tiers_to_run` STOPS at the first tier with zero runnable entries, even when a later tier is runnable | `test_tiers_to_run_stops_before_an_unreachable_expensive_tier` | `if not cat.runnable_in_tier(tier): break` → `… continue` | **RED — after the row was repaired, see below.** `assert [<Tier.ADVERSARIAL>] == []`, "Left contains one more item" |
| 8 | **CT7** exactly one `BlockedReason` definition in `src/` | `test_packs_never_add_a_second_catalog_or_blocked_reason_definition` | inserted a second `class BlockedReason(StrEnum)` in `schema/catalog.py` | **RED.** `assert 2 == 1` |
| 9 | **CT8** a blocked row states the ACTION, not the bare enum name | `test_missing_credential_row_names_the_key_not_the_bare_enum` | `routes_catalog.py`: `action = escape(unblock_action) if unblock_action else ""` → `action = ""` | **RED.** the key no longer appears in the rendered row |
| 10 | **ISS-t125-5 (a)** an unrelated flow's unset secret does not block the auth rows | `test_an_unrelated_flows_unset_secret_does_not_block_the_auth_rows` | `missing_login = _missing_keys(project, login_keys) if login_keys else all_missing` → `missing_login = all_missing` | **RED.** `auth_wrong_creds blocked on a key login never reads: 'set SFTP_KEY in the repo-root .env'` |
| 11 | **ISS-t125-5 (b) / ISS-t125-2** the OAuth pack is gated and worded by ITS OWN flows' keys | `test_the_oauth_pack_does_not_advertise_a_login_only_key` | `missing_oauth = _missing_keys(project, _auth_secret_keys(spec, only=oauth_ids))` → `missing_oauth = all_missing` | **RED.** `the OAuth pack names a login-only key: 'set DEMO_PASSWORD, GOOGLE_SIGNUP_TOKEN …'` |
| 12 | **ISS-t125-3 (no regression)** a flow that is BOTH a Google sign-up and the product's own login keeps its credential | `test_a_hybrid_oauth_and_password_flow_still_blocks_the_auth_rows` | `missing_login` recomputed with `only={all flows} - _oauth_signup_flow_ids(spec)` (cycle-2's partition, fallback removed) | **RED — after the row was repaired, see below.** `auth_wrong_creds claims runnable while HYBRID_PASSWORD is unset` |

### Two rows survived their first sabotage. Both are reported; neither was dropped.

**Row 7 (CT6) survived — and the test was the problem, not the code.**
`test_tiers_to_run_stops_before_an_unreachable_expensive_tier` built its fixture with
`catalog(project, None, …)` — **no FlowSpec, so EVERY tier is blocked.** `tiers_to_run` then returns
`[]` whether it `break`s or `continue`s: the fixture's construction decided the outcome, so the row
proved nothing. **This is AT-697 shape A exactly.** Its own docstring claimed "even though
ADVERSARIAL has a runnable entry" — a state that fixture never contained. The sibling
`test_tiers_to_run_observed_via_call_order_not_just_final_state` shared the same dead fixture.

This is inherited code that had already passed through three checker cycles. I fixed both tests in
place (`tests/test_catalog.py:193-215`) to use a hand-built `Catalog` with STATIC blocked and
ADVERSARIAL runnable — the only state that distinguishes a stopping walk from a non-stopping one.
`catalog()` never blocks a STATIC class, so no project-shaped fixture can express it; building the
`Catalog` directly is the correct unit test for a pure function over a `Catalog`. The
`break`→`continue` sabotage now goes RED.

**Row 12 (ISS-t125-3) survived for a different and better reason: defence in depth.**
My first edit re-imposed cycle-2's OAuth/non-OAuth partition on `login_keys`. The hybrid fixture's
non-OAuth flow references no secret, so the partition emptied `login_keys` — and the
`login_keys or all_missing` **fallback** restored the spec-wide gate, keeping the row correctly
blocked. The code was right; my sabotage never reached the mechanism the row names. Re-cut to
remove the fallback in the same hunk, it goes RED.

Worth stating plainly: **the fallback is load-bearing.** It is what makes the failure direction of
the `_LOGIN_FIELD_WORDS` heuristic over-blocking (visible) rather than omission (invisible).

---

## Verify output

VERIFY_PLACEHOLDER

---

## What I could NOT do

1. **CT6's dispatch half — blocked on the open HUMAN_GATE, not attempted.**
   `ui/routes_runs.py::trigger_run()` still runs every case with no tier gating. Wiring
   `tiers_to_run()` into it would break `ui-run.md` RU3 and weaken F-058's pinned-regression
   guarantee. Umesh's decision (options A–D in `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md`)
   unblocks it. **The ordering half is now genuinely proven (row 7); the stop-the-dispatch half is
   not implemented, and I am not claiming it is.**

2. **No live browser walk this cycle.** Cycles 1–3 left committed browser evidence under
   `qa/evidence/t125-catalog-2026-09-27-checker-cycle{2,3}/`, including the exact `demo-overblock`
   fixture that produced ISS-t125-5. My change is to the pure stage and is covered at unit level in
   both directions, but **a live re-walk of `demo-overblock` and `demo-hybrid` is the single
   highest-value thing a checker can do to this unit** — ISS-t125-3 and ISS-t125-5 were both found
   that way, and unit tests did not find either.

3. **`_LOGIN_FIELD_WORDS` is a heuristic, not a derived rule.** CT5 never says which key a row
   needs; three cycles each picked a different answer and mine is the fourth. Limits are written up
   in `qa/feedback-inbox.md`: an unconventionally-named login field falls back to the spec-wide gate
   (over-blocks, visibly), and an admin "change password" screen would read as a login credential. I
   did not pick a narrower rule on my own authority because every narrowing I tried re-opened
   ISS-t125-3.

4. **Both `stages/catalog.py` (299) and `tests/test_catalog.py` (300) are AT the C2 cap.** The next
   change to either needs a split, and a new module is a HUMAN_GATE in this repo. Flagged now rather
   than left for the next unit to trip over. `ui/app.py` crossed the cap during this merge and was
   brought back by the router loop described above.

5. **I did not touch `qa/contracts/`** — checker-owned. The CT5 disagreement went to
   `qa/feedback-inbox.md` verbatim. The contract's DRAFT→ACTIVE flip is the checker's to make.

6. **`docs/FEATURES.jsonl` not appended** — the ledger row lands on a checker PASS, not before.

7. **`qa/issues.jsonl` not edited.** ISS-t125-5's status flip is the checker's call on re-derivation,
   not a maker self-attestation.
