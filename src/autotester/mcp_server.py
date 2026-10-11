"""AutoTester as a local MCP server (stdio): run tests, get report, get catalog.

One job: expose the three `run_ops` functions the CLI already calls as MCP tools -- no stage is
re-implemented here (CM4). `run_tests` goes through the same `RunApproval` gate as every other
entry point and can neither grant nor bypass one. Outputs are the CM2 `RunReport` / the
`Catalog`, already scrubbed. Local stdio only; a networked transport needs its own decision.
"""

from __future__ import annotations

import logging
from typing import Annotated

from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.server.mcpserver import MCPServer
from mcp.shared.exceptions import MCPError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, CallToolResult, TextContent
from pydantic import ValidationError

from autotester import run_ops
from autotester.schema.catalog import Catalog
from autotester.schema.cli_output import ExitCode, RunReport


class _SDKLogFilter(logging.Filter):
    """Mask SDK diagnostics before any downstream handler formats a traceback."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = run_ops._redactor("mcp").scrub(record.getMessage())
        except Exception:
            message = "SDK diagnostic withheld: credential masking unavailable."
        record.msg, record.args = message, ()
        record.exc_info = record.exc_text = record.stack_info = None
        return True


def _sdk_failure() -> CallToolResult:
    """SDK error text has lost its exception type: do not guess or reflect inputs."""
    report = RunReport(project="[unavailable]", status="internal_error",
                       exit_code=int(ExitCode.INTERNAL), message="SDK tool invocation failed.")
    return CallToolResult(content=[TextContent(type="text", text=report.model_dump_json())],
                          structured_content=report.model_dump(mode="json"), is_error=True)


async def _safe_sdk_boundary(ctx: ServerRequestContext, call_next: CallNext) -> HandlerResult:
    """Keep SDK validation/handshake intact; seal errors before wire serialization."""
    try:
        result = await call_next(ctx)
    except MCPError as exc:
        raise MCPError(code=exc.code, message="SDK request refused.") from None
    except ValidationError:
        raise MCPError(code=INVALID_PARAMS, message="Invalid request parameters.") from None
    except Exception:
        raise MCPError(code=INTERNAL_ERROR, message="SDK request failed.") from None
    if ctx.method != "tools/call" or not isinstance(result, dict) or not result.get("isError"):
        return result
    try:
        RunReport.model_validate(result.get("structuredContent"))
    except ValidationError:
        safe = _sdk_failure().model_dump(mode="json", by_alias=True, exclude_none=True)
        return {**result, **safe}
    return result


for _name in ("mcp.server.mcpserver.server", "mcp.server.runner",
              "mcp.shared.jsonrpc_dispatcher", "mcp.shared.dispatcher"):
    _logger = logging.getLogger(_name)
    if not any(f.name == "autotester-sdk-mask" for f in _logger.filters):
        _logger.addFilter(_SDKLogFilter("autotester-sdk-mask"))

server = MCPServer("autotester", instructions=(
    "Run a project's regression suite, read the stored report, or read what the project can "
    "run. A run needs a human-granted (or credential-derived) approval; this server cannot "
    "grant one. exit_code in the result follows the documented CLI table."))
server.middleware.append(_safe_sdk_boundary)


@server.tool(name="run_tests")
def tool_run_tests(project: str, dry_run: bool = False) -> RunReport:
    """Run the project's cases (or only list them with dry_run) and return the report."""
    return run_ops.perform_run(project, dry_run=dry_run, requested_by="mcp")


@server.tool(name="get_report")
def tool_get_report(project: str, run_id: str | None = None) -> RunReport:
    """The stored report of a run; the latest run when run_id is omitted."""
    return run_ops.get_report(project, run_id)


@server.tool(name="get_catalog")
def tool_get_catalog(project: str) -> Annotated[CallToolResult, Catalog]:
    """What the project can run now and what blocks the rest."""
    result = run_ops.get_catalog(project)
    # Explicit protocol errors bypass Catalog validation without changing success shape.
    return CallToolResult(content=[TextContent(type="text", text=result.model_dump_json())],
                          structured_content=result.model_dump(mode="json"),
                          is_error=isinstance(result, RunReport))


def serve() -> None:
    """Block serving stdio until the client disconnects. Loads the repo `.env` like the CLI."""
    from autotester.core.env import load_repo_env
    load_repo_env()
    server.run("stdio")


if __name__ == "__main__":
    serve()
