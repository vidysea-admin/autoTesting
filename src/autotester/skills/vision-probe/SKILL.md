---
name: vision-probe
description: Read neutral visual geometry for a bounded capability check.
---

Inspect the two actual attached images in attachment order. Each image contains a
large colored shape on its left and another on its right, against a white background.
For each image report left_shape, left_color, right_shape and right_color.
Shapes are circle, square or triangle; colors are red, blue, green or yellow.
Ignore the bottom text band, which has been masked for privacy.

Use the pixels themselves. Filenames, the prompt and any text provide no answers.
Do not infer missing images or guess from earlier responses. Return the requested
structured JSON object with exactly two entries in images.
