# mr1.a falsification (one throwaway copy per row, head df5d6f5b, PYTHONPATH at the copy, autotester.__file__ printed from inside each copy)
| Row | edit (one hunk, one file) | named check | before -> after |
|---|---|---|---|
| F1 review registration | cli_video.py: `app.command("review", cls=ReviewCommand)(review_cmd)` -> `pass` | tests/test_cli_video_review.py | 20 passed -> 19 failed, 1 passed (fz-f1-before/after.txt) |
| F2 intake registration | cli_video.py: `register_intake_commands(app)` -> `pass` | tests/test_cli_intake.py | 8 passed -> 7 failed, 1 passed (fz-f2-*) |
| F3 site count | tests/test_cli_advice_resolves.py `EXPECTED_SITE_COUNT = 25` -> 24 | ::test_no_advice_site_can_vanish_unnoticed | 1 passed -> 1 failed on the count assertion (line 215) (fz-f3-*) |
| F4 duplicate name | video_review_render.py `def render_review_html(` -> `def render_html(` | `autotester doctor` | clean -> `duplicate-concept: video_review_render.py:60 'render_html' also defined in stages/unified_report_render.py`, 1 violation (fz-f4-*) |
Note: the first F4 doctor invocation in falsify.sh used `-m autotester` (no __main__) and printed nothing useful; the F4 pair was re-run via `from autotester.cli import app` in the same copy (copy edited, run, restored by sed, run again clean).
