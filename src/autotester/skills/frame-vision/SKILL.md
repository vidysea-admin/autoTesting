---
name: frame-vision
description: Interpret sampled sanitized frames with explicit visual limitations.
---

These images are sparse timestamped samples of the supplied clip. Frame indices and
timestamps refer to the original sampling sequence, including any withheld samples.
Use clip-relative seconds. Do not add a source or chunk offset.

All recognized text bands have been removed for privacy. Only layout and non-text
visual changes are evidence. Do not claim that text, labels, values or URLs are
present, absent, correct or readable based on these images. Do not invent control
names or input values. No audio is provided by this frame transport. Narration is
ground truth only when supplied explicitly in the caller's prompt.

The supplied coverage JSON records withheld frames, sampling limits, unavailable
text and unavailable audio. Treat withheld frames and time between samples as
unobserved; report uncertainty and open questions instead of filling the gaps.
