# t197-video-pointers seat B adversarial results (head 3d0be650, fake provider, no network, no model call)

Run: `uv run --project <worktree> --directory <worktree> pytest <this dir>/test_b_adv.py test_b_adv2.py -p no:xdist -o addopts= -s`
(scripts need the worktree path D:/autoTesting/.worktrees/t197-video-pointers and real ffmpeg; env key is a fake).

## Approval gate (exit 3, provider.calls == 0, no reviews/ dir created) - all held
other project, other provider id, target case/space variants, kinds CRAWL/LIVE_CASE/ADVERSARIAL/READ, unsigned,
expired, unparsable expiry, max_actions 1 and 0 against a multi-call plan; tampered rows (widened max_actions with id and
signature kept, signature dropped, id dropped, retargeted, kind swapped) and a row signed with another key.
Cached review: approvals emptied, rerun -> exit 3 and no new call. Dry-run: exit 0, zero calls, directory snapshot
(names, mtime, size) identical before and after. Dry-run with bad pointers: exit 2.
## Approval is a ceiling per run, not consumed
approval max_actions=1 (plan = 1 call): three `--refresh` runs made 3 calls, all exit 0.
## Spend cap
`--max-cost` 1e-9 -> partial, 1 call. 0 and -0.0 -> exit 1 (failed review, 0 calls). -1 -> exit 2 (click min). `nan` and `inf` ->
exit 0, status ok, ALL planned calls (2) made: nan is accepted by `min=0.0` and `cost >= nan` is always False.
## Pointers
2:10 (== duration) exit 2; 2:09 ok; -0:10, 0:10-0:10, 0:10-2:11, 999999999999:00, a/b/c/d (4 free), `|` all exit 2, calls 0.
NUL byte line exit 2. Directory / non-UTF8 / missing pointer file exit 1, calls 0. Audio-only source exit 4, also when the pointer file is bad.
3,000,000-char single free pointer: exit 0, one call with a 3,002,185-char prompt. 60,000 timed lines: 46 s, 3 calls, ~1 MB prompts.
Slug `../../evil` with --dry-run: exit 1, nothing created outside the root.
Full-width digits `１:００` parse as 1:00 (exit 0).
## Redaction
No-op derivative (copy of the original swapped in for redact_video): refused, exit 3, 0 calls, message names window 55-75s.
LEFT ON DISK: projects/demo/reviews/rv_b6a6cec6d7ad/redacted.mp4 (a full copy of the recording).
Real redaction run: every path handed to the provider is a .png under reviews/<rid>/; no frame time in either window;
the source path is not in any prompt; work dir keeps redacted.mp4 next to the frames.
`git check-ignore -v projects/demo/reviews/rv_x/redacted.mp4 .../frames/1.png .../rv_x.json` -> exit 1 (none ignored);
.gitignore ignores the sibling projects/*/sources/*/frames/ and recording.*.
Tail window 2:00-2:10 on a 130 s 1 fps clip: exit 3 (cannot read the copy at 129.9s); on a 25 fps clip exit 0.
## Secrets (declared and undeclared .env key; canary in pointer note, free pointer, transcript segment, provider error, reply item)
canary absent from every file under reviews/, stdout, stderr, caplog (DEBUG), and from all prompts. base64/hex/reversed/percent spellings
in a note: exit 3, 0 calls, raw canary not echoed. `repr(SecretStore)` shows keys only; `scrub_values()` returns the raw mapping by design.
## Determinism
two fresh roots, same inputs, 1.1 s apart: same id, every key equal except `created_at`.
