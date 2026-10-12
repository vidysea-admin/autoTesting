# Run kinds through the real CLI (wrapped mock provider 'wm'), scratch project, scratch data root

Head 0dcbbfa5, worktree .worktrees/check-t197-r1-b; autotester.__file__ = D:utoTesting\.worktrees\check-t197-r1-b\srcutotester\__init__.py
Columns: rc | provider calls | frames the provider received | received frame inside the 60-90 s window | secret text in a prompt | derived media left | original copied | tmp (system temp) after | untracked-not-ignored paths

| kind | rc | calls | frames | in window | secret in prompt | media left | original copied | untracked (not ignored) |
|---|---|---|---|---|---|---|---|---|
| 1 success (redact 1:00-1:30, pointers) | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 2 no redaction windows | 0 | 2 | 23 | [] | True | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 3 --dry-run (redact+pointers) | 0 | 0 | 0 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 4a first run for refresh | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 4b --refresh over stored review | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 5 --max-cost stops midway | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 6 provider error midway (fails from call 2) | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 7 pointer file with errors | 2 | 0 | 0 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 8a killed mid-run (taskkill /F /T on the recorded pid, windows set) | 1 | 2 | 16 | [] | False | 17 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 8b run again after the kill (normal, no sleep) | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 8c killed mid-run (CTRL_BREAK_EVENT signal) | 3221225786 | 2 | 16 | [] | False | 17 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 8d run again after CTRL_BREAK kill | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 9a seed for status test | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 9b plain re-run (no --refresh) | 0 | 0 | 0 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 9c --refresh keeps human status | 0 | 2 | 16 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, projects/zzr1b/project.json |
| 5b --max-cost 0.05 / 0.02, WM_IN=20000 (midway stop) | 0 | 1 | 12 | [] | False | 0 | no | projects/zzr1b/approvals.jsonl, project.json (the scratch project's own files, not review output) |

In every row the only untracked-not-ignored paths are the scratch project's approvals.jsonl and project.json. reviews/ is ignored (`git status --porcelain --ignored` shows `!! projects/zzr1b/reviews/`).

## File tree before / after, per kind (projects/zzr1b/, system tmp scratch was empty before and after every kind)

### 1 success (redact 1:00-1:30, pointers)
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2120 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 2 no redaction windows
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_e88d99bb4482.json  (2034 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 3 --dry-run (redact+pointers)
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 4a first run for refresh
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2120 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 4b --refresh over stored review
- before: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2120 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2120 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 5 --max-cost stops midway
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2120 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 6 provider error midway (fails from call 2)
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (1876 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 7 pointer file with errors
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 8a killed mid-run (taskkill /F /T on the recorded pid, windows set)
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6/redacted.mp4  (97244 B); sources.jsonl  (355 B); reviews/<rid>/frames/*.png  (16 files)
- system tmp after: empty
- derived media found: 17

### 8b run again after the kill (normal, no sleep)
- before: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6/redacted.mp4  (97244 B); sources.jsonl  (355 B); reviews/<rid>/frames/*.png  (16 files)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2120 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 8c killed mid-run (CTRL_BREAK_EVENT signal)
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6/redacted.mp4  (97244 B); sources.jsonl  (355 B); reviews/<rid>/frames/*.png  (16 files)
- system tmp after: empty
- derived media found: 17

### 8d run again after CTRL_BREAK kill
- before: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6/redacted.mp4  (97244 B); sources.jsonl  (355 B); reviews/<rid>/frames/*.png  (16 files)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2120 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 9a seed for status test
- before: approvals.jsonl  (850 B); project.json  (537 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2120 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 9b plain re-run (no --refresh)
- before: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (1572 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (1572 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 9c --refresh keeps human status
- before: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (1572 B); sources.jsonl  (355 B)
- after: approvals.jsonl  (850 B); project.json  (537 B); reviews/rv_382f72c9b1c6.json  (2125 B); sources.jsonl  (355 B)
- system tmp after: empty
- derived media found: 0

### 5b --max-cost 0.05 and 0.02 (midway stop, WM_IN=20000)
- before: approvals.jsonl; project.json; sources.jsonl
- after: approvals.jsonl; project.json; reviews/rv_382f72c9b1c6.json (1830 B); sources.jsonl
- result: status partial, reason 'spend cap $0.02 reached', 1 provider call of 2, 12 frames, none inside 60-90 s, 0 media left, original not copied

## Human status
- 9a seed -> status set to confirmed on one item; 9b plain re-run: 0 calls, statuses ['confirmed', 'open']; 9c --refresh: 2 calls, statuses ['confirmed', 'open'] (human status preserved)
