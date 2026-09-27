# Verdict — at590-doctor-optional-imports

**Date:** 2026-09-26
**Cycle checked:** 1
**Checker:** /checker (standing checker session, orchestrator plus 3 fresh-context lenses: rows, scope/placement, adversary; the decisive finding was reproduced by the orchestrator itself)
**Contract:** qa/contracts/core-invariants.md C11 (undeclared dependencies; "not a licence to skip declaring a real import"), C2, C3, C7; issue AT-590
**Branch / code commit:** at590-doctor-optional-imports · d77ffeb (manifest 7278c7a)

```
VERDICT: FAIL
SCOREBOARD: 1/2 criteria met (AT-590 false positives removed for TYPE_CHECKING and graceful try/except: met; C11 real imports still flagged: NOT met), 3/4 invariants hold (C2, C3, C7 hold; C1/C2 module one-job docstring inaccurate)
FAILURES:
- [C11] sev: medium · try_is_soft judges only the handler's exception TYPE, never its body, so a REQUIRED dependency written as `try: import x / except ImportError: raise` (or `raise RuntimeError('pip install x') from e`, or `sys.exit('need x')`) is classified soft, and doctor goes silent on an undeclared hard dependency. That is the exact "licence to skip declaring a real import" C11 forbids · treat an ImportError handler as soft only when it degrades gracefully (binds a fallback or continues); a body that raises or exits is hard; add a test per shape plus a sabotage row · issue: AT-619
- [module one-job rule] sev: low · ledger/render.py's module docstring ("Derive the living docs from code and the ledger") was not updated for its new, unrelated job: the AST import classifier consumed only by doctor.py. The placement is disclosed and forced by C2, but the docstring must state what the file does · update render.py's module docstring (or move the helper to a module with headroom whose docstring names it) · issue: none (fold into this unit)
CAPABILITY-COVERAGE: 4/4 rows reproduced (A: 4 red, B: 4 red, C: 2 red, D: 8 red, each on the named tests)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/doctor.py, ledger/render.py, tests/test_doctor.py; no UI surface)
ISSUES-WRITTEN: AT-619
EXECUTOR: maker builder (checker: claude-opus orchestrator + sonnet subagents)
EXPLANATION: The shapes the unit targets are right: TYPE_CHECKING bare and dotted, if/else keeping else hard, `if not TYPE_CHECKING` hard, except-tuples, except Exception and bare except hard, else/finally hard, and a hard import beside a soft one still flagged. SKIP is an option AT-590's expected text explicitly allows. But the soft rule is wider than "optional": it also exempts the idiomatic required-dependency guard, which weakens the guard the unit modifies.
```

## Reproduction (orchestrator; `soft_import_ids(ast.parse(src))` on d77ffeb)

```
pass        (except ImportError: foo = None)                        SOFT  (correct)
reraise     (except ImportError: raise)                             SOFT  (should be hard)
raise_from  (except ImportError as e: raise RuntimeError(..) from e) SOFT  (should be hard)
sys_exit    (except ImportError: sys.exit('need foo'))              SOFT  (should be hard)
```

The adversary lens reproduced this end-to-end with `check_dependencies_declared`, using an installed-but-undeclared package (colorama):
- plain `import colorama` is flagged `undeclared-dependency`;
- the same import inside `try/except ImportError: raise` produces 0 violations.

## What passed

- `tests/test_doctor.py` gave 32 passed. `-k doctor` gave 40 passed. `tests/test_cli_advice_resolves.py` gave 28 passed. ruff reported `All checks passed!` and doctor reported `doctor: clean`.
- Rows in own copies:
  - A, `is_type_checking` returns False: 4 red.
  - B, `try_is_soft` returns False: 4 red.
  - C, `try_is_soft` returns `bool(node.handlers)`: 2 red.
  - D, `if False:` in doctor: 8 red.
  - All fired on the named tests.
- 4c: exactly 4 paths changed, nothing was deleted. doctor.py is 277 lines, render.py 260 and test_doctor.py 285. `check_dependencies_declared` is exactly 50 lines, at the cap but not over.
- C3: render.py holds the only AST import classifier in src/.
- The full suite was started and then stopped by the checker once the FAIL was established, to free RAM. Cycle 2 re-runs it.

---

# Verdict — at590-doctor-optional-imports, cycle 2

**Date:** 2026-09-27
**Cycle checked:** 2
**Checker:** /checker (standing checker session: orchestrator plus 2 fresh-context lenses — rows/verify/scope, and adversarial handler shapes)
**Contract:** qa/contracts/core-invariants.md C11 (AT-590), C2, C3, C7; issue AT-619
**Branch / code commit:** wave/at590-doctor-optional-imports · 4135e98 (merge-master 7ae860f, manifest/flip 08374be)

```
VERDICT: PASS
SCOREBOARD: 2/2 criteria met (C11: optional imports are soft and undeclared hard dependencies are flagged; AT-619: a handler that raises or exits makes the import hard), 3/3 invariants hold (C2: render.py exactly 300, where doctor's cap is `> 300`, and no function over 50; C3: one classifier, in render.py; C7: 5/5 rows kill)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 rows reproduced in own copies (A: 4 red, B: 4 red, C: the 2 named too-broad tests red, plus 3 AT-619 params because the edit also bypasses _handler_exits, D: 8 red, E: exactly the 3 new reraise/raise_from/sys_exit params red)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/ledger/render.py, tests/test_doctor.py; no UI surface)
ISSUES-WRITTEN: AT-621 (low, os._exit and aliased sys.exit still soft; outside AT-619's named scope)
EXECUTOR: maker builder (checker: claude-opus orchestrator + subagents)
EXPLANATION: Every shape AT-619's expected clause names is now HARD: raise, raise X from e, sys.exit, exit() and quit(), plus raise SystemExit, log-then-raise, and the tuple and Exception handlers that re-raise. The graceful shapes stay SOFT: pass, a bound fallback, warn plus a fallback, return None, and a nested def that raises. The cycle-1 low FAIL line is closed, because render.py's module docstring now names soft_import_ids and its job.
```

**Re-ran:**
- `uv run ruff check src tests scripts`: clean.
- `uv run autotester doctor`: clean.
- `tests/test_doctor.py`: 35 passed.
- `-k doctor`: 43 passed.
- Full `uv run pytest`: 1954 passed, 1 failed (AT-518 `test_flake_probe_real_process…grandchild`, which also fails on master), 6 skipped, 32 xfailed (13m09s).
- Diff scope `7ae860f..08374be`: exactly render.py, test_doctor.py and the manifest, additive only.

**Adversarial notes, not failures:**
- `os._exit(1)` and `import sys as s; s.exit()` in the handler are still classified SOFT. I reproduced this end to end with colorama: 0 doctor violations. These are rare idioms outside AT-619's named scope; filed as AT-621 (low).
- `if STRICT: raise / else: x = None`, and a re-raise that an outer `except Exception` swallows, are classified HARD. That errs on the safe side (a false positive), so it is not a finding.
