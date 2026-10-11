# HUMAN_GATE: AU20 own-origin check on a wildcard bind (t204-team-login)

**Asked:** 2026-10-11 by the maker, on checker A's HUMAN_GATE-REQUEST
(`qa/verdicts/t204-team-login.r1.a.md`, head 6ea9b688). **Answered:** 2026-10-11 by Umesh, option A
(D-082): the app gets `AUTOTESTER_PUBLIC_ORIGIN` and startup raises on a wildcard bind unless that
origin is admitted. Folded into fix cycle 2 as an owner-authorised change.

## What is blocked

`wave/t204-team-login` fix cycle 1 (6ea9b688) repaired all four failed items. Checker A found three
MET and ruled the fourth, AU20, **not met as written** for the way the product is shipped. A PASS is
not possible until this is answered. The branch is NOT merged.

## The contract sentence

AU20: "With `AUTOTESTER_HOSTED=1` at least one of `AUTOTESTER_ALLOWED_HOSTS` /
`AUTOTESTER_ALLOWED_ORIGINS` must be set, and the server's own origin must be an allowed one;
otherwise startup raises."

## What the code does (checker A's matrix, 9 binds by 7 allow-lists, `au20-matrix.txt`)

- A loopback bind always starts.
- A concrete bind (for example `10.0.0.5:8443`) starts only when its host, host:port or origin is in
  the list; otherwise startup raises.
- A wildcard bind (`0.0.0.0`, `::`) starts with any non-empty list, including a list that does not
  name the server. `docker/entrypoint.sh` starts the app with `--host 0.0.0.0 --port 8000`, and
  `docker/compose.prod.yml:55` gives `AUTOTESTER_DOMAIN` to the proxy service only, so the app has no
  way to know its public origin.

The effect is fail-closed: with a wrong list every request gets 403 and nothing is exposed. But
startup does not raise, which is what the sentence requires.

## The question

- **A. Give the app its public origin.** Pass `AUTOTESTER_DOMAIN`, or a new
  `AUTOTESTER_PUBLIC_ORIGIN`, to the app container, and make startup raise unless that origin is in
  the allow-list. The interim no-domain flow (`docker/DEPLOY.md:122`, reached by IP) needs its own
  value. This is one more fix cycle on T-204 (cycle 2, the last allowed) and one new setting.
- **B. Amend AU20** so the own-origin check applies to a concrete bind only, and a wildcard bind needs
  a non-empty list. This weakens a startup safety line in the contract; the checker folds it in, and
  T-204 can then be judged on the code as it is.

- **C. A middle rule (checker B's option).** Keep no new setting. On a wildcard bind, require at least
  one non-loopback entry in `AUTOTESTER_ALLOWED_HOSTS` or one `AUTOTESTER_ALLOWED_ORIGINS` netloc.
  This catches an empty or loopback-only list at startup but not a list that names the wrong host.
  It also needs an AU20 amendment.

## Separate from this gate (added 2026-10-11)

Checker B (`qa/verdicts/t204-team-login.r1.b.md`) FAILed AU20 on a defect that does not depend on
this answer: for a concrete bind, `_check_own_origin` accepts a bare host although the Host check
(AU19) matches host:port, so `--host 10.0.0.5 --port 8443` with `AUTOTESTER_ALLOWED_HOSTS=10.0.0.5`
starts and then answers every request 403. Fix cycle 2 (the last allowed) repairs that now and leaves
the wildcard rule as it is. If the answer here is A or C, that is one more change after cycle 2, made
on your decision.

Maker's recommendation: A. It keeps the contract as written, and a wrong allow-list then fails at
startup with a readable message, not as a 403 on every page that the operator has to diagnose. For
the interim run on this machine the value is simply `http://localhost:<port>` or the machine's LAN
address.
