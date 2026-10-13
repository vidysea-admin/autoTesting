"""Authorization: the central route policy and (T-204) accounts, groups and sessions.

Team login (T-204, D-072): accounts, IAM-style groups, server-side sessions, project scope.
Pure storage and decision logic over one SQLite file (`auth_db_path`); it never imports
`ui/`. The HTTP gate lives in `ui/auth_middleware.py`."""
