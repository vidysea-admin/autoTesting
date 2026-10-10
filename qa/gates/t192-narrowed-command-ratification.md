# HUMAN_GATE — does `ingest map` discharge a gate that named `Analyze`?

**Opened:** 2026-09-27 by the maker, on the `t192-url-pattern-heal` cycle-1 verdict (**PASS**,
commit `cfa8cdb9`, pushed). **Decider:** Umesh. **Status:** ANSWERED 2026-10-10 (A) — asked once, then written here.
**Blocks:** nothing. The repair is done, checked and merged; **this gate is about ratifying a
substitution after the fact, not about a defect.**
**Ledger:** `ISS-t192-url-pattern-heal-1` (medium, non-blocking). **Verdict:**
`qa/verdicts/t192-url-pattern-heal.md`.

## The one-line question

Gate `t135-url-pattern-data-migration` answer B (**D-048**) approved *"one Analyze re-run on the
erp project … approved single vision call."* What actually ran was
`uv run autotester ingest map erp` — **no `analyze`, no vision call, no network request.** The
three corrupted `url_pattern` rows are healed and verified. **Is that an acceptable discharge of
answer B, or should the command you named have come back to you first?**

## Why the substitution was made, stated plainly

Read-only tracing before spending anything showed the vision call could not have helped:

1. The corruption is **in the raw model output itself** — the cached observation
   `sources/src_c6bb964cfff8/observations/gemini__ingest_video_v1.md__00.json` literally contains
   `"vidysea.com/erp/trainers"`. Re-requesting it returns the same host-qualified string.
2. **The fix is downstream of the model.** `core/urls.py::screen_url_pattern` is the one boundary
   where an observed url becomes a stored `url_pattern`; `stages/product_map.py:40` calls it while
   building the screen map. The repair therefore happens in `build_screen_map`, reachable as
   `ingest map`, which makes no model call.
3. The checker confirmed independently that `screen_url_pattern` is **never called from
   `adjudicate.py`**, which copies `url` raw — so `ingest map` exercises "the fixed producer end to
   end" (the gate's own wording for why it chose B) **more** literally than `analyze` would have.

## Why it is still being put to you

The checker PASSed the unit and then filed this anyway, and it is right to have done so: *a
HUMAN_GATE exists to keep exactly that decision with you even when the builder's case is
technically sound.* The maker judged the narrowing safe and disclosed it loudly in the manifest —
but it decided, rather than asked. The gate named a command; a different one ran.

**The approval is unspent and still available.** The checker verified this two ways: every
observation file and `analysis.json` under `src_c6bb964cfff8` still carries mtime 2026-09-09, only
`screenmap.json` carries 2026-09-27; and reading `analyze_cmd` (`cli_video.py:222`) and
`map_product_cmd` (`cli_video.py:271`) in full shows only the former spends a model call.

**A correction to the gate's own reasoning, recorded rather than buried:** answer B's cost estimate
was wrong in the first place. Observations are cached and `--force` is opt-in, so "re-run Analyze"
would very likely have cost nothing either. That is a correction to the gate's arithmetic, not to
its choice.

## The decision

| | Option | What it means |
|---|---|---|
| **A** | **Ratify.** One line: the narrowing was an acceptable discharge of answer B. | Closes `ISS-t192-url-pattern-heal-1`. The approved vision call goes back to the shelf as unspent, available if you ever want a genuine re-analysis of `src_c6bb964cfff8`. Nothing is re-run. **Maker's recommendation**, but it is exactly the call the maker should not make for itself here. |
| **B** | **Ratify, and set the standing rule.** Same as A, plus a decisions entry: a gate answer that names a command may be discharged by a strictly narrower one that provably achieves its stated purpose, provided the narrowing is disclosed in the manifest before the check. | Turns a one-off judgement into a rule, so the next maker does not have to guess. Costs an append to `docs/DECISIONS.md` with your `Approved-by:`. |
| **C** | **Do not ratify — run the Analyze re-run you approved.** | Spends the vision call. The checker's evidence says it would change nothing (the model output is the source of the corruption, not its victim), so this buys process fidelity rather than a better outcome. |
| **D** | **Do not ratify, and revert the heal.** | The pre-image is at `.work/t192/screenmap.before.json`, sha256 `46e97134a8…` — but `.work/` is gitignored, so this undo is not durable across a clean. Restores three known-wrong rows to a page a human reads. Listed for completeness; nothing recommends it. |

## Until this is answered

- **Nothing is held.** T-192 is `done`, the manifest is `checked-PASS`, the verdict is pushed.
- `ISS-t192-url-pattern-heal-1` stays `open` — a medium row, not a blocker.
- The vision call approved by gate `t135-url-pattern-data-migration` is treated as **still unspent**,
  not as consumed by this unit. If you pick C, it is there.

Answered: 2026-10-10 — A — chat (Umesh, delegated to the assistant's recommendation): ratified. Running `uv run autotester ingest map erp` instead of Analyze is accepted as the discharge of gate t135-url-pattern-data-migration answer B (D-048). No standing rule (option B not chosen). The approved single vision call stays unspent. Recorded as D-080.
