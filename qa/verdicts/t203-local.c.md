# t203-local checker note (HO41 follow-up)

Cycle checked: 2
Head checked: merged master after T-204 (login gate on master)

| HO | Verdict | Evidence |
|---|---|---|
| HO41 | PASS | `tests/test_windows_host.py::test_unauthenticated_project_route_is_refused` un-skipped and run with the login gate ON (`gate_on` harness): unsigned-in GET / answers 401 or 302. Launcher test confirms it never sets the auth-disabled switch. 9 passed in that file. |

Adjusted with the un-skip, because T-204 AU16 now gates `/healthz` detail: the in-process healthz test and the loopback smoke test assert that an unsigned-in caller gets exactly `{"ok": true}`; the freshness fields need `settings.manage`.

HO39 and HO40 remain pending a real install (Get-Credential, scheduled task, kill-and-recheck); not run on this shared machine.
