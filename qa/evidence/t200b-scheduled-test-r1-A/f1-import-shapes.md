# F1 - TS6 scheduler-side import guard: import-shape probe (read-only sub-checker)

autotester.__file__ (both runs): C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\236a59b4-e0ec-4b2d-b22e-73d3059dd7f6\scratchpad\f1-copy\src\autotester\__init__.py
(falsification run: ...\scratchpad\f1-copy2\src\autotester\__init__.py)
Copy = worktree src/ tests/ scripts/ pyproject.toml (scripts/ needed: tests/conftest.py imports regression_proof). Python = worktree .venv, PYTHONPATH=<copy>/src;<copy>/scripts.

## 1 Baseline
`python -m pytest -p no:xdist -o addopts= <copy>/tests/test_schedule_tick.py` -> 20 passed (7.28s). Real tree clean.

## 2 Shapes (patched={module: source + leak}; each generic shape tried on all 5 SCHEDULER_SIDE modules, identical result on all 5)
| Shape | Result |
|---|---|
| import autotester.browser.session / `as s` / from autotester.browser import session as s | DETECTED |
| from ...session import BrowserSession as B / from ...session import * | DETECTED |
| from autotester.stages import explore / import stages.agent_loop / stages.execute as e / from autotester import cli | DETECTED |
| inside try/except ImportError, if TYPE_CHECKING, if sys.platform, nested function, class method | DETECTED (ast.walk, any depth; TYPE_CHECKING is a conservative false positive) |
| relative: from .explore import x, from . import explore, from ..browser import session, from ..browser.session import BrowserSession | DETECTED |
| importlib.import_module(...), `import importlib as il; il.import_module`, __import__('a'+'b'), builtins.__import__, importlib.__import__, __import__ inside lambda | DETECTED (any call named import_module/__import__) |
| from autotester.stages import * (package star) | MISSED - harmless: stages/__init__.py is docstring only, no __all__, star loads no submodule |
| from autotester import stages ; from .. import browser | MISSED - harmless: package __init__ only (and __init__ files are walked anyway) |
| from importlib import import_module as im; im('..') | MISSED |
| imp = __import__; imp('..') | MISSED |
| getattr(importlib,'import_module')('..') | MISSED |
| spec_from_file_location + exec_module ; importlib.util.find_spec | MISSED (find_spec does not import) |
| exec('import ...') ; eval("__import__(..)") | MISSED |
| runpy.run_module ; pkgutil.resolve_name | MISSED |
| sys.modules['...'] | MISSED (lookup, not an import) |
| Transitive: leak planted in explore_consent, core.localtime, core.consent, schema.schedule, schema.project, store.project_store, store.filestore | DETECTED |
| Package __init__ re-export: autotester.core, .schema, .store, .stages, .browser, .ui | DETECTED |
| browser.secrets importing session / stages.explore | DETECTED |
| Allow-listed ui.env_editor importing session / stages.execute | DETECTED (allow-listed modules are still walked; their own deps checked) |
| Allow-listed modules (explore_consent, ui.env_editor) using the aliased/exec dynamic forms above | MISSED (same dynamic gap) |
| schedule_gate `from browser.secrets import SecretStore as BrowserSession` | MISSED - not a bypass: guard reads a.name (SecretStore), not asname; the real direction (`BrowserSession as B`) is DETECTED |
| scheduler `from browser.secrets import BrowserSession` | DETECTED (BANNED_NAMES) |

## 3 Judgement of MISSED
- Harmless / runtime imports nothing: package star, `from autotester import stages`, `from .. import browser`, sys.modules lookup, find_spec, reverse-alias name.
- Deliberately obfuscated, would import at runtime: `import_module as im`, `imp=__import__`, getattr(...), exec/eval, runpy, pkgutil.resolve_name, spec_from_file_location+exec_module. None is an accidental slip; the single plausible accident (aliasing import_module) is the only one worth hardening (flag Name/Attribute `import_module` imports, or any `exec`/`eval`/`runpy`/`resolve_name`).
- Static-only limit (documented in docstring): root autotester/__init__ imports the CLI so runtime sys.modules always has the browser.

## 4 Falsification (f1-copy2, one test: test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively)
- BEFORE: 1 passed
- scheduler.py += `from autotester.stages import explore  # noqa` -> 1 failed: `AssertionError: assert ['autotester....emental', ...] == []  Left contains 77 more items, first extra item: 'autotester.stages.scheduler -> autotester.stages.explore'`
- schedule_gate.py += `import autotester.browser.session` -> 1 failed: `Left contains 11 more items, first extra item: 'autotester.stages.schedule_gate -> autotester.browser.session'`
- schedule_tick.py += `import autotester.browser.session` -> 1 failed: `first extra item: 'autotester.stages.schedule_tick -> autotester.browser.session'`
- files restored -> 1 passed.

Scripts: scratchpad/f1_shapes.py, output f1_out.txt (deleted with scratchpad copies not needed).
