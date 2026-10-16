import os, sys
os.environ.pop("AUTOTESTER_DATA_DIR", None); os.environ.pop("AUTOTESTER_AUTH_DIR", None); os.environ.pop("AUTOTESTER_ROOT", None)
from autotester.core.paths import ProjectPaths, repo_root, work_dir, team_path
from autotester.auth.db import auth_db_path
from autotester.ui.run_queue import _queue_file
r = repo_root(); p = ProjectPaths("pathlynks")
checks = {"dir": p.dir == r/"projects"/"pathlynks", "profile": p.profile_dir == r/"profiles"/"pathlynks",
 "queue": _queue_file() == r/".work"/"run_queue.json", "auth": auth_db_path() == r/".auth"/"auth.sqlite3",
 "team": team_path("a") == r/".work"/"team"/"a"}
os.environ["AUTOTESTER_DATA_DIR"] = str(r/"zz-data")
checks["set_dir"] = ProjectPaths("x").dir == (r/"zz-data").resolve()/"projects"/"x"
checks["set_env_file_repo"] = ProjectPaths("x").env_file == r/".env"
checks["explicit_root_wins"] = ProjectPaths("x", r/"q").dir == r/"q"/"projects"/"x"
print(checks); sys.exit(0 if all(checks.values()) else 1)
