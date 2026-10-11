Evidence for the t199b-bug-loop-run check (cycle 0). Everything ran in a git-archive copy of d196c26e on C: (autotester.__file__ inside the copy).
- tb3.py / tb3-probe-output.txt: coordinator's own TB3 inputs (raw-only, replayed, unevidenced PASS, uncited FAIL, missing case/criterion, mixed, empty, corrupt rubric, run dir problems).
- tb4.py / tb4k.py and outputs: coordinator's own TB4 inputs, and the replay-after-edit reproduction (finding P-T1).
- falsify-tb3-red.txt, falsify-tb4-red.txt: coordinator's two falsifications (red output; green-before 8 passed each).
- affected.txt: 21 affected test files, 537 passed 3 skipped.
- trial-merge.txt: trial merge into current master.
- probeA/ (store, TB6, backward compat, schema ripple, TB6 falsification) and probeB/ (TB9, TB10, TB11, TB13, live-client, four falsifications): sub-checker scripts and outputs.
