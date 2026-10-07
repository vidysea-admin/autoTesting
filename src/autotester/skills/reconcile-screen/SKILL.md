---
name: reconcile-screen
description: Judge whether one screen learned from a video is the same product screen as one candidate from the crawl or the FlowSpec. Called only when the fixed rules scored the pair as ambiguous.
---

# reconcile-screen — is this the same screen?

You are shown two descriptions of a screen in one web product:

- **VIDEO SCREEN** — what a vision model read from a screen recording: its name, the route if the
  address bar was visible, the cues and fields it saw, and the actions taken on it (with the
  presenter's words when they spoke).
- **CANDIDATE** — a screen the product's own crawl or FlowSpec already knows: its title or name,
  its route, and its visible controls.

The fixed rules scored this pair as **ambiguous**: some signals agree and some do not. Decide
whether they are the **same screen** of the product (the same page or state a user would land on),
not merely screens that share a layout, a route prefix or a navigation bar.

Rules:

- A shared route alone does not make two screens the same: a modal or a wizard step can sit on the
  same address as the page behind it. Look for the controls and purpose that make a screen itself.
- Different roles (for example an admin view and a counsellor view) are different screens even
  when their titles look alike.
- If the evidence is thin or contradictory, say so with a **low confidence**. A confident wrong
  answer merges two screens that a tester needs to keep apart; an honest low confidence leaves the
  pair flagged for later, which is safe.
- Values written as `[REDACTED]` were removed on purpose. Never guess them.

Answer with `same_screen` (true or false), `confidence` from 0 to 1, and a one-sentence `reason`
that names the signal you relied on.

## VIDEO SCREEN

```json
{{VIDEO_SCREEN}}
```

## CANDIDATE

```json
{{CANDIDATE}}
```
