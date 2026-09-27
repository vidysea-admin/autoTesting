# GATE: commit-before-verdict

**Opened:** 2026-09-16
**Blocks:** nothing. The loop continues under the current practice until this is answered.
**Raised by:** the at423 cycle-1 and cycle-2 checkers (not charged either time). The cycle-2 checker
noted that it belongs here, with an `Answered:` line, not as a paragraph in a manifest.

## The question in one line

Should the maker commit a unit before its checker verdict, or only after a PASS?

## What happens now

For this whole session the maker has **committed each unit before dispatching its checker**. The
maker protocol says the maker commits **only after PASS**: the checker dispatch text notes that "the
unit is normally uncommitted at check time", and the checker's own copy-the-tree procedure assumes
it.

## Why it has been done this way

- **Exact comparison.** Each checker could run `git show <sha>^` against a fixed commit. It did this
  often, for example diffing a mutation spec before and after a rename to prove no row had been
  pointed at a different test.
- **A shared working tree.** Two maker loops run in this repo. Work left uncommitted in the tree can
  be overwritten, or picked up by the other loop's broad `git add`. This session had one real
  incident in the other direction: the maker's broad `git add tests/` swept in the other loop's
  tracked file.

## The costs

- The history holds commits that later FAILed. In this session each was fixed in a follow-up commit
  and none was pushed until a PASS: D-007 lets only the checker push, and only on PASS.
- It departs from the written protocol **without anyone having decided that**, which is the thing
  this gate records.

## Options

**A — Keep committing before check, and write it into the protocol for this repo.** Nothing pushes
before a PASS (D-007 already enforces that), so commits that later FAIL stay local and get fixed
forward.

**B — Commit only after PASS, as the protocol says.** Leave units uncommitted while they are checked,
and accept the shared-tree risk and the loss of exact comparison.

**C — Commit before check on a per-unit branch; merge to master only on PASS.** This matches the
protocol's intent that master holds only checked work. It costs branch handling in a repo with two
concurrent loops.

## Recommendation

**A.** The protocol rule exists so unchecked work is not *shipped*, and D-007 already guarantees that
at push time. Commits before check have been what let checkers compare exact versions, and that is
how several of this session's findings were made.

## How to answer

Reply `A`, `B` or `C`. I will append `Answered: <ISO date> — <choice> — <where>` to this file before
changing anything.

Answered: 2026-09-26T22:34:22+05:30 — C — Umesh via AskUserQuestion in the checker session. Official rule: a unit is committed on its own branch (wave/<slug> worktree) before check, and reaches master only by merge after a checker PASS with a matching cycle. This ratifies the current practice.
