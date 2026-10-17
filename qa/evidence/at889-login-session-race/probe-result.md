# AT-889 checker probe (cycle 0)
Probe (throwaway copy outside the worktree; source in probe_wrong_login_masked.py.txt): login case =
NAVIGATE /signin, FILL identifier (present), CLICK submit (app lands on a non-login path), FILL password (absent there).
- fix 05595c71 `_live_session_midcase`: `STATUS completed | frontier empty` (assert LOGIN_FAILED fails)
- base 69ebfae7 explore.py, same probe: `STATUS login_failed | login case did not complete` (passes)
Cause: explore.py:109-111 accepts ANY failing FILL step, even after the case's own CLICK/submit moved the page.
Falsification floor (copy, base explore.py): both new tests red on base (2 failed, 5 passed), green on fix (31 passed in the 3 login files).
