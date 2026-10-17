# AT-746 — answered gates carried no `Answered:` line

Unit: AT-746 (medium)
Fix cycle: 0
Status: merged-no-check (docs-lane)
Files: `qa/gates/at638-four-contract-files-authorization.md`, `qa/gates/pathlynks-user-account-first.md`, `qa/gates/write-policy-tier.md`, `qa/gates/plan-approved-g10.md`, this manifest. Markdown only; no code or test touched.

## What changed

One `Answered: <ISO> — <choice> — <where>` line appended to the end of each gate, taken from its own on-disk record and the D-entry it cites.

| Gate | Line | Answer | Record used |
|---|---|---|---|
| `at638-four-contract-files-authorization.md` | 122 | 2026-09-27, option A, all four contract files | gate header (lines 4-5) and D-054 (`docs/DECISIONS.md:1432`, `Approved-by: Umesh`) |
| `pathlynks-user-account-first.md` | 79 | 2026-09-27, Pathlynks USER account first (`PATHLYNKS_USER_*`) | gate "The answer, verbatim" section; D-052 (`docs/DECISIONS.md:1281`, `Approved-by: Umesh`) |
| `write-policy-tier.md` | 114 | 2026-09-27, `ALLOW_WRITES` on every target including production | gate "The answer" section; D-053 (`docs/DECISIONS.md:1360`); re-confirmation 2026-09-28 is in the gate's closing note |
| `plan-approved-g10.md` | 31 | 2026-10-07, Group 10 plan approved | gate line 29 ("Approved -- Umesh, 2026-10-07 (chat), recorded as D-074"); D-074 (`docs/DECISIONS.md:2218`, `Approved-by: Umesh (chat, 2026-10-07)`) |

The row's title and the checker's 2026-10-11 note name different gate sets; the union of what is answered on disk with no line is these four.

## Left untouched

- `t125-stalled-at-cycle-cap.md` already has an `Answered:` line (line 100, option A, D-070). Nothing to add.
- `t192-narrowed-command-ratification.md` already has an `Answered:` line (line 66, answer A, D-080). The row calls it genuinely unanswered, which is stale on this base; nothing to add. Not edited.
- 25 other gate files lack a literal `^Answered:` line (listed by the `grep -L` below). The row does not name them, so I did not judge whether each is answered; they are for the checker's next sweep.

## Needs code

- A `doctor` check that every gate whose status says ANSWERED carries an `Answered:` line (the "close the class" suggestion in AT-746 `expected`). Code and test change, out of this lane.

## Commands run (claims checked against them)

- `grep -n -E "^Answered:" qa/gates/{at638-four-contract-files-authorization,pathlynks-user-account-first,write-policy-tier,plan-approved-g10}.md` returns lines 122, 79, 114, 31.
- `grep -n "^Answered:" qa/gates/t125-stalled-at-cycle-cap.md qa/gates/t192-narrowed-command-ratification.md` returns lines 100 and 66.
- `sed -n` on `docs/DECISIONS.md` at 1281, 1360, 1432, 2218 shows the headings D-052, D-053, D-054, D-074; the `Approved-by` lines for D-052, D-054 and D-074 were read in place. D-053 has no `Approved-by` line in the span read; its authority is cited as Umesh via `qa/gates/write-policy-tier.md` in its "What" paragraph.
- `git diff --stat`: 4 files, 8 insertions, no deletions. Files are CRLF and the appended lines are CRLF.
- `grep -L -E "^Answered:" qa/gates/*.md` run before the edit listed all four gates above.
