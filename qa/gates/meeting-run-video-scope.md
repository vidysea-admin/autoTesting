# GATE — meeting-run-video-scope

**Opened:** 2026-09-26 (by /checker, from the 2026-09-25 counselor-tool meeting review)
**Blocks:** AT-587 (no run video)
**Approver:** Umesh (Lab Protocol)

## The question in one line

Should AutoTester record a video of its browser runs so a human can review a 15–20 minute walkthrough, and when?

## Why it needs you

A video is new evidence that can leave the machine, and it can capture secrets. The credential rule (CLAUDE.md:
"Screenshots mask secret inputs before capture") must extend to video before anything is recorded. Recording also costs
disk and RAM on a host that is already RAM-starved, so scope and retention are product decisions.

## Options

- **A — Record on FAIL/INCONCLUSIVE only (checker's recommendation).** Playwright `record_video` per case, kept only
  when the verdict isn't PASS. Secret inputs are masked for the whole recording; retention is the last N runs.
- **B — Always record, plus one stitched end-to-end walkthrough per run** (the "watch the whole flow" demo the meeting
  asked for). Masking and retention as in A.
- **C — Not now.** Screenshots, flow diagrams and the live noVNC view stay the review surface.

## How to answer

Add `Answered: YYYY-MM-DD — A | B | C (+ retention N)` below, or tell the checker or maker session.

Answered: 2026-09-26T22:34:22+05:30 — A, retention 20 — Umesh via AskUserQuestion in the checker session. Record run video only on FAIL or inconclusive; keep the most recent 20; secret inputs masked in video exactly as in screenshots (CLAUDE.md credentials boundary). Maker: goal task for AT-587; checker: contract criterion.
