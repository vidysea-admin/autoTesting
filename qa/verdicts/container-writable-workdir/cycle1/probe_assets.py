import os, sys, tempfile
d = tempfile.mkdtemp()
os.environ["AUTOTESTER_ROOT"] = d
from autotester.core.paths import RepoDocs, repo_root, work_dir
from autotester.ui.routes_live import package_root
from autotester.providers.base import load_skill_prompt
docs = RepoDocs()
print("root", repo_root() == __import__("pathlib").Path(d).resolve())
print("prompts_dir_exists", docs.prompts_dir.is_dir(), "under_root", str(docs.prompts_dir).startswith(str(repo_root())))
print("skills_dir_exists", docs.skills_dir.is_dir())
print("grade_skill_len", len(load_skill_prompt("grade")) > 0)
print("package_root_has_ui", (package_root() / "ui").is_dir())
print("work_dir_under_root", work_dir().parent == repo_root())
import autotester.browser.observe  # JS assets via __file__
print("observe_js_ok", True)
