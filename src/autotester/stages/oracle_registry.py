"""The oracle registry: every G11 oracle by module name, built or not (MP15).

One job: map each `OracleName` to `autotester.stages.oracle_<name>`, import it by name with
`importlib`, run the selected ones and report one `OracleStatus` per oracle -- `ran`, `not built`
(the module is absent), `not run` (built, not selected) or `errored` (it exists but cannot be
imported, has no `run`, raised, or returned something other than `MultiRoleFinding`s). Every
`OracleName` is always in the summary, so an oracle that nobody has written yet is visible instead
of silently missing. The names are listed up front by the enum, so an oracle unit adds its module
and never edits this file. The interface an oracle implements is documented in
`schema/oracle_context.py`.

A failure is reported by exception type only: an oracle may be holding a probed page, and the
message of its error must not reach a summary, a log or a prompt (MPI1).
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable
from types import ModuleType

from autotester.schema.multi_role_enums import OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import (
    OracleContext,
    OracleRunSummary,
    OracleState,
    OracleStatus,
)

MODULE_PREFIX = "autotester.stages.oracle_"
Importer = Callable[[str], ModuleType]


def module_name(oracle: OracleName) -> str:
    """The stage module an oracle lives in, e.g. `autotester.stages.oracle_tenant`."""
    return f"{MODULE_PREFIX}{oracle.value}"


def _status(oracle: OracleName, state: OracleState, reason: str | None = None,
            count: int = 0) -> OracleStatus:
    return OracleStatus(oracle=oracle, module=module_name(oracle), state=state, reason=reason,
                        finding_count=count)


def _load(oracle: OracleName, importer: Importer) -> tuple[Callable | None, OracleStatus | None]:
    """The oracle's `run` callable, or the status that explains why there is none."""
    name = module_name(oracle)
    try:
        module = importer(name)
    except ModuleNotFoundError as exc:
        if exc.name == name:
            return None, _status(oracle, OracleState.NOT_BUILT)
        return None, _status(oracle, OracleState.ERRORED, f"import needs {exc.name}")
    except Exception as exc:
        return None, _status(oracle, OracleState.ERRORED, f"import failed: {type(exc).__name__}")
    run = getattr(module, "run", None)
    if not callable(run):
        return None, _status(oracle, OracleState.ERRORED, "module has no run(context)")
    return run, None


def _execute(oracle: OracleName, run: Callable, context: OracleContext,
             ) -> tuple[OracleStatus, list[MultiRoleFinding]]:
    try:
        found = run(context)
    except Exception as exc:
        return _status(oracle, OracleState.ERRORED, type(exc).__name__), []
    if not isinstance(found, list) or not all(isinstance(f, MultiRoleFinding) for f in found):
        return _status(oracle, OracleState.ERRORED, "run did not return list[MultiRoleFinding]"), []
    return _status(oracle, OracleState.RAN, count=len(found)), found


def run_oracles(context: OracleContext, selected: Iterable[OracleName] = (),
                importer: Importer = importlib.import_module,
                ) -> tuple[OracleRunSummary, list[MultiRoleFinding]]:
    """Run the selected oracles in enum order; report every oracle, built or not."""
    chosen = set(selected)
    statuses: list[OracleStatus] = []
    findings: list[MultiRoleFinding] = []
    for oracle in OracleName:
        run, problem = _load(oracle, importer)
        if problem is not None:
            statuses.append(problem)
        elif oracle not in chosen:
            statuses.append(_status(oracle, OracleState.NOT_RUN))
        else:
            status, found = _execute(oracle, run, context)
            statuses.append(status)
            findings.extend(found)
    return OracleRunSummary(statuses=statuses), findings


def oracle_statuses(importer: Importer = importlib.import_module) -> OracleRunSummary:
    """What is built right now, without running anything."""
    empty = OracleContext(project_slug="registry", run_dir=".", scenario_id="registry")
    return run_oracles(empty, (), importer)[0]
