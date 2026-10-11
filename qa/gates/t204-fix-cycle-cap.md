# HUMAN_GATE: t204-team-login failed its last allowed fix cycle

**Asked:** 2026-10-11 by the maker, on checker B's FAIL
(`qa/verdicts/t204-team-login.r2.b.md`, master 0705d2d4, head 27a3a0a9). **Answered:** pending.

## What is blocked

`wave/t204-team-login` (team login, email and password) is at fix cycle 2, the last one the policy
allows. Checker B FAILed one criterion, AU20. 26 of 27 criteria are met. The branch is NOT merged.
Everything that needs login waits on it: the local deployment (T-203 remainder), the Test button and
report delivery wiring (T-201), the dev portal (T-198b) and Group 10 acceptance (T-206).

## What failed

Both defects from cycle 1 are fixed in the code (78 real-server rows; no concrete bind starts and then
refuses every request). A new defect of the same kind is in the shipped Docker path:

- `docker/compose.prod.yml:20` gives the app a default public origin of `https://localhost` when
  neither `AUTOTESTER_PUBLIC_ORIGIN` nor `AUTOTESTER_DOMAIN` is set.
- The app accepts that value (`src/autotester/auth/config.py:132`), because a loopback host is always
  admitted. So the rule "a wildcard bind needs an admitted public origin" is satisfied by a value
  nobody chose.
- Result: with a wrong allow-list the container starts and answers every request 403. Nothing is
  exposed, but AU20 says startup must raise.
- `docker/DEPLOY.md:131-133` and the comment at `docker/compose.prod.yml:16-17` say the app refuses to
  start in this case. That statement is false.

This affects the Docker deployment only. Running the app directly on this machine with an explicit
origin is not affected.

## The question

- **A. Allow one more fix cycle (cycle 3), scoped to this one defect.** The compose default becomes
  empty unless a domain is set, a loopback public origin is refused on a wildcard bind, and the two
  false sentences are corrected. Then two blind checkers re-check AU20 and the unit gets its full
  suite. The checker measured the corrected compose form already.
- **B. Merge as it is and file AU20's Docker gap as an open issue.** Login reaches master today, and
  the local (non-Docker) deployment can start. The Docker path stays wrong until the follow-up lands,
  and a criterion of the contract is knowingly unmet.

Maker's recommendation: A. The fix is a few lines in one compose file, one function and one guide, and
merging a security-class unit with a criterion its checker failed is the kind of shortcut this project
refuses.
