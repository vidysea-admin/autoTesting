# Verdict — crawl-toggle-coverage (combined Checker A + B)

**Checked by:** /checker (combined A+B seat, fresh context, no builder reasoning)
**Date:** 2026-10-29
**Branch / head:** `fix/crawl-record-gaps` @ `81f86001` (worktree `.claude/worktrees/crawl-gaps`)
**Contract:** `qa/contracts/explore.md` X3, X4, X11; `core-invariants.md` C1, C3; CLAUDE.md design rules (file <= 300 lines, enforced by `autotester doctor`)
**Manifest:** `qa/manifests/crawl-toggle-coverage.md`, `Status: ready-for-check`, Fix cycle 1

**Cycle checked: 1**

## Verdict: FAIL (1 blocking finding, 2 warnings)

The cycle-0 blocker B-1 is fixed and both halves of the fix are proven by falsification. The one blocking
finding is a new `autotester doctor` violation that this cycle introduced and the manifest wrongly denies.
It is a one-line fix; nothing else needs re-opening.

## What I re-ran myself (worktree `.venv`, 2 files per call, one pytest at a time)

| Command | Result |
|---|---|
| `uv run pytest tests/test_crawl_toggle_coverage.py tests/test_crawl_record_gaps.py -o addopts=` | 27 passed |
| `tests/test_explore_replay.py tests/test_screen_identity.py` | 20 passed |
| `tests/test_explore.py tests/test_explore_error_causes.py` | 27 passed |
| `tests/test_explore_traversal.py tests/test_explore_node_recovery.py` | 11 passed |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor` | 3 violations: `file-too-long` (A-1 below) + `stale-generated` + `stale-committed` for `docs/SNAPSHOT.md` (pre-existing, as briefed) |

## Falsification (scratch copies from `git archive HEAD`, `PYTHONPATH` verified to load the copy; no git stash, worktree untouched)

| Revert | Result |
|---|---|
| `screen_identity.py:72` `return revealed and all(...)` -> `return False and all(...)` | `1 failed, 7 passed`: `test_a_revealed_control_that_does_not_navigate_is_the_same_screen` fails at `tests/test_crawl_toggle_coverage.py:135` (`assert 2 == 1`, a duplicate `/` node is minted again) |
| `explore_replay.py:218` `press_revealer(rt, edge.from_node, edge.target)` removed from `perform` | `1 failed, 7 passed`: `test_replay_presses_the_revealer_before_a_revealed_control` fails at `tests/test_crawl_toggle_coverage.py:150` (crawl `ABORTED`, not `COMPLETED`) |

Each revert turns exactly its named test red and leaves the other seven green, so the two tests are independent and bite.

## Probes (read of code + tests)

- **Non-navigating revealed control (B-1):** `same_screen` (`screen_identity.py:57-72`) returns True on the same `url_template` when `revealed` and every visible element of the result is among the node's known role+selector pairs. `try_action` passes the node's latest elements and `revealed` (`explore_node.py:171-172`). Test 130 asserts COMPLETED, one `/` node, all EXPLORED, SAME_SCREEN with `to_node == from_node`. Holds.
- **Dialog at the same URL stays a new screen:** a different `url_template` returns False (`screen_identity.py:67`); a press showing a control the node never had (the `Close dialog` control) fails the `known` check. Test 142 asserts two `/` nodes, both EXPLORED, COMPLETED, toggle pressed >= 3 times. Holds.
- **Persistent toggle ends loudly:** test 156 requires a NAVIGATION issue containing "lost this screen" and no NAVIGATED `Reports` edge. Passes. Holds.
- **Budget:** `press_revealer` adds 1 to `actions_used` (`explore_replay.py:181`); `_click_loop` charges a revealed control 2 against the per-node cap (`explore_node.py:253`) and 1 + the re-press against `actions_used`. Keyed by `(node_id, selector)`; test 179 covers key and count. Holds, conservative (over-counts rather than under-counts).
- **Open points declared honestly:** the manifest's "For the checker to weigh" lists the nested-expander case (new state, new node, reachable by toggle + control) and the "only the observation right after the toggle" limit. Both match the code (`note_revealed` runs only at the SAME_SCREEN layout-toggle branch, `explore_return.py:147`).

## Findings

### A-1 (BLOCKING) Cycle 1 adds a new `autotester doctor` violation, and the manifest says otherwise

`tests/test_explore_replay.py` is 301 lines (`file-too-long: 301 lines > 300`). At `HEAD~1` (`f4acf9b8`) it was exactly 300; the cycle added `self.revealed_by = {}` at `tests/test_explore_replay.py:167` and pushed it over. Manifest criterion 8 and "Tests run" claim `autotester doctor` shows "only `docs/SNAPSHOT.md` stale"; that is false at `81f86001`. `autotester doctor` is a declared verify command in `qa/adapter.json`, and the 300-line rule is a CLAUDE.md design rule enforced by it, so this cannot PASS.
Fix direction (checker does not edit): remove or condense one line in that test file (or move the `_FakeRuntime` attribute into an existing shared fixture), then re-run `uv run autotester doctor` and confirm only the two `docs/SNAPSHOT.md` rows remain. No behaviour change needed.

### A-W1 (warning) Replay presses now spend `actions_used`; replay of a revealed edge is dearer than other replays

`explore_replay.py:181` charges every revealer press, including those in `perform` during a `return_to` replay, while the replayed click itself is not charged there. A crawl with many revealed edges reaches `max_actions` sooner, and the stop reason is named, so it is not silent. Acceptable; flag if crawl budgets are tuned later.

### A-W2 (warning) `same_screen` is vacuously True when the result has no visible elements

`screen_identity.py:72`: `all(...)` over an empty visible set is True, so a revealed control whose press leaves a blank or error page on the same URL is recorded SAME_SCREEN. Only reachable on a revealed control at an unchanged `url_template`, and `drain`/`check_destination` still run first (`explore_node.py:165-170`), so low impact. Not blocking; consider requiring a non-empty visible set.

## Close-out

Maker: fix A-1, set `Fix cycle: 2`, `Status: ready-for-check`. No need to re-run the full falsification; only `autotester doctor` plus the two named tests.

---

# Cycle 2 re-check (fresh checker, head `50196145`)

**Cycle checked: 2**

## Verdict: PASS

Cycle 1 failed only on A-1 (`tests/test_explore_replay.py` 301 lines). It is fixed; nothing else changed.

| Check | Evidence |
|---|---|
| Diff scope | `git diff 95318047..50196145 --stat`: only `qa/manifests/crawl-toggle-coverage.md` (+11/-1) and `tests/test_explore_replay.py` (+1/-2). No `src/` change. |
| Test change is behaviour-identical | The only test hunk (`tests/test_explore_replay.py:170-173`, `_FakeRuntime.__init__`) replaces `self.edges = 0` / `self.issues = 0` with `self.edges = self.issues = 0`. Both are ints, so no aliasing; same values. |
| File length | `wc -l tests/test_explore_replay.py` = 300 (cap is 300). |
| Doctor | `uv run autotester doctor`, advisory `decision-citation-*` rows filtered: `stale-generated: docs/SNAPSHOT.md`, `stale-committed: docs/SNAPSHOT.md`, `2 violation(s)`. No `file-too-long` row. The two rows are the pre-existing SNAPSHOT staleness. |
| Manifest claim | Manifest "Cycle 2" item 9 states exactly those two SNAPSHOT rows and `2 violation(s)`; matches actual output. It also corrects cycle 1's false doctor claim. |
| Tests | `tests/test_explore_replay.py tests/test_explore_flows.py`: 32 passed. `tests/test_crawl_toggle_coverage.py tests/test_crawl_record_gaps.py`: 27 passed. (2 files per call, one pytest at a time, `-o addopts=`.) |
| Worktree | clean before this verdict was appended; main checkout untouched. |

Cycle 1 warnings A-W1 (replay presses spend `actions_used`) and A-W2 (`same_screen` vacuously True on an empty visible set) remain open as non-blocking; neither is touched by this cycle. Falsification from cycle 1 is unaffected, since `src/` is unchanged since `81f86001`.

Maker: close out by flipping the manifest to `checked-PASS`.
