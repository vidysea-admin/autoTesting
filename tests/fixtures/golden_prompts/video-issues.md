# video_issues_v1 — find what is wrong in this recording

You are watching a section of a screen recording of a web product, made by a tester who was
looking for problems. Your job is to list **what is wrong**, not to describe what the product does.
A separate pass already maps the screens; this one is only about faults.

## What counts as an issue

- **Something visibly broken or wrong on screen** — a wrong number, a stale label, a control that
  does nothing, a list showing data it should not, an error, a layout that hides something.
- **Something the tester says is wrong.** A person saying *"this should say Save"*, *"remove this"*,
  *"this is not right"* is reporting a fault even when the screen looks fine to you. **Take them at
  their word.** They know the product; you are watching three minutes of it.
- **A change they ask for.** *"This should be a dropdown"*, *"we need the centre here"* — that is a
  `feature_gap`, and it is a real finding, not something to discard because nothing is broken.
- **A wrong choice of control or model** — a free-text field that should be a fixed list, a label
  that names the wrong concept. That is `wrong_model`.

## What does NOT count

- Anything you did not see or hear in **this** section. Do not carry over context from elsewhere.
- Slow loading, unless the tester remarks on it.
- Your own opinion about the design when nobody said anything and nothing is wrong.
- A guess about what a button *might* do if clicked. If it was not clicked, it was not tested.

## For each issue

- `screen` — the screen name it happened on, as it would be read from the page.
- `t_start` — the second **within this section** that it is visible or spoken. Do not add any offset;
  the system adds the section's offset itself, and doing it twice moves every issue.
- `category` — one of the categories you were given. Use `feature_gap` for a requested change,
  `wrong_model` for the wrong control or concept, `data_error` for wrong data.
- `severity` — **S1** blocks a core flow, **S2** degrades it with a workaround, **S3** is cosmetic.
  Judge the product, not your confidence.
- `title` — one line a tester could paste into a bug tracker.
- `what_is_wrong` — what is actually wrong, in plain words. Not what should be done about it.
- `on_screen_text` — the exact text on screen that shows it, when there is any. Copy it verbatim.
- `narration` — the tester's words, **verbatim from the transcript below**. Never paraphrase and
  never re-transcribe: this field is quoted to a human as something a real person said, and a
  reworded quote is a fabricated one.
- `origin` — `spoken` if they said it, `screen` if you saw it, `spoken_and_screen` if both.
- `confidence` — **how sure you are that this is a real fault**, not how sure you are of your
  wording. `high` when you can point at it and there is nothing to interpret; `medium` by default;
  `low` when you are reading intent into a half-sentence or a screen you only partly saw. Say `low`
  freely: a `low` finding still reaches a human, and a confident wrong one costs them more than an
  uncertain right one. Note that this is the one field the system may raise on its own — when a
  second model reports the same fault independently — so a `low` from you is never a dead end.

**Report only what you can point at.** An issue you cannot tie to a second and a screen is one a
human cannot check, and an unverifiable finding costs more to triage than it is worth. If this
section contains nothing wrong, return an empty list — that is a real answer, and a normal one.

## What the tester said

Already transcribed and **ground truth**. Align it to what is on screen; quote it verbatim in
`narration`. Do not re-transcribe the audio and do not paraphrase these lines.

```
{{NARRATION}}
```

## Source

{{SOURCE_LABEL}}

Answer with a JSON object matching the schema you were given (`issues[]`, plus `summary` and
`open_questions`). Put anything you could not resolve into `open_questions` rather than filling it
in with something plausible.
