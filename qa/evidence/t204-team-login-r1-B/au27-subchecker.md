# AU27 audit-on-refusal sub-check (t204-team-login, r1 seat B, head 6ea9b688)

Probe: `qa/evidence/t204-team-login-r1-B/au27_probe.py` (scratch data root + auth dir, dummy passwords only).
Commands (cwd = a scratch dir; python = worktree .venv):

    PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 <wt>/.venv/Scripts/python.exe au27_probe.py <scratch>          # sections 1-6
    PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 <wt>/.venv/Scripts/python.exe au27_probe.py <scratch> extra    # extras

Audit file: `<AUTOTESTER_ROOT>/.work/audit.jsonl` (auth/audit.py `_append`: `json.dumps(..., ensure_ascii=False)`, default
separators, opened "a" in text mode; on Windows lines end CRLF). `record_action` writes `{ts, actor, target, action}`; the
middleware `finally` writes the AU22 request line `{ts, email, method, path template, status}` for every signed-in unsafe
request. So every refusal now yields TWO lines (AU27 line, then the request line carrying the status).

## Verdict
AU27 last bullet: MET on every refusal branch reachable. No defect fails the sentence. Low/informational notes at the end.

## 1. Per-branch table (every row: store unchanged = True)
### AU27 403 (actor mgr@team.test: group with users.manage+groups.manage+settings.manage+project.view/edit@all, not in Admin/CEO)
| branch | HTTP | actor / target / action |
|---|---|---|
| user groups: add dev to Admin/CEO | 403 | mgr / dev@team.test / user.groups.refused |
| user groups: remove admin2 from Admin/CEO | 403 | mgr / admin2@team.test / user.groups.refused |
| user groups: add tester to a group holding project.run@all (not held) | 403 | mgr / tester@team.test / user.groups.refused |
| user password: reset Admin account (canary pw) | 403 | mgr / admin2@team.test / user.password.refused |
| user disable / enable / delete an Admin account | 403 x3 | mgr / admin2@team.test / user.disable.refused, user.enable.refused, user.delete.refused |
| group create: tick users.manage / groups.manage / settings.manage / credentials.view / project.run@all (not held) | 403 x5 | mgr / G1..G5 / group.create.refused |
| group update: tick each of the same five | 403 x5 | mgr / Custom / group.update.refused |
| group update: edit Admin/CEO; add member to Admin/CEO; members into group with a perm not held | 403 x3 | mgr / Admin/CEO or Custom / group.update.refused |
| group delete Admin/CEO (confirm=yes) | 403 | mgr / Admin/CEO / group.delete.refused |

### Admin-driven 400 refusals
| branch | HTTP | actor / target / action |
|---|---|---|
| user password weak ("abc") | 400 | admin / dev@team.test / user.password.refused |
| user name 1000 chars | 400 | admin / dev@team.test / user.name.refused |
| user groups unknown group 9999 | 400 | admin / dev@team.test / user.groups.refused |
| group create dup name / empty name / unknown permission | 400 | admin / Custom, "", Gx / group.create.refused |
| group update dup name / unknown member | 400 | admin / Custom / group.update.refused |

### AU9 last-admin (sole admin acts), all 400
| branch | actor / target / action |
|---|---|
| disable self | admin / admin@team.test / user.disable.refused |
| delete self | admin / admin@team.test / user.delete.refused |
| remove self from Admin/CEO | admin / admin@team.test / user.groups.refused |
| untick users.manage on Admin/CEO | admin / Admin/CEO / group.update.refused |
| update Admin/CEO with empty member list | admin / Admin/CEO / group.update.refused |
| delete Admin/CEO group | admin / Admin/CEO / group.delete.refused |

Sample exact lines (every branch's lines are in the script output):

    {"ts": "...", "actor": "mgr@team.test", "target": "dev@team.test", "action": "user.groups.refused"}
    {"ts": "...", "email": "mgr@team.test", "method": "POST", "path": "/admin/users/{user_id}/{action}", "status": 403}
    {"ts": "...", "actor": "mgr@team.test", "target": "G4", "action": "group.create.refused"}
    {"ts": "...", "actor": "admin@team.test", "target": "Admin/CEO", "action": "group.delete.refused"}

All five user actions with a refusal path (groups, disable, enable, delete, password) plus `name` (400) have a refusal row.
`name` by a non-admin on an Admin account is not refused (set_display_name takes no actor): accepted and audited as `user.name`, not an AU27 case.

## 2. Canary (CanaryPw-r1b-9f3)
Used in the refused reset (403) and an accepted reset. grep over the whole audit file: canary False; every user password hash False;
both session cookie values False; "$argon", "pbkdf2", "scrypt$" False; form field names (group_id, member_id, display_name, "permission, "password) False
(the bare word "password" appears only inside the action name `user.password`; "group_id" only inside the path TEMPLATE `{group_id}`).
App log (root logger at DEBUG captured in-process, 5012 chars): canary False. Only two key-sets exist in the file:
{ts,actor,target,action} and {ts,email,method,path,status}.

## 3. Attacker-controlled target (create-group refusal via unknown permission; target = raw name[:80])
Every name produced exactly 2 physical `\n` lines, each json.loads()-parses, and `target == name[:80]` round-trips for: double quotes, backslash, CR, LF,
U+2028, U+2029, U+0085, NUL, non-BMP, `x\n{"actor":"admin@team.test","action":"user.promote"}`, the same with U+2028, the same with CRLF, a 100000-char name,
100000 NULs, 100000 quotes, 100000 backslashes. CR/LF/NUL are JSON-escaped, so an LF/CR forged record is impossible.
- Forgery: injected text stays INSIDE the target string; its quotes become `\"`, so no parseable second record exists.
- Residual (info): `ensure_ascii=False` leaves U+2028, U+2029, U+0085 raw, so a consumer using Python `str.splitlines()` sees an extra line. The fragments are
  NOT valid JSON (`{"ts"...,"target": "x` and `{\"actor\":...\",\"z", "action": "group.create.re`), so no record can be forged, only a naive reader confused.
  Repo code has no audit reader (grep). `for line in file` and `split("\n")` readers are unaffected.
- Oversize: 10000 non-BMP chars (120 KB body) -> line carries 80 chars. 100000 non-BMP (1.2 MB body) -> Starlette 400 "Field exceeded maximum size of 1024KB"
  before the handler: request line only, no AU27 line (framework parse refusal, not an AU27 case).
- Invalid UTF-8 (%ED%A0%80, %FF, multipart surrogate bytes) -> replacement chars, no 500, 2 lines.
- Max bytes of one line: target <= 80 chars, worst case a control char = 6 bytes (`\u0000`): measured 597 B (80 NULs). With a 254-char actor email
  (MAX_EMAIL_LENGTH) worst case ~840 B + CRLF. Other refusal targets are DB values (email <= 254, group name <= 64).

## 4. Flood
- Accepted action (admin group create): 250 B, 2 lines (action + request). One AU27 refusal: 254 B, 2 lines. Before the repair a refusal wrote only the middleware
  request line (128 B incl. CRLF), so the repair adds ~120 B per refusal (about 2x); the new line is a second line per refusal, the request line already existed.
- 1000 refusals (mgr, TestClient): 254,000 B, 2000 lines, 28 s (36/s; an earlier run took 125 s) = ~9 KiB/s, theoretical ~0.8 GB/day if sustained by a signed-in
  users.manage/groups.manage holder. No rotation or size cap in audit.py. Unauthenticated requests write nothing. Severity: low.

## 5. Route-policy refusals (stopped before any handler)
Tester POST /admin/groups, Developer POST /admin/users/<id>/disable, Tester POST /admin/groups/<id>/delete: HTTP 403, store unchanged, ONE line only:
`{"email": "tester@team.test", "method": "POST", "path": "/admin/groups", "status": 403}` (actor, route, status; no target, no action name).
Unauthenticated POST: HTTP 401, no line at all (no principal; pre-existing AU22 behaviour, not AU27).
Ruling: AU27 says "Each refused attempt is audited under AU22 (status 403, with `{actor, target, action}`)". It sits under AU27's two rules: granting what the caller does not hold,
and the admin-only set, aimed at "a users.manage, groups.manage or settings.manage holder who is not in Admin/CEO". A route-policy 403 for an account that lacks the key is
AU13/AU14 (route policy), not an escalation attempt, so it is outside the AU27 sentence; the AU22 request line (who, template, 403) covers it. If a reader insists on
{actor,target,action} there, it is not met -- an interpretation call, not a code defect.

## 6. Missing/invalid targets
user 99999 (admin and mgr), group 99999 update, group 99999 delete, unknown action `promote` on an existing user: HTTP 404, store unchanged, request line only
(404 is an HTTPException outside `_REFUSED`, so no AU27 line), no 500. Non-integer group id list -> HTTP 400 (`_ints`), request line only. Group delete without confirm -> 200
confirm page, no refusal. No crashes (no 500) anywhere.

## Notes (none fails AU27)
1. The AU27 line has no status/path; "status 403" lives on the adjacent request line (two records correlated by ts/actor, no shared id). Together the sentence holds.
2. Refusal flood doubles audit bytes per refusal (low); no rotation.
3. U+2028/2029/0085 raw in the file (naive splitlines readers only; cannot forge a record).
4. A disk error in `_audit_refusal` would turn a refusal into a 500 (store still unchanged); not triggered.
